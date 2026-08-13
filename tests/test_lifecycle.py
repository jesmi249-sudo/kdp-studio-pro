import unittest
import os
import json
import time
from uuid import UUID, uuid4
from book_builder.engine import BookBuilderEngine
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from book_builder.recent import RecentProjectsManager
from book_builder.autosave import AutosaveManager
from database.db import db

class TestProjectLifecycle(unittest.TestCase):
    """Verifies that the BookBuilderEngine and ProjectStateManager coordinate project lifecycles, databases, and events."""

    def setUp(self) -> None:
        self.engine = BookBuilderEngine(autosave_interval_sec=0.1) # Fast autosave for testing
        self.event_bus = EventBus()
        self.received_events = []
        
        # Subscribe to lifecycle events
        self.event_bus.subscribe("PROJECT_CREATED", self._collect_event)
        self.event_bus.subscribe("PROJECT_OPENED", self._collect_event)
        self.event_bus.subscribe("PROJECT_SAVED", self._collect_event)
        self.event_bus.subscribe("PROJECT_CLOSED", self._collect_event)
        self.event_bus.subscribe("PROJECT_MODIFIED", self._collect_event)
        self.event_bus.subscribe("DIRTY_STATE_CHANGED", self._collect_event)
        self.event_bus.subscribe("AUTOSAVE_COMPLETED", self._collect_event)

    def tearDown(self) -> None:
        self.engine.close_project()
        
        self.event_bus.unsubscribe("PROJECT_CREATED", self._collect_event)
        self.event_bus.unsubscribe("PROJECT_OPENED", self._collect_event)
        self.event_bus.unsubscribe("PROJECT_SAVED", self._collect_event)
        self.event_bus.unsubscribe("PROJECT_CLOSED", self._collect_event)
        self.event_bus.unsubscribe("PROJECT_MODIFIED", self._collect_event)
        self.event_bus.unsubscribe("DIRTY_STATE_CHANGED", self._collect_event)
        self.event_bus.unsubscribe("AUTOSAVE_COMPLETED", self._collect_event)

    def _collect_event(self, event: Event) -> None:
        self.received_events.append(event)

    def test_project_creation_flow(self) -> None:
        """Verifies engine instantiates project aggregate and broadcasts events."""
        settings = {"trim_width_in": 6.0, "trim_height_in": 9.0}
        project = self.engine.create_project("Coloring Novel", "Coloring Book", settings)
        
        self.assertIsInstance(project, BookProject)
        self.assertEqual(project.name, "Coloring Novel")
        self.assertEqual(project.trim_width_in, 6.0)
        self.assertTrue(self.engine.state_manager.is_dirty())
        
        # Verify events triggered
        types = [e.event_type for e in self.received_events]
        self.assertIn("PROJECT_OPENED", types)
        self.assertIn("PROJECT_CREATED", types)

    def test_repository_save_and_load(self) -> None:
        """Verifies project aggregate compiles, writes to SQLite, and loads matching fields."""
        settings = {"trim_width_in": 8.0, "trim_height_in": 10.0}
        project = self.engine.create_project("Persistence Book", "Coloring Book", settings)
        project.metadata.author = "Test Author"
        
        # Add a test page
        test_page = Page(page_number=1, page_type="Front Matter")
        project.pages.append(test_page)
        
        # Save project to DB
        success = self.engine.save_project()
        self.assertTrue(success)
        self.assertFalse(self.engine.state_manager.is_dirty())
        db_id = project.id # Saved row ID
        
        # Verify event saved
        types = [e.event_type for e in self.received_events]
        self.assertIn("PROJECT_SAVED", types)
        
        # Close project
        self.engine.close_project()
        self.assertIsNone(self.engine.get_active_project())
        
        # Reload project
        loaded_project = self.engine.open_project(db_id)
        self.assertIsNotNone(loaded_project)
        self.assertEqual(loaded_project.name, "Persistence Book")
        self.assertEqual(loaded_project.metadata.author, "Test Author")
        self.assertEqual(len(loaded_project.pages), 1)
        self.assertEqual(loaded_project.pages[0].page_type, "Front Matter")
        
        # Cleanup DB
        self.engine.delete_project(db_id)

    def test_recent_projects_registry(self) -> None:
        """Verifies ProjectStateManager registers recently opened projects in recents registry."""
        settings = {"trim_width_in": 5.0, "trim_height_in": 8.0}
        project = self.engine.create_project("Recent Book", "Notebook", settings)
        
        recents = RecentProjectsManager.get_recent_projects()
        self.assertTrue(len(recents) > 0)
        top = recents[0]
        self.assertEqual(top["name"], "Recent Book")
        self.assertEqual(top["book_type"], "Notebook")

    def test_autosave_recovery_checkpoints(self) -> None:
        """Verifies AutosaveManager dumps recovery checkpoints to disk on dirty states."""
        settings = {"trim_width_in": 6.0, "trim_height_in": 9.0}
        project = self.engine.create_project("Autosave Book", "Journal", settings)
        
        # Trigger autosave manual run
        AutosaveManager.create_checkpoint(project)
        path = AutosaveManager.get_checkpoint_path(project.id)
        self.assertTrue(os.path.exists(path))
        
        # Verify load recovery checkpoint
        recovered = AutosaveManager.load_checkpoint(project.id)
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.name, "Autosave Book")
        self.assertEqual(recovered.book_type, "Journal")
        # Close project to stop the background autosave manager timer loop
        self.engine.close_project()
        
        # Clear checkpoint
        AutosaveManager.clear_checkpoint(project.id)
        self.assertFalse(os.path.exists(path))

if __name__ == "__main__":
    unittest.main()
