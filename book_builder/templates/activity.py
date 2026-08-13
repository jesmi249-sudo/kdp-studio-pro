import os
import random
from typing import List, Dict, Any, Optional
from book_builder.models.page import Page
from book_builder.templates.base import ITemplateGenerator

# Import the registry and layouts so that they are registered
from book_builder.templates.registry import ActivityTemplateRegistry
import book_builder.templates.activity_layouts

from core.logger import get_logger

logger = get_logger(__name__)

class ActivityTemplateGenerator(ITemplateGenerator):
    """
    Template generator for KDP Activity Books.
    Acts as an orchestrator that computes margins, headers, and instructions,
    and delegates the specific puzzle layout rendering to the ActivityTemplateRegistry.
    """
    def generate_page_objects(self, page: Page, template_type: str, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        page.images = []
        page.text_blocks = []
        
        w = page.width_pt
        h = page.height_pt
        
        m_top = page.margin_top_pt if page.margin_top_pt is not None else 36.0
        m_bottom = page.margin_bottom_pt if page.margin_bottom_pt is not None else 36.0
        m_inside = page.margin_inside_pt if page.margin_inside_pt is not None else 36.0
        m_outside = page.margin_outside_pt if page.margin_outside_pt is not None else 36.0
        
        gutter = settings.get("gutter_pt", 0.0)
        mirror = settings.get("mirror_margins", True)
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
        
        printable_w = x_end - x_start
        printable_h = y_end - y_start
        
        vector_objects: List[Dict[str, Any]] = []
        
        theme_color = settings.get("theme_color", "#000000")
        line_color = settings.get("line_color", "#A0A0A0")
        text_color = settings.get("text_color", "#000000")
        
        # Difficulty & seed resolving
        difficulty = settings.get("difficulty", "Medium")
        seed = settings.get("seed")
        if seed is None:
            seed = 42 + page.page_number
        else:
            try:
                seed = int(seed) + page.page_number
            except Exception:
                seed = 42 + page.page_number
                
        is_answer_key = settings.get("is_answer_key", False)
        
        # Heading Title Properties
        title_font = settings.get("font_family", "Helvetica")
        title_size = float(settings.get("title_font_size", 22.0 if is_answer_key else 26.0))
        title_color = settings.get("theme_color", "#000000")
        title_align = settings.get("title_alignment", "center")
        title_spacing = float(settings.get("title_spacing", 20.0))
        
        title_text = settings.get("header_text", "").strip()
        if not title_text:
            title_text = f"{template_type.upper()}"
            if is_answer_key:
                title_text += " (ANSWER KEY)"
                
        # Draw Title
        vector_objects.append({
            "shape_type": "text_block",
            "text": title_text,
            "geometry": {"x": x_start, "y": y_end - title_size - 5.0, "width": printable_w, "height": title_size + 4.0},
            "properties": {"font_size": title_size, "color": title_color, "alignment": title_align, "font_name": title_font}
        })
        
        # Customizable Instruction Text
        instruction_text = settings.get("instruction_text", "Find your way through the maze!" if not is_answer_key else "").strip()
        instruction_size = float(settings.get("instruction_font_size", 11.0))
        instruction_color = settings.get("text_color", "#4A4A4A")
        instruction_align = settings.get("instruction_alignment", "center")
        
        if instruction_text:
            # Draw Instructions below title
            instr_y = y_end - title_size - 10.0 - instruction_size
            vector_objects.append({
                "shape_type": "text_block",
                "text": instruction_text,
                "geometry": {"x": x_start, "y": instr_y, "width": printable_w, "height": instruction_size + 3.0},
                "properties": {"font_size": instruction_size, "color": instruction_color, "alignment": instruction_align, "font_name": title_font}
            })
            content_y_end = instr_y - title_spacing
        else:
            content_y_end = y_end - title_size - 10.0 - title_spacing
            
        content_h = content_y_end - y_start
        
        layout = template_type.lower().replace(" ", "_").replace("-", "_")
        
        # Build context for the layout generator
        context = {
            "x_start": x_start,
            "x_end": x_end,
            "y_start": y_start,
            "printable_w": printable_w,
            "content_h": content_h,
            "theme_color": theme_color,
            "line_color": line_color,
            "text_color": text_color,
            "difficulty": difficulty,
            "seed": seed,
            "is_answer_key": is_answer_key,
            "layout": layout
        }

        # Resolve generator from registry
        generator_class = ActivityTemplateRegistry.get_generator(layout)
        generator_instance = generator_class()
        
        layout_objects = generator_instance.generate_layout(context, settings)
        vector_objects.extend(layout_objects)
                
        # Optional page number at bottom
        show_page_number = settings.get("show_page_number", True)
        if show_page_number:
            align = "right" if is_odd else "left"
            vector_objects.append({
                "shape_type": "text_block",
                "text": str(page.page_number),
                "geometry": {"x": x_start, "y": y_start - 18.0, "width": printable_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": align}
            })
            
        return vector_objects
