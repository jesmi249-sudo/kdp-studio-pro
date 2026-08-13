import unittest
import time
import os
from unittest.mock import patch, MagicMock
import customtkinter as ctk

from ui.app import KDPStudioApp
from ui.views.book_builder import BookBuilderView, PropertiesPanel
from ui.views.coloring_studio import ColoringStudioView, ColoringSettingsPanel
from ui.views.notebook_studio import NotebookStudioView
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.templates.coloring import ColoringTemplateGenerator
from book_builder.commands.coloring_commands import (
    GenerateColoringPagesCommand, ReplaceArtworkCommand, BatchImportArtworkCommand, ShuffleArtworkCommand
)
from book_builder.studio_registry import StudioRegistry
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from core.logger import get_logger

logger = get_logger(__name__)


class TestColoringTemplateGenerator(unittest.TestCase):
    """Verifies KDP coloring book artwork placement, single-sided blanks, and outline validation."""
    
    def setUp(self) -> None:
        self.generator = ColoringTemplateGenerator()
        
        # We need a dummy image file for validation testing
        self.dummy_img_path = os.path.abspath("test_dummy_color.png")
        from PIL import Image, ImageDraw
        # Create a mostly white image with some black lines (clean outline line art)
        img = Image.new("RGB", (800, 1000), "white")
        draw = ImageDraw.Draw(img)
        # Draw some thin black outlines
        draw.rectangle([100, 100, 700, 900], outline="black", width=4)
        draw.line([100, 100, 700, 900], fill="black", width=4)
        img.save(self.dummy_img_path)
        
        self.page_odd = Page(
            page_number=1, width_pt=612.0, height_pt=792.0,
            margin_top_pt=36.0, margin_bottom_pt=36.0,
            margin_inside_pt=36.0, margin_outside_pt=36.0
        )
        self.page_even = Page(
            page_number=2, width_pt=612.0, height_pt=792.0,
            margin_top_pt=36.0, margin_bottom_pt=36.0,
            margin_inside_pt=36.0, margin_outside_pt=36.0
        )

    def tearDown(self) -> None:
        if os.path.exists(self.dummy_img_path):
            os.remove(self.dummy_img_path)

    def test_single_sided_blank_backs(self) -> None:
        """Verifies even numbered pages are completely blank when single-sided is enabled."""
        settings = {
            "single_sided": True,
            "artwork_path": self.dummy_img_path
        }
        
        # Odd page should contain the image
        vectors_odd = self.generator.generate_page_objects(self.page_odd, "Coloring Page", settings)
        self.assertEqual(len(self.page_odd.images), 1)
        self.assertEqual(self.page_odd.images[0]["file_path"], self.dummy_img_path)
        
        # Even page should have no images or vectors (completely blank)
        vectors_even = self.generator.generate_page_objects(self.page_even, "Coloring Page", settings)
        self.assertEqual(len(vectors_even), 0)
        self.assertEqual(len(self.page_even.images), 0)

    def test_artwork_scaling_fit_vs_stretch(self) -> None:
        """Verifies image scaling calculates geometry rectangles accurately within printable limits."""
        settings = {
            "single_sided": False,
            "scale_mode": "stretch",
            "artwork_path": self.dummy_img_path,
            "border_style": "None"
        }
        
        # Stretch mode should exactly match printable width/height
        # w = 612, inside=36, outside=36 -> print width = 540
        # h = 792, top=36, bottom=36 -> print height = 720
        self.generator.generate_page_objects(self.page_odd, "Coloring Page", settings)
        img_geom = self.page_odd.images[0]["geometry"]
        self.assertEqual(img_geom["width"], 540.0)
        self.assertEqual(img_geom["height"], 720.0)
        
        # Fit mode with vertical orientation dummy (800x1000)
        # Ratio of fit inside 540x720: min(540/800, 720/1000) = min(0.675, 0.72) = 0.675
        # width = 800 * 0.675 = 540. height = 1000 * 0.675 = 675.
        settings["scale_mode"] = "fit"
        self.generator.generate_page_objects(self.page_odd, "Coloring Page", settings)
        img_geom_fit = self.page_odd.images[0]["geometry"]
        self.assertEqual(img_geom_fit["width"], 540.0)
        self.assertEqual(img_geom_fit["height"], 675.0)

    def test_outline_quality_validation(self) -> None:
        """Verifies outline brightness check triggers warnings for low contrast input."""
        settings = {
            "single_sided": False,
            "artwork_path": self.dummy_img_path
        }
        
        # Clean dummy outlines image should pass
        self.generator.generate_page_objects(self.page_odd, "Coloring Page", settings)
        self.assertEqual(self.page_odd.validation_state["status"], "passed")
        
        # Create a mostly black (very dark) dummy image
        dark_img_path = os.path.abspath("test_dummy_dark.png")
        from PIL import Image
        img = Image.new("RGB", (400, 400), "black")
        img.save(dark_img_path)
        
        try:
            settings["artwork_path"] = dark_img_path
            self.generator.generate_page_objects(self.page_odd, "Coloring Page", settings)
            # Low average brightness should trigger warning/error status
            self.assertEqual(self.page_odd.validation_state["status"], "warning")
            self.assertIn("average brightness is low", self.page_odd.validation_state["message"])
        finally:
            if os.path.exists(dark_img_path):
                os.remove(dark_img_path)


