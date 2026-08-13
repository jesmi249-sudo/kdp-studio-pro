import unittest
from uuid import UUID, uuid4
from book_builder.engine import BookBuilderEngine
from book_builder.models.page import Page
from book_builder.models.asset import Asset
from book_builder.models.book import BookMetadata
from book_builder.events.bus import EventBus
from book_builder.events.event import Event

class TestEditingCommands(unittest.TestCase):
    """Verifies that project layout mutations occur through validation-capped undoable commands."""

    def setUp(self) -> None:
        self.engine = BookBuilderEngine(autosave_interval_sec=60.0)
        self.project = self.engine.create_project("Command Test Book", "Coloring Book", {})
        self.event_bus = EventBus()
        self.emitted_events = []
        
        # Register listeners
        self.event_bus.subscribe("PageAdded", self._collect_event)
        self.event_bus.subscribe("PageDeleted", self._collect_event)
        self.event_bus.subscribe("PageMoved", self._collect_event)
        self.event_bus.subscribe("MetadataUpdated", self._collect_event)
        self.event_bus.subscribe("AssetImported", self._collect_event)
        self.event_bus.subscribe("AssetRemoved", self._collect_event)
        self.event_bus.subscribe("UndoExecuted", self._collect_event)
        self.event_bus.subscribe("RedoExecuted", self._collect_event)

    def tearDown(self) -> None:
        self.engine.close_project()
        
        self.event_bus.unsubscribe("PageAdded", self._collect_event)
        self.event_bus.unsubscribe("PageDeleted", self._collect_event)
        self.event_bus.unsubscribe("PageMoved", self._collect_event)
        self.event_bus.unsubscribe("MetadataUpdated", self._collect_event)
        self.event_bus.unsubscribe("AssetImported", self._collect_event)
        self.event_bus.unsubscribe("AssetRemoved", self._collect_event)
        self.event_bus.unsubscribe("UndoExecuted", self._collect_event)
        self.event_bus.unsubscribe("RedoExecuted", self._collect_event)

    def _collect_event(self, event: Event) -> None:
        self.emitted_events.append(event)

    def test_add_and_delete_pages(self) -> None:
        """Verifies page addition, page re-indexing, out-of-sequence validation, and deletion."""
        self.assertEqual(len(self.project.pages), 0)
        
        # Add Page 1
        p1 = Page(page_number=1, page_type="Body")
        success = self.engine.add_page(p1)
        self.assertTrue(success)
        self.assertEqual(len(self.project.pages), 1)
        self.assertEqual(self.project.pages[0].id, p1.id)
        
        # Add Page 2
        p2 = Page(page_number=2, page_type="Body")
        self.assertTrue(self.engine.add_page(p2))
        self.assertEqual(len(self.project.pages), 2)
        
        # Try adding out of sequence - should fail validation
        p_invalid = Page(page_number=5, page_type="Body")
        self.assertFalse(self.engine.add_page(p_invalid))
        self.assertEqual(len(self.project.pages), 2)
        
        # Undo Page 2 addition
        self.assertTrue(self.engine.undo())
        self.assertEqual(len(self.project.pages), 1)
        
        # Redo Page 2 addition
        self.assertTrue(self.engine.redo())
        self.assertEqual(len(self.project.pages), 2)
        
        # Delete Page 1 (Page 2 shifts to Page 1)
        self.assertTrue(self.engine.delete_page(1))
        self.assertEqual(len(self.project.pages), 1)
        self.assertEqual(self.project.pages[0].id, p2.id)
        self.assertEqual(self.project.pages[0].page_number, 1) # Shifted
        
        # Undo delete Page 1
        self.assertTrue(self.engine.undo())
        self.assertEqual(len(self.project.pages), 2)
        self.assertEqual(self.project.pages[0].id, p1.id)
        self.assertEqual(self.project.pages[1].id, p2.id)
        self.assertEqual(self.project.pages[1].page_number, 2)

    def test_move_and_duplicate_pages(self) -> None:
        """Verifies re-positioning pages and duplicate cloning checks."""
        # Add 3 pages
        p1 = Page(page_number=1)
        p2 = Page(page_number=2)
        p3 = Page(page_number=3)
        self.engine.add_page(p1)
        self.engine.add_page(p2)
        self.engine.add_page(p3)
        
        self.assertEqual(self.project.pages[0].id, p1.id)
        self.assertEqual(self.project.pages[1].id, p2.id)
        
        # Move page index 0 to index 2 (Move p1 to the end)
        self.assertTrue(self.engine.move_page(0, 2))
        self.assertEqual(self.project.pages[0].id, p2.id)
        self.assertEqual(self.project.pages[1].id, p3.id)
        self.assertEqual(self.project.pages[2].id, p1.id)
        self.assertEqual(self.project.pages[0].page_number, 1)
        self.assertEqual(self.project.pages[2].page_number, 3)
        
        # Undo move page
        self.assertTrue(self.engine.undo())
        self.assertEqual(self.project.pages[0].id, p1.id)
        
        # Duplicate page 2 (clones p2 and inserts at page 3 position)
        self.assertTrue(self.engine.duplicate_page(2))
        self.assertEqual(len(self.project.pages), 4)
        self.assertEqual(self.project.pages[2].page_type, p2.page_type)
        self.assertNotEqual(self.project.pages[2].id, p2.id)
        
        # Undo duplicate page
        self.assertTrue(self.engine.undo())
        self.assertEqual(len(self.project.pages), 3)

    def test_metadata_and_rename_commands(self) -> None:
        """Verifies metadata edits and project renaming."""
        self.assertEqual(self.project.name, "Command Test Book")
        
        # Rename project
        self.assertTrue(self.engine.rename_project("Renamed Book"))
        self.assertEqual(self.project.name, "Renamed Book")
        
        # Undo rename
        self.assertTrue(self.engine.undo())
        self.assertEqual(self.project.name, "Command Test Book")
        
        # Update metadata
        new_meta = BookMetadata(author="Command Author", keywords=["coloring"])
        self.assertTrue(self.engine.update_metadata(new_meta))
        self.assertEqual(self.project.metadata.author, "Command Author")
        
        # Undo metadata
        self.assertTrue(self.engine.undo())
        self.assertEqual(self.project.metadata.author, "")

    def test_asset_library_commands(self) -> None:
        """Verifies asset imports, updates, and removals."""
        self.assertEqual(len(self.project.assets), 0)
        
        # Import Asset
        asset = Asset(name="test_pattern.svg", asset_type="SVG")
        self.assertTrue(self.engine.import_asset(asset))
        self.assertEqual(len(self.project.assets), 1)
        self.assertEqual(self.project.assets[0].id, asset.id)
        
        # Try importing duplicate - should fail validation
        self.assertFalse(self.engine.import_asset(asset))
        self.assertEqual(len(self.project.assets), 1)
        
        # Update Asset
        updated_asset = Asset(id=asset.id, name="updated_pattern.svg", asset_type="SVG", is_favorite=True)
        self.assertTrue(self.engine.update_asset(updated_asset))
        self.assertEqual(self.project.assets[0].name, "updated_pattern.svg")
        self.assertTrue(self.project.assets[0].is_favorite)
        
        # Undo update asset
        self.assertTrue(self.engine.undo())
        self.assertEqual(self.project.assets[0].name, "test_pattern.svg")
        self.assertFalse(self.project.assets[0].is_favorite)
        
        # Remove Asset
        self.assertTrue(self.engine.remove_asset(asset.id))
        self.assertEqual(len(self.project.assets), 0)
        
        # Undo remove asset
        self.assertTrue(self.engine.undo())
        self.assertEqual(len(self.project.assets), 1)
        self.assertEqual(self.project.assets[0].id, asset.id)

    def test_event_bus_publishing(self) -> None:
        """Verifies correct event types are broadcasted during command executions."""
        self.assertEqual(len(self.emitted_events), 0)
        
        p = Page(page_number=1)
        self.engine.add_page(p)
        
        types = [e.event_type for e in self.emitted_events]
        self.assertIn("PageAdded", types)
        
        self.engine.undo()
        types = [e.event_type for e in self.emitted_events]
        self.assertIn("UndoExecuted", types)

if __name__ == "__main__":
    unittest.main()
