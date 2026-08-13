import unittest
from unittest.mock import patch, MagicMock
import os
import random

from ui.app import KDPStudioApp
from ui.views.book_builder import BookBuilderView, WorkspaceController
from ui.views.activity_studio import ActivityBookStudioView, ActivitySettingsPanel
from ui.views.notebook_studio import NotebookStudioView
from ui.views.coloring_studio import ColoringStudioView
from ui.views.planner_studio import PlannerStudioView

from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.templates.activity import ActivityTemplateGenerator

# Import generators
from book_builder.generators.maze_generator import MazeGenerator
from book_builder.generators.sudoku_generator import SudokuGenerator
from book_builder.generators.wordsearch_generator import WordSearchGenerator
from book_builder.generators.crossword_generator import CrosswordGenerator
from book_builder.generators.tracing_generator import TracingGenerator
from book_builder.generators.dot_to_dot_generator import DotToDotGenerator
from book_builder.generators.matching_generator import MatchingGenerator

# Import commands
from book_builder.commands.activity_commands import (
    GenerateActivityPagesCommand, RegenerateActivityCommand,
    ShuffleActivityCommand, ReplaceArtworkCommand, DuplicateActivityPageCommand,
    DeleteActivityPageCommand, BatchGenerateActivitiesCommand
)

from book_builder.studio_registry import StudioRegistry
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from book_builder.rendering.engine import RenderingEngine


class TestActivityGenerators(unittest.TestCase):
    """Verifies internal logic, stability, and outputs of all 8 puzzle generators."""
    def test_maze_generator(self) -> None:
        gen = MazeGenerator(rows=10, cols=10, seed=123)
        walls, path = gen.generate()
        self.assertTrue(len(walls) > 0)
        self.assertTrue(len(path) >= 10)
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (9, 9))

    def test_sudoku_generator(self) -> None:
        # Easy
        gen_easy = SudokuGenerator(difficulty="Easy", seed=42)
        solved, puzzle = gen_easy.generate()
        easy_zeros = sum(row.count(0) for row in puzzle)
        self.assertEqual(easy_zeros, 35)
        
        # Hard
        gen_hard = SudokuGenerator(difficulty="Hard", seed=42)
        _, puzzle_hard = gen_hard.generate()
        hard_zeros = sum(row.count(0) for row in puzzle_hard)
        self.assertEqual(hard_zeros, 54)

    def test_wordsearch_generator(self) -> None:
        gen = WordSearchGenerator(size=12, words=["PYTHON", "PUZZLE"], seed=99)
        grid, placed, solution = gen.generate()
        self.assertEqual(len(grid), 12)
        self.assertIn("PYTHON", placed)
        self.assertIn("PYTHON", solution)
        self.assertTrue(len(solution["PYTHON"]) == 6)

    def test_crossword_generator(self) -> None:
        gen = CrosswordGenerator(size=10, seed=1234)
        grid, across, down = gen.generate()
        self.assertEqual(len(grid), 10)
        self.assertTrue(len(across) + len(down) > 0)

    def test_tracing_generator(self) -> None:
        gen = TracingGenerator()
        letter_paths = gen.get_letter_paths('A')
        self.assertTrue(len(letter_paths) > 0)
        number_paths = gen.get_number_paths('1')
        self.assertTrue(len(number_paths) > 0)
        shape_paths = gen.get_shape_paths('star')
        self.assertTrue(len(shape_paths) > 0)

    def test_dot_to_dot_generator(self) -> None:
        gen = DotToDotGenerator()
        points = gen.generate("house")
        self.assertTrue(len(points) >= 5)
        for x, y in points:
            self.assertTrue(0.0 <= x <= 1.0)
            self.assertTrue(0.0 <= y <= 1.0)

    def test_matching_generator(self) -> None:
        gen = MatchingGenerator(seed=888)
        left, right, solutions = gen.generate()
        self.assertEqual(len(left), 5)
        self.assertEqual(len(right), 5)
        self.assertEqual(len(solutions), 5)