class TestColoringCommands(unittest.TestCase):
    """Tests GenerateColoringPagesCommand, ReplaceArtworkCommand, BatchImportArtworkCommand, and ShuffleArtworkCommand."""
    
    def setUp(self) -> None:
        self.project = BookProject(name="My Coloring Book", book_type="Coloring Book")
        self.event_bus = EventBus()
        self.received = []
        self.event_bus.subscribe("PROJECT_MODIFIED", self._collect)

        self.dummy1 = os.path.abspath("dummy1.png")
        self.dummy2 = os.path.abspath("dummy2.png")
        from PIL import Image
        Image.new("RGB", (100, 100), "white").save(self.dummy1)
        Image.new("RGB", (100, 100), "white").save(self.dummy2)

    def tearDown(self) -> None:
        self.event_bus.unsubscribe("PROJECT_MODIFIED", self._collect)
        if os.path.exists(self.dummy1):
            os.remove(self.dummy1)
        if os.path.exists(self.dummy2):
            os.remove(self.dummy2)

    def _collect(self, event: Event) -> None:
        self.received.append(event)

    def test_generate_pages_command_undo_redo(self) -> None:
        cmd = GenerateColoringPagesCommand(
            project=self.project,
            page_count=6,
            trim_width_in=8.5,
            trim_height_in=11.0,
            margin_top_in=0.5,
            margin_bottom_in=0.5,
            margin_inside_in=0.5,
            margin_outside_in=0.5,
            has_bleed=True,
            settings={"single_sided": True, "artwork_paths": [self.dummy1, self.dummy2]}
        )
        
        # Execute
        self.assertTrue(cmd.execute())
        self.assertEqual(len(self.project.pages), 6)
        # Page 1 (odd) has dummy1 image
        self.assertEqual(len(self.project.pages[0].images), 1)
        self.assertEqual(self.project.pages[0].images[0]["file_path"], self.dummy1)
        # Page 2 (even) is blank back
        self.assertEqual(len(self.project.pages[1].images), 0)
        # Page 3 (odd) has dummy2 image
        self.assertEqual(self.project.pages[2].images[0]["file_path"], self.dummy2)
        
        # Undo
        self.assertTrue(cmd.undo())
        self.assertEqual(len(self.project.pages), 0)
        
        # Redo
        self.assertTrue(cmd.redo())
        self.assertEqual(len(self.project.pages), 6)

    def test_replace_artwork_command(self) -> None:
        # Generate 2 blank pages first
        self.project.pages = [
            Page(page_number=1, width_pt=612.0, height_pt=792.0),
            Page(page_number=2, width_pt=612.0, height_pt=792.0)
        ]
        
        cmd = ReplaceArtworkCommand(
            project=self.project,
            page_index=0,
            new_artwork_path=self.dummy2,
            settings={"single_sided": False}
        )
        
        self.assertTrue(cmd.execute())
        self.assertEqual(len(self.project.pages[0].images), 1)
        self.assertEqual(self.project.pages[0].images[0]["file_path"], self.dummy2)
        
        # Undo
        self.assertTrue(cmd.undo())
        self.assertEqual(len(self.project.pages[0].images), 0)

    def test_batch_import_command(self) -> None:
        cmd = BatchImportArtworkCommand(
            project=self.project,
            artwork_paths=[self.dummy1, self.dummy2],
            settings={"single_sided": True}
        )
        
        self.assertTrue(cmd.execute())
        # Single-sided means:
        # Page 1 (dummy1 image)
        # Page 2 (blank back page)
        # Page 3 (dummy2 image)
        # Page 4 (blank back page)
        # Total = 4 pages
        self.assertEqual(len(self.project.pages), 4)
        self.assertEqual(self.project.pages[0].images[0]["file_path"], self.dummy1)
        self.assertEqual(len(self.project.pages[1].images), 0)
        self.assertEqual(self.project.pages[2].images[0]["file_path"], self.dummy2)
        
        self.assertTrue(cmd.undo())
        self.assertEqual(len(self.project.pages), 0)

    def test_shuffle_artwork_command(self) -> None:
        # Generate with dummy1 and dummy2
        cmd_gen = GenerateColoringPagesCommand(
            project=self.project,
            page_count=4,
            trim_width_in=8.5, trim_height_in=11.0,
            margin_top_in=0.5, margin_bottom_in=0.5,
            margin_inside_in=0.5, margin_outside_in=0.5,
            has_bleed=True,
            settings={"single_sided": True, "artwork_paths": [self.dummy1, self.dummy2]}
        )
        cmd_gen.execute()
        
        # Shuffling
        cmd_shuffle = ShuffleArtworkCommand(self.project, {"single_sided": True})
        self.assertTrue(cmd_shuffle.execute())
        self.assertEqual(len(self.project.pages), 4)
        
        # Undo should restore original pages
        self.assertTrue(cmd_shuffle.undo())
        self.assertEqual(self.project.pages[0].images[0]["file_path"], self.dummy1)


