from typing import List, Dict, Any, Optional
from book_builder.commands.base import Command
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.templates.notebook import NotebookTemplateGenerator
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from core.logger import get_logger

logger = get_logger(__name__)

class GenerateNotebookPagesCommand(Command):
    """
    Optimized command that generates notebook page layouts.
    Reuses existing page instances to prevent redundant thumbnail invalidation.
    """
    def __init__(self, project: BookProject, page_count: int, trim_width_in: float, trim_height_in: float,
                 margin_top_in: float, margin_bottom_in: float, margin_inside_in: float, margin_outside_in: float,
                 has_bleed: bool, template_type: str, settings: Optional[Dict[str, Any]] = None) -> None:
        self.project = project
        self.page_count = page_count
        self.trim_width_in = trim_width_in
        self.trim_height_in = trim_height_in
        self.margin_top_in = margin_top_in
        self.margin_bottom_in = margin_bottom_in
        self.margin_inside_in = margin_inside_in
        self.margin_outside_in = margin_outside_in
        self.has_bleed = has_bleed
        self.template_type = template_type
        self.settings = settings or {}
        self.event_bus = EventBus()
        
        # Mementos for Undo/Redo
        self.prev_pages: List[Page] = []
        self.prev_trim_width_in = project.trim_width_in
        self.prev_trim_height_in = project.trim_height_in
        self.prev_has_bleed = project.has_bleed
        
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        logger.info(f"GenerateNotebookPagesCommand: executing for project '{self.project.name}'")
        try:
            self.prev_pages = list(self.project.pages)
            
            # Update project settings
            self.project.trim_width_in = self.trim_width_in
            self.project.trim_height_in = self.trim_height_in
            self.project.has_bleed = self.has_bleed
            
            self.new_pages = []
            generator = NotebookTemplateGenerator()
            
            # Map existing pages by page number for reuse
            existing_by_num = {p.page_number: p for p in self.prev_pages}
            
            for i in range(1, self.page_count + 1):
                # Calculate coordinates
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
                
                vectors = generator.generate_page_objects(temp_page, self.template_type, self.settings)
                
                # Check if we can reuse the existing Page object
                existing_page = existing_by_num.get(i)
                if (existing_page and 
                    existing_page.width_pt == temp_page.width_pt and 
                    existing_page.height_pt == temp_page.height_pt and 
                    existing_page.margin_top_pt == temp_page.margin_top_pt and 
                    existing_page.margin_bottom_pt == temp_page.margin_bottom_pt and 
                    existing_page.margin_inside_pt == temp_page.margin_inside_pt and 
                    existing_page.margin_outside_pt == temp_page.margin_outside_pt and 
                    existing_page.has_bleed == temp_page.has_bleed and 
                    existing_page.vector_objects == vectors):
                    
                    # Exact match - reuse instance completely!
                    self.new_pages.append(existing_page)
                else:
                    # Content or layout changed - create/update
                    new_p = Page(
                        id=existing_page.id if existing_page else temp_page.id, # Keep UUID if page exists
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
                    
            # Apply pages to project
            self.project.pages = self.new_pages
            
            # Broadcast modification
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "GenerateNotebookPagesCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"GenerateNotebookPagesCommand: execution failed: {e}")
            self.project.pages = self.prev_pages
            self.project.trim_width_in = self.prev_trim_width_in
            self.project.trim_height_in = self.prev_trim_height_in
            self.project.has_bleed = self.prev_has_bleed
            return False

    def undo(self) -> bool:
        logger.info(f"GenerateNotebookPagesCommand: undoing for project '{self.project.name}'")
        try:
            self.project.pages = self.prev_pages
            self.project.trim_width_in = self.prev_trim_width_in
            self.project.trim_height_in = self.prev_trim_height_in
            self.project.has_bleed = self.prev_has_bleed
            
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "GenerateNotebookPagesCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"GenerateNotebookPagesCommand: undo failed: {e}")
            return False

    def redo(self) -> bool:
        logger.info(f"GenerateNotebookPagesCommand: redoing for project '{self.project.name}'")
        try:
            self.project.pages = self.new_pages
            self.project.trim_width_in = self.trim_width_in
            self.project.trim_height_in = self.trim_height_in
            self.project.has_bleed = self.has_bleed
            
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "GenerateNotebookPagesCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"GenerateNotebookPagesCommand: redo failed: {e}")
            return False

    def get_description(self) -> str:
        return f"Generate {self.page_count} {self.template_type} pages"
