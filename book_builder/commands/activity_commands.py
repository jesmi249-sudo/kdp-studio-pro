import random
from typing import List, Dict, Any, Optional
from copy import deepcopy
from book_builder.commands.base import Command
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.templates.activity import ActivityTemplateGenerator
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from core.logger import get_logger

logger = get_logger(__name__)


class GenerateActivityPagesCommand(Command):
    """Generates a collection of activity pages with specified types and settings."""
    def __init__(self, project: BookProject, page_count: int, trim_width_in: float, trim_height_in: float,
                 margin_top_in: float, margin_bottom_in: float, margin_inside_in: float, margin_outside_in: float,
                 has_bleed: bool, activity_type: str, settings: Optional[Dict[str, Any]] = None) -> None:
        self.project = project
        self.page_count = page_count
        self.trim_width_in = trim_width_in
        self.trim_height_in = trim_height_in
        self.margin_top_in = margin_top_in
        self.margin_bottom_in = margin_bottom_in
        self.margin_inside_in = margin_inside_in
        self.margin_outside_in = margin_outside_in
        self.has_bleed = has_bleed
        self.activity_type = activity_type
        self.settings = settings or {}
        self.event_bus = EventBus()
        
        self.prev_pages = list(project.pages)
        self.prev_trim_w = project.trim_width_in
        self.prev_trim_h = project.trim_height_in
        self.prev_bleed = project.has_bleed
        
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        try:
            self.prev_pages = list(self.project.pages)
            self.new_pages = []
            
            # Apply project trim settings
            self.project.trim_width_in = self.trim_width_in
            self.project.trim_height_in = self.trim_height_in
            self.project.has_bleed = self.has_bleed
            
            generator = ActivityTemplateGenerator()
            existing_by_num = {p.page_number: p for p in self.prev_pages}
            
            # We generate the main activity pages
            main_page_count = self.page_count
            include_answer_key = self.settings.get("include_answer_key", True)
            pack_answers = self.settings.get("pack_answers", False)
            
            if include_answer_key:
                if pack_answers:
                    import math
                    ans_pages = math.ceil(main_page_count / 4)
                    total_pages_to_generate = main_page_count + ans_pages
                else:
                    total_pages_to_generate = main_page_count * 2
            else:
                total_pages_to_generate = main_page_count
                
            for i in range(1, total_pages_to_generate + 1):
                is_key = (i > main_page_count)
                page_settings = self.settings.copy()
                page_settings["is_answer_key"] = is_key
                page_settings["pack_answers"] = pack_answers
                
                # If it's an answer key page, match it to the corresponding puzzle page numbers
                if is_key:
                    if pack_answers:
                        ans_page_idx = i - main_page_count - 1
                        puzzle_start = ans_page_idx * 4 + 1
                        puzzle_end = min(main_page_count, puzzle_start + 3)
                        page_settings["puzzle_range"] = (puzzle_start, puzzle_end)
                        page_settings["header_text"] = f"Solutions (Puzzles {puzzle_start}-{puzzle_end})"
                    else:
                        puzzle_page_num = i - main_page_count
                        # Keep same seed as the puzzle page to be deterministic
                        page_settings["seed"] = self.settings.get("seed", 42) + puzzle_page_num
                        page_settings["header_text"] = f"Puzzle {puzzle_page_num} Solution"
                else:
                    page_settings["seed"] = self.settings.get("seed", 42) + i
                    page_settings["header_text"] = f"Puzzle {i}"
                    
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
                
                vectors = generator.generate_page_objects(temp_page, self.activity_type, page_settings)
                
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
            self.event_bus.publish(Event("PROJECT_MODIFIED", "GenerateActivityPagesCommand", {"project_id": str(self.project.id)}))
            return True
        except Exception as e:
            logger.error(f"GenerateActivityPagesCommand failed: {e}")
            self.project.pages = self.prev_pages
            self.project.trim_width_in = self.prev_trim_w
            self.project.trim_height_in = self.prev_trim_h
            self.project.has_bleed = self.prev_bleed
            return False

    def undo(self) -> bool:
        self.project.pages = self.prev_pages
        self.project.trim_width_in = self.prev_trim_w
        self.project.trim_height_in = self.prev_trim_h
        self.project.has_bleed = self.prev_bleed
        self.event_bus.publish(Event("PROJECT_MODIFIED", "GenerateActivityPagesCommand", {"project_id": str(self.project.id)}))
        return True

    def redo(self) -> bool:
        self.project.pages = self.new_pages
        self.project.trim_width_in = self.trim_width_in
        self.project.trim_height_in = self.trim_height_in
        self.project.has_bleed = self.has_bleed
        self.event_bus.publish(Event("PROJECT_MODIFIED", "GenerateActivityPagesCommand", {"project_id": str(self.project.id)}))
        return True

    def get_description(self) -> str:
        return f"Generate {self.page_count} {self.activity_type} pages"


