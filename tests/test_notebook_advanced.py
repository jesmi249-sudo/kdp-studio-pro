import unittest
import time
import os
from unittest.mock import patch, MagicMock

from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.templates.notebook import NotebookTemplateGenerator, PRESETS
from book_builder.commands.notebook_commands import GenerateNotebookPagesCommand
from book_builder.studio_registry import StudioRegistry
from core.logger import get_logger

logger = get_logger(__name__)


class TestNotebookAdvancedFeatures(unittest.TestCase):
    """Verifies KDP notebook generator layout parameters, presets, and performance scaling."""
    
    def setUp(self) -> None:
        self.generator = NotebookTemplateGenerator()
        self.project = BookProject(name="Advanced Notebook", book_type="Notebook")
        
        # Base 6x9" page setup
        self.page_odd = Page(
            page_number=1, width_pt=432.0, height_pt=648.0,
            margin_top_pt=36.0, margin_bottom_pt=36.0,
            margin_inside_pt=54.0, margin_outside_pt=36.0
        )
        self.page_even = Page(
            page_number=2, width_pt=432.0, height_pt=648.0,
            margin_top_pt=36.0, margin_bottom_pt=36.0,
            margin_inside_pt=54.0, margin_outside_pt=36.0
        )

    # --- 1. Preset Loading Verification ---
    def test_preset_configuration_mapping(self) -> None:
        """Verifies presets map correctly to the layout engine without duplicating code."""
        # College Ruled spacing verification (20.25 pt spacing)
        vectors_college = self.generator.generate_page_objects(self.page_odd, "College Ruled", {})
        lines_college = [v for v in vectors_college if v["shape_type"] == "line" and v["geometry"]["height"] == 0.0]
        
        # Wide Ruled spacing verification (24.75 pt spacing)
        vectors_wide = self.generator.generate_page_objects(self.page_odd, "Wide Ruled", {})
        lines_wide = [v for v in vectors_wide if v["shape_type"] == "line" and v["geometry"]["height"] == 0.0]
        
        # College Ruled has closer spacing, so it should generate more lines than Wide Ruled
        self.assertGreater(len(lines_college), len(lines_wide))

    # --- 2. Gutter & Mirrored Margins Layout Calculations ---
    def test_mirror_margins_and_gutter_shift(self) -> None:
        """Verifies inside gutter shifts print areas to the right on odd pages and left on even pages."""
        settings = {
            "mirror_margins": True,
            "gutter_pt": 18.0,  # 0.25 inch gutter
            "layout_type": "ruled",
            "show_vertical_margin": True
        }
        
        # Odd page (inside margin on Left)
        # Left margin = margin_inside (54) + gutter (18) = 72
        # Right margin = margin_outside (36)
        # Printable start x = 72
        vectors_odd = self.generator.generate_page_objects(self.page_odd, "Ruled", settings)
        h_lines_odd = [v for v in vectors_odd if v["shape_type"] == "line" and v["geometry"]["height"] == 0.0]
        for line in h_lines_odd:
            # Lines should start after the vertical red margin line, which is shifted by left margin (x >= 72)
            self.assertGreaterEqual(line["geometry"]["x"], 72.0)
            
        # Even page (inside margin on Right)
        # Left margin = margin_outside (36)
        # Right margin = margin_inside (54) + gutter (18) = 72
        # Printable start x = 36, end x = width (432) - 72 = 360
        vectors_even = self.generator.generate_page_objects(self.page_even, "Ruled", settings)
        h_lines_even = [v for v in vectors_even if v["shape_type"] == "line" and v["geometry"]["height"] == 0.0]
        for line in h_lines_even:
            self.assertGreaterEqual(line["geometry"]["x"], 36.0)
            self.assertLessEqual(line["geometry"]["x"] + line["geometry"]["width"], 360.0)

    # --- 3. Dynamic Headers, Footers, and Page Number Alignments ---
    def test_headers_footers_and_page_number_alignment(self) -> None:
        """Verifies page numbering alignments swap dynamically for outside pages layout."""
        settings = {
            "header_text": "My Custom Journal",
            "footer_text": "Confidential",
            "show_page_numbers": True,
            "page_number_alignment": "Outside"
        }
        
        # Odd page numbering should be right-aligned
        vectors_odd = self.generator.generate_page_objects(self.page_odd, "Ruled", settings)
        txt_blocks_odd = [v for v in vectors_odd if v["shape_type"] == "text_block"]
        
        # Verify page number text block alignment is right
        page_num_odd = [t for t in txt_blocks_odd if t["text"] == "1"][0]
        self.assertEqual(page_num_odd["properties"]["alignment"], "right")
        
        # Even page numbering should be left-aligned
        vectors_even = self.generator.generate_page_objects(self.page_even, "Ruled", settings)
        txt_blocks_even = [v for v in vectors_even if v["shape_type"] == "text_block"]
        
        page_num_even = [t for t in txt_blocks_even if t["text"] == "2"][0]
        self.assertEqual(page_num_even["properties"]["alignment"], "left")

    # --- 4. First Page Different Rule ---
    def test_first_page_different_skips_layout(self) -> None:
        """Verifies that enabling 'first_page_different' leaves Page 1 blank (or as belongs-to) and formats page 2."""
        settings = {
            "first_page_different": True,
            "show_page_numbers": True,
            "layout_type": "ruled"
        }
        
        # Page 1 (first page) -> Should generate introductory "Belongs To" block instead of ruled lines
        vectors_p1 = self.generator.generate_page_objects(self.page_odd, "Ruled", settings)
        ruled_lines_p1 = [v for v in vectors_p1 if v["shape_type"] == "line" and v["properties"].get("stroke_color") == "#D0D4DC"]
        self.assertEqual(len(ruled_lines_p1), 0)
        
        # Verify page belongs-to text block exists
        belongs_to_txt = [t for t in vectors_p1 if t["shape_type"] == "text_block" and "Belongs To" in t["text"]]
        self.assertEqual(len(belongs_to_txt), 1)
        
        # Page 2 (second page) -> Should generate standard ruled lines
        vectors_p2 = self.generator.generate_page_objects(self.page_even, "Ruled", settings)
        ruled_lines_p2 = [v for v in vectors_p2 if v["shape_type"] == "line" and v["properties"].get("stroke_color") == "#D0D4DC"]
        self.assertGreater(len(ruled_lines_p2), 0)

    # --- 5. Performance Scaling Benchmarks (500 Pages) ---
    def test_large_notebook_generation_performance(self) -> None:
        """Benchmarks in-memory page generation and layout mapping for a 500-page notebook."""
        settings = {
            "gutter_pt": 9.0,
            "mirror_margins": True,
            "first_page_different": True,
            "show_page_numbers": True,
            "page_number_alignment": "Outside",
            "header_text": "Large Book Header",
            "show_header_line": True,
            "line_spacing_pt": 20.25,
            "line_color": "#404040",
            "line_thickness": 0.5
        }
        
        cmd = GenerateNotebookPagesCommand(
            project=self.project,
            page_count=500,
            trim_width_in=6.0,
            trim_height_in=9.0,
            margin_top_in=0.5,
            margin_bottom_in=0.5,
            margin_inside_in=0.75,
            margin_outside_in=0.5,
            has_bleed=False,
            template_type="College Ruled",
            settings=settings
        )
        
        # Measure execution time
        start_time = time.perf_counter()
        success = cmd.execute()
        end_time = time.perf_counter()
        
        elapsed = end_time - start_time
        logger.info(f"BENCHMARK: Generated 500 pages in {elapsed:.4f} seconds")
        
        self.assertTrue(success)
        self.assertEqual(len(self.project.pages), 500)
        
        # Ensure generation runs under the 1.0 second threshold limit (usually takes ~0.08s)
        self.assertLess(elapsed, 1.0, f"Performance bottleneck: 500-page layout generation took {elapsed:.2f}s (target < 1.0s)")

    # --- 6. Only Regenerate Affected Pages Optimization ---
    def test_incremental_page_regeneration(self) -> None:
        """Verifies that page regeneration reuses unchanged page instances to prevent redundant canvas invalidation."""
        settings = {
            "gutter_pt": 9.0,
            "mirror_margins": True,
            "show_page_numbers": True
        }
        
        cmd = GenerateNotebookPagesCommand(
            project=self.project,
            page_count=10,
            trim_width_in=6.0,
            trim_height_in=9.0,
            margin_top_in=0.5,
            margin_bottom_in=0.5,
            margin_inside_in=0.75,
            margin_outside_in=0.5,
            has_bleed=False,
            template_type="Ruled",
            settings=settings
        )
        cmd.execute()
        
        # Get references to the generated pages
        original_pages = list(self.project.pages)
        original_page_ids = [p.id for p in original_pages]
        
        # Re-execute with IDENTICAL settings -> Should reuse all page instances (same UUIDs and object references)
        cmd2 = GenerateNotebookPagesCommand(
            project=self.project,
            page_count=10,
            trim_width_in=6.0,
            trim_height_in=9.0,
            margin_top_in=0.5,
            margin_bottom_in=0.5,
            margin_inside_in=0.75,
            margin_outside_in=0.5,
            has_bleed=False,
            template_type="Ruled",
            settings=settings
        )
        cmd2.execute()
        
        reused_pages = list(self.project.pages)
        reused_page_ids = [p.id for p in reused_pages]
        
        # Verify complete object and ID reuse!
        for i in range(10):
            self.assertIs(reused_pages[i], original_pages[i])
            self.assertEqual(reused_page_ids[i], original_page_ids[i])
            
        # Re-execute with DIFFERENT settings (e.g. changing spacing) -> Should generate new page objects
        modified_settings = {**settings, "line_spacing_pt": 30.0}
        cmd3 = GenerateNotebookPagesCommand(
            project=self.project,
            page_count=10,
            trim_width_in=6.0,
            trim_height_in=9.0,
            margin_top_in=0.5,
            margin_bottom_in=0.5,
            margin_inside_in=0.75,
            margin_outside_in=0.5,
            has_bleed=False,
            template_type="Ruled",
            settings=modified_settings
        )
        cmd3.execute()
        
        new_pages = list(self.project.pages)
        for i in range(10):
            # Object references should differ because spacing changed lines layouts
            self.assertIsNot(new_pages[i], original_pages[i])


if __name__ == "__main__":
    unittest.main()
