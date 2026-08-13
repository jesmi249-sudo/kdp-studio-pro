import unittest
from unittest.mock import patch, MagicMock
import customtkinter as ctk

from ui.app import KDPStudioApp
from ui.views.book_builder import BookBuilderView, PropertiesPanel
from ui.views.notebook_studio import NotebookStudioView, NotebookSettingsPanel
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.templates.notebook import NotebookTemplateGenerator
from book_builder.commands.notebook_commands import GenerateNotebookPagesCommand
from book_builder.studio_registry import StudioRegistry
from book_builder.events.bus import EventBus
from book_builder.events.event import Event


class TestNotebookTemplateGenerator(unittest.TestCase):
    """Verifies that NotebookTemplateGenerator generates ruled/grid layouts correctly."""
    
    def setUp(self) -> None:
        self.generator = NotebookTemplateGenerator()
        self.page = Page(
            page_number=1,
            width_pt=612.0,  # 8.5"
            height_pt=792.0,  # 11"
            margin_top_pt=36.0,
            margin_bottom_pt=36.0,
            margin_inside_pt=36.0,
            margin_outside_pt=36.0
        )

    def test_blank_template(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Blank", {})
        self.assertEqual(len(vectors), 0)

    def test_ruled_template(self) -> None:
        vectors = self.generator.generate_page_objects(
            self.page, "Ruled", 
            {"line_spacing_pt": 24.0, "mirror_margins": False, "gutter_pt": 0.0, "show_vertical_margin": True}
        )
        self.assertGreater(len(vectors), 0)
        
        # First vector is the vertical red margin line
        margin_line = vectors[0]
        self.assertEqual(margin_line["shape_type"], "line")
        self.assertEqual(margin_line["geometry"]["width"], 0.0)
        self.assertEqual(margin_line["properties"]["stroke_color"], "#FF9999")
        
        # Subsequent vectors are horizontal lines
        horiz_line = vectors[1]
        self.assertEqual(horiz_line["shape_type"], "line")
        self.assertEqual(horiz_line["geometry"]["height"], 0.0)
        self.assertEqual(horiz_line["geometry"]["x"], 36.0)

    def test_college_ruled_template(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "College Ruled", {})
        # Spacing is 20.25 pt. Height printable is 720 pt. Lines ~ 35.
        self.assertGreater(len(vectors), 30)

    def test_wide_ruled_template(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Wide Ruled", {})
        # Spacing is 24.75 pt. Lines ~ 28.
        self.assertGreater(len(vectors), 25)

    def test_graph_template(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Graph", {"grid_spacing_pt": 36.0})
        # Spacing 36 pt. printable width 540 (16 vertical lines). printable height 720 (21 horiz lines).
        self.assertGreater(len(vectors), 30)
        for obj in vectors:
            self.assertEqual(obj["shape_type"], "line")

    def test_dot_grid_template(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Dot Grid", {"dot_spacing": 36.0, "dot_size": 2.0})
        # printable size 540x720. 16 cols x 21 rows = 336 dots.
        self.assertGreater(len(vectors), 300)
        for obj in vectors:
            self.assertEqual(obj["shape_type"], "ellipse")
            self.assertEqual(obj["geometry"]["width"], 2.0)
            self.assertEqual(obj["geometry"]["height"], 2.0)


class TestGenerateNotebookPagesCommand(unittest.TestCase):
    """Verifies execution, undo, and redo of GenerateNotebookPagesCommand."""
    
    def setUp(self) -> None:
        self.project = BookProject(name="Test Notebook Project", book_type="Notebook")
        self.event_bus = EventBus()
        self.received = []
        self.event_bus.subscribe("PROJECT_MODIFIED", self._collect)

    def tearDown(self) -> None:
        self.event_bus.unsubscribe("PROJECT_MODIFIED", self._collect)

    def _collect(self, event: Event) -> None:
        self.received.append(event)

    def test_command_execution_undo_redo(self) -> None:
        cmd = GenerateNotebookPagesCommand(
            project=self.project,
            page_count=50,
            trim_width_in=6.0,
            trim_height_in=9.0,
            margin_top_in=0.5,
            margin_bottom_in=0.5,
            margin_inside_in=0.75,
            margin_outside_in=0.5,
            has_bleed=True,
            template_type="College Ruled"
        )
        
        # Execute
        success = cmd.execute()
        self.assertTrue(success)
        self.assertEqual(len(self.project.pages), 50)
        self.assertEqual(self.project.trim_width_in, 6.0)
        self.assertEqual(self.project.trim_height_in, 9.0)
        self.assertEqual(self.project.has_bleed, True)
        self.assertEqual(len(self.received), 1)
        
        # Undo
        success_undo = cmd.undo()
        self.assertTrue(success_undo)
        self.assertEqual(len(self.project.pages), 0)
        self.assertEqual(self.project.trim_width_in, 8.5)  # Restored default
        self.assertEqual(len(self.received), 2)
        
        # Redo
        success_redo = cmd.redo()
        self.assertTrue(success_redo)
        self.assertEqual(len(self.project.pages), 50)
        self.assertEqual(self.project.trim_width_in, 6.0)
        self.assertEqual(len(self.received), 3)


class TestNotebookWorkspaceIntegration(unittest.TestCase):
    """Verifies full workspace integration of Notebook Studio dynamic panel hosting."""
    
    @classmethod
    def setUpClass(cls) -> None:
        # Clear icon cache to prevent interpreter errors
        from core.icon_manager import IconManager
        IconManager()._cache.clear()
        
        cls.app = KDPStudioApp()
        cls.app.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.app.destroy()

    def setUp(self) -> None:
        # Mock widgets dialogs
        self.patcher_confirm = patch("tkinter.messagebox.askyesno", return_value=True)
        self.patcher_info = patch("tkinter.messagebox.showinfo")
        self.patcher_err = patch("tkinter.messagebox.showerror")
        
        self.mock_confirm = self.patcher_confirm.start()
        self.mock_info = self.patcher_info.start()
        self.mock_err = self.patcher_err.start()

        # Load view
        self.view = self.app._lazy_load_view("Notebook Studio")
        self.app.select_frame("Notebook Studio")
        self.controller = self.view.controller
        self.controller.engine.close_project()

    def tearDown(self) -> None:
        self.patcher_confirm.stop()
        self.patcher_info.stop()
        self.patcher_err.stop()
        self.controller.engine.close_project()

    def test_notebook_studio_view_swaps_panel(self) -> None:
        """Verifies BookBuilderView swaps standard metadata with NotebookSettingsPanel for Notebook projects."""
        self.controller.create_project("My Notebook", "Notebook", {})
        self.app.update()
        
        # Properties panel right sidebar should host NotebookSettingsPanel
        properties_panel = self.view.properties_panel
        self.assertIsInstance(properties_panel.plugin_panel, NotebookSettingsPanel)
        self.assertEqual(properties_panel.active_project_type, "Notebook")

    def test_apply_notebook_template_flow(self) -> None:
        """Verifies filling form and applying template executes command and inserts pages."""
        self.controller.create_project("My Empty Notebook", "Notebook", {})
        self.app.update()
        
        panel: NotebookSettingsPanel = self.view.properties_panel.plugin_panel
        
        # Configure panel widgets directly
        panel.preset_var.set("Wide Ruled")
        panel.trim_var.set("6 x 9 in")
        panel.first_different_var.set(False)
        panel.page_count_entry.delete(0, "end")
        panel.page_count_entry.insert(0, "120")
        
        # Trigger apply button command
        panel._on_apply_template()
        self.app.update()
        
        project = self.controller.engine.get_active_project()
        self.assertEqual(len(project.pages), 120)
        self.assertEqual(project.trim_width_in, 6.0)
        self.assertEqual(project.trim_height_in, 9.0)
        self.assertEqual(project.pages[0].vector_objects[0]["shape_type"], "line")


if __name__ == "__main__":
    unittest.main()
