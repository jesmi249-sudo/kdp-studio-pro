from typing import List, Dict, Any, Optional
from book_builder.models.page import Page
from book_builder.templates.base import ITemplateGenerator
from core.logger import get_logger

logger = get_logger(__name__)

# Reusable Preset Configurations
PRESETS: Dict[str, Dict[str, Any]] = {
    "blank": {
        "layout_type": "blank"
    },
    "ruled": {
        "layout_type": "ruled",
        "line_spacing_pt": 24.0,
        "line_thickness": 0.75,
        "line_color": "#D0D4DC",
        "show_vertical_margin": True
    },
    "college_ruled": {
        "layout_type": "ruled",
        "line_spacing_pt": 20.25,
        "line_thickness": 0.75,
        "line_color": "#D0D4DC",
        "show_vertical_margin": True
    },
    "wide_ruled": {
        "layout_type": "ruled",
        "line_spacing_pt": 24.75,
        "line_thickness": 0.75,
        "line_color": "#D0D4DC",
        "show_vertical_margin": True
    },
    "narrow_ruled": {
        "layout_type": "ruled",
        "line_spacing_pt": 18.0,
        "line_thickness": 0.75,
        "line_color": "#D0D4DC",
        "show_vertical_margin": True
    },
    "graph": {
        "layout_type": "graph",
        "graph_spacing": 18.0,
        "line_thickness": 0.5,
        "line_color": "#E5E8EB"
    },
    "dot_grid": {
        "layout_type": "dot_grid",
        "dot_spacing": 18.0,
        "dot_size": 1.5,
        "line_color": "#A5B0C0"
    },
    "cornell_notes": {
        "layout_type": "cornell",
        "line_spacing_pt": 20.25,
        "cue_column_width_in": 2.25,
        "summary_height_in": 2.0,
        "line_thickness": 0.75,
        "line_color": "#D0D4DC"
    },
    "music_sheet": {
        "layout_type": "music",
        "staff_spacing_pt": 6.0,
        "staff_gap_pt": 28.0,
        "line_thickness": 0.75,
        "line_color": "#808080"
    },
    "handwriting_practice": {
        "layout_type": "handwriting",
        "practice_spacing_pt": 9.0,
        "practice_gap_pt": 24.0,
        "line_thickness": 0.75,
        "mid_line_thickness": 0.5,
        "line_color": "#A0A0A0",
        "mid_line_color": "#C2C6CC"
    }
}


