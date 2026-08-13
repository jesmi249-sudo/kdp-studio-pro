from copy import deepcopy
from typing import List, Optional, Any
from uuid import UUID, uuid4
from book_builder.commands.base import Command
from book_builder.models.book import BookProject, BookMetadata
from book_builder.models.page import Page
from book_builder.models.asset import Asset
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from core.logger import get_logger

logger = get_logger(__name__)

class AddPageCommand(Command):
    """Command that adds a Page model to the project page collection."""
    def __init__(self, project: BookProject, page: Page) -> None:
        self.project = project
        self.page = page
        self.event_bus = EventBus()

    def execute(self) -> bool:
        # Validation: Verify page number sequence integrity
        if self.page.page_number < 1 or self.page.page_number > len(self.project.pages) + 1:
            logger.error(f"AddPageCommand: invalid insertion page index {self.page.page_number}")
            return False
            
        # Insert page at page_number - 1 offset
        idx = self.page.page_number - 1
        self.project.pages.insert(idx, self.page)
        
        # Adjust page numbers for subsequent pages
        for i in range(idx + 1, len(self.project.pages)):
            self.project.pages[i].page_number = i + 1
            
        self.event_bus.publish(
            Event("PageAdded", "AddPageCommand", {"page_id": str(self.page.id), "page_number": self.page.page_number})
        )
        return True

    def undo(self) -> bool:
        idx = self.page.page_number - 1
        if 0 <= idx < len(self.project.pages) and self.project.pages[idx].id == self.page.id:
            self.project.pages.pop(idx)
            # Re-adjust page numbers
            for i in range(idx, len(self.project.pages)):
                self.project.pages[i].page_number = i + 1
            self.event_bus.publish(
                Event("PageDeleted", "AddPageCommand", {"page_id": str(self.page.id), "page_number": self.page.page_number})
            )
            return True
        return False

    def redo(self) -> bool:
        return self.execute()

    def get_description(self) -> str:
        return f"Add Page {self.page.page_number}"


class DeletePageCommand(Command):
    """Command that deletes a Page from the project by its 1-indexed page number."""
    def __init__(self, project: BookProject, page_number: int) -> None:
        self.project = project
        self.page_number = page_number
        self.deleted_page: Optional[Page] = None
        self.event_bus = EventBus()

    def execute(self) -> bool:
        # Validation
        if self.page_number < 1 or self.page_number > len(self.project.pages):
            logger.error(f"DeletePageCommand: page index {self.page_number} is out of bounds.")
            return False
            
        idx = self.page_number - 1
        self.deleted_page = self.project.pages.pop(idx)
        
        # Adjust remaining page numbers
        for i in range(idx, len(self.project.pages)):
            self.project.pages[i].page_number = i + 1
            
        self.event_bus.publish(
            Event("PageDeleted", "DeletePageCommand", {"page_id": str(self.deleted_page.id), "page_number": self.page_number})
        )
        return True

    def undo(self) -> bool:
        if not self.deleted_page:
            return False
            
        idx = self.page_number - 1
        self.project.pages.insert(idx, self.deleted_page)
        
        # Adjust page numbers
        for i in range(idx + 1, len(self.project.pages)):
            self.project.pages[i].page_number = i + 1
            
        self.event_bus.publish(
            Event("PageAdded", "DeletePageCommand", {"page_id": str(self.deleted_page.id), "page_number": self.page_number})
        )
        return True

    def redo(self) -> bool:
        return self.execute()

    def get_description(self) -> str:
        return f"Delete Page {self.page_number}"


class DuplicatePageCommand(Command):
    """Command that duplicates a Page and inserts it adjacent to the original."""
    def __init__(self, project: BookProject, page_number: int) -> None:
        self.project = project
        self.page_number = page_number
        self.cloned_page: Optional[Page] = None
        self.event_bus = EventBus()

    def execute(self) -> bool:
        # Validation
        if self.page_number < 1 or self.page_number > len(self.project.pages):
            logger.error(f"DuplicatePageCommand: index {self.page_number} is out of bounds.")
            return False
            
        idx = self.page_number - 1
        original_page = self.project.pages[idx]
        
        # Perform deep copy and reset identifiers
        self.cloned_page = deepcopy(original_page)
        self.cloned_page.id = uuid4()
        self.cloned_page.page_number = self.page_number + 1
        
        # Insert next to original page
        self.project.pages.insert(self.page_number, self.cloned_page)
        
        # Re-index subsequent page numbers
        for i in range(self.page_number + 1, len(self.project.pages)):
            self.project.pages[i].page_number = i + 1
            
        self.event_bus.publish(
            Event("PageAdded", "DuplicatePageCommand", {"page_id": str(self.cloned_page.id), "page_number": self.cloned_page.page_number})
        )
        return True

    def undo(self) -> bool:
        if not self.cloned_page:
            return False
            
        idx = self.page_number # Index of the cloned page is exactly self.page_number
        if 0 <= idx < len(self.project.pages) and self.project.pages[idx].id == self.cloned_page.id:
            self.project.pages.pop(idx)
            # Re-adjust page numbers
            for i in range(idx, len(self.project.pages)):
                self.project.pages[i].page_number = i + 1
            self.event_bus.publish(
                Event("PageDeleted", "DuplicatePageCommand", {"page_id": str(self.cloned_page.id), "page_number": idx + 1})
            )
            return True
        return False

    def redo(self) -> bool:
        return self.execute()

    def get_description(self) -> str:
        return f"Duplicate Page {self.page_number}"


