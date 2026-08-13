from typing import List, Dict, Any, Optional
from book_builder.commands.base import Command
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.templates.storybook import StorybookTemplateGenerator
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from core.logger import get_logger

logger = get_logger(__name__)

class GenerateStorybookPagesCommand(Command):
    """
    Command that generates storybook pages based on the project.custom_settings['storybook_data']
    It updates the project pages and emits PROJECT_MODIFIED.
    """
    def __init__(self, project: BookProject) -> None:
        self.project = project
        self.event_bus = EventBus()
        
        # Mementos for Undo/Redo
        self.prev_pages: List[Page] = []
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        logger.info(f"GenerateStorybookPagesCommand: executing for project '{self.project.name}'")
        try:
            self.prev_pages = list(self.project.pages)
            
            storybook_data = self.project.custom_settings.get("storybook_data", {})
            pages_data = storybook_data.get("pages", [])
            global_settings = storybook_data.get("global_settings", {})
            
            self.new_pages = []
            generator = StorybookTemplateGenerator()
            
            # Map existing pages by page number for reuse
            existing_by_num = {p.page_number: p for p in self.prev_pages}
            
            # We map 1-to-1 with the pages_data array
            for idx, page_conf in enumerate(pages_data):
                page_number = idx + 1
                
                # Calculate coordinates
                temp_page = Page(
                    page_number=page_number,
                    page_type="Body",
                    width_pt=self.project.trim_width_in * 72.0,
                    height_pt=self.project.trim_height_in * 72.0,
                    has_bleed=self.project.has_bleed
                    # margin attributes use defaults
                )
                
                # Build settings dict combining global and page-specific
                settings = {}
                settings.update(global_settings)
                settings.update(page_conf)
                
                # Apply generation
                generator.generate_page_objects(temp_page, "storybook", settings)
                
                # Because images and text blocks change rapidly in Storybook, 
                # we just instantiate/reuse the ID to preserve references, but update the lists.
                existing_page = existing_by_num.get(page_number)
                if existing_page:
                    existing_page.images = temp_page.images
                    existing_page.text_blocks = temp_page.text_blocks
                    existing_page.vector_objects = temp_page.vector_objects
                    self.new_pages.append(existing_page)
                else:
                    self.new_pages.append(temp_page)
                    
            # Apply pages to project
            self.project.pages = self.new_pages
            
            # Broadcast modification
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "GenerateStorybookPagesCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"GenerateStorybookPagesCommand: execution failed: {e}")
            self.project.pages = self.prev_pages
            return False

    def undo(self) -> bool:
        logger.info(f"GenerateStorybookPagesCommand: undoing for project '{self.project.name}'")
        try:
            self.project.pages = self.prev_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "GenerateStorybookPagesCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"GenerateStorybookPagesCommand: undo failed: {e}")
            return False

    def redo(self) -> bool:
        logger.info(f"GenerateStorybookPagesCommand: redoing for project '{self.project.name}'")
        try:
            self.project.pages = self.new_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "GenerateStorybookPagesCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"GenerateStorybookPagesCommand: redo failed: {e}")
            return False

    def get_description(self) -> str:
        return f"Generate storybook pages"
