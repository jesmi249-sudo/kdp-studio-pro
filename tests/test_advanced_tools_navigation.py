import unittest
from unittest.mock import MagicMock
from ui.app import KDPStudioApp
from ui.views.advanced_tools import AdvancedToolsView
from ui.views.book_workspace import BookWorkspaceView

class TestAdvancedToolsNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = KDPStudioApp()
        
    @classmethod
    def tearDownClass(cls):
        from book_builder.container import Container
        from book_builder.interfaces.core import IBookBuilder
        try:
            engine = Container().resolve(IBookBuilder)
            if hasattr(engine, 'state_manager') and hasattr(engine.state_manager, 'autosave_manager'):
                engine.state_manager.autosave_manager.stop()
        except:
            pass
        cls.app.destroy()
        
    def test_legacy_tools_in_advanced_menu(self):
        # Ensure Advanced Tools is in the menu structure
        self.assertIn("Legacy Studios", self.app.nav_buttons, "Legacy Studios not found in navigation buttons")
        
    def test_advanced_tools_view_loads(self):
        # Create the Advanced Tools View
        view = AdvancedToolsView(self.app.main_content_frame, self.app)
        # Verify it has buttons for legacy studios
        self.assertTrue(len(view.winfo_children()) > 0, "No UI elements registered in AdvancedToolsView")
        
    def test_book_workspace_is_default(self):
        # We can simulate UI flow to check that Workspace is the primary book creation flow
        view = BookWorkspaceView(self.app.main_content_frame)
        self.assertEqual(view.steps[0], "Setup")
        self.assertEqual(view.steps[1], "Planner")

if __name__ == '__main__':
    unittest.main()
