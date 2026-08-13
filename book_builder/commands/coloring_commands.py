from typing import List, Dict, Any, Optional
from book_builder.commands.base import Command
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.templates.coloring import ColoringTemplateGenerator
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from core.logger import get_logger

logger = get_logger(__name__)


class GenerateColoringPagesCommand(Command):
    """
    Command to generate a sequence of coloring book pages with selected artwork.
    Maintains clean undo/redo stack.
    """
    def __init__(self, project: BookProject, page_count: int, trim_width_in: float, trim_height_in: float,
                 margin_top_in: float, margin_bottom_in: float, margin_inside_in: float, margin_outside_in: float,
                 has_bleed: bool, settings: Optional[Dict[str, Any]] = None) -> None:
        self.project = project
        self.page_count = page_count
        self.trim_width_in = trim_width_in
        self.trim_height_in = trim_height_in
        self.margin_top_in = margin_top_in
        self.margin_bottom_in = margin_bottom_in
        self.margin_inside_in = margin_inside_in
        self.margin_outside_in = margin_outside_in
        self.has_bleed = has_bleed
        self.settings = settings or {}
        self.event_bus = EventBus()
        
        # Mementos
        self.prev_pages: List[Page] = []
        self.prev_trim_w = project.trim_width_in
        self.prev_trim_h = project.trim_height_in
        self.prev_bleed = project.has_bleed
        
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        logger.info(f"GenerateColoringPagesCommand: executing for project '{self.project.name}'")
        try:
            self.prev_pages = list(self.project.pages)
            
            # Update settings
            self.project.trim_width_in = self.trim_width_in
            self.project.trim_height_in = self.trim_height_in
            self.project.has_bleed = self.has_bleed
            
            self.new_pages = []
            generator = ColoringTemplateGenerator()
            
            # Map existing pages by page number for potential reuse
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
                
                # Generate layout elements (populates images/text_blocks/validation_state on temp_page)
                vectors = generator.generate_page_objects(temp_page, "Coloring Page", self.settings)
                
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
                new_p.images = list(temp_page.images)
                new_p.text_blocks = list(temp_page.text_blocks)
                new_p.vector_objects = vectors
                new_p.validation_state = temp_page.validation_state
                
                self.new_pages.append(new_p)
                
            self.project.pages = self.new_pages
            
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "GenerateColoringPagesCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"GenerateColoringPagesCommand failed: {e}")
            self.project.pages = self.prev_pages
            self.project.trim_width_in = self.prev_trim_w
            self.project.trim_height_in = self.prev_trim_h
            self.project.has_bleed = self.prev_bleed
            return False

    def undo(self) -> bool:
        logger.info(f"GenerateColoringPagesCommand: undoing for project '{self.project.name}'")
        try:
            self.project.pages = self.prev_pages
            self.project.trim_width_in = self.prev_trim_w
            self.project.trim_height_in = self.prev_trim_h
            self.project.has_bleed = self.prev_bleed
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "GenerateColoringPagesCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"GenerateColoringPagesCommand: undo failed: {e}")
            return False

    def redo(self) -> bool:
        logger.info(f"GenerateColoringPagesCommand: redoing for project '{self.project.name}'")
        try:
            self.project.pages = self.new_pages
            self.project.trim_width_in = self.trim_width_in
            self.project.trim_height_in = self.trim_height_in
            self.project.has_bleed = self.has_bleed
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "GenerateColoringPagesCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"GenerateColoringPagesCommand: redo failed: {e}")
            return False

    def get_description(self) -> str:
        return f"Generate {self.page_count} coloring pages"


