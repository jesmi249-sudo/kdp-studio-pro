from typing import List, Dict, Any, Optional
from copy import deepcopy
from book_builder.commands.base import Command
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.templates.planner import PlannerTemplateGenerator
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from core.logger import get_logger

logger = get_logger(__name__)


class GeneratePlannerPagesCommand(Command):
    """
    Command that generates a sequence of low-content planner pages.
    """
    def __init__(self, project: BookProject, page_count: int, trim_width_in: float, trim_height_in: float,
                 margin_top_in: float, margin_bottom_in: float, margin_inside_in: float, margin_outside_in: float,
                 has_bleed: bool, planner_type: str, settings: Optional[Dict[str, Any]] = None) -> None:
        self.project = project
        self.page_count = page_count
        self.trim_width_in = trim_width_in
        self.trim_height_in = trim_height_in
        self.margin_top_in = margin_top_in
        self.margin_bottom_in = margin_bottom_in
        self.margin_inside_in = margin_inside_in
        self.margin_outside_in = margin_outside_in
        self.has_bleed = has_bleed
        self.planner_type = planner_type
        self.settings = settings or {}
        self.event_bus = EventBus()
        
        # Mementos
        self.prev_pages: List[Page] = []
        self.prev_trim_w = project.trim_width_in
        self.prev_trim_h = project.trim_height_in
        self.prev_bleed = project.has_bleed
        
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        logger.info(f"GeneratePlannerPagesCommand: executing for project '{self.project.name}'")
        try:
            self.prev_pages = list(self.project.pages)
            
            # Update project settings
            self.project.trim_width_in = self.trim_width_in
            self.project.trim_height_in = self.trim_height_in
            self.project.has_bleed = self.has_bleed
            
            self.new_pages = []
            generator = PlannerTemplateGenerator()
            existing_by_num = {p.page_number: p for p in self.prev_pages}
            
            for i in range(1, self.page_count + 1):
                temp_page = Page(
                    page_number=i,
                    page_type="Body",
                    width_pt=self.trim_width_in * 72.0,
                    height_pt=self.trim_height_in * 72.0,
                    margin_top_pt=self.margin_top_in * 72.0,
                    margin_bottom_pt=self.margin_bottom_in * 72.0,
                    margin_inside_pt=self.margin_inside_in * 72.0,
                    margin_outside_pt=self.margin_outside_in * 72.0,
                    has_bleed=self.has_bleed
                )
                
                vectors = generator.generate_page_objects(temp_page, self.planner_type, self.settings)
                
                existing_page = existing_by_num.get(i)
                new_p = Page(
                    id=existing_page.id if existing_page else temp_page.id,
                    page_number=i,
                    page_type="Body",
                    width_pt=temp_page.width_pt,
                    height_pt=temp_page.height_pt,
                    margin_top_pt=temp_page.margin_top_pt,
                    margin_bottom_pt=temp_page.margin_bottom_pt,
                    margin_inside_pt=temp_page.margin_inside_pt,
                    margin_outside_pt=temp_page.margin_outside_pt,
                    has_bleed=temp_page.has_bleed
                )
                new_p.vector_objects = vectors
                self.new_pages.append(new_p)
                
            self.project.pages = self.new_pages
            
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "GeneratePlannerPagesCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"GeneratePlannerPagesCommand failed: {e}")
            self.project.pages = self.prev_pages
            self.project.trim_width_in = self.prev_trim_w
            self.project.trim_height_in = self.prev_trim_h
            self.project.has_bleed = self.prev_bleed
            return False

    def undo(self) -> bool:
        try:
            self.project.pages = self.prev_pages
            self.project.trim_width_in = self.prev_trim_w
            self.project.trim_height_in = self.prev_trim_h
            self.project.has_bleed = self.prev_bleed
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "GeneratePlannerPagesCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"GeneratePlannerPagesCommand undo failed: {e}")
            return False

    def redo(self) -> bool:
        try:
            self.project.pages = self.new_pages
            self.project.trim_width_in = self.trim_width_in
            self.project.trim_height_in = self.trim_height_in
            self.project.has_bleed = self.has_bleed
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "GeneratePlannerPagesCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"GeneratePlannerPagesCommand redo failed: {e}")
            return False

    def get_description(self) -> str:
        return f"Generate {self.page_count} planner pages"


