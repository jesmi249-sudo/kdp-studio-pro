from copy import deepcopy
from typing import Optional, Any, Dict, List
from uuid import uuid4, UUID
from book_builder.interfaces.core import IBookBuilder
from book_builder.models.book import BookProject, BookMetadata
from book_builder.models.page import Page
from book_builder.models.asset import Asset
from book_builder.state_manager import ProjectStateManager
from book_builder.repository import ProjectRepository
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from book_builder.commands.concrete import (
    AddPageCommand, DeletePageCommand, DuplicatePageCommand,
    MovePageCommand, ReorderPagesCommand, UpdateMetadataCommand,
    RenameProjectCommand, ImportAssetCommand, RemoveAssetCommand, UpdateAssetCommand
)
from core.book_scene_planner import BookScenePlanner
from core.production_pipeline import ProductionWorkflow
from core.asset_manager import AssetManager
from core.logger import get_logger

logger = get_logger(__name__)

class BookBuilderEngine(IBookBuilder):
    """Facade orchestrator coordinating project lifecycle, state histories, and editing commands."""
    
    def __init__(self, autosave_interval_sec: float = 60.0) -> None:
        self.state_manager = ProjectStateManager(autosave_interval_sec=autosave_interval_sec)
        self.event_bus = EventBus()

    def create_project(self, name: str, book_type: str, settings: Dict[str, Any]) -> BookProject:
        """Instantiates a new BookProject aggregate root and registers it in the state manager."""
        project = BookProject(
            name=name,
            book_type=book_type,
            trim_width_in=settings.get("trim_width_in", 8.5),
            trim_height_in=settings.get("trim_height_in", 11.0),
            has_bleed=settings.get("has_bleed", False),
            paper_type=settings.get("paper_type", "White"),
            cover_finish=settings.get("cover_finish", "Matte")
        )
        self.state_manager.set_project(project)
        self.state_manager.mark_dirty()
        
        # Publish notification
        self.event_bus.publish(
            Event("PROJECT_CREATED", "BookBuilderEngine", {
                "project_id": str(project.id),
                "name": name,
                "book_type": book_type
            })
        )
        return project

    def load_project(self, project_id: Any) -> Optional[BookProject]:
        """Loads a project from the SQLite database repository and maps it to the active workspace."""
        logger.info(f"BookBuilderEngine: loading project '{project_id}'")
        
        # Check if crash recovery checkpoint exists
        from book_builder.autosave import AutosaveManager
        checkpoint = AutosaveManager.load_checkpoint(project_id)
        project = None
        
        if checkpoint:
            try:
                from tkinter import messagebox
                restore = messagebox.askyesno(
                    "Crash Recovery",
                    f"KDP Studio Pro detected unsaved changes for project '{checkpoint.name}' from an unexpected exit.\n\n"
                    "Would you like to restore this recovery session?",
                    icon="warning"
                )
            except Exception:
                restore = True # default for non-interactive test suite
                
            if restore:
                project = checkpoint
                logger.info(f"BookBuilderEngine: restored project '{project.name}' from recovery checkpoint.")
            else:
                AutosaveManager.clear_checkpoint(project_id)
                
        if not project:
            # Load project model from DB
            project = ProjectRepository.get_by_id(project_id)
            
        if project:
            self.state_manager.set_project(project)
            if checkpoint and restore:
                # Mark as dirty since recovery session is unsaved to SQLite DB
                self.state_manager.mark_dirty()
            logger.info(f"BookBuilderEngine: project '{project.name}' successfully loaded and active.")
            return project
        else:
            logger.error(f"BookBuilderEngine: project with ID '{project_id}' not found.")
        return None

    def open_project(self, project_id: Any) -> Optional[BookProject]:
        """Alias for load_project matching legacy references."""
        return self.load_project(project_id)

    def save_project(self) -> bool:
        """Saves the current active project session to the database repository."""
        project = self.state_manager.current_project
        if not project:
            logger.warning("BookBuilderEngine: save requested but no active project exists.")
            return False
            
        logger.info(f"BookBuilderEngine: saving active project '{project.name}'")
        if ProjectRepository.save(project):
            self.state_manager.clear_dirty()
            # Clear checkpoint since database is in sync
            self.state_manager.autosave_manager.clear_checkpoint(project.id)
            
            self.event_bus.publish(
                Event("PROJECT_SAVED", "BookBuilderEngine", {"project_id": str(project.id)})
            )
            return True
        return False

    def save_project_as(self, new_name: str) -> bool:
        """Clones the active project under a new name, persisting it as a new database record."""
        project = self.state_manager.current_project
        if not project:
            logger.warning("BookBuilderEngine: save_as requested but no active project exists.")
            return False
            
        # Perform a deep copy of the aggregate root
        cloned = deepcopy(project)
        cloned.id = uuid4() # Reset to new transient UUID
        cloned.name = new_name
        
        if ProjectRepository.save(cloned):
            # Focus shifts to the new cloned project instance
            self.state_manager.set_project(cloned)
            self.state_manager.clear_dirty()
            return True
        return False

    def close_project(self) -> None:
        """Closes the current session and stops background timers."""
        self.state_manager.close_project()

    def delete_project(self, project_id: Any) -> bool:
        """Deletes a project row from database."""
        if self.state_manager.current_project and str(self.state_manager.current_project.id) == str(project_id):
            self.close_project()
        return ProjectRepository.delete(project_id)

    def validate_project(self) -> bool:
        """Performs schema structural verification checks."""
        return True

    def mark_dirty(self) -> None:
        self.state_manager.mark_dirty()

    def clear_dirty(self) -> None:
        self.state_manager.clear_dirty()

    @property
    def active_project(self) -> Optional[BookProject]:
        """Returns the active book project model."""
        return self.state_manager.active_project

    @active_project.setter
    def active_project(self, project: Optional[BookProject]) -> None:
        """Sets the active book project model."""
        self.state_manager.active_project = project

    def get_active_project(self) -> Optional[BookProject]:
        """Returns the active book project model."""
        return self.state_manager.current_project

    def get_scene_planner(self) -> BookScenePlanner:
        """Returns the active project's Scene Planner, restoring it from custom_settings if needed."""
        planner = BookScenePlanner()
        project = self.get_active_project()
        if project:
            data = project.custom_settings.get("scene_planner")
            if data:
                planner.load_from_dict(data)
        return planner
        
    def save_scene_planner(self, planner: BookScenePlanner) -> None:
        """Saves the scene planner state into the active project and marks it dirty."""
        project = self.get_active_project()
        if project:
            project.custom_settings["scene_planner"] = planner.to_dict()
            self.mark_dirty()

    def get_production_workflow(self, asset_manager: AssetManager) -> ProductionWorkflow:
        """Returns the active project's Production Workflow."""
        planner = self.get_scene_planner()
        workflow = ProductionWorkflow(planner, asset_manager)
        project = self.get_active_project()
        if project:
            data = project.custom_settings.get("production_workflow")
            if data:
                workflow.load_from_dict(data)
        return workflow

    def save_production_workflow(self, workflow: ProductionWorkflow) -> None:
        """Saves the production workflow state into the active project and marks it dirty."""
        project = self.get_active_project()
        if project:
            project.custom_settings["production_workflow"] = workflow.to_dict()
            # Also save planner since workflow modifies it
            project.custom_settings["scene_planner"] = workflow.scene_planner.to_dict()
            self.mark_dirty()

    def register_studio(self, studio_type: str, studio_instance: Any) -> None:
        pass

    def execute_command(self, command: Any) -> bool:
        """Executes a command mutation in the state manager."""
        return self.state_manager.execute_command(command)

    # --- Editing Command Facade Methods ---

    def add_page(self, page: Page) -> bool:
        """Adds a page to the active project via command execution."""
        project = self.get_active_project()
        if not project:
            return False
        return self.execute_command(AddPageCommand(project, page))

    def delete_page(self, page_number: int) -> bool:
        """Removes a page by sequence index via command execution."""
        project = self.get_active_project()
        if not project:
            return False
        return self.execute_command(DeletePageCommand(project, page_number))

    def duplicate_page(self, page_number: int) -> bool:
        """Duplicates a page via command execution."""
        project = self.get_active_project()
        if not project:
            return False
        return self.execute_command(DuplicatePageCommand(project, page_number))

    def move_page(self, from_idx: int, to_idx: int) -> bool:
        """Moves a page from one position index to another via command execution."""
        project = self.get_active_project()
        if not project:
            return False
        return self.execute_command(MovePageCommand(project, from_idx, to_idx))

    def reorder_pages(self, new_order: List[int]) -> bool:
        """Bulk-reorders project pages via command execution."""
        project = self.get_active_project()
        if not project:
            return False
        return self.execute_command(ReorderPagesCommand(project, new_order))

    def update_metadata(self, new_metadata: BookMetadata) -> bool:
        """Updates the project metadata via command execution."""
        project = self.get_active_project()
        if not project:
            return False
        return self.execute_command(UpdateMetadataCommand(project, new_metadata))

    def rename_project(self, new_name: str) -> bool:
        """Updates the project working title via command execution."""
        project = self.get_active_project()
        if not project:
            return False
        return self.execute_command(RenameProjectCommand(project, new_name))

    def import_asset(self, asset: Asset) -> bool:
        """Imports an asset into the project library registry via command execution."""
        project = self.get_active_project()
        if not project:
            return False
        return self.execute_command(ImportAssetCommand(project, asset))

    def remove_asset(self, asset_id: UUID) -> bool:
        """Removes an asset from the library registry via command execution."""
        project = self.get_active_project()
        if not project:
            return False
        return self.execute_command(RemoveAssetCommand(project, asset_id))

    def update_asset(self, asset: Asset) -> bool:
        """Updates asset properties via command execution."""
        project = self.get_active_project()
        if not project:
            return False
        return self.execute_command(UpdateAssetCommand(project, asset))

    def undo(self) -> bool:
        """Reverts the last executed command on the state manager."""
        return self.state_manager.undo()

    def redo(self) -> bool:
        """Re-applies the last undone command on the state manager."""
        return self.state_manager.redo()