class ReplaceArtworkCommand(Command):
    """
    Replaces the illustration artwork for a specific single page.
    """
    def __init__(self, project: BookProject, page_index: int, new_artwork_path: str, settings: Dict[str, Any]) -> None:
        self.project = project
        self.page_index = page_index
        self.new_artwork_path = new_artwork_path
        self.settings = settings.copy()
        self.event_bus = EventBus()
        
        # Mementos
        self.old_images: List[Dict[str, Any]] = []
        self.old_vectors: List[Dict[str, Any]] = []
        self.old_texts: List[Dict[str, Any]] = []
        self.old_validation: Dict[str, Any] = {}
        
        self.new_images: List[Dict[str, Any]] = []
        self.new_vectors: List[Dict[str, Any]] = []
        self.new_texts: List[Dict[str, Any]] = []
        self.new_validation: Dict[str, Any] = {}

    def execute(self) -> bool:
        try:
            if self.page_index < 0 or self.page_index >= len(self.project.pages):
                return False
                
            page = self.project.pages[self.page_index]
            self.old_images = list(page.images)
            self.old_vectors = list(page.vector_objects)
            self.old_texts = list(page.text_blocks)
            self.old_validation = dict(page.validation_state)
            
            # Override settings with this specific artwork
            run_settings = {**self.settings, "artwork_path": self.new_artwork_path}
            generator = ColoringTemplateGenerator()
            
            # Generate new content
            vectors = generator.generate_page_objects(page, "Coloring Page", run_settings)
            
            self.new_images = list(page.images)
            self.new_vectors = vectors
            self.new_texts = list(page.text_blocks)
            self.new_validation = dict(page.validation_state)
            
            page.images = self.new_images
            page.vector_objects = self.new_vectors
            page.text_blocks = self.new_texts
            page.validation_state = self.new_validation
            
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "ReplaceArtworkCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"ReplaceArtworkCommand: failed execution: {e}")
            return False

    def undo(self) -> bool:
        try:
            page = self.project.pages[self.page_index]
            page.images = self.old_images
            page.vector_objects = self.old_vectors
            page.text_blocks = self.old_texts
            page.validation_state = self.old_validation
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "ReplaceArtworkCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"ReplaceArtworkCommand: undo failed: {e}")
            return False

    def redo(self) -> bool:
        try:
            page = self.project.pages[self.page_index]
            page.images = self.new_images
            page.vector_objects = self.new_vectors
            page.text_blocks = self.new_texts
            page.validation_state = self.new_validation
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "ReplaceArtworkCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"ReplaceArtworkCommand: redo failed: {e}")
            return False

    def get_description(self) -> str:
        return f"Replace artwork on Page {self.page_index + 1}"