class RegenerateActivityCommand(Command):
    """Re-rolls a specific page's puzzle layout using a new random seed."""
    def __init__(self, project: BookProject, page_index: int, settings: Dict[str, Any]) -> None:
        self.project = project
        self.page_index = page_index
        self.settings = settings.copy()
        self.event_bus = EventBus()
        
        self.prev_pages = deepcopy(project.pages)
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        try:
            if self.page_index < 0 or self.page_index >= len(self.project.pages):
                return False
                
            self.prev_pages = deepcopy(self.project.pages)
            self.new_pages = deepcopy(self.project.pages)
            
            target_page = self.new_pages[self.page_index]
            
            # Increment random seed to guarantee a new layout
            current_seed = self.settings.get("seed", 42)
            self.settings["seed"] = current_seed + random.randint(1, 1000)
            
            generator = ActivityTemplateGenerator()
            activity_type = self.settings.get("activity_type", "Maze")
            
            # Determine if this page is a solution/answer key page
            is_key = target_page.page_number > (len(self.new_pages) // 2)
            self.settings["is_answer_key"] = is_key
            
            vectors = generator.generate_page_objects(target_page, activity_type, self.settings)
            target_page.vector_objects = vectors
            
            self.project.pages = self.new_pages
            self.event_bus.publish(Event("PROJECT_MODIFIED", "RegenerateActivityCommand", {"project_id": str(self.project.id)}))
            return True
        except Exception as e:
            logger.error(f"RegenerateActivityCommand failed: {e}")
            return False

    def undo(self) -> bool:
        self.project.pages = self.prev_pages
        self.event_bus.publish(Event("PROJECT_MODIFIED", "RegenerateActivityCommand", {"project_id": str(self.project.id)}))
        return True

    def redo(self) -> bool:
        self.project.pages = self.new_pages
        self.event_bus.publish(Event("PROJECT_MODIFIED", "RegenerateActivityCommand", {"project_id": str(self.project.id)}))
        return True

    def get_description(self) -> str:
        return f"Regenerate puzzle on page {self.page_index + 1}"


class ShuffleActivityCommand(Command):
    """Shuffles items, clues, or layout elements on a page."""
    def __init__(self, project: BookProject, page_index: int, settings: Dict[str, Any]) -> None:
        self.project = project
        self.page_index = page_index
        self.settings = settings.copy()
        self.event_bus = EventBus()
        self.prev_pages = deepcopy(project.pages)
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        try:
            if self.page_index < 0 or self.page_index >= len(self.project.pages):
                return False
            self.prev_pages = deepcopy(self.project.pages)
            self.new_pages = deepcopy(self.project.pages)
            
            target_page = self.new_pages[self.page_index]
            # Change seed slightly to shuffle
            self.settings["seed"] = self.settings.get("seed", 42) + 999
            
            generator = ActivityTemplateGenerator()
            activity_type = self.settings.get("activity_type", "Maze")
            vectors = generator.generate_page_objects(target_page, activity_type, self.settings)
            target_page.vector_objects = vectors
            
            self.project.pages = self.new_pages
            self.event_bus.publish(Event("PROJECT_MODIFIED", "ShuffleActivityCommand", {"project_id": str(self.project.id)}))
            return True
        except Exception as e:
            logger.error(f"ShuffleActivityCommand failed: {e}")
            return False

    def undo(self) -> bool:
        self.project.pages = self.prev_pages
        self.event_bus.publish(Event("PROJECT_MODIFIED", "ShuffleActivityCommand", {"project_id": str(self.project.id)}))
        return True

    def redo(self) -> bool:
        self.project.pages = self.new_pages
        self.event_bus.publish(Event("PROJECT_MODIFIED", "ShuffleActivityCommand", {"project_id": str(self.project.id)}))
        return True

    def get_description(self) -> str:
        return f"Shuffle items on page {self.page_index + 1}"


class ReplaceArtworkCommand(Command):
    """Replaces or swaps the puzzle generator style on a specific page."""
    def __init__(self, project: BookProject, page_index: int, new_activity_type: str, settings: Dict[str, Any]) -> None:
        self.project = project
        self.page_index = page_index
        self.new_activity_type = new_activity_type
        self.settings = settings.copy()
        self.event_bus = EventBus()
        self.prev_pages = deepcopy(project.pages)
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        try:
            if self.page_index < 0 or self.page_index >= len(self.project.pages):
                return False
            self.prev_pages = deepcopy(self.project.pages)
            self.new_pages = deepcopy(self.project.pages)
            
            target_page = self.new_pages[self.page_index]
            generator = ActivityTemplateGenerator()
            vectors = generator.generate_page_objects(target_page, self.new_activity_type, self.settings)
            target_page.vector_objects = vectors
            
            self.project.pages = self.new_pages
            self.event_bus.publish(Event("PROJECT_MODIFIED", "ReplaceArtworkCommand", {"project_id": str(self.project.id)}))
            return True
        except Exception as e:
            logger.error(f"ReplaceArtworkCommand failed: {e}")
            return False

    def undo(self) -> bool:
        self.project.pages = self.prev_pages
        self.event_bus.publish(Event("PROJECT_MODIFIED", "ReplaceArtworkCommand", {"project_id": str(self.project.id)}))
        return True

    def redo(self) -> bool:
        self.project.pages = self.new_pages
        self.event_bus.publish(Event("PROJECT_MODIFIED", "ReplaceArtworkCommand", {"project_id": str(self.project.id)}))
        return True

    def get_description(self) -> str:
        return f"Replace activity with {self.new_activity_type} on page {self.page_index + 1}"


class DuplicateActivityPageCommand(Command):
    """Duplicates a specific page containing an activity."""
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
            
            src = self.new_pages[self.page_index]
            duplicated = Page(
                page_number=src.page_number + 1,
                page_type=src.page_type,
                width_pt=src.width_pt,
                height_pt=src.height_pt,
                margin_top_pt=src.margin_top_pt,
                margin_bottom_pt=src.margin_bottom_pt,
                margin_inside_pt=src.margin_inside_pt,
                margin_outside_pt=src.margin_outside_pt,
                has_bleed=src.has_bleed
            )
            duplicated.vector_objects = deepcopy(src.vector_objects)
            duplicated.images = deepcopy(src.images)
            duplicated.text_blocks = deepcopy(src.text_blocks)
            
            self.new_pages.insert(self.page_index + 1, duplicated)
            
            # Reset page numbers
            for idx, p in enumerate(self.new_pages):
                p.page_number = idx + 1
                
            self.project.pages = self.new_pages
            self.event_bus.publish(Event("PROJECT_MODIFIED", "DuplicateActivityPageCommand", {"project_id": str(self.project.id)}))
            return True
        except Exception as e:
            logger.error(f"DuplicateActivityPageCommand failed: {e}")
            return False

    def undo(self) -> bool:
        self.project.pages = self.prev_pages
        self.event_bus.publish(Event("PROJECT_MODIFIED", "DuplicateActivityPageCommand", {"project_id": str(self.project.id)}))
        return True

    def redo(self) -> bool:
        self.project.pages = self.new_pages
        self.event_bus.publish(Event("PROJECT_MODIFIED", "DuplicateActivityPageCommand", {"project_id": str(self.project.id)}))
        return True

    def get_description(self) -> str:
        return f"Duplicate page {self.page_index + 1}"


class DeleteActivityPageCommand(Command):
    """Deletes a specific activity page."""
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
            
            self.new_pages.pop(self.page_index)
            
            # Reset page numbers
            for idx, p in enumerate(self.new_pages):
                p.page_number = idx + 1
                
            self.project.pages = self.new_pages
            self.event_bus.publish(Event("PROJECT_MODIFIED", "DeleteActivityPageCommand", {"project_id": str(self.project.id)}))
            return True
        except Exception as e:
            logger.error(f"DeleteActivityPageCommand failed: {e}")
            return False

    def undo(self) -> bool:
        self.project.pages = self.prev_pages
        self.event_bus.publish(Event("PROJECT_MODIFIED", "DeleteActivityPageCommand", {"project_id": str(self.project.id)}))
        return True

    def redo(self) -> bool:
        self.project.pages = self.new_pages
        self.event_bus.publish(Event("PROJECT_MODIFIED", "DeleteActivityPageCommand", {"project_id": str(self.project.id)}))
        return True

    def get_description(self) -> str:
        return f"Delete page {self.page_index + 1}"


class BatchGenerateActivitiesCommand(Command):
    """Generates a batch of distinct activity pages sequentially."""
    def __init__(self, project: BookProject, page_count: int, trim_width_in: float, trim_height_in: float,
                 margin_top_in: float, margin_bottom_in: float, margin_inside_in: float, margin_outside_in: float,
                 has_bleed: bool, activity_types: List[str], settings: Optional[Dict[str, Any]] = None) -> None:
        self.project = project
        self.page_count = page_count
        self.trim_width_in = trim_width_in
        self.trim_height_in = trim_height_in
        self.margin_top_in = margin_top_in
        self.margin_bottom_in = margin_bottom_in
        self.margin_inside_in = margin_inside_in
        self.margin_outside_in = margin_outside_in
        self.has_bleed = has_bleed
        self.activity_types = activity_types
        self.settings = settings or {}
        self.event_bus = EventBus()
        
        self.prev_pages = list(project.pages)
        self.prev_trim_w = project.trim_width_in
        self.prev_trim_h = project.trim_height_in
        self.prev_bleed = project.has_bleed
        
        self.new_pages: List[Page] = []

    def execute(self) -> bool:
        try:
            self.prev_pages = list(self.project.pages)
            self.new_pages = []
            
            # Apply project trim settings
            self.project.trim_width_in = self.trim_width_in
            self.project.trim_height_in = self.trim_height_in
            self.project.has_bleed = self.has_bleed
            
            generator = ActivityTemplateGenerator()
            
            for i in range(1, self.page_count + 1):
                # Distribute activity types in a cycle
                act_type = self.activity_types[(i - 1) % len(self.activity_types)]
                
                page_settings = self.settings.copy()
                page_settings["seed"] = self.settings.get("seed", 42) + i
                page_settings["header_text"] = f"{act_type} - Game {i}"
                
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
                
                vectors = generator.generate_page_objects(temp_page, act_type, page_settings)
                new_p = Page(
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
            self.event_bus.publish(Event("PROJECT_MODIFIED", "BatchGenerateActivitiesCommand", {"project_id": str(self.project.id)}))
            return True
        except Exception as e:
            logger.error(f"BatchGenerateActivitiesCommand failed: {e}")
            self.project.pages = self.prev_pages
            self.project.trim_width_in = self.prev_trim_w
            self.project.trim_height_in = self.prev_trim_h
            self.project.has_bleed = self.prev_bleed
            return False

    def undo(self) -> bool:
        self.project.pages = self.prev_pages
        self.project.trim_width_in = self.prev_trim_w
        self.project.trim_height_in = self.prev_trim_h
        self.project.has_bleed = self.prev_bleed
        self.event_bus.publish(Event("PROJECT_MODIFIED", "BatchGenerateActivitiesCommand", {"project_id": str(self.project.id)}))
        return True

    def redo(self) -> bool:
        self.project.pages = self.new_pages
        self.project.trim_width_in = self.trim_width_in
        self.project.trim_height_in = self.trim_height_in
        self.project.has_bleed = self.has_bleed
        self.event_bus.publish(Event("PROJECT_MODIFIED", "BatchGenerateActivitiesCommand", {"project_id": str(self.project.id)}))
        return True

    def get_description(self) -> str:
        return f"Batch generate {self.page_count} activities"


class AddDecorativeAssetCommand(Command):
    """Command that adds a decorative asset to a page aggregate layers."""
    def __init__(self, project: BookProject, page_index: int, asset_path: str, geometry: Dict[str, Any], asset_id: Optional[str] = None) -> None:
        self.project = project
        self.page_index = page_index
        self.asset_path = asset_path
        self.geometry = geometry
        from uuid import uuid4
        self.asset_id = asset_id or str(uuid4())
        self.event_bus = EventBus()
        self.asset_dict = {}

    def execute(self) -> bool:
        try:
            if self.page_index < 0 or self.page_index >= len(self.project.pages):
                return False
            page = self.project.pages[self.page_index]
            self.asset_dict = {
                "id": self.asset_id,
                "file_path": self.asset_path,
                "geometry": self.geometry
            }
            page.images.append(self.asset_dict)
            self.event_bus.publish(Event("PROJECT_MODIFIED", "AddDecorativeAssetCommand", {"project_id": str(self.project.id)}))
            return True
        except Exception as e:
            logger.error(f"AddDecorativeAssetCommand failed: {e}")
            return False

    def undo(self) -> bool:
        try:
            page = self.project.pages[self.page_index]
            page.images = [img for img in page.images if img.get("id") != self.asset_id]
            self.event_bus.publish(Event("PROJECT_MODIFIED", "AddDecorativeAssetCommand", {"project_id": str(self.project.id)}))
            return True
        except Exception as e:
            logger.error(f"AddDecorativeAssetCommand undo failed: {e}")
            return False

    def redo(self) -> bool:
        try:
            page = self.project.pages[self.page_index]
            page.images.append(self.asset_dict)
            self.event_bus.publish(Event("PROJECT_MODIFIED", "AddDecorativeAssetCommand", {"project_id": str(self.project.id)}))
            return True
        except Exception as e:
            logger.error(f"AddDecorativeAssetCommand redo failed: {e}")
            return False

    def get_description(self) -> str:
        return f"Add asset to page {self.page_index + 1}"


class RemoveDecorativeAssetCommand(Command):
    """Command that removes a decorative asset from a page."""
    def __init__(self, project: BookProject, page_index: int, asset_id: str) -> None:
        self.project = project
        self.page_index = page_index
        self.asset_id = asset_id
        self.event_bus = EventBus()
        self.removed_asset_dict = {}

    def execute(self) -> bool:
        try:
            if self.page_index < 0 or self.page_index >= len(self.project.pages):
                return False
            page = self.project.pages[self.page_index]
            for img in page.images:
                if img.get("id") == self.asset_id:
                    self.removed_asset_dict = img
                    break
            if self.removed_asset_dict:
                page.images.remove(self.removed_asset_dict)
                self.event_bus.publish(Event("PROJECT_MODIFIED", "RemoveDecorativeAssetCommand", {"project_id": str(self.project.id)}))
                return True
            return False
        except Exception as e:
            logger.error(f"RemoveDecorativeAssetCommand failed: {e}")
            return False

    def undo(self) -> bool:
        try:
            if self.removed_asset_dict:
                page = self.project.pages[self.page_index]
                page.images.append(self.removed_asset_dict)
                self.event_bus.publish(Event("PROJECT_MODIFIED", "RemoveDecorativeAssetCommand", {"project_id": str(self.project.id)}))
                return True
            return False
        except Exception as e:
            logger.error(f"RemoveDecorativeAssetCommand undo failed: {e}")
            return False

    def redo(self) -> bool:
        return self.execute()

    def get_description(self) -> str:
        return f"Remove asset from page {self.page_index + 1}"


class ModifyDecorativeAssetCommand(Command):
    """Command that modifies geometry (position, size, rotation) of a page asset."""
    def __init__(self, project: BookProject, page_index: int, asset_id: str, new_geometry: Dict[str, Any]) -> None:
        self.project = project
        self.page_index = page_index
        self.asset_id = asset_id
        self.new_geometry = new_geometry
        self.event_bus = EventBus()
        self.old_geometry = {}

    def execute(self) -> bool:
        try:
            if self.page_index < 0 or self.page_index >= len(self.project.pages):
                return False
            page = self.project.pages[self.page_index]
            for img in page.images:
                if img.get("id") == self.asset_id:
                    self.old_geometry = deepcopy(img.get("geometry", {}))
                    img["geometry"] = deepcopy(self.new_geometry)
                    self.event_bus.publish(Event("PROJECT_MODIFIED", "ModifyDecorativeAssetCommand", {"project_id": str(self.project.id)}))
                    return True
            return False
        except Exception as e:
            logger.error(f"ModifyDecorativeAssetCommand failed: {e}")
            return False

    def undo(self) -> bool:
        try:
            page = self.project.pages[self.page_index]
            for img in page.images:
                if img.get("id") == self.asset_id:
                    img["geometry"] = deepcopy(self.old_geometry)
                    self.event_bus.publish(Event("PROJECT_MODIFIED", "ModifyDecorativeAssetCommand", {"project_id": str(self.project.id)}))
                    return True
            return False
        except Exception as e:
            logger.error(f"ModifyDecorativeAssetCommand undo failed: {e}")
            return False

    def redo(self) -> bool:
        try:
            page = self.project.pages[self.page_index]
            for img in page.images:
                if img.get("id") == self.asset_id:
                    img["geometry"] = deepcopy(self.new_geometry)
                    self.event_bus.publish(Event("PROJECT_MODIFIED", "ModifyDecorativeAssetCommand", {"project_id": str(self.project.id)}))
                    return True
            return False
        except Exception as e:
            logger.error(f"ModifyDecorativeAssetCommand redo failed: {e}")
            return False

    def get_description(self) -> str:
        return f"Modify asset on page {self.page_index + 1}"
