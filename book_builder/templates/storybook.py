from typing import List, Dict, Any, Optional
from book_builder.models.page import Page
from book_builder.templates.base import ITemplateGenerator

class StorybookTemplateGenerator(ITemplateGenerator):
    """
    Template generator for Storybook pages.
    Supports layouts like 'full_page', 'image_top_text_bottom', 'text_overlay', 'title_page', 'ending_page'.
    """
    def generate_page_objects(self, page: Page, template_type: str, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        page.images = []
        page.text_blocks = []
        page.vector_objects = []
        
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
        
        layout = settings.get("layout", "image_top_text_bottom")
        
        font_family = settings.get("font_family", "Helvetica")
        font_size = float(settings.get("font_size", 16.0))
        text_color = settings.get("theme_color", "#000000")
        
        story_text = settings.get("text", "")
        image_path = settings.get("image_path", "")
        
        if layout == "title_page":
            title = settings.get("title", "My Storybook")
            author = settings.get("author", "Author Name")
            
            page.text_blocks.append({
                "text": title,
                "geometry": {"x": x_start, "y": y_start + printable_h * 0.6, "width": printable_w, "height": 60.0},
                "properties": {"font_size": 36.0, "color": text_color, "alignment": "center", "font_name": font_family}
            })
            page.text_blocks.append({
                "text": f"By {author}",
                "geometry": {"x": x_start, "y": y_start + printable_h * 0.4, "width": printable_w, "height": 30.0},
                "properties": {"font_size": 24.0, "color": text_color, "alignment": "center", "font_name": font_family}
            })
            if image_path:
                img_sz = min(printable_w, printable_h * 0.3)
                page.images.append({
                    "file_path": image_path,
                    "geometry": {"x": x_start + (printable_w - img_sz) / 2, "y": y_start + printable_h * 0.7, "width": img_sz, "height": img_sz}
                })

        elif layout == "ending_page":
            page.text_blocks.append({
                "text": "The End",
                "geometry": {"x": x_start, "y": y_start + printable_h / 2, "width": printable_w, "height": 60.0},
                "properties": {"font_size": 36.0, "color": text_color, "alignment": "center", "font_name": font_family}
            })
            
        elif layout == "full_page_image":
            if image_path:
                # With bleed? If page has bleed, image should stretch to full w/h
                if page.has_bleed:
                    img_x, img_y, img_w, img_h = 0.0, 0.0, w, h
                else:
                    img_x, img_y, img_w, img_h = x_start, y_start, printable_w, printable_h
                
                page.images.append({
                    "file_path": image_path,
                    "geometry": {"x": img_x, "y": img_y, "width": img_w, "height": img_h}
                })

        elif layout == "image_top_text_bottom":
            img_h = printable_h * 0.65
            if image_path:
                page.images.append({
                    "file_path": image_path,
                    "geometry": {"x": x_start, "y": y_start + (printable_h - img_h), "width": printable_w, "height": img_h}
                })
            if story_text:
                page.text_blocks.append({
                    "text": story_text,
                    "geometry": {"x": x_start, "y": y_start, "width": printable_w, "height": printable_h - img_h - 20.0},
                    "properties": {"font_size": font_size, "color": text_color, "alignment": "center", "font_name": font_family}
                })

        elif layout == "text_top_image_bottom":
            img_h = printable_h * 0.65
            if story_text:
                page.text_blocks.append({
                    "text": story_text,
                    "geometry": {"x": x_start, "y": y_start + img_h + 20.0, "width": printable_w, "height": printable_h - img_h - 20.0},
                    "properties": {"font_size": font_size, "color": text_color, "alignment": "center", "font_name": font_family}
                })
            if image_path:
                page.images.append({
                    "file_path": image_path,
                    "geometry": {"x": x_start, "y": y_start, "width": printable_w, "height": img_h}
                })

        elif layout == "text_overlay":
            if image_path:
                if page.has_bleed:
                    img_x, img_y, img_w, img_h = 0.0, 0.0, w, h
                else:
                    img_x, img_y, img_w, img_h = x_start, y_start, printable_w, printable_h
                page.images.append({
                    "file_path": image_path,
                    "geometry": {"x": img_x, "y": img_y, "width": img_w, "height": img_h}
                })
            
            # Semi-transparent backing for text readability
            if story_text:
                overlay_h = 100.0
                page.vector_objects.append({
                    "shape_type": "rectangle",
                    "geometry": {"x": x_start, "y": y_start, "width": printable_w, "height": overlay_h},
                    "properties": {"fill_color": (255, 255, 255, 200), "stroke_color": "none"}
                })
                page.text_blocks.append({
                    "text": story_text,
                    "geometry": {"x": x_start + 10.0, "y": y_start + 10.0, "width": printable_w - 20.0, "height": overlay_h - 20.0},
                    "properties": {"font_size": font_size, "color": text_color, "alignment": "center", "font_name": font_family}
                })

        else:
            # Fallback pure text page
            if story_text:
                page.text_blocks.append({
                    "text": story_text,
                    "geometry": {"x": x_start, "y": y_start, "width": printable_w, "height": printable_h},
                    "properties": {"font_size": font_size, "color": text_color, "alignment": "left", "font_name": font_family}
                })

        # Page numbering
        show_page_number = settings.get("show_page_number", False)
        if show_page_number and layout not in ("title_page", "ending_page"):
            align = "right" if is_odd else "left"
            page.vector_objects.append({
                "shape_type": "text_block",
                "text": str(page.page_number),
                "geometry": {"x": x_start, "y": y_start - 18.0, "width": printable_w, "height": 10.0},
                "properties": {"font_size": 10.0, "color": text_color, "alignment": align, "font_name": font_family}
            })

        return []