class BatchImportArtworkCommand(Command):
    """
    Imports multiple illustration images. Automatically inserts odd print pages
    and even blank pages if single_sided layout mode is checked.
    """
    def __init__(self, project: BookProject, artwork_paths: List[str], settings: Dict[str, Any]) -> None:
        self.project = project
        self.artwork_paths = artwork_paths
        self.settings = settings.copy()
        self.event_bus = EventBus()
        
        self.prev_pages = list(project.pages)
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        try:
            self.prev_pages = list(self.project.pages)
            self.new_pages = list(self.project.pages)
            
            single_sided = self.settings.get("single_sided", True)
            generator = ColoringTemplateGenerator()
            
            # Determine start page number
            if self.new_pages:
                start_num = max(p.page_number for p in self.new_pages) + 1
            else:
                start_num = 1
                
            for path in self.artwork_paths:
                # 1. Print Page (always odd page number for single_sided print)
                if single_sided and (start_num % 2 == 0):
                    # Insert empty blank page first to align artwork to odd slots
                    blank_page = Page(
                        page_number=start_num, page_type="Body",
                        width_pt=self.project.trim_width_in * 72.0,
                        height_pt=self.project.trim_height_in * 72.0,
                        has_bleed=self.project.has_bleed
                    )
                    generator.generate_page_objects(blank_page, "Coloring Page", self.settings)
                    self.new_pages.append(blank_page)
                    start_num += 1
                    
                # Generate main print page with image
                print_page = Page(
                    page_number=start_num, page_type="Body",
                    width_pt=self.project.trim_width_in * 72.0,
                    height_pt=self.project.trim_height_in * 72.0,
                    has_bleed=self.project.has_bleed
                )
                
                # Apply artwork specifically
                run_settings = {**self.settings, "artwork_path": path}
                vectors = generator.generate_page_objects(print_page, "Coloring Page", run_settings)
                
                print_page.vector_objects = vectors
                self.new_pages.append(print_page)
                start_num += 1
                
                # 2. Blank Back Page (even page number if single-sided printing is enabled)
                if single_sided:
                    back_page = Page(
                        page_number=start_num, page_type="Body",
                        width_pt=self.project.trim_width_in * 72.0,
                        height_pt=self.project.trim_height_in * 72.0,
                        has_bleed=self.project.has_bleed
                    )
                    generator.generate_page_objects(back_page, "Coloring Page", self.settings)
                    self.new_pages.append(back_page)
                    start_num += 1
                    
            self.project.pages = self.new_pages
            
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "BatchImportArtworkCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"BatchImportArtworkCommand failed execution: {e}")
            self.project.pages = self.prev_pages
            return False

    def undo(self) -> bool:
        try:
            self.project.pages = self.prev_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "BatchImportArtworkCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"BatchImportArtworkCommand undo failed: {e}")
            return False

    def redo(self) -> bool:
        try:
            self.project.pages = self.new_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "BatchImportArtworkCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"BatchImportArtworkCommand redo failed: {e}")
            return False

    def get_description(self) -> str:
        return f"Batch import {len(self.artwork_paths)} illustrations"


class ShuffleArtworkCommand(Command):
    """
    Shuffles all placed artwork images across the coloring project pages.
    """
    def __init__(self, project: BookProject, settings: Dict[str, Any]) -> None:
        self.project = project
        self.settings = settings.copy()
        self.event_bus = EventBus()
        
        self.prev_pages = list(project.pages)
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        import random
        logger.info(f"ShuffleArtworkCommand: executing for project '{self.project.name}'")
        try:
            self.prev_pages = list(self.project.pages)
            self.new_pages = []
            
            # Extract all artwork file paths currently on pages
            artwork_paths = []
            for page in self.project.pages:
                for img in page.images:
                    if img.get("file_path"):
                        artwork_paths.append(img["file_path"])
            
            # Shuffle them
            random.shuffle(artwork_paths)
            
            generator = ColoringTemplateGenerator()
            single_sided = self.settings.get("single_sided", True)
            
            # Regenerate pages with shuffled artwork
            art_idx = 0
            for page in self.project.pages:
                # Keep UUIDs and basic properties
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
                
                # Check if it should have artwork
                if single_sided and (page.page_number % 2 == 0):
                    # Blank page
                    generator.generate_page_objects(new_p, "Coloring Page", self.settings)
                else:
                    # Place next shuffled artwork
                    path = artwork_paths[art_idx] if art_idx < len(artwork_paths) else None
                    art_idx += 1
                    
                    run_settings = {**self.settings, "artwork_path": path}
                    vectors = generator.generate_page_objects(new_p, "Coloring Page", run_settings)
                    new_p.vector_objects = vectors
                    
                self.new_pages.append(new_p)
                
            self.project.pages = self.new_pages
            
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "ShuffleArtworkCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"ShuffleArtworkCommand failed: {e}")
            self.project.pages = self.prev_pages
            return False

    def undo(self) -> bool:
        try:
            self.project.pages = self.prev_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "ShuffleArtworkCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"ShuffleArtworkCommand undo failed: {e}")
            return False

    def redo(self) -> bool:
        try:
            self.project.pages = self.new_pages
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "ShuffleArtworkCommand", {"project_id": str(self.project.id)})
            )
            return True
        except Exception as e:
            logger.error(f"ShuffleArtworkCommand redo failed: {e}")
            return False

    def get_description(self) -> str:
        return "Shuffle artwork layout order"
