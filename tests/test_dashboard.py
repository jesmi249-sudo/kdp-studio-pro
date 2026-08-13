import unittest
import os
import json
import sqlite3
import customtkinter as ctk

from database.db import db
from core.config import config
from core.dashboard_service import DashboardService

class TestDashboardService(unittest.TestCase):
    """Verifies that DashboardService processes database operations and diagnostics correctly."""
    
    def test_statistics_retrieval(self):
        """Verifies statistics counts are returned successfully as integers."""
        proj_count, book_count, export_count = DashboardService.get_statistics()
        self.assertIsInstance(proj_count, int)
        self.assertIsInstance(book_count, int)
        self.assertIsInstance(export_count, int)
        self.assertGreaterEqual(proj_count, 0)
        self.assertGreaterEqual(book_count, 0)
        self.assertGreaterEqual(export_count, 0)

    def test_recent_projects_list(self):
        """Verifies that recent projects are fetched and properly structured for UI integration."""
        projects = DashboardService.get_recent_projects(limit=3)
        self.assertIsInstance(projects, list)
        self.assertLessEqual(len(projects), 3)
        
        for p in projects:
            self.assertIn("id", p)
            self.assertIn("name", p)
            self.assertIn("project_type", p)
            self.assertIn("book_type", p)
            self.assertIn("last_modified", p)
            self.assertIn("status", p)

    def test_system_health_checks(self):
        """Verifies system diagnostics check files and connectivity, returning valid status indicators."""
        health = DashboardService.check_system_health()
        self.assertIsInstance(health, list)
        self.assertGreater(len(health), 0)
        
        for name, status, color in health:
            self.assertIsInstance(name, str)
            self.assertIsInstance(status, str)
            self.assertIn(color, ["green", "red"])


class TestDashboardArchitectureAndNavigation(unittest.TestCase):
    """Verifies KDPStudioApp startup, lazy view creation, and navigation command routes."""
    
    @classmethod
    def setUpClass(cls):
        # Clear icon cache to prevent Tkinter TclError "image doesn't exist" in regression test runs
        from core.icon_manager import IconManager
        IconManager()._cache.clear()
        
        # Create a single hidden root app instance for all test cases
        from ui.app import KDPStudioApp
        cls.app = KDPStudioApp()
        cls.app.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.app.destroy()

    def setUp(self):
        from unittest.mock import patch
        self.patcher_info = patch('tkinter.messagebox.showinfo')
        self.patcher_warn = patch('tkinter.messagebox.showwarning')
        self.patcher_err = patch('tkinter.messagebox.showerror')
        
        self.mock_info = self.patcher_info.start()
        self.mock_warn = self.patcher_warn.start()
        self.mock_err = self.patcher_err.start()

    def tearDown(self):
        self.patcher_info.stop()
        self.patcher_warn.stop()
        self.patcher_err.stop()

    def test_lazy_loading_dashboard(self):
        """Verifies that DashboardView loads lazily without raising exceptions."""
        from ui.views.dashboard import DashboardView
        
        dashboard_view = self.app._lazy_load_view("Dashboard")
        self.assertIsInstance(dashboard_view, DashboardView)

    def test_routing_callbacks(self):
        """Verifies that critical commands (open, export, settings) exist on KDPStudioApp."""
        self.assertTrue(hasattr(self.app, "cmd_open"))
        self.assertTrue(hasattr(self.app, "cmd_export"))
        self.assertTrue(hasattr(self.app, "cmd_help"))
        self.assertTrue(hasattr(self.app, "open_project"))

    def test_export_prevalidation_empty_db(self):
        """Verifies Export pre-validation warns user gracefully and doesn't fail silently on empty datasets."""
        # Mock database get_all_projects to return empty
        original_get_all = db.get_all_projects
        db.get_all_projects = lambda: []
        
        # Execute cmd_export - should return gracefully without loading frame
        self.app.cmd_export()
        self.assertNotEqual(self.app.current_frame, self.app.views.get("Export Center"))
        
        # Restore mock
        db.get_all_projects = original_get_all

if __name__ == "__main__":
    unittest.main()
