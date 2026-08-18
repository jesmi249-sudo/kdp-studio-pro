import unittest
from unittest.mock import MagicMock, patch
from ui.views.book_workspace import BookWorkspaceView
from book_builder.models.book import BookProject

class TestWorkspaceEmptyStates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import customtkinter as ctk
        cls.root = ctk.CTk()
        
    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()
        
    def setUp(self):
        with patch('ui.views.book_workspace.BookWorkspaceView._refresh_preview'), \
             patch('ui.views.book_workspace.BookWorkspaceView._refresh_thumbnails'):
            self.view = BookWorkspaceView(self.root)
            self.view.engine = MagicMock()
        
    def test_plan_empty_state(self):
        self.view.engine.get_active_project.return_value = None
        self.view._build_planner_tab()
        # Verify the empty state label is created
        self.assertIsNotNone(self.view._empty_plan_label)
        self.assertIn("No AI Plan generated yet", self.view._empty_plan_label.cget("text"))
        
    def test_content_empty_state(self):
        self.view.engine.get_active_project.return_value = BookProject(name="Empty")
        self.view._build_content_tab()
        # Content tab should handle empty project without throwing exceptions
        self.assertTrue(True)
        
    def test_qa_empty_state(self):
        print("Running QA empty state")
        self.view._build_kdp_check_tab()
        # Should contain default guidance label
        self.assertIsNotNone(self.view.qa_results_label)
        self.assertIn("Add your pages to run", self.view.qa_results_label.cget("text"))
        print("Done QA")

if __name__ == '__main__':
    print("Starting tests")
    unittest.main()
    print("Tests finished")