class MovePageCommand(Command):
    """Command that moves a Page from one position to another (0-indexed)."""
    def __init__(self, project: BookProject, from_idx: int, to_idx: int) -> None:
        self.project = project
        self.from_idx = from_idx
        self.to_idx = to_idx
        self.event_bus = EventBus()

    def execute(self) -> bool:
        # Validation
        num_pages = len(self.project.pages)
        if not (0 <= self.from_idx < num_pages and 0 <= self.to_idx < num_pages):
            logger.error(f"MovePageCommand: out of bounds indices ({self.from_idx} -> {self.to_idx})")
            return False
            
        page = self.project.pages.pop(self.from_idx)
        self.project.pages.insert(self.to_idx, page)
        
        # Re-index all page numbers
        for i in range(len(self.project.pages)):
            self.project.pages[i].page_number = i + 1
            
        self.event_bus.publish(
            Event("PageMoved", "MovePageCommand", {
                "page_id": str(page.id),
                "from_page_number": self.from_idx + 1,
                "to_page_number": self.to_idx + 1
            })
        )
        return True

    def undo(self) -> bool:
        # Swap indices to undo
        page = self.project.pages.pop(self.to_idx)
        self.project.pages.insert(self.from_idx, page)
        
        # Re-index
        for i in range(len(self.project.pages)):
            self.project.pages[i].page_number = i + 1
            
        self.event_bus.publish(
            Event("PageMoved", "MovePageCommand", {
                "page_id": str(page.id),
                "from_page_number": self.to_idx + 1,
                "to_page_number": self.from_idx + 1
            })
        )
        return True

    def redo(self) -> bool:
        return self.execute()

    def get_description(self) -> str:
        return f"Move Page {self.from_idx + 1} to {self.to_idx + 1}"


class ReorderPagesCommand(Command):
    """Command that bulk-reorders the project pages collection according to a list of new indices."""
    def __init__(self, project: BookProject, new_order: List[int]) -> None:
        self.project = project
        self.new_order = new_order
        self.previous_order: List[Page] = []
        self.event_bus = EventBus()

    def execute(self) -> bool:
        # Validation
        if len(self.new_order) != len(self.project.pages):
            logger.error("ReorderPagesCommand: new order array length mismatch.")
            return False
            
        unique_indices = set(self.new_order)
        if len(unique_indices) != len(self.project.pages) or min(self.new_order) < 0 or max(self.new_order) >= len(self.project.pages):
            logger.error("ReorderPagesCommand: invalid indices list.")
            return False
            
        self.previous_order = list(self.project.pages)
        self.project.pages = [self.previous_order[i] for i in self.new_order]
        
        # Re-index page numbers
        for i in range(len(self.project.pages)):
            self.project.pages[i].page_number = i + 1
            
        self.event_bus.publish(Event("ProjectModified", "ReorderPagesCommand", {"action": "reorder"}))
        return True

    def undo(self) -> bool:
        if not self.previous_order:
            return False
        self.project.pages = list(self.previous_order)
        for i in range(len(self.project.pages)):
            self.project.pages[i].page_number = i + 1
        self.event_bus.publish(Event("ProjectModified", "ReorderPagesCommand", {"action": "reorder_undo"}))
        return True

    def redo(self) -> bool:
        return self.execute()

    def get_description(self) -> str:
        return "Reorder Pages"


class UpdateMetadataCommand(Command):
    """Command that overrides the metadata value object."""
    def __init__(self, project: BookProject, new_metadata: BookMetadata) -> None:
        self.project = project
        self.new_metadata = new_metadata
        self.old_metadata: Optional[BookMetadata] = None
        self.event_bus = EventBus()

    def execute(self) -> bool:
        self.old_metadata = deepcopy(self.project.metadata)
        self.project.metadata = deepcopy(self.new_metadata)
        self.event_bus.publish(Event("MetadataUpdated", "UpdateMetadataCommand", {}))
        return True

    def undo(self) -> bool:
        if not self.old_metadata:
            return False
        self.project.metadata = deepcopy(self.old_metadata)
        self.event_bus.publish(Event("MetadataUpdated", "UpdateMetadataCommand", {}))
        return True

    def redo(self) -> bool:
        return self.execute()

    def get_description(self) -> str:
        return "Update Book Metadata"


