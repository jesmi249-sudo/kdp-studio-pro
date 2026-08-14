import unittest
from unittest.mock import MagicMock, patch
import customtkinter as ctk

from book_builder.models.book import BookProject
from book_builder.models.page import Page
from ui.views.book_workspace import BookWorkspaceView
from core.compliance_checker import ComplianceChecker

class TestWorkspacePreview(unittest.TestCase):
    def setUp(self):
        # We need a root window to instantiate CTk widgets
        self.root = ctk.CTk()
        self.workspace = BookWorkspaceView(self.root)
        
        # Mock engine and project
        self.workspace.engine = MagicMock()
        self.project = BookProject(name="Test")
        self.page1 = Page(id="p1")
        self.page2 = Page(id="p2")
        self.project.pages.append(self.page1)
        self.project.pages.append(self.page2)
        
        self.workspace.engine.get_active_project.return_value = self.project
        self.workspace.project_id = "test1"

    def tearDown(self):
        self.root.destroy()

    def test_preview_navigation(self):
        self.workspace._build_preview_tab()
        
        # Default starts at page 0
        self.assertEqual(self.workspace.current_preview_index, 0)
        
        # Go next
        self.workspace._preview_next_page()
        self.assertEqual(self.workspace.current_preview_index, 1)
        
        # Next again (should clamp to max)
        self.workspace._preview_next_page()
        self.assertEqual(self.workspace.current_preview_index, 1)
        
        # Go prev
        self.workspace._preview_prev_page()
        self.assertEqual(self.workspace.current_preview_index, 0)
        
    def test_spread_navigation(self):
        self.workspace._build_preview_tab()
        self.workspace.preview_mode.set("Two-Page Spread")
        
        # Go next (steps by 2)
        self.project.pages.append(Page())
        self.project.pages.append(Page())
        
        self.workspace._preview_next_page()
        self.assertEqual(self.workspace.current_preview_index, 2)
        
        self.workspace._preview_prev_page()
        self.assertEqual(self.workspace.current_preview_index, 0)
        
    @patch('book_builder.rendering.service.PreviewService')
    @patch('book_builder.rendering.thumbnail.PageThumbnailGenerator')
    def test_preview_refresh_does_not_crash(self, MockThumb, MockPreview):
        self.workspace._build_preview_tab()
        self.workspace._refresh_preview()
        self.assertTrue(True) # Verifying no synchronous exceptions

    def test_zoom_controls(self):
        self.workspace._build_preview_tab()
        self.workspace.preview_zoom.set(1.0)
        
        # Zoom in
        self.workspace._set_preview_zoom(0.2)
        self.assertEqual(self.workspace.preview_zoom.get(), 1.2)
        
        # Zoom out
        self.workspace._set_preview_zoom(-0.4)
        self.assertAlmostEqual(self.workspace.preview_zoom.get(), 0.8)
        
        # Fit
        self.workspace._set_preview_zoom(0, fit=True)
        self.assertEqual(self.workspace.preview_zoom.get(), 1.0)

    def test_qa_dashboard_initialization(self):
        self.workspace._build_kdp_check_tab()
        self.assertEqual(self.workspace.qa_btn.cget("text"), "Run Inspection")

    @patch('core.compliance_checker.ComplianceChecker.run_inspection')
    def test_qa_inspection_worker(self, mock_run):
        # Setup mock result
        mock_result = MagicMock()
        mock_result.health_score = 100
        mock_result.issues = []
        mock_run.return_value = mock_result
        
        self.workspace._build_kdp_check_tab()
        # Direct call to result renderer
        self.workspace._render_qa_results(mock_result)
        
        # Button state should return to normal
        self.assertEqual(self.workspace.qa_btn.cget("state"), "normal")

if __name__ == '__main__':
    unittest.main()
