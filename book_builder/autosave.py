import os
import json
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Callable, Any
from book_builder.models.book import BookProject
from book_builder.serializer import ProjectSerializer
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from core.logger import get_logger

logger = get_logger(__name__)

BACKUP_DIR = os.path.join("settings", "backup")

class AutosaveManager:
    """Manages background autosave timers and recovery session checkpoints."""
    _checkpoint_lock = threading.Lock()
    
    def __init__(self, 
                 get_active_project_cb: Callable[[], Optional[BookProject]], 
                 is_dirty_cb: Callable[[], bool],
                 clear_dirty_cb: Callable[[], None],
                 interval_sec: float = 300.0) -> None:
        self._get_project = get_active_project_cb
        self._is_dirty = is_dirty_cb
        self._clear_dirty = clear_dirty_cb
        self._interval = interval_sec
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._running = False
        self._event_bus = EventBus()

        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

    def start(self) -> None:
        """Starts the background autosave timer thread."""
        with self._lock:
            if not self._running:
                self._running = True
                self._schedule_next()
                logger.info(f"AutosaveManager: started loop (Interval: {self._interval}s)")

    def stop(self) -> None:
        """Stops the background autosave timer thread."""
        with self._lock:
            self._running = False
            if self._timer:
                self._timer.cancel()
                self._timer = None
            logger.info("AutosaveManager: stopped loop")

    def _schedule_next(self) -> None:
        if self._running:
            self._timer = threading.Timer(self._interval, self._run_autosave)
            self._timer.daemon = True
            self._timer.start()

    def _run_autosave(self) -> None:
        try:
            project = self._get_project()
            if project and self._is_dirty():
                logger.info(f"AutosaveManager: auto-saving checkpoint for '{project.name}'")
                self.create_checkpoint(project)
                self._clear_dirty()
                
                # Notify subscribers
                self._event_bus.publish(
                    Event("AUTOSAVE_COMPLETED", "AutosaveManager", {"project_id": str(project.id)})
                )
        except Exception as e:
            logger.error(f"AutosaveManager: error during autosave execution: {e}")
        finally:
            with self._lock:
                self._schedule_next()

    @classmethod
    def get_checkpoint_path(cls, project_id: Any) -> str:
        """Returns the local backup path for the project ID."""
        return os.path.join(BACKUP_DIR, f"recovery_{project_id}.json")

    @classmethod
    def create_checkpoint(cls, project: BookProject) -> None:
        """Writes project to settings backup recovery folder atomically."""
        with cls._checkpoint_lock:
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)
            path = cls.get_checkpoint_path(project.id)
            
            # Wrap project JSON with session metadata
            serialized = ProjectSerializer.serialize_project(project)
            checkpoint = {
                "project_id": str(project.id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": serialized
            }
            
            # Double-buffer write to prevent corruptions during app crashes
            temp_path = f"{path}.tmp"
            with open(temp_path, "w") as f:
                json.dump(checkpoint, f, indent=4)
            
            if os.path.exists(path):
                os.remove(path)
            os.rename(temp_path, path)
            logger.debug(f"AutosaveManager: checkpoint successfully written to '{path}'")

    @classmethod
    def load_checkpoint(cls, project_id: Any) -> Optional[BookProject]:
        """Loads recovery checkpoint model if it exists on disk."""
        with cls._checkpoint_lock:
            path = cls.get_checkpoint_path(project_id)
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        checkpoint = json.load(f)
                    data = checkpoint.get("data")
                    if data:
                        return ProjectSerializer.deserialize_project(data)
                except Exception as e:
                    logger.error(f"AutosaveManager: failed to load checkpoint from '{path}': {e}")
            return None

    @classmethod
    def clear_checkpoint(cls, project_id: Any) -> None:
        """Removes the checkpoint file from disk (e.g., on clean save or close)."""
        with cls._checkpoint_lock:
            path = cls.get_checkpoint_path(project_id)
            if os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"AutosaveManager: cleared recovery checkpoint for project '{project_id}'")
                except Exception as e:
                    logger.error(f"AutosaveManager: failed to delete checkpoint '{path}': {e}")
