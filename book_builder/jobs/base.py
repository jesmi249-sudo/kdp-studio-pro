import uuid
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Any

@dataclass
class ProgressEvent:
    """Carries task progress status details."""
    task_id: str
    progress: float # Value between 0.0 and 1.0
    message: str


class CancellationToken:
    """Thread-safe flag used to signal background task cancellation."""
    def __init__(self) -> None:
        self._is_cancelled = False
        self._lock = threading.Lock()

    def cancel(self) -> None:
        """Signals cancellation to listening tasks."""
        with self._lock:
            self._is_cancelled = True

    def is_cancelled(self) -> bool:
        """Returns True if task cancellation was requested."""
        with self._lock:
            return self._is_cancelled


class Task(ABC):
    """Abstract Base Class representing an asynchronous background task with priority weight."""
    def __init__(self, priority: int = 1) -> None:
        self.id: str = str(uuid.uuid4())
        self.priority: int = priority # Lower values indicate higher execution priority

    @abstractmethod
    def execute(self, progress_callback: Callable[[ProgressEvent], None], token: CancellationToken) -> Any:
        """Runs the background task logic. Must audit token.is_cancelled() frequently."""
        pass