class NotebookTemplateGenerator(ITemplateGenerator):
    """
    Parameter-driven notebook template layout generator.
    Accepts layout configuration options and outputs generic vector/text page structures.
    """
    
    def generate_page_objects(self, page: Page, template_type: str, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Resolve preset and override with settings
        p_name = template_type.lower().replace(" ", "_")
        preset = PRESETS.get(p_name, PRESETS["ruled"]).copy()
        
        # Merge settings over presets
        config = {**preset, **settings}
        
        # Check first page different rule
        if config.get("first_page_different", False) and page.page_number == 1:
            # Generate introductory "Belongs To" page
            return self._generate_belongs_to_page(page)
            
        # Parse sizes and margins
        w = page.width_pt
        h = page.height_pt
        
        m_top = page.margin_top_pt if page.margin_top_pt is not None else 36.0
        m_bottom = page.margin_bottom_pt if page.margin_bottom_pt is not None else 36.0
        m_inside = page.margin_inside_pt if page.margin_inside_pt is not None else 36.0
        m_outside = page.margin_outside_pt if page.margin_outside_pt is not None else 36.0
        
        gutter = config.get("gutter_pt", 0.0)
        mirror = config.get("mirror_margins", False)
        
        # Resolve left and right margins based on odd/even page numbering
        is_odd = (page.page_number % 2 != 0)
        
        if mirror:
            if is_odd:
                m_left = m_inside + gutter
                m_right = m_outside
            else:
                m_left = m_outside
                m_right = m_inside + gutter
        else:
            m_left = m_inside + gutter
            m_right = m_outside
            
        x_start = m_left
        x_end = w - m_right
        y_start = m_bottom
        y_end = h - m_top
        
        width = x_end - x_start
        height = y_end - y_start
        
        vector_objects: List[Dict[str, Any]] = []
        
        # 1. Generate core layout pattern
        l_type = config.get("layout_type", "ruled")
        l_thickness = float(config.get("line_thickness", 0.75))
        l_color = config.get("line_color", "#D0D4DC")
        
        if l_type == "ruled":
            spacing = float(config.get("line_spacing_pt", 24.0))
            
            # Show red vertical margin line
            if config.get("show_vertical_margin", True):
                # Put it at 20% of page width, or standard inside margin
                margin_x = x_start + (54.0 if is_odd else 36.0) if mirror else (x_start + 36.0)
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": margin_x, "y": y_start, "width": 0.0, "height": height},
                    "properties": {"stroke_color": "#FF9999", "stroke_width": 1.0, "fill_color": "none"}
                })
                h_start_x = x_start
            else:
                h_start_x = x_start
                
            # Draw horizontal lines
            y = y_end - spacing
            while y >= y_start:
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": h_start_x, "y": y, "width": x_end - h_start_x, "height": 0.0},
                    "properties": {"stroke_color": l_color, "stroke_width": l_thickness, "fill_color": "none"}
                })
                y -= spacing
                
        elif l_type == "graph":
            spacing = float(config.get("graph_spacing", 18.0))
            
            # Horizontal lines
            y = y_start
            while y <= y_end:
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x_start, "y": y, "width": width, "height": 0.0},
                    "properties": {"stroke_color": l_color, "stroke_width": l_thickness, "fill_color": "none"}
                })
                y += spacing
                
            # Vertical lines
            x = x_start
            while x <= x_end:
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x, "y": y_start, "width": 0.0, "height": height},
                    "properties": {"stroke_color": l_color, "stroke_width": l_thickness, "fill_color": "none"}
                })
                x += spacing
                
        elif l_type == "dot_grid":
            spacing = float(config.get("dot_spacing", 18.0))
            dot_sz = float(config.get("dot_size", 1.5))
            r = dot_sz / 2.0
            
            y = y_start
            while y <= y_end:
                x = x_start
                while x <= x_end:
                    vector_objects.append({
                        "shape_type": "ellipse",
                        "geometry": {"x": x - r, "y": y - r, "width": dot_sz, "height": dot_sz},
                        "properties": {"fill_color": l_color, "stroke_color": l_color, "stroke_width": 0.0}
                    })
                    x += spacing
                y += spacing
                
        elif l_type == "cornell":
            spacing = float(config.get("line_spacing_pt", 20.25))
            cue_w = float(config.get("cue_column_width_in", 2.25)) * 72.0
            sum_h = float(config.get("summary_height_in", 2.0)) * 72.0
            
            # Summary separator line
            y_sum = y_start + sum_h
            vector_objects.append({
                "shape_type": "line",
                "geometry": {"x": x_start, "y": y_sum, "width": width, "height": 0.0},
                "properties": {"stroke_color": l_color, "stroke_width": 1.5, "fill_color": "none"}
            })
            
            # Cue column vertical separator line
            x_cue = x_start + cue_w
            vector_objects.append({
                "shape_type": "line",
                "geometry": {"x": x_cue, "y": y_sum, "width": 0.0, "height": y_end - y_sum},
                "properties": {"stroke_color": l_color, "stroke_width": 1.5, "fill_color": "none"}
            })
            
            # Draw horizontal lines only in the notes/ruled area (above summary, right of cue)
            y = y_end - spacing
            while y >= y_sum:
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x_cue, "y": y, "width": x_end - x_cue, "height": 0.0},
                    "properties": {"stroke_color": l_color, "stroke_width": l_thickness, "fill_color": "none"}
                })
                y -= spacing
                
        elif l_type == "music":
            staff_sp = float(config.get("staff_spacing_pt", 6.0))
            staff_gap = float(config.get("staff_gap_pt", 28.0))
            
            # Draw staves
            y = y_end - 10.0
            while y - (4 * staff_sp) >= y_start:
                # Group of 5 lines
                for i in range(5):
                    line_y = y - (i * staff_sp)
                    vector_objects.append({
                        "shape_type": "line",
                        "geometry": {"x": x_start, "y": line_y, "width": width, "height": 0.0},
                        "properties": {"stroke_color": l_color, "stroke_width": l_thickness, "fill_color": "none"}
                    })
                y -= (4 * staff_sp + staff_gap)
                
        elif l_type == "handwriting":
            pr_sp = float(config.get("practice_spacing_pt", 9.0))
            pr_gap = float(config.get("practice_gap_pt", 24.0))
            m_color = config.get("mid_line_color", "#C2C6CC")
            m_thick = float(config.get("mid_line_thickness", 0.5))
            
            # Draw handwriting practice groups (Top Solid, Mid Dashed, Bottom Solid)
            y = y_end - 10.0
            while y - (2 * pr_sp) >= y_start:
                # Top solid
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x_start, "y": y, "width": width, "height": 0.0},
                    "properties": {"stroke_color": l_color, "stroke_width": l_thickness, "fill_color": "none"}
                })
                # Mid dashed/soft line
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x_start, "y": y - pr_sp, "width": width, "height": 0.0},
                    "properties": {"stroke_color": m_color, "stroke_width": m_thick, "fill_color": "none"}
                })
                # Bottom solid
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x_start, "y": y - (2 * pr_sp), "width": width, "height": 0.0},
                    "properties": {"stroke_color": l_color, "stroke_width": l_thickness, "fill_color": "none"}
                })
                y -= (2 * pr_sp + pr_gap)

        # 2. Page Numbering & Header/Footer text additions (represented as text blocks)
        self._add_decorations(page, config, vector_objects, is_odd, x_start, x_end, y_start, y_end, h)
        
        return vector_objects

    def _add_decorations(self, page: Page, config: Dict[str, Any], vector_objects: List[Dict[str, Any]], 
                        is_odd: bool, x_start: float, x_end: float, y_start: float, y_end: float, page_height: float) -> None:
        """Appends text block primitives representing page numbers, headers, and footers."""
        
        # Running Header
        header_text = config.get("header_text", "").strip()
        show_header_line = config.get("show_header_line", False)
        
        # Running Footer
        footer_text = config.get("footer_text", "").strip()
        show_footer_line = config.get("show_footer_line", False)
        
        # Page numbering
        show_num = config.get("show_page_numbers", False)
        num_align = config.get("page_number_alignment", "Center").lower()
        
        # Header text blocks
        if header_text:
            # Position at 50% height of top margin
            header_y = y_end + (page_height - y_end) / 2.0
            align = self._resolve_alignment(num_align, is_odd)
            
            # Simple text drawing mockup representation
            # We represent text blocks inside page.text_blocks, but templates generate a merged output list.
            # We will write text blocks to the vector_objects list directly as "text_block" custom shape type
            # so the page renderer displays them cleanly.
            vector_objects.append({
                "shape_type": "text_block",
                "text": header_text,
                "geometry": {"x": x_start, "y": header_y, "width": x_end - x_start, "height": 12.0},
                "properties": {"font_size": 9.0, "color": "#505050", "alignment": align}
            })
            
        if show_header_line:
            vector_objects.append({
                "shape_type": "line",
                "geometry": {"x": x_start, "y": y_end + 4.0, "width": x_end - x_start, "height": 0.0},
                "properties": {"stroke_color": "#D3D3D3", "stroke_width": 0.75, "fill_color": "none"}
            })
            
        # Footer text blocks
        if footer_text:
            footer_y = y_start / 2.0
            align = self._resolve_alignment(num_align, is_odd)
            vector_objects.append({
                "shape_type": "text_block",
                "text": footer_text,
                "geometry": {"x": x_start, "y": footer_y, "width": x_end - x_start, "height": 12.0},
                "properties": {"font_size": 9.0, "color": "#505050", "alignment": align}
            })
            
        if show_footer_line:
            vector_objects.append({
                "shape_type": "line",
                "geometry": {"x": x_start, "y": y_start - 4.0, "width": x_end - x_start, "height": 0.0},
                "properties": {"stroke_color": "#D3D3D3", "stroke_width": 0.75, "fill_color": "none"}
            })
            
        # Dynamic Page Numbers
        if show_num:
            footer_y = y_start / 2.0
            align = self._resolve_alignment(num_align, is_odd)
            vector_objects.append({
                "shape_type": "text_block",
                "text": str(page.page_number),
                "geometry": {"x": x_start, "y": footer_y - 2.0, "width": x_end - x_start, "height": 12.0},
                "properties": {"font_size": 9.0, "color": "#303030", "alignment": align}
            })
            
        # Prompts (Date / Title fields)
        show_date = config.get("show_date_field", False)
        show_title = config.get("show_title_field", False)
        
        prompt_y = y_end + 10.0
        
        if show_title:
            title_align = "left" if is_odd else "right"
            vector_objects.append({
                "shape_type": "text_block",
                "text": "Title: _______________________",
                "geometry": {"x": x_start, "y": prompt_y, "width": x_end - x_start, "height": 12.0},
                "properties": {"font_size": 10.0, "color": "#404040", "alignment": title_align}
            })
            
        if show_date:
            date_align = "right" if is_odd else "left"
            vector_objects.append({
                "shape_type": "text_block",
                "text": "Date: _________",
                "geometry": {"x": x_start, "y": prompt_y, "width": x_end - x_start, "height": 12.0},
                "properties": {"font_size": 10.0, "color": "#404040", "alignment": date_align}
            })

    def _resolve_alignment(self, align_type: str, is_odd: bool) -> str:
        if align_type == "outside":
            return "right" if is_odd else "left"
        elif align_type == "inside":
            return "left" if is_odd else "right"
        return "center"

    def _generate_belongs_to_page(self, page: Page) -> List[Dict[str, Any]]:
        """Generates an introductory 'This Book Belongs To' page layout."""
        w = page.width_pt
        h = page.height_pt
        
        cx = w / 2.0
        cy = h / 2.0
        
        return [
            # Title
            {
                "shape_type": "text_block",
                "text": "This Notebook Belongs To:",
                "geometry": {"x": cx - 150.0, "y": cy + 40.0, "width": 300.0, "height": 20.0},
                "properties": {"font_size": 16.0, "color": "#202020", "alignment": "center"}
            },
            # Entry blank line
            {
                "shape_type": "line",
                "geometry": {"x": cx - 120.0, "y": cy - 10.0, "width": 240.0, "height": 0.0},
                "properties": {"stroke_color": "#808080", "stroke_width": 1.0, "fill_color": "none"}
            }
        ]
