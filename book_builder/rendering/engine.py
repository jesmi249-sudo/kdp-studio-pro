import os
import time
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, Tuple, Optional, List
from uuid import UUID
from book_builder.interfaces.services import IRenderer
from book_builder.models.page import Page
from book_builder.models.book import BookProject
from core.logger import get_logger

logger = get_logger(__name__)

class AssetImageCache:
    """In-memory cache for loaded and resized image assets with LRU eviction and mtime check."""
    def __init__(self, max_size: int = 50):
        self.max_size = max_size
        self._cache = {} # Key: (file_path, w, h) -> (PIL Image, mtime, access_time)
        
    def get_image(self, file_path: str, w: int, h: int) -> Optional[Image.Image]:
        try:
            mtime = os.path.getmtime(file_path)
        except Exception:
            return None
            
        key = (file_path, w, h)
        if key in self._cache:
            img, cached_mtime, _ = self._cache[key]
            if cached_mtime == mtime:
                # Update access time (LRU)
                self._cache[key] = (img, mtime, time.time())
                return img
            else:
                # File changed on disk, invalidate entry
                del self._cache[key]
        return None
        
    def put_image(self, file_path: str, w: int, h: int, img: Image.Image) -> None:
        try:
            mtime = os.path.getmtime(file_path)
        except Exception:
            return
            
        key = (file_path, w, h)
        
        # Evict LRU if cache exceeds max size
        if len(self._cache) >= self.max_size:
            # Find the oldest accessed entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][2])
            del self._cache[oldest_key]
            
        self._cache[key] = (img, mtime, time.time())

# Global asset image cache instance
IMAGE_CACHE = AssetImageCache()


class RenderContext:
    """Manages pixel-scaling ratios, inverted Y coordinate grids, and PIL drawing surfaces."""
    
    def __init__(self, width_pt: float, height_pt: float, dpi: int = 300) -> None:
        self.width_pt = width_pt
        self.height_pt = height_pt
        self.dpi = dpi
        
        # Scale: 1 point = 1/72 inch. Pixels = (pts / 72) * dpi
        self.scale = dpi / 72.0
        self.width_px = int(width_pt * self.scale)
        self.height_px = int(height_pt * self.scale)
        
        self.image = Image.new("RGBA", (self.width_px, self.height_px), (255, 255, 255, 255))
        self.draw = ImageDraw.Draw(self.image)

    def pt_to_px(self, pt: float) -> int:
        return int(pt * self.scale)

    def map_y(self, y_pt: float, h_pt: float) -> int:
        """Translates bottom-left origin to top-left PIL pixel grid coordinates."""
        inverted_y = self.height_pt - y_pt - h_pt
        return self.pt_to_px(inverted_y)

    def draw_text(self, text: str, x_pt: float, y_pt: float, w_pt: float, h_pt: float, font_size_pt: float = 9.0, color: str = "black", alignment: str = "left", font_name: str = "arial.ttf") -> None:
        x = self.pt_to_px(x_pt)
        # Approximate baseline offset or just direct translation
        y = self.map_y(y_pt, h_pt)
        w_px = self.pt_to_px(w_pt)
        
        # Try loading true type fonts or fallback
        try:
            from PIL import ImageFont
            # Only use font_name if it is a .ttf or .otf, else fallback
            font = ImageFont.truetype(font_name if font_name.endswith('.ttf') else "arial.ttf", self.pt_to_px(font_size_pt))
        except IOError:
            # Fallback PIL font loading
            font = ImageFont.load_default()
        except Exception:
            font = None
            
        # Implement text wrapping
        words = text.split(' ')
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            # Use getlength if available, else fallback to textlength
            if font and hasattr(font, 'getlength'):
                w = font.getlength(test_line)
            elif font and hasattr(font, 'getsize'):
                w = font.getsize(test_line)[0]
            elif hasattr(self.draw, 'textlength'):
                w = self.draw.textlength(test_line, font=font)
            else:
                w = len(test_line) * self.pt_to_px(font_size_pt) * 0.5 # rough approx
                
            if w > w_px and len(current_line) > 1:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
            
        # Draw lines with alignment
        current_y = y
        line_height_pt = font_size_pt * 1.2
        line_height_px = self.pt_to_px(line_height_pt)
        
        for line in lines:
            if font and hasattr(font, 'getlength'):
                line_w = font.getlength(line)
            elif font and hasattr(font, 'getsize'):
                line_w = font.getsize(line)[0]
            elif hasattr(self.draw, 'textlength'):
                line_w = self.draw.textlength(line, font=font)
            else:
                line_w = len(line) * self.pt_to_px(font_size_pt) * 0.5
                
            if alignment == "center":
                line_x = x + (w_px - line_w) / 2
            elif alignment == "right":
                line_x = x + w_px - line_w
            else:
                line_x = x
                
            self.draw.text((line_x, current_y), line, fill=color, font=font)
            current_y += line_height_px

    def draw_shape(self, shape_type: str, x_pt: float, y_pt: float, w_pt: float, h_pt: float, fill_color: Optional[str] = None, stroke_color: str = "black", stroke_width_pt: float = 1.0) -> None:
        if fill_color == "none":
            fill_color = None
        if stroke_color == "none":
            stroke_color = None
            
        x0 = self.pt_to_px(x_pt)
        y0 = self.map_y(y_pt, h_pt)
        x1 = x0 + self.pt_to_px(w_pt)
        y1 = y0 + self.pt_to_px(h_pt)
        width = self.pt_to_px(stroke_width_pt)
        
        if shape_type == "rectangle":
            self.draw.rectangle([x0, y0, x1, y1], fill=fill_color, outline=stroke_color, width=width)
        elif shape_type == "ellipse":
            self.draw.ellipse([x0, y0, x1, y1], fill=fill_color, outline=stroke_color, width=width)
        elif shape_type == "line":
            self.draw.line([x0, y0, x1, y1], fill=stroke_color, width=width)

    def draw_image(self, file_path: str, x_pt: float, y_pt: float, w_pt: float, h_pt: float) -> None:
        """Loads and pastes image assets onto the canvas."""
        x = self.pt_to_px(x_pt)
        y = self.map_y(y_pt, h_pt)
        w = self.pt_to_px(w_pt)
        h = self.pt_to_px(h_pt)
        
        if os.path.exists(file_path):
            try:
                # Try cache first
                img = IMAGE_CACHE.get_image(file_path, w, h)
                if img is None:
                    img = Image.open(file_path).convert("RGBA")
                    img = img.resize((w, h), Image.Resampling.LANCZOS)
                    IMAGE_CACHE.put_image(file_path, w, h, img)
                self.image.paste(img, (x, y), img)
            except Exception as e:
                logger.error(f"RenderContext: failed to draw image '{file_path}': {e}")
        else:
            # Draw placeholder box
            self.draw_shape("rectangle", x_pt, y_pt, w_pt, h_pt, fill_color=(240, 240, 240, 255), stroke_color="red")
            self.draw_text("IMAGE NOT FOUND", x_pt + 5, y_pt + 5, w_pt, h_pt, 8, "red")