class RenameProjectCommand(Command):
    """Command that updates the project working name."""
    def __init__(self, project: BookProject, new_name: str) -> None:
        self.project = project
        self.new_name = new_name
        self.old_name: str = ""
        self.event_bus = EventBus()

    def execute(self) -> bool:
        # Validation
        if not self.new_name.strip():
            logger.error("RenameProjectCommand: name cannot be empty.")
            return False
            
        self.old_name = self.project.name
        self.project.name = self.new_name.strip()
        self.event_bus.publish(Event("ProjectModified", "RenameProjectCommand", {"name": self.project.name}))
        return True

    def undo(self) -> bool:
        self.project.name = self.old_name
        self.event_bus.publish(Event("ProjectModified", "RenameProjectCommand", {"name": self.project.name}))
        return True

    def redo(self) -> bool:
        return self.execute()

    def get_description(self) -> str:
        return f"Rename Project to '{self.new_name}'"


class ImportAssetCommand(Command):
    """Command that registers a media asset inside the project asset registry."""
    def __init__(self, project: BookProject, asset: Asset) -> None:
        self.project = project
        self.asset = asset
        self.event_bus = EventBus()

    def execute(self) -> bool:
        # Validation: Verify asset unique ID
        if any(a.id == self.asset.id for a in self.project.assets):
            logger.error(f"ImportAssetCommand: asset ID {self.asset.id} already exists.")
            return False
            
        self.project.assets.append(self.asset)
        self.event_bus.publish(
            Event("AssetImported", "ImportAssetCommand", {"asset_id": str(self.asset.id), "name": self.asset.name})
        )
        return True

    def undo(self) -> bool:
        idx = next((i for i, a in enumerate(self.project.assets) if a.id == self.asset.id), -1)
        if idx != -1:
            self.project.assets.pop(idx)
            self.event_bus.publish(
                Event("AssetRemoved", "ImportAssetCommand", {"asset_id": str(self.asset.id)})
            )
            return True
        return False

    def redo(self) -> bool:
        return self.execute()

    def get_description(self) -> str:
        return f"Import Asset '{self.asset.name}'"


class RemoveAssetCommand(Command):
    """Command that removes a media asset from the registry."""
    def __init__(self, project: BookProject, asset_id: UUID) -> None:
        self.project = project
        self.asset_id = asset_id
        self.removed_asset: Optional[Asset] = None
        self.event_bus = EventBus()

    def execute(self) -> bool:
        idx = next((i for i, a in enumerate(self.project.assets) if a.id == self.asset_id), -1)
        if idx == -1:
            logger.error(f"RemoveAssetCommand: asset {self.asset_id} not found.")
            return False
            
        self.removed_asset = self.project.assets.pop(idx)
        self.event_bus.publish(
            Event("AssetRemoved", "RemoveAssetCommand", {"asset_id": str(self.asset_id)})
        )
        return True

    def undo(self) -> bool:
        if not self.removed_asset:
            return False
        self.project.assets.append(self.removed_asset)
        self.event_bus.publish(
            Event("AssetImported", "RemoveAssetCommand", {"asset_id": str(self.removed_asset.id), "name": self.removed_asset.name})
        )
        return True

    def redo(self) -> bool:
        return self.execute()

    def get_description(self) -> str:
        name = self.removed_asset.name if self.removed_asset else str(self.asset_id)
        return f"Remove Asset '{name}'"


class UpdateAssetCommand(Command):
    """Command that updates metadata details on an asset inside the registry."""
    def __init__(self, project: BookProject, updated_asset: Asset) -> None:
        self.project = project
        self.updated_asset = updated_asset
        self.old_asset: Optional[Asset] = None
        self.event_bus = EventBus()

    def execute(self) -> bool:
        idx = next((i for i, a in enumerate(self.project.assets) if a.id == self.updated_asset.id), -1)
        if idx == -1:
            logger.error(f"UpdateAssetCommand: asset {self.updated_asset.id} not found.")
            return False
            
        self.old_asset = deepcopy(self.project.assets[idx])
        self.project.assets[idx] = deepcopy(self.updated_asset)
        self.event_bus.publish(
            Event("ProjectModified", "UpdateAssetCommand", {"action": "update_asset", "asset_id": str(self.updated_asset.id)})
        )
        return True

    def undo(self) -> bool:
        if not self.old_asset:
            return False
        idx = next((i for i, a in enumerate(self.project.assets) if a.id == self.old_asset.id), -1)
        if idx != -1:
            self.project.assets[idx] = deepcopy(self.old_asset)
            self.event_bus.publish(
                Event("ProjectModified", "UpdateAssetCommand", {"action": "update_asset_undo", "asset_id": str(self.old_asset.id)})
            )
            return True
        return False

    def redo(self) -> bool:
        return self.execute()

    def get_description(self) -> str:
        return f"Update Asset '{self.updated_asset.name}'"
