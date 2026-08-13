import os
from typing import List, Dict, Any, Optional
from PIL import Image

from book_builder.models.page import Page
from book_builder.templates.base import ITemplateGenerator
from core.logger import get_logger

logger = get_logger(__name__)


class ColoringTemplateGenerator(ITemplateGenerator):
    """
    Layout generator for coloring books.
    Places illustration images, handles borders, captions, safe margins, and outline validation.
    """
    
    def generate_page_objects(self, page: Page, template_type: str, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Clear existing page sub-lists
        page.images = []
        page.text_blocks = []
        
        # 1. Check if single-sided printing is enabled and this is an even page
        single_sided = settings.get("single_sided", True)
        if single_sided and (page.page_number % 2 == 0):
            # Page is a blank back page, no elements generated
            page.validation_state = {"status": "passed", "type": "blank_back_page"}
            return []
            
        # Determine illustration source for this page
        # Settings should contain artwork_paths or a mapping from page_number to artwork path
        artwork_path = settings.get("artwork_path")
        if not artwork_path:
            # Check list mapping
            artwork_paths = settings.get("artwork_paths", [])
            # Calculate index: since even pages are blank, page 1 maps to idx 0, page 3 maps to idx 1, etc.
            idx = (page.page_number - 1) // 2 if single_sided else (page.page_number - 1)
            if idx < len(artwork_paths):
                artwork_path = artwork_paths[idx]
                
        if not artwork_path or not os.path.exists(artwork_path):
            page.validation_state = {"status": "warning", "message": "No artwork file attached"}
            return []
            
        # 2. Get image dimensions and perform outline validation
        try:
            with Image.open(artwork_path) as img:
                img_w, img_h = img.size
            self._validate_artwork_outline(page, artwork_path)
        except Exception as e:
            logger.error(f"ColoringTemplateGenerator: failed to read image size: {e}")
            img_w, img_h = 800, 600
            page.validation_state = {"status": "error", "message": f"Failed to open image file: {e}"}
            
        # 3. Calculate print area limits
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
        
        # Adjust y_start if caption is enabled
        caption_text = settings.get("caption_text", "").strip()
        has_caption = bool(caption_text)
        caption_space = 25.0 if has_caption else 0.0
        y_start += caption_space
        
        printable_w = x_end - x_start
        printable_h = y_end - y_start
        
        # 4. Calculate scaling & positioning
        scale_mode = settings.get("scale_mode", "fit").lower()
        full_bleed = settings.get("full_bleed", False)
        
        if full_bleed:
            # Fill the entire page (0, 0, w, h)
            target_x = 0.0
            target_y = 0.0
            target_w = w
            target_h = h
        else:
            if scale_mode == "fill":
                # Scale to fill the printable area, cropping excess (centered)
                ratio = max(printable_w / img_w, printable_h / img_h)
                target_w = img_w * ratio
                target_h = img_h * ratio
                target_x = x_start + (printable_w - target_w) / 2.0
                target_y = y_start + (printable_h - target_h) / 2.0
            elif scale_mode == "stretch":
                # Stretch to fill the bounds exactly
                target_x = x_start
                target_y = y_start
                target_w = printable_w
                target_h = printable_h
            else:  # "fit"
                # Fit within margins maintaining aspect ratio
                ratio = min(printable_w / img_w, printable_h / img_h)
                target_w = img_w * ratio
                target_h = img_h * ratio
                target_x = x_start + (printable_w - target_w) / 2.0
                target_y = y_start + (printable_h - target_h) / 2.0
                
        # 5. Populate image definition
        page.images.append({
            "file_path": artwork_path,
            "geometry": {"x": target_x, "y": target_y, "width": target_w, "height": target_h}
        })
        
        vector_objects: List[Dict[str, Any]] = []
        
        # 6. Apply Border Frame if requested (and not full bleed)
        border_style = settings.get("border_style", "None").lower()
        if not full_bleed and border_style != "none":
            # Add thin border
            thick = 1.5 if border_style == "bold" else 0.75
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": y_start, "width": printable_w, "height": printable_h},
                "properties": {"stroke_color": "black", "stroke_width": thick, "fill_color": "none"}
            })
            
        # 7. Add Caption
        if has_caption:
            caption_y = y_start - 18.0
            page.text_blocks.append({
                "text": caption_text,
                "geometry": {"x": x_start, "y": caption_y, "width": printable_w, "height": 12.0},
                "properties": {"font_size": 10.0, "color": "black", "alignment": "center"}
            })
            
        return vector_objects

    def _validate_artwork_outline(self, page: Page, filepath: str) -> None:
        """Validates that artwork contains clean black outlines on white backgrounds."""
        try:
            with Image.open(filepath) as img:
                # Convert to grayscale
                gray = img.convert("L")
                hist = gray.histogram()
                total_pixels = sum(hist)
                if total_pixels == 0:
                    total_pixels = 1
                
                avg_lum = sum(i * count for i, count in enumerate(hist)) / total_pixels
                
                # Check for white space vs outlines
                # Lines should be dark (close to 0), background should be white (close to 255)
                dark_pixels = sum(hist[:60])
                dark_ratio = dark_pixels / total_pixels
                
                # Validation rules:
                # 1. If average luminance is too dark (e.g. under 150), it is likely not a coloring page
                # 2. There should be some dark lines, but not too many (e.g. dark ratio between 0.5% and 25%)
                if avg_lum < 160:
                    page.validation_state = {
                        "status": "warning",
                        "message": f"Artwork average brightness is low ({avg_lum:.1f}). Ensure background is solid white."
                    }
                elif dark_ratio < 0.005:
                    page.validation_state = {
                        "status": "warning",
                        "message": "Too few dark line pixels detected. Ensure the image outlines are dark and visible."
                    }
                elif dark_ratio > 0.35:
                    page.validation_state = {
                        "status": "warning",
                        "message": f"High ratio of dark pixels ({dark_ratio * 100:.1f}%). May contain too much solid black ink."
                    }
                else:
                    page.validation_state = {
                        "status": "passed",
                        "message": f"Outline validation passed. (Avg brightness: {avg_lum:.1f})"
                    }
        except Exception as e:
            page.validation_state = {
                "status": "warning",
                "message": f"Outline validation failed to execute: {e}"
            }
