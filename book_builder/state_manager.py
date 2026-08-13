from typing import Optional, List, Dict, Any
from uuid import UUID
from book_builder.models.book import BookProject, BookMetadata
from book_builder.models.page import Page
from book_builder.models.state import ProjectState
from book_builder.commands.manager import CommandManager
from book_builder.commands.base import Command
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from book_builder.autosave import AutosaveManager
from book_builder.recent import RecentProjectsManager
from core.logger import get_logger

logger = get_logger(__name__)

class ProjectStateManager:
    """Manages active project session focus, undo/redo Command stacks, and selection dirty flags."""
    
    def __init__(self, autosave_interval_sec: float = 60.0) -> None:
        self.current_project: Optional[BookProject] = None
        self.project_state: Optional[ProjectState] = None
        self.command_manager = CommandManager()
        self.event_bus = EventBus()
        self.last_executed_command: Optional[Command] = None
        
        # Inject state callbacks into background AutosaveManager
        self.autosave_manager = AutosaveManager(
            get_active_project_cb=lambda: self.current_project,
            is_dirty_cb=self.is_dirty,
            clear_dirty_cb=self.clear_dirty,
            interval_sec=autosave_interval_sec
        )

    @property
    def active_project(self) -> Optional[BookProject]:
        """Returns the active book project model."""
        return self.current_project

    @active_project.setter
    def active_project(self, project: Optional[BookProject]) -> None:
        """Sets the active book project model."""
        if project:
            self.set_project(project)
        else:
            self.close_project()

    def set_project(self, project: BookProject) -> None:
        """Binds the project aggregate to the active session, launching recovery timers."""
        self.autosave_manager.stop()
        
        self.current_project = project
        self.project_state = ProjectState(
            project_id=project.id,
            is_dirty=False,
            active_page_index=0,
            selected_element_uuids=[],
            clipboard_content=None
        )
        
        # Reset undo histories
        self.command_manager.undo_stack.clear()
        self.command_manager.redo_stack.clear()
        self.last_executed_command = None
        
        # Register in recents config
        RecentProjectsManager.add_recent_project(project.id, project.name, project.book_type)
        
        # Start recovery dumps
        self.autosave_manager.start()
        
        self.event_bus.publish(
            Event("PROJECT_OPENED", "ProjectStateManager", {"project_id": str(project.id)})
        )

    def close_project(self) -> None:
        """Unbinds the active project, stopping autosaves and clearing memory caches."""
        if self.current_project:
            proj_id = self.current_project.id
            self.autosave_manager.stop()
            
            # Wipe disk checkpoints to indicate a clean session close
            self.autosave_manager.clear_checkpoint(proj_id)
            
            self.current_project = None
            self.project_state = None
            self.last_executed_command = None
            
            self.event_bus.publish(
                Event("PROJECT_CLOSED", "ProjectStateManager", {"project_id": str(proj_id)})
            )

    def is_dirty(self) -> bool:
        """Returns True if there are unsaved modifications."""
        return self.project_state.is_dirty if self.project_state else False

    def mark_dirty(self) -> None:
        """Sets the dirty flag and broadcasts the change."""
        if self.project_state and not self.project_state.is_dirty:
            self.project_state.is_dirty = True
            self.event_bus.publish(
                Event("DIRTY_STATE_CHANGED", "ProjectStateManager", {"is_dirty": True})
            )

    def clear_dirty(self) -> None:
        """Resets the dirty flag."""
        if self.project_state and self.project_state.is_dirty:
            self.project_state.is_dirty = False
            self.event_bus.publish(
                Event("DIRTY_STATE_CHANGED", "ProjectStateManager", {"is_dirty": False})
            )

    def execute_command(self, command: Command) -> bool:
        """Executes a command within the active state, marking it dirty."""
        if self.command_manager.execute(command):
            self.last_executed_command = command
            if self.project_state:
                self.project_state.undo_count = self.command_manager.undo_stack.size()
                self.project_state.redo_count = self.command_manager.redo_stack.size()
            self.mark_dirty()
            return True
        return False

    def undo(self) -> bool:
        """Undoes the last command, updating state flags."""
        undo_desc = ""
        if not self.command_manager.undo_stack.is_empty():
            undo_desc = self.command_manager.undo_stack._stack[-1].get_description()
            
        if self.command_manager.undo():
            if self.project_state:
                self.project_state.undo_count = self.command_manager.undo_stack.size()
                self.project_state.redo_count = self.command_manager.redo_stack.size()
            self.mark_dirty()
            
            self.event_bus.publish(
                Event("UndoExecuted", "ProjectStateManager", {"command_description": undo_desc})
            )
            return True
        return False

    def redo(self) -> bool:
        """Redoes the last command, updating state flags."""
        redo_desc = ""
        if not self.command_manager.redo_stack.is_empty():
            redo_desc = self.command_manager.redo_stack._stack[-1].get_description()

        if self.command_manager.redo():
            if self.project_state:
                self.project_state.undo_count = self.command_manager.undo_stack.size()
                self.project_state.redo_count = self.command_manager.redo_stack.size()
            self.mark_dirty()
            
            self.event_bus.publish(
                Event("RedoExecuted", "ProjectStateManager", {"command_description": redo_desc})
            )
            return True
        return False

    def set_active_page(self, index: int) -> None:
        """Sets the page selection index and broadcasts the focus shift."""
        if self.project_state:
            self.project_state.active_page_index = index
            self.event_bus.publish(
                Event("PAGE_SELECTION_CHANGED", "ProjectStateManager", {"active_page_index": index})
            )

    def get_active_page(self) -> Optional[Page]:
        """Returns the page model currently in focus."""
        if self.current_project and self.project_state:
            idx = self.project_state.active_page_index
            if 0 <= idx < len(self.current_project.pages):
                return self.current_project.pages[idx]
        return None

    def copy_to_clipboard(self, content: Dict[str, Any]) -> None:
        """Caches elements or properties inside the session clipboard."""
        if self.project_state:
            self.project_state.clipboard_content = content

    def paste_from_clipboard(self) -> Optional[Dict[str, Any]]:
        """Retrieves layout data from the session clipboard."""
        return self.project_state.clipboard_content if self.project_state else None