class UpdatePlannerSettingsCommand(Command):
    """
    Command that updates the general planner settings and regenerates layouts.
    """
    def __init__(self, project: BookProject, settings: Dict[str, Any]) -> None:
        self.project = project
        self.settings = settings.copy()
        self.event_bus = EventBus()
        
        self.prev_pages: List[Page] = []
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        try:
            self.prev_pages = deepcopy(self.project.pages)
            self.new_pages = []
            
            generator = PlannerTemplateGenerator()
            for page in self.project.pages:
                new_p = Page(
                    id=page.id,
                    page_number=page.page_number,
                    page_type=page.page_type,
                    width_pt=page.width_pt,
                    height_pt=page.height_pt,
                    margin_top_pt=page.margin_top_pt,
                    margin_bottom_pt=page.margin_bottom_pt,
                    margin_inside_pt=page.margin_inside_pt,
                    margin_outside_pt=page.margin_outside_pt,
                    has_bleed=page.has_bleed
                )
                
                # Check layout type in settings
                planner_type = self.settings.get("planner_type", "Custom Planner")
                vectors = generator.generate_page_objects(new_p, planner_type, self.settings)
                new_p.vector_objects = vectors
                self.new_pages.append(new_p)
                
            self.project.pages = self.new_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "UpdatePlannerSettingsCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"UpdatePlannerSettingsCommand execution failed: {e}")
            return False

    def undo(self) -> bool:
        try:
            self.project.pages = self.prev_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "UpdatePlannerSettingsCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"UpdatePlannerSettingsCommand undo failed: {e}")
            return False

    def redo(self) -> bool:
        try:
            self.project.pages = self.new_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "UpdatePlannerSettingsCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"UpdatePlannerSettingsCommand redo failed: {e}")
            return False

    def get_description(self) -> str:
        return "Update planner settings & layouts"


class InsertPlannerSectionCommand(Command):
    """
    Inserts a sequence of planner pages at a given index.
    """
    def __init__(self, project: BookProject, start_page_number: int, page_count: int,
                 planner_type: str, settings: Dict[str, Any]) -> None:
        self.project = project
        self.start_page_number = start_page_number
        self.page_count = page_count
        self.planner_type = planner_type
        self.settings = settings.copy()
        self.event_bus = EventBus()
        
        self.prev_pages = list(project.pages)
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        try:
            self.prev_pages = list(self.project.pages)
            self.new_pages = list(self.project.pages)
            
            generator = PlannerTemplateGenerator()
            insert_idx = self.start_page_number - 1
            if insert_idx < 0 or insert_idx > len(self.new_pages):
                return False
                
            inserted_pages = []
            for i in range(self.page_count):
                page_num = self.start_page_number + i
                new_p = Page(
                    page_number=page_num,
                    page_type="Body",
                    width_pt=self.project.trim_width_in * 72.0,
                    height_pt=self.project.trim_height_in * 72.0,
                    margin_top_pt=0.5 * 72.0,
                    margin_bottom_pt=0.5 * 72.0,
                    margin_inside_pt=0.5 * 72.0,
                    margin_outside_pt=0.5 * 72.0,
                    has_bleed=self.project.has_bleed
                )
                vectors = generator.generate_page_objects(new_p, self.planner_type, self.settings)
                new_p.vector_objects = vectors
                inserted_pages.append(new_p)
                
            # Insert pages into the collection
            for p in reversed(inserted_pages):
                self.new_pages.insert(insert_idx, p)
                
            # Shift subsequent page numbers
            for idx in range(len(self.new_pages)):
                self.new_pages[idx].page_number = idx + 1
                
            self.project.pages = self.new_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "InsertPlannerSectionCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"InsertPlannerSectionCommand failed: {e}")
            self.project.pages = self.prev_pages
            return False

    def undo(self) -> bool:
        try:
            self.project.pages = self.prev_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "InsertPlannerSectionCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"InsertPlannerSectionCommand undo failed: {e}")
            return False

    def redo(self) -> bool:
        try:
            self.project.pages = self.new_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "InsertPlannerSectionCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"InsertPlannerSectionCommand redo failed: {e}")
            return False

    def get_description(self) -> str:
        return f"Insert {self.page_count} {self.planner_type} pages at Page {self.start_page_number}"