class TestColoringWorkspaceIntegration(unittest.TestCase):
    """Verifies Coloring Book Studio registers correctly and loads dynamic sidebar panels."""
    
    @classmethod
    def setUpClass(cls) -> None:
        # Clear icon cache
        from core.icon_manager import IconManager
        IconManager()._cache.clear()
        
        cls.app = KDPStudioApp()
        cls.app.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.app.destroy()

    def setUp(self) -> None:
        self.patcher_confirm = patch("tkinter.messagebox.askyesno", return_value=True)
        self.patcher_info = patch("tkinter.messagebox.showinfo")
        self.patcher_err = patch("tkinter.messagebox.showerror")
        
        self.mock_confirm = self.patcher_confirm.start()
        self.mock_info = self.patcher_info.start()
        self.mock_err = self.patcher_err.start()

        # Route app view to Coloring Book Studio
        self.view = self.app._lazy_load_view("Coloring Book Studio")
        self.app.select_frame("Coloring Book Studio")
        self.controller = self.view.controller
        self.controller.engine.close_project()

    def tearDown(self) -> None:
        self.patcher_confirm.stop()
        self.patcher_info.stop()
        self.patcher_err.stop()
        self.controller.engine.close_project()

    def test_coloring_studio_swaps_panel_correctly(self) -> None:
        """Verifies PropertiesPanel right sidebar swaps standard fields with ColoringSettingsPanel."""
        self.controller.create_project("My Coloring Book", "Coloring Book", {})
        self.app.update()
        
        properties_panel = self.view.properties_panel
        self.assertIsInstance(properties_panel.plugin_panel, ColoringSettingsPanel)
        self.assertEqual(properties_panel.active_project_type, "Coloring Book")

    def test_notebook_and_coloring_studios_coexist(self) -> None:
        """Verifies both studios are registered inside the centralized StudioRegistry singleton."""
        registry = StudioRegistry()
        
        # Verify Notebook Studio registration
        meta_notebook = registry.get_studio_metadata("notebook")
        self.assertIsNotNone(meta_notebook)
        self.assertEqual(meta_notebook.name, "Notebook Studio")
        
        # Verify Coloring Book Studio registration
        meta_coloring = registry.get_studio_metadata("Coloring Book")
        self.assertIsNotNone(meta_coloring)
        self.assertEqual(meta_coloring.name, "Coloring Book Studio")


if __name__ == "__main__":
    unittest.main()
