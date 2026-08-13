import unittest
from unittest.mock import patch, MagicMock
import os
import datetime

from ui.app import KDPStudioApp
from ui.views.book_builder import BookBuilderView, WorkspaceController
from ui.views.planner_studio import PlannerStudioView, PlannerSettingsPanel
from ui.views.notebook_studio import NotebookStudioView
from ui.views.coloring_studio import ColoringStudioView
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.templates.planner import PlannerTemplateGenerator
from book_builder.commands.planner_commands import (
    GeneratePlannerPagesCommand, UpdatePlannerSettingsCommand,
    InsertPlannerSectionCommand, DuplicatePlannerPageCommand, DeletePlannerSectionCommand
)
from book_builder.studio_registry import StudioRegistry
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from book_builder.rendering.engine import RenderingEngine


class TestPlannerTemplateGenerator(unittest.TestCase):
    """Verifies that PlannerTemplateGenerator correctly outputs shapes for all 12 planner types."""
    def setUp(self) -> None:
        self.generator = PlannerTemplateGenerator()
        self.page = Page(page_number=1, width_pt=612.0, height_pt=792.0)
        self.settings = {
            "start_date": "2026-01-01",
            "start_weekday": 0,
            "theme_color": "#000000",
            "line_color": "#D3D3D3",
            "text_color": "#333333",
            "show_page_number": True
        }

    def test_daily_planner(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Daily Planner", self.settings)
        # Verify text block for title/date is added
        self.assertTrue(any(v.get("shape_type") == "text_block" for v in vectors))
        # Verify water drops are added
        self.assertTrue(any(v.get("shape_type") == "ellipse" for v in vectors))

    def test_weekly_planner(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Weekly Planner", self.settings)
        self.assertTrue(len(vectors) > 10)
        # Should have at least 8 day/notes rectangles
        rects = [v for v in vectors if v.get("shape_type") == "rectangle"]
        self.assertTrue(len(rects) >= 8)

    def test_monthly_planner(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Monthly Planner", self.settings)
        # Monthly grid should contain 35 day rectangles (5 rows x 7 cols)
        rects = [v for v in vectors if v.get("shape_type") == "rectangle"]
        # 35 grid cells + any main borders or small boxes
        self.assertTrue(len(rects) >= 35)

    def test_yearly_planner(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Yearly Planner", self.settings)
        rects = [v for v in vectors if v.get("shape_type") == "rectangle"]
        # 12 months boxes + mini day rectangles
        self.assertTrue(len(rects) > 12)

    def test_habit_tracker(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Habit Tracker", self.settings)
        rects = [v for v in vectors if v.get("shape_type") == "rectangle"]
        # 10 habits * 31 days = 310 cells + 10 label boxes
        self.assertTrue(len(rects) >= 320)

    def test_goal_planner(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Goal Tracker", self.settings)
        rects = [v for v in vectors if v.get("shape_type") == "rectangle"]
        self.assertTrue(len(rects) >= 3) # 3 main panel boxes

    def test_budget_planner(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Budget Planner", self.settings)
        rects = [v for v in vectors if v.get("shape_type") == "rectangle"]
        self.assertTrue(len(rects) >= 2) # Expenses box + Income box

    def test_meal_planner(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Meal Planner", self.settings)
        rects = [v for v in vectors if v.get("shape_type") == "rectangle"]
        # 7 days * 4 categories = 28 grid cells + 7 day labels
        self.assertTrue(len(rects) >= 35)

    def test_fitness_planner(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Fitness Planner", self.settings)
        rects = [v for v in vectors if v.get("shape_type") == "rectangle"]
        self.assertTrue(len(rects) >= 3)

    def test_reading_log(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Reading Log", self.settings)
        rects = [v for v in vectors if v.get("shape_type") == "rectangle"]
        self.assertTrue(len(rects) >= 1) # Main table box

    def test_project_planner(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Project Planner", self.settings)
        rects = [v for v in vectors if v.get("shape_type") == "rectangle"]
        self.assertTrue(len(rects) >= 2)

    def test_appointment_planner(self) -> None:
        vectors = self.generator.generate_page_objects(self.page, "Appointment Planner", self.settings)
        rects = [v for v in vectors if v.get("shape_type") == "rectangle"]
        self.assertTrue(len(rects) >= 1)


class TestPlannerCommands(unittest.TestCase):
    """Tests GeneratePlannerPagesCommand, UpdatePlannerSettingsCommand, InsertPlannerSectionCommand, DuplicatePlannerPageCommand, and DeletePlannerSectionCommand."""
    def setUp(self) -> None:
        self.project = BookProject(name="My Low-Content Planner", book_type="Planner")
        self.event_bus = EventBus()
        self.received = []
        self.event_bus.subscribe("PROJECT_MODIFIED", self._collect)

    def tearDown(self) -> None:
        self.event_bus.unsubscribe("PROJECT_MODIFIED", self._collect)

    def _collect(self, event: Event) -> None:
        self.received.append(event)

    def test_generate_pages_command_undo_redo(self) -> None:
        cmd = GeneratePlannerPagesCommand(
            project=self.project,
            page_count=12,
            trim_width_in=8.5,
            trim_height_in=11.0,
            margin_top_in=0.5,
            margin_bottom_in=0.5,
            margin_inside_in=0.5,
            margin_outside_in=0.5,
            has_bleed=False,
            planner_type="Monthly Planner"
        )
        
        self.assertTrue(cmd.execute())
        self.assertEqual(len(self.project.pages), 12)
        self.assertEqual(len(self.received), 1)
        
        # Undo
        self.assertTrue(cmd.undo())
        self.assertEqual(len(self.project.pages), 0)
        
        # Redo
        self.assertTrue(cmd.redo())
        self.assertEqual(len(self.project.pages), 12)

    def test_update_settings_command(self) -> None:
        self.project.pages = [Page(page_number=1), Page(page_number=2)]
        
        cmd = UpdatePlannerSettingsCommand(
            project=self.project,
            settings={"planner_type": "Weekly Planner", "theme_color": "#1A365D"}
        )
        
        self.assertTrue(cmd.execute())
        # The vector objects should have been updated to Weekly Planner
        self.assertTrue(len(self.project.pages[0].vector_objects) > 0)
        
        # Undo
        self.assertTrue(cmd.undo())
        self.assertEqual(len(self.project.pages[0].vector_objects), 0)

    def test_insert_planner_section_command(self) -> None:
        # Generate 2 blank pages first
        self.project.pages = [Page(page_number=1), Page(page_number=2)]
        
        cmd = InsertPlannerSectionCommand(
            project=self.project,
            start_page_number=2,
            page_count=3,
            planner_type="Habit Tracker",
            settings={}
        )
        
        self.assertTrue(cmd.execute())
        # Inserts 3 pages at page_number 2: total 5 pages
        self.assertEqual(len(self.project.pages), 5)
        self.assertEqual(self.project.pages[1].page_number, 2)
        # Check that page numbers are sequential
        for idx, p in enumerate(self.project.pages):
            self.assertEqual(p.page_number, idx + 1)
            
        self.assertTrue(cmd.undo())
        self.assertEqual(len(self.project.pages), 2)

    def test_duplicate_page_command(self) -> None:
        self.project.pages = [Page(page_number=1), Page(page_number=2)]
        self.project.pages[0].vector_objects = [{"shape_type": "ellipse"}]
        
        cmd = DuplicatePlannerPageCommand(project=self.project, page_index=0)
        self.assertTrue(cmd.execute())
        self.assertEqual(len(self.project.pages), 3)
        self.assertEqual(self.project.pages[1].vector_objects[0]["shape_type"], "ellipse")
        
        self.assertTrue(cmd.undo())
        self.assertEqual(len(self.project.pages), 2)

    def test_delete_section_command(self) -> None:
        self.project.pages = [Page(page_number=1), Page(page_number=2), Page(page_number=3), Page(page_number=4)]
        
        cmd = DeletePlannerSectionCommand(project=self.project, start_page_number=2, end_page_number=3)
        self.assertTrue(cmd.execute())
        self.assertEqual(len(self.project.pages), 2)
        self.assertEqual(self.project.pages[1].page_number, 2)
        
        self.assertTrue(cmd.undo())
        self.assertEqual(len(self.project.pages), 4)


class TestPlannerWorkspaceIntegration(unittest.TestCase):
    """Verifies Planner Studio registers correctly and integrates with the Workspace View."""
    @classmethod
    def setUpClass(cls) -> None:
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

        # Load view
        self.view = self.app._lazy_load_view("Planner Studio")
        self.app.select_frame("Planner Studio")
        self.controller = self.view.controller
        self.controller.engine.close_project()

    def tearDown(self) -> None:
        self.patcher_confirm.stop()
        self.patcher_info.stop()
        self.patcher_err.stop()
        self.controller.engine.close_project()

    def test_planner_studio_swaps_panel_correctly(self) -> None:
        self.controller.create_project("My low-content planner", "Planner", {})
        self.app.update()
        
        properties_panel = self.view.properties_panel
        self.assertIsInstance(properties_panel.plugin_panel, PlannerSettingsPanel)
        self.assertEqual(properties_panel.active_project_type, "Planner")

    def test_rendering_engine_renders_planner_pages(self) -> None:
        self.controller.create_project("My low-content planner", "Planner", {})
        # Generate 1 Daily Planner page
        self.controller.generate_planner(
            page_count=1, trim_width_in=8.5, trim_height_in=11.0,
            margin_top_in=0.5, margin_bottom_in=0.5, margin_inside_in=0.5, margin_outside_in=0.5,
            has_bleed=False, planner_type="Daily Planner", settings={}
        )
        
        page = self.controller.engine.get_active_project().pages[0]
        # Render page
        engine = RenderingEngine()
        img = engine.render(page, dpi=72)
        self.assertIsNotNone(img)
        self.assertEqual(img.size, (int(8.5 * 72), int(11.0 * 72)))

    def test_notebook_coloring_and_planner_coexist(self) -> None:
        registry = StudioRegistry()
        
        meta_notebook = registry.get_studio_metadata("notebook")
        self.assertIsNotNone(meta_notebook)
        
        meta_coloring = registry.get_studio_metadata("Coloring Book")
        self.assertIsNotNone(meta_coloring)
        
        meta_planner = registry.get_studio_metadata("Planner")
        self.assertIsNotNone(meta_planner)


if __name__ == "__main__":
    unittest.main()