class DuplicatePlannerPageCommand(Command):
    """
    Duplicates a planner page at a given index.
    """
    def __init__(self, project: BookProject, page_index: int) -> None:
        self.project = project
        self.page_index = page_index
        self.event_bus = EventBus()
        
        self.prev_pages = list(project.pages)
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        try:
            if self.page_index < 0 or self.page_index >= len(self.project.pages):
                return False
                
            self.prev_pages = list(self.project.pages)
            self.new_pages = list(self.project.pages)
            
            target_page = self.new_pages[self.page_index]
            duplicated = Page(
                page_number=target_page.page_number + 1,
                page_type=target_page.page_type,
                width_pt=target_page.width_pt,
                height_pt=target_page.height_pt,
                margin_top_pt=target_page.margin_top_pt,
                margin_bottom_pt=target_page.margin_bottom_pt,
                margin_inside_pt=target_page.margin_inside_pt,
                margin_outside_pt=target_page.margin_outside_pt,
                has_bleed=target_page.has_bleed
            )
            duplicated.vector_objects = deepcopy(target_page.vector_objects)
            duplicated.images = deepcopy(target_page.images)
            duplicated.text_blocks = deepcopy(target_page.text_blocks)
            
            # Insert directly after
            self.new_pages.insert(self.page_index + 1, duplicated)
            
            # Adjust page numbers
            for idx in range(len(self.new_pages)):
                self.new_pages[idx].page_number = idx + 1
                
            self.project.pages = self.new_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "DuplicatePlannerPageCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"DuplicatePlannerPageCommand failed: {e}")
            self.project.pages = self.prev_pages
            return False

    def undo(self) -> bool:
        try:
            self.project.pages = self.prev_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "DuplicatePlannerPageCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"DuplicatePlannerPageCommand undo failed: {e}")
            return False

    def redo(self) -> bool:
        try:
            self.project.pages = self.new_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "DuplicatePlannerPageCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"DuplicatePlannerPageCommand redo failed: {e}")
            return False

    def get_description(self) -> str:
        return f"Duplicate page {self.page_index + 1}"


class DeletePlannerSectionCommand(Command):
    """
    Deletes a range of page indices.
    """
    def __init__(self, project: BookProject, start_page_number: int, end_page_number: int) -> None:
        self.project = project
        self.start_page_number = start_page_number
        self.end_page_number = end_page_number
        self.event_bus = EventBus()
        
        self.prev_pages = list(project.pages)
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        try:
            start_idx = self.start_page_number - 1
            end_idx = self.end_page_number - 1
            if start_idx < 0 or end_idx >= len(self.project.pages) or start_idx > end_idx:
                return False
                
            self.prev_pages = list(self.project.pages)
            self.new_pages = list(self.project.pages)
            
            # Remove range
            del self.new_pages[start_idx:end_idx + 1]
            
            # Adjust page numbers
            for idx in range(len(self.new_pages)):
                self.new_pages[idx].page_number = idx + 1
                
            self.project.pages = self.new_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "DeletePlannerSectionCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"DeletePlannerSectionCommand failed: {e}")
            self.project.pages = self.prev_pages
            return False

    def undo(self) -> bool:
        try:
            self.project.pages = self.prev_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "DeletePlannerSectionCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"DeletePlannerSectionCommand undo failed: {e}")
            return False

    def redo(self) -> bool:
        try:
            self.project.pages = self.new_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "DeletePlannerSectionCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"DeletePlannerSectionCommand redo failed: {e}")
            return False

    def get_description(self) -> str:
        return f"Delete planner pages {self.start_page_number} to {self.end_page_number}"
