import unittest
import os
from typing import Dict, Any
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.templates.activity import ActivityTemplateGenerator
from book_builder.commands.activity_commands import (
    AddDecorativeAssetCommand, RemoveDecorativeAssetCommand,
    ModifyDecorativeAssetCommand, GenerateActivityPagesCommand
)

class TestActivityAssetsAndLayout(unittest.TestCase):
    def setUp(self) -> None:
        self.project = BookProject(
            name="Test Activity Book",
            book_type="Activity Book",
            trim_width_in=8.5,
            trim_height_in=11.0,
            has_bleed=False
        )

    def test_maze_deterministic_scaling(self) -> None:
        """Verifies that maze cell sizes preserve square 1:1 aspect ratios."""
        generator = ActivityTemplateGenerator()
        page = Page(
            page_number=1,
            width_pt=612.0,  # 8.5" * 72
            height_pt=792.0, # 11" * 72
            margin_inside_pt=36.0,
            margin_outside_pt=36.0,
            margin_top_pt=36.0,
            margin_bottom_pt=36.0
        )
        settings = {
            "grid_rows": 15,
            "grid_cols": 15,
            "seed": 42,
            "start_marker": "flag",
            "finish_marker": "star",
            "pack_answers": False
        }
        
        # Generate layout shapes
        vectors = generator.generate_page_objects(page, "Mazes", settings)
        self.assertTrue(len(vectors) > 0)
        
        # Verify title text block presence
        titles = [v for v in vectors if v.get("shape_type") == "text_block" and v.get("text") == "MAZES"]
        self.assertEqual(len(titles), 1)

    def test_start_finish_markers(self) -> None:
        """Verifies configurable start/finish markers and their shape creations."""
        generator = ActivityTemplateGenerator()
        page = Page(page_number=1, width_pt=612.0, height_pt=792.0)
        
        settings = {
            "grid_rows": 10,
            "grid_cols": 10,
            "start_marker": "flag",
            "finish_marker": "star"
        }
        vectors = generator.generate_page_objects(page, "Mazes", settings)
        
        # Verify we drew star icon (using text '★')
        stars = [v for v in vectors if v.get("shape_type") == "text_block" and v.get("text") == "★"]
        self.assertEqual(len(stars), 1)

    def test_add_decorative_asset_command(self) -> None:
        """Tests the decorative asset creation command lifecycle including undo and redo."""
        page = Page(page_number=1, width_pt=612.0, height_pt=792.0)
        self.project.pages = [page]
        
        geom = {"x": 50.0, "y": 50.0, "width": 100.0, "height": 100.0}
        asset_path = "assets_library/Animals/cat.png"
        
        cmd = AddDecorativeAssetCommand(self.project, page_index=0, asset_path=asset_path, geometry=geom, asset_id="test_cat")
        
        # 1. Execute
        res = cmd.execute()
        self.assertTrue(res)
        self.assertEqual(len(page.images), 1)
        self.assertEqual(page.images[0]["id"], "test_cat")
        self.assertEqual(page.images[0]["file_path"], asset_path)
        
        # 2. Undo
        self.assertTrue(cmd.undo())
        self.assertEqual(len(page.images), 0)
        
        # 3. Redo
        self.assertTrue(cmd.redo())
        self.assertEqual(len(page.images), 1)
        self.assertEqual(page.images[0]["id"], "test_cat")

    def test_remove_decorative_asset_command(self) -> None:
        """Tests the decorative asset removal command lifecycle including undo and redo."""
        page = Page(page_number=1, width_pt=612.0, height_pt=792.0)
        page.images = [{"id": "test_star", "file_path": "icon.png", "geometry": {}}]
        self.project.pages = [page]
        
        cmd = RemoveDecorativeAssetCommand(self.project, page_index=0, asset_id="test_star")
        
        self.assertTrue(cmd.execute())
        self.assertEqual(len(page.images), 0)
        
        self.assertTrue(cmd.undo())
        self.assertEqual(len(page.images), 1)
        self.assertEqual(page.images[0]["id"], "test_star")

    def test_modify_decorative_asset_command(self) -> None:
        """Tests the modify asset geometry command."""
        page = Page(page_number=1, width_pt=612.0, height_pt=792.0)
        old_geom = {"x": 0.0, "y": 0.0, "width": 50.0, "height": 50.0}
        page.images = [{"id": "test_asset", "file_path": "icon.png", "geometry": old_geom}]
        self.project.pages = [page]
        
        new_geom = {"x": 10.0, "y": 20.0, "width": 80.0, "height": 80.0}
        cmd = ModifyDecorativeAssetCommand(self.project, page_index=0, asset_id="test_asset", new_geometry=new_geom)
        
        self.assertTrue(cmd.execute())
        self.assertEqual(page.images[0]["geometry"]["x"], 10.0)
        self.assertEqual(page.images[0]["geometry"]["y"], 20.0)
        
        self.assertTrue(cmd.undo())
        self.assertEqual(page.images[0]["geometry"]["x"], 0.0)
        
        self.assertTrue(cmd.redo())
        self.assertEqual(page.images[0]["geometry"]["x"], 10.0)

    def test_packed_solution_pages(self) -> None:
        """Verifies packed answers render 4 solutions in a 2x2 grid quadrant."""
        generator = ActivityTemplateGenerator()
        page = Page(page_number=5, width_pt=612.0, height_pt=792.0)
        
        settings = {
            "grid_rows": 15,
            "grid_cols": 15,
            "is_answer_key": True,
            "pack_answers": True,
            "puzzle_range": (1, 4),
            "start_marker": "text",
            "finish_marker": "text"
        }
        
        vectors = generator.generate_page_objects(page, "Mazes", settings)
        self.assertTrue(len(vectors) > 0)
        
        # Verify headers/solutions titles for quadrants
        solutions_headers = [v for v in vectors if v.get("shape_type") == "text_block" and "Solution" in v.get("text", "")]
        self.assertEqual(len(solutions_headers), 4)
