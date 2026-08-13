import unittest
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock
from PIL import Image
from uuid import uuid4, UUID

from book_builder.models.book import BookProject, BookMetadata
from book_builder.models.page import Page
from book_builder.models.export import ExportProfile
from book_builder.autosave import AutosaveManager
from exporters.validation import KDPValidator
from exporters.export_engine import ExportEngine
from ui.views.book_builder import WorkspaceController
from book_builder.rendering.cache import PreviewCache

class TestPublishingWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.project = BookProject(name="Workflow Book", book_type="Coloring Book")
        # Populate minimum pages
        for i in range(24):
            page = Page(page_number=i+1, width_pt=612.0, height_pt=792.0)
            self.project.pages.append(page)
            
        self.profile = ExportProfile(
            profile_name="Async Preset",
            export_format="KDP_PDF",
            color_space="RGB",
            dpi=72,
            custom_options={
                "output_folder": self.temp_dir,
                "naming_template": "async_export_test"
            }
        )
            
    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_autosave_default_interval(self) -> None:
        """Verify autosave loop interval is set to 60s default."""
        from book_builder.state_manager import ProjectStateManager
        mgr = ProjectStateManager()
        self.assertEqual(mgr.autosave_manager._interval, 60.0)

    def test_validation_missing_author(self) -> None:
        """Verify pre-flight warning for missing author metadata."""
        validator = KDPValidator()
        self.project.metadata.title = "A Valid Title"
        self.project.metadata.author = ""
        issues = validator.run_full_preflight_audit(self.project)
        warnings = [i for i in issues if i.rule_name == "Missing Book Author"]
        self.assertEqual(len(warnings), 1)

    def test_validation_missing_title(self) -> None:
        """Verify pre-flight error for missing title and project name."""
        validator = KDPValidator()
        self.project.name = ""
        self.project.metadata.title = ""
        issues = validator.run_full_preflight_audit(self.project)
        errors = [i for i in issues if i.rule_name == "Missing Book Title"]
        self.assertEqual(len(errors), 1)

    def test_validation_blank_page(self) -> None:
        """Verify blank page detection generates warning."""
        validator = KDPValidator()
        issues = validator.run_full_preflight_audit(self.project)
        blanks = [i for i in issues if i.rule_name == "Blank Page Detected"]
        self.assertTrue(len(blanks) > 0)

    def test_validation_low_resolution(self) -> None:
        """Verify profile with resolution < 300 DPI produces a warning."""
        validator = KDPValidator()
        profile = ExportProfile(profile_name="Draft Profile", dpi=150)
        self.project.export_profiles = [profile]
        issues = validator.run_full_preflight_audit(self.project)
        low_res = [i for i in issues if i.rule_name == "Low Export Resolution Preset"]
        self.assertEqual(len(low_res), 1)

    def test_validation_rgb_color_mode(self) -> None:
        """Verify warning when RGB profile is used for coloring/activity books."""
        validator = KDPValidator()
        profile = ExportProfile(profile_name="RGB Profile", color_space="RGB")
        self.project.export_profiles = [profile]
        issues = validator.run_full_preflight_audit(self.project)
        rgb_issues = [i for i in issues if i.rule_name == "RGB Color Mode Preset"]
        self.assertEqual(len(rgb_issues), 1)

    def test_lru_cache_eviction(self) -> None:
        """Verify PreviewCache evicts oldest entries when exceeding max_size."""
        cache = PreviewCache(max_size=3)
        p1 = Page(page_number=1)
        p2 = Page(page_number=2)
        p3 = Page(page_number=3)
        p4 = Page(page_number=4)
        
        img = Image.new("RGBA", (10, 10))
        
        cache.set(p1, 1.0, img)
        cache.set(p2, 1.0, img)
        cache.set(p3, 1.0, img)
        self.assertEqual(len(cache), 3)
        
        cache.set(p4, 1.0, img)
        self.assertEqual(len(cache), 3)
        self.assertIsNone(cache.get(p1, 1.0))
        self.assertIsNotNone(cache.get(p4, 1.0))

    def test_facing_pages_active_index_0(self) -> None:
        """Verify page 1 spread returns a single preview page (right page standalone)."""
        controller = WorkspaceController()
        controller.set_project(self.project)
        controller.set_view_mode("Facing")
        controller.select_page(0)
        
        p_img = Image.new("RGBA", (100, 100), (255, 255, 255))
        controller.preview_service.generate_preview = MagicMock(return_value=p_img)
        
        img = controller.get_facing_pages_image()
        self.assertEqual(img.size, (100, 100))

    def test_facing_pages_spread(self) -> None:
        """Verify page index 1 spread returns side-by-side stitched pages."""
        controller = WorkspaceController()
        controller.set_project(self.project)
        controller.set_view_mode("Facing")
        controller.select_page(1)
        
        p_img = Image.new("RGBA", (100, 100), (255, 255, 255))
        controller.preview_service.generate_preview = MagicMock(return_value=p_img)
        
        img = controller.get_facing_pages_image()
        self.assertEqual(img.size, (200, 100))

    def test_book_flip_single_mode(self) -> None:
        """Verify flip step is 1 page in single view mode."""
        controller = WorkspaceController()
        controller.set_project(self.project)
        controller.set_view_mode("Single")
        controller.select_page(0)
        
        controller.book_flip_forward()
        self.assertEqual(controller.engine.state_manager.project_state.active_page_index, 1)
        
        controller.book_flip_backward()
        self.assertEqual(controller.engine.state_manager.project_state.active_page_index, 0)

    def test_book_flip_facing_mode(self) -> None:
        """Verify flip step is 2 pages in facing view mode."""
        controller = WorkspaceController()
        controller.set_project(self.project)
        controller.set_view_mode("Facing")
        controller.select_page(1)
        
        controller.book_flip_forward()
        self.assertEqual(controller.engine.state_manager.project_state.active_page_index, 3)
        
        controller.book_flip_backward()
        self.assertEqual(controller.engine.state_manager.project_state.active_page_index, 1)

    def test_search_page_content(self) -> None:
        """Verify keyword search selects the matching page index."""
        controller = WorkspaceController()
        controller.set_project(self.project)
        self.project.pages[3].text_blocks.append({
            "text": "Finding Unicorns", "geometry": {}
        })
        idx = controller.search_page("unicorns")
        self.assertEqual(idx, 3)
        self.assertEqual(controller.engine.state_manager.project_state.active_page_index, 3)

    def test_search_page_number(self) -> None:
        """Verify numeric page search matches page number metadata."""
        controller = WorkspaceController()
        controller.set_project(self.project)
        idx = controller.search_page("12")
        self.assertEqual(idx, 11)

    def test_page_thumbnail_pagination(self) -> None:
        """Verify page panel virtual window range updates scroll view size."""
        mock_view = MagicMock()
        from ui.views.book_builder import PageThumbnailPanel
        panel = PageThumbnailPanel(mock_view, WorkspaceController())
        panel.page_size = 5
        panel.current_page = 0
        
        controller = WorkspaceController()
        controller.set_project(self.project)
        panel.controller = controller
        
        panel.refresh()
        self.assertEqual(len(panel.cards), 5)
        self.assertEqual(panel.page_lbl.cget("text"), "1-5 of 24")
        
        panel.next_page()
        self.assertEqual(panel.current_page, 1)
        panel.refresh()
        self.assertEqual(panel.page_lbl.cget("text"), "6-10 of 24")

    def test_page_thumbnail_auto_pagination(self) -> None:
        """Verify set_active_page_index auto-switches page if out of current window bounds."""
        mock_view = MagicMock()
        from ui.views.book_builder import PageThumbnailPanel
        panel = PageThumbnailPanel(mock_view, WorkspaceController())
        panel.page_size = 5
        panel.current_page = 0
        
        controller = WorkspaceController()
        controller.set_project(self.project)
        panel.controller = controller
        panel.refresh()
        
        panel.set_active_page_index(11)
        self.assertEqual(panel.current_page, 2)

    def test_crash_recovery_restore(self) -> None:
        """Verify load_project recovers unsaved changes if restoration accepted."""
        from book_builder.engine import BookBuilderEngine
        engine = BookBuilderEngine()
        
        mock_project = BookProject(name="Recovered Book")
        with patch('book_builder.autosave.AutosaveManager.load_checkpoint', return_value=mock_project):
            with patch('tkinter.messagebox.askyesno', return_value=True):
                loaded = engine.load_project(1)
                self.assertEqual(loaded.name, "Recovered Book")
                self.assertTrue(engine.state_manager.is_dirty())

    def test_crash_recovery_decline(self) -> None:
        """Verify load_project cleans recovery checkpoint and reads DB if restoration declined."""
        from book_builder.engine import BookBuilderEngine
        engine = BookBuilderEngine()
        
        mock_project = BookProject(name="Recovered Book")
        db_project = BookProject(name="Database Saved Book")
        
        with patch('book_builder.autosave.AutosaveManager.load_checkpoint', return_value=mock_project):
            with patch('tkinter.messagebox.askyesno', return_value=False):
                with patch('book_builder.repository.ProjectRepository.get_by_id', return_value=db_project):
                    with patch('book_builder.autosave.AutosaveManager.clear_checkpoint') as mock_clear:
                        loaded = engine.load_project(1)
                        self.assertEqual(loaded.name, "Database Saved Book")
                        mock_clear.assert_called_once_with(1)

    def test_preset_profiles_initialization(self) -> None:
        """Verify empty projects get auto-populated with all 4 standard KDP presets."""
        from ui.views.export_center import ExportCenterView
        mock_master = MagicMock()
        view = ExportCenterView(mock_master)
        
        self.project.export_profiles = []
        view.project = self.project
        view._load_active_project()
        
        presets = [p.profile_name for p in self.project.export_profiles]
        self.assertEqual(len(presets), 4)
        self.assertIn("Low Quality", presets)
        self.assertIn("Standard", presets)
        self.assertIn("Print Quality", presets)
        self.assertIn("KDP Ready", presets)

    def test_barcode_and_isbn_placeholder_injection(self) -> None:
        """Verify barcode and ISBN fields are injected on covers and copyright pages at compile time."""
        engine = ExportEngine()
        profile = ExportProfile(profile_name="Compile Profile")
        profile.custom_options["barcode_placeholder"] = True
        profile.custom_options["isbn_placeholder"] = True
        profile.custom_options["output_folder"] = self.temp_dir
        
        self.project.metadata.isbn = "978-3-16-148410-0"
        
        pdf_file = engine.compile_pdf(self.project, profile)
        self.assertTrue(os.path.exists(pdf_file))
