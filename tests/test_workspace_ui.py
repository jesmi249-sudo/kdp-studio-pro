import unittest
import os
import json
import customtkinter as ctk
from unittest.mock import patch, MagicMock
from uuid import UUID

from ui.app import KDPStudioApp
from ui.views.book_builder import BookBuilderView, WorkspaceController
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.models.asset import Asset
from book_builder.events.bus import EventBus
from book_builder.events.event import Event


class TestBookBuilderWorkspaceUI(unittest.TestCase):
    """
    Comprehensive integration test suite validating the Book Builder Workspace,
    WorkspaceController command routing, events subscriptions, and UI refreshes.
    """
    @classmethod
    def setUpClass(cls) -> None:
        # Clear icon cache to prevent Tkinter TclError "image doesn't exist" in regression test runs
        from core.icon_manager import IconManager
        IconManager()._cache.clear()
        
        # Create a single hidden root app instance to initialize CustomTkinter environment
        cls.app = KDPStudioApp()
        cls.app.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.app.destroy()

    def setUp(self) -> None:
        from book_builder.rendering.queue import RenderQueue
        RenderQueue._reset_singleton()
        
        # Intercept and mock Tkinter dialog elements
        self.patcher_info = patch("tkinter.messagebox.showinfo")
        self.patcher_warn = patch("tkinter.messagebox.showwarning")
        self.patcher_err = patch("tkinter.messagebox.showerror")
        self.patcher_confirm = patch("tkinter.messagebox.askyesno", return_value=True)
        self.patcher_open_file = patch("tkinter.filedialog.askopenfilename", return_value="dummy_path.png")
        
        self.mock_info = self.patcher_info.start()
        self.mock_warn = self.patcher_warn.start()
        self.mock_err = self.patcher_err.start()
        self.mock_confirm = self.patcher_confirm.start()
        self.mock_open_file = self.patcher_open_file.start()

        # Load Book Builder View
        self.view = self.app._lazy_load_view("Book Builder")
        self.app.select_frame("Book Builder")
        self.controller = self.view.controller
        
        # Start with a clean project
        self.controller.engine.close_project()
        self.controller.zoom_level = 1.0

    def tearDown(self) -> None:
        self.controller.render_queue.shutdown()
        from book_builder.rendering.queue import RenderQueue
        RenderQueue._reset_singleton()
        
        self.patcher_info.stop()
        self.patcher_warn.stop()
        self.patcher_err.stop()
        self.patcher_confirm.stop()
        self.patcher_open_file.stop()
        self.controller.engine.close_project()

    # --- 1. Workspace Initialization Tests ---
    def test_workspace_initialization(self) -> None:
        """Verifies BookBuilderView subcomponents instantiate and bind correctly."""
        self.assertIsInstance(self.view, BookBuilderView)
        self.assertIsNotNone(self.view.toolbar)
        self.assertIsNotNone(self.view.status_bar)
        self.assertIsNotNone(self.view.thumbnail_panel)
        self.assertIsNotNone(self.view.canvas_panel)
        self.assertIsNotNone(self.view.properties_panel)
        self.assertIsNotNone(self.view.asset_panel)
        
        # Verify controller link
        self.assertIs(self.view.controller, self.controller)
        self.assertIs(self.controller.view, self.view)

    # --- 2. Project Lifecycle & Event Updates ---
    def test_project_created_and_opened_events(self) -> None:
        """Verifies PROJECT_CREATED and PROJECT_OPENED events populate UI indicators."""
        # Create a new project
        self.controller.create_project("My New Coloring Book", "Coloring Book", {"trim_width_in": 8.5, "trim_height_in": 11.0})
        
        project = self.controller.engine.get_active_project()
        self.assertIsNotNone(project)
        self.assertEqual(project.name, "My New Coloring Book")
        
        # Allow event loop processing
        self.app.update()
        
        # Verify status bar text
        self.assertIn("My New Coloring Book", self.view.status_bar.project_lbl.cget("text"))
        self.assertIn("No Pages", self.view.status_bar.selection_lbl.cget("text"))

    # --- 3. Page Operations and Command Routing ---
    def test_add_page_flow(self) -> None:
        """Verifies that adding a page increases project page counts and refreshes thumbnail panel."""
        self.controller.create_project("Page Test Book", "Coloring Book", {})
        self.app.update()
        
        # Initially 0 pages
        self.assertEqual(len(self.controller.engine.get_active_project().pages), 0)
        
        # Add Page
        self.controller.add_page()
        self.app.update()
        
        project = self.controller.engine.get_active_project()
        self.assertEqual(len(project.pages), 1)
        self.assertEqual(project.pages[0].page_number, 1)
        
        # Check active selection and UI updates
        self.assertEqual(self.controller.engine.state_manager.project_state.active_page_index, 0)
        self.assertIn("Page 1 of 1", self.view.status_bar.selection_lbl.cget("text"))
        
        # Thumbnail list should contain 1 page card
        self.assertEqual(len(self.view.thumbnail_panel.cards), 1)

    def test_duplicate_and_delete_page_flow(self) -> None:
        """Verifies duplicate and delete page pipeline command routing."""
        self.controller.create_project("Page Ops Book", "Coloring Book", {})
        self.controller.add_page() # Page 1
        self.app.update()
        
        # Duplicate
        self.controller.duplicate_page()
        self.app.update()
        
        project = self.controller.engine.get_active_project()
        self.assertEqual(len(project.pages), 2)
        self.assertEqual(project.pages[1].page_number, 2)
        self.assertEqual(self.controller.engine.state_manager.project_state.active_page_index, 1)
        
        # Delete active page (Page 2)
        self.controller.delete_page()
        self.app.update()
        
        self.assertEqual(len(project.pages), 1)
        self.assertEqual(self.controller.engine.state_manager.project_state.active_page_index, 0)

    def test_move_page_up_and_down_flow(self) -> None:
        """Verifies moving pages up and down updates layout sequences via commands."""
        self.controller.create_project("Move Test Book", "Coloring Book", {})
        self.controller.add_page() # Page 1
        self.controller.add_page() # Page 2
        
        project = self.controller.engine.get_active_project()
        p1_id = project.pages[0].id
        p2_id = project.pages[1].id
        
        # Move up from Page 2 position
        self.controller.select_page(1)
        self.controller.move_page_up()
        self.app.update()
        
        # Order should be swapped
        self.assertEqual(project.pages[0].id, p2_id)
        self.assertEqual(project.pages[1].id, p1_id)
        
        # Move down from Page 1 position (index 0)
        self.controller.select_page(0)
        self.controller.move_page_down()
        self.app.update()
        
        self.assertEqual(project.pages[0].id, p1_id)
        self.assertEqual(project.pages[1].id, p2_id)

    # --- 4. Undo and Redo Routing ---
    def test_undo_redo_command_routing(self) -> None:
        """Verifies undo/redo trigger events and successfully rollback/rollforward page counts."""
        self.controller.create_project("History Book", "Coloring Book", {})
        self.controller.add_page() # Action 1
        
        project = self.controller.engine.get_active_project()
        self.assertEqual(len(project.pages), 1)
        
        # Undo page add
        self.controller.undo()
        self.app.update()
        self.assertEqual(len(project.pages), 0)
        
        # Redo page add
        self.controller.redo()
        self.app.update()
        self.assertEqual(len(project.pages), 1)

    # --- 5. Zoom Updates ---
    def test_zoom_scaling(self) -> None:
        """Verifies changing zoom constraints updates footer and triggers render refresh."""
        self.controller.create_project("Zoom Book", "Coloring Book", {})
        self.controller.add_page()
        self.app.update()
        
        self.controller.set_zoom(1.5)
        self.assertEqual(self.controller.zoom_level, 1.5)
        self.assertIn("150%", self.view.status_bar.zoom_lbl.cget("text"))
        
        # Zoom constraint check (huge zoom should limit to 8.0)
        self.controller.set_zoom(50.0)
        self.assertEqual(self.controller.zoom_level, 8.0)
        self.assertIn("800%", self.view.status_bar.zoom_lbl.cget("text"))

    # --- 6. Metadata Updates ---
    def test_metadata_updates(self) -> None:
        """Verifies metadata edits are updated properly on the project model via engine commands."""
        self.controller.create_project("Meta Book", "Coloring Book", {})
        self.app.update()
        
        self.controller.update_metadata(
            title="Custom Book Title",
            subtitle="",
            author="Jane Doe",
            publisher="Studio Press",
            description="Lovely book description"
        )
        self.app.update()
        
        project = self.controller.engine.get_active_project()
        self.assertEqual(project.metadata.title, "Custom Book Title")
        self.assertEqual(project.metadata.author, "Jane Doe")
        self.assertEqual(project.metadata.publisher, "Studio Press")
        self.assertEqual(project.metadata.description, "Lovely book description")

    # --- 7. Assets Panel Operations ---
    def test_asset_import_and_removal(self) -> None:
        """Verifies enqueuing assets triggers UI refresh and modifies models."""
        self.controller.create_project("Asset Book", "Coloring Book", {})
        self.app.update()
        
        # Initially empty assets
        project = self.controller.engine.get_active_project()
        self.assertEqual(len(project.assets), 0)
        
        # Import Asset
        with patch("os.path.exists", return_value=True), patch("os.path.getsize", return_value=2048):
            self.controller.import_asset()
        self.app.update()
        
        self.assertEqual(len(project.assets), 1)
        self.assertEqual(project.assets[0].name, "dummy_path.png")
        self.assertEqual(project.assets[0].asset_type, "Image")
        
        # Remove Asset
        asset_id = project.assets[0].id
        self.controller.remove_asset(asset_id)
        self.app.update()
        
        self.assertEqual(len(project.assets), 0)


if __name__ == "__main__":
    unittest.main()