class TestActivityCommands(unittest.TestCase):
    """Tests all low-level activity book undo/redo commands."""
    def setUp(self) -> None:
        self.project = BookProject(name="My Activity Book", book_type="Activity Book")
        self.event_bus = EventBus()
        self.received = []
        self.event_bus.subscribe("PROJECT_MODIFIED", self._collect)
        self.event_bus.subscribe("BatchGenerateActivitiesCommand", self._collect)

    def tearDown(self) -> None:
        self.event_bus.unsubscribe("PROJECT_MODIFIED", self._collect)
        self.event_bus.unsubscribe("BatchGenerateActivitiesCommand", self._collect)

    def _collect(self, event: Event) -> None:
        self.received.append(event)

    def test_generate_activity_command(self) -> None:
        cmd = GenerateActivityPagesCommand(
            project=self.project,
            page_count=6,
            trim_width_in=8.5,
            trim_height_in=11.0,
            margin_top_in=0.5,
            margin_bottom_in=0.5,
            margin_inside_in=0.5,
            margin_outside_in=0.5,
            has_bleed=False,
            activity_type="Mazes",
            settings={"include_answer_key": True}
        )
        self.assertTrue(cmd.execute())
        # 6 puzzles + 6 answer key pages = 12 total pages
        self.assertEqual(len(self.project.pages), 12)
        
        self.assertTrue(cmd.undo())
        self.assertEqual(len(self.project.pages), 0)
        
        self.assertTrue(cmd.redo())
        self.assertEqual(len(self.project.pages), 12)

    def test_regenerate_activity_command(self) -> None:
        self.project.pages = [Page(page_number=1), Page(page_number=2)]
        cmd = RegenerateActivityCommand(self.project, 0, {"activity_type": "Sudoku"})
        self.assertTrue(cmd.execute())
        self.assertTrue(len(self.project.pages[0].vector_objects) > 0)
        
        self.assertTrue(cmd.undo())
        self.assertEqual(len(self.project.pages[0].vector_objects), 0)

    def test_shuffle_activity_command(self) -> None:
        self.project.pages = [Page(page_number=1)]
        cmd = ShuffleActivityCommand(self.project, 0, {"activity_type": "Word Search"})
        self.assertTrue(cmd.execute())
        
        self.assertTrue(cmd.undo())

    def test_replace_artwork_command(self) -> None:
        self.project.pages = [Page(page_number=1)]
        cmd = ReplaceArtworkCommand(self.project, 0, "Crossword", {})
        self.assertTrue(cmd.execute())
        self.assertTrue(len(self.project.pages[0].vector_objects) > 0)
        
        self.assertTrue(cmd.undo())
        self.assertEqual(len(self.project.pages[0].vector_objects), 0)

    def test_duplicate_and_delete_page_commands(self) -> None:
        self.project.pages = [Page(page_number=1), Page(page_number=2)]
        
        cmd_dup = DuplicateActivityPageCommand(self.project, 0)
        self.assertTrue(cmd_dup.execute())
        self.assertEqual(len(self.project.pages), 3)
        
        self.assertTrue(cmd_dup.undo())
        self.assertEqual(len(self.project.pages), 2)
        
        cmd_del = DeleteActivityPageCommand(self.project, 0)
        self.assertTrue(cmd_del.execute())
        self.assertEqual(len(self.project.pages), 1)
        
        self.assertTrue(cmd_del.undo())
        self.assertEqual(len(self.project.pages), 2)

    def test_batch_generate_activities_command(self) -> None:
        cmd = BatchGenerateActivitiesCommand(
            project=self.project,
            page_count=5,
            trim_width_in=8.5,
            trim_height_in=11.0,
            margin_top_in=0.5,
            margin_bottom_in=0.5,
            margin_inside_in=0.5,
            margin_outside_in=0.5,
            has_bleed=False,
            activity_types=["Mazes", "Sudoku", "Word Search"]
        )
        self.assertTrue(cmd.execute())
        self.assertEqual(len(self.project.pages), 5)
        
        self.assertTrue(cmd.undo())
        self.assertEqual(len(self.project.pages), 0)


class TestActivityWorkspaceIntegration(unittest.TestCase):
    """Verifies that Activity Studio loads and integrates with the main KDP App and RenderingEngine."""
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
        self.view = self.app._lazy_load_view("Activity Book Studio")
        self.app.select_frame("Activity Book Studio")
        self.controller = self.view.controller
        self.controller.engine.close_project()

    def tearDown(self) -> None:
        self.patcher_confirm.stop()
        self.patcher_info.stop()
        self.patcher_err.stop()
        self.controller.engine.close_project()

    def test_activity_studio_swaps_panel_correctly(self) -> None:
        self.controller.create_project("My fun activity book", "Activity Book", {})
        self.app.update()
        
        properties_panel = self.view.properties_panel
        self.assertIsInstance(properties_panel.plugin_panel, ActivitySettingsPanel)
        self.assertEqual(properties_panel.active_project_type, "Activity Book")

    def test_rendering_engine_renders_activity_pages(self) -> None:
        self.controller.create_project("My fun activity book", "Activity Book", {})
        # Generate 1 Word Search page
        self.controller.generate_activity(
            page_count=1, trim_width_in=8.5, trim_height_in=11.0,
            margin_top_in=0.5, margin_bottom_in=0.5, margin_inside_in=0.5, margin_outside_in=0.5,
            has_bleed=False, activity_type="Word Search", settings={"include_answer_key": False}
        )
        
        page = self.controller.engine.get_active_project().pages[0]
        # Render page
        engine = RenderingEngine()
        img = engine.render(page, dpi=72)
        self.assertIsNotNone(img)
        self.assertEqual(img.size, (int(8.5 * 72), int(11.0 * 72)))

    def test_notebook_coloring_planner_and_activity_coexist(self) -> None:
        registry = StudioRegistry()
        
        self.assertIsNotNone(registry.get_studio_metadata("notebook"))
        self.assertIsNotNone(registry.get_studio_metadata("Coloring Book"))
        self.assertIsNotNone(registry.get_studio_metadata("Planner"))
        self.assertIsNotNone(registry.get_studio_metadata("Activity Book"))


if __name__ == "__main__":
    unittest.main()