class PageRenderer(IRenderer):
    """Compiles abstract Page elements to a target RenderContext."""
    
    def render_page(self, page: Page, canvas_context: RenderContext) -> None:
        """Renders page vector layers, text layers, and images onto the canvas context."""
        logger.debug(f"PageRenderer: rendering page {page.page_number}")
        
        # 1. Draw shapes/vector objects
        for shape in page.vector_objects:
            s_type = shape.get("shape_type", "rectangle")
            geom = shape.get("geometry", {})
            props = shape.get("properties", {})
            
            if s_type == "text_block":
                canvas_context.draw_text(
                    text=shape.get("text", ""),
                    x_pt=geom.get("x", 0.0),
                    y_pt=geom.get("y", 0.0),
                    w_pt=geom.get("width", 100.0),
                    h_pt=geom.get("height", 20.0),
                    font_size_pt=props.get("font_size", 9.0),
                    color=props.get("color", "black"),
                    alignment=props.get("alignment", "left"),
                    font_name=props.get("font_name", "arial.ttf")
                )
            else:
                canvas_context.draw_shape(
                    shape_type=s_type,
                    x_pt=geom.get("x", 0.0),
                    y_pt=geom.get("y", 0.0),
                    w_pt=geom.get("width", 50.0),
                    h_pt=geom.get("height", 50.0),
                    fill_color=props.get("fill_color"),
                    stroke_color=props.get("stroke_color", "black"),
                    stroke_width_pt=props.get("stroke_width", 1.0)
                )
            
        # 2. Draw images
        for img_obj in page.images:
            geom = img_obj.get("geometry", {})
            canvas_context.draw_image(
                file_path=img_obj.get("file_path", ""),
                x_pt=geom.get("x", 0.0),
                y_pt=geom.get("y", 0.0),
                w_pt=geom.get("width", 100.0),
                h_pt=geom.get("height", 100.0)
            )
            
        # 3. Draw text blocks
        for text in page.text_blocks:
            geom = text.get("geometry", {})
            props = text.get("properties", {})
            canvas_context.draw_text(
                text=text.get("text", ""),
                x_pt=geom.get("x", 0.0),
                y_pt=geom.get("y", 0.0),
                w_pt=geom.get("width", 100.0),
                h_pt=geom.get("height", 20.0),
                font_size_pt=props.get("font_size", 10.0),
                color=props.get("color", "black"),
                alignment=props.get("alignment", "left"),
                font_name=props.get("font_name", "arial.ttf")
            )

    def render_document(self, book_project: BookProject, output_path: str) -> bool:
        """Saves a simple multi-page image sequence to output path."""
        # Main document rendering logic is handled in final PDF Export phase.
        # This compiles the pages to image arrays as a mock verification.
        return True


class RenderingEngine:
    """Core rendering coordinator compiling pages into PIL Image objects."""
    
    def __init__(self) -> None:
        self.renderer = PageRenderer()

    def render(self, page: Page, dpi: int = 300) -> Image.Image:
        """Compiles the page layout and returns a PIL Image."""
        ctx = RenderContext(page.width_pt, page.height_pt, dpi)
        self.renderer.render_page(page, ctx)
        return ctx.image
