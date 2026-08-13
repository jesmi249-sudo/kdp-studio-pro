"""
Cover Generation Engine for KDP Coloring Book Generator.
Computes KDP-style spine width, and renders/exports full-wrap covers
(back + spine + front) as a front-cover PNG, a vector "Full Wrap" PDF,
and a flattened 300 DPI print-ready PDF.

Fully offline - uses only reportlab / Pillow, no network or API calls.
"""

import os
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any

from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import Color, HexColor, black, white

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .logger import get_logger
from .pdf_engine import TRIM_SIZES, BLEED_SIZE  # reuse existing trim/bleed definitions

logger = get_logger("cover_engine")

# ─── Paper Type Spine Multipliers (inches of spine width per page) ──────────
# Approximate industry-standard KDP paperback spine formulas. Users should
# always confirm final spine width against Amazon KDP's own cover calculator
# before submitting, especially near the low/high end of the page range.
PAPER_TYPES: Dict[str, float] = {
    "White (60lb / 90gsm)": 0.002252,
    "Cream (60lb / 90gsm)": 0.0025,
    "Standard Color (60lb / 90gsm)": 0.002252,
    "Premium Color (70lb / 105gsm)": 0.002263,
}

MIN_PAGES_FOR_TEXT_SPINE = 79  # KDP guidance: spine text generally unsafe below this
DEFAULT_TRIM_SIZE = "8.5 x 11 inches (Letter)"

# Standard font choices available for cover text (ReportLab base-14 fonts,
# guaranteed to work fully offline with no embedded font files required).
COVER_FONTS = [
    "Helvetica",
    "Helvetica-Bold",
    "Helvetica-Oblique",
    "Helvetica-BoldOblique",
    "Times-Roman",
    "Times-Bold",
    "Times-Italic",
    "Times-BoldItalic",
    "Courier",
    "Courier-Bold",
]

# Candidate TrueType font file locations for high-res raster (PNG) export,
# tried in order. Falls back to PIL's built-in bitmap font if none found.
_FONT_FILE_CANDIDATES: Dict[str, List[str]] = {
    "Helvetica": ["arial.ttf", "Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "Helvetica-Bold": ["arialbd.ttf", "Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "Helvetica-Oblique": ["ariali.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"],
    "Helvetica-BoldOblique": ["arialbi.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"],
    "Times-Roman": ["times.ttf", "Times New Roman.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"],
    "Times-Bold": ["timesbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"],
    "Times-Italic": ["timesi.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"],
    "Times-BoldItalic": ["timesbi.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf"],
    "Courier": ["cour.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"],
    "Courier-Bold": ["courbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"],
}

_ttf_cache: Dict[str, Any] = {}


def calculate_spine_width_points(page_count: int, paper_type: str) -> float:
    """
    Calculate spine width in points (72pt = 1 inch) from page count and paper type.

    Args:
        page_count: Total interior page count of the book.
        paper_type: One of the PAPER_TYPES keys.

    Returns:
        Spine width in points. Never returns less than a small minimum
        so the spine panel always remains visible/usable in the editor.
    """
    per_page = PAPER_TYPES.get(paper_type, PAPER_TYPES["White (60lb / 90gsm)"])
    try:
        pages = max(int(page_count), 0)
    except (TypeError, ValueError):
        pages = 0
    width_in = pages * per_page
    width_in = max(width_in, 0.02)  # floor so the panel never collapses to zero
    return width_in * 72.0


def spine_text_is_safe(page_count: int) -> bool:
    """Return True if the page count is high enough for spine text to be advisable."""
    try:
        return int(page_count) >= MIN_PAGES_FOR_TEXT_SPINE
    except (TypeError, ValueError):
        return False


def get_trim_dimensions(trim_size: str):
    """Return (width_pt, height_pt) for a trim size key, defaulting safely."""
    return TRIM_SIZES.get(trim_size, TRIM_SIZES[DEFAULT_TRIM_SIZE])


class CoverLayout:
    """
    Computes the full-wrap geometry (back / spine / front panels) in points,
    given trim size, page count, paper type, and whether bleed is enabled.

    Coordinate space: origin (0, 0) at the bottom-left of the full wrap
    (matching ReportLab's canvas convention), x increasing left -> right
    across [back][spine][front].
    """

    def __init__(self, trim_size: str, page_count: int, paper_type: str, use_bleed: bool = True):
        self.trim_size = trim_size
        self.page_count = page_count
        self.paper_type = paper_type
        self.use_bleed = use_bleed

        self.trim_w, self.trim_h = get_trim_dimensions(trim_size)
        self.bleed = BLEED_SIZE if use_bleed else 0.0
        self.spine_w = calculate_spine_width_points(page_count, paper_type)

        # Full wrap dimensions
        self.total_w = self.bleed + self.trim_w + self.spine_w + self.trim_w + self.bleed
        self.total_h = self.trim_h + (2 * self.bleed)

        # Panel x-ranges (absolute, within the full wrap coordinate space)
        self.back_x0 = 0.0
        self.back_x1 = self.bleed + self.trim_w
        self.spine_x0 = self.back_x1
        self.spine_x1 = self.spine_x0 + self.spine_w
        self.front_x0 = self.spine_x1
        self.front_x1 = self.front_x0 + self.trim_w + self.bleed

        self.y0 = 0.0
        self.y1 = self.total_h

    def panel_rect(self, panel: str):
        """Return (x0, y0, x1, y1) for 'back', 'spine', or 'front'."""
        if panel == "back":
            return (self.back_x0, self.y0, self.back_x1, self.y1)
        if panel == "spine":
            return (self.spine_x0, self.y0, self.spine_x1, self.y1)
        if panel == "front":
            return (self.front_x0, self.y0, self.front_x1, self.y1)
        raise ValueError(f"Unknown panel: {panel}")

    def default_layer_rect(self, panel: str, width: float, height: float):
        """Return a centered (x, y, w, h) rect for a new layer placed on a panel."""
        x0, y0, x1, y1 = self.panel_rect(panel)
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        return (cx - width / 2, cy - height / 2, width, height)


def _resolve_ttf(font_name: str, size: int):
    """Resolve a ReportLab base font name to a usable PIL ImageFont, cached."""
    cache_key = f"{font_name}:{size}"
    if cache_key in _ttf_cache:
        return _ttf_cache[cache_key]

    font = None
    for candidate in _FONT_FILE_CANDIDATES.get(font_name, []):
        try:
            font = ImageFont.truetype(candidate, size)
            break
        except (OSError, IOError):
            continue

    if font is None:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

    _ttf_cache[cache_key] = font
    return font


class CoverEngine:
    """
    Renders a cover design (list of layers) to:
      - A high-resolution front-cover PNG (300 DPI)
      - A vector "Full Wrap" PDF (back + spine + front, single page)
      - A flattened 300 DPI print-ready PDF

    A "layer" is a dict with keys:
      type: "image" | "text"
      x, y, width, height: floats in points, absolute full-wrap coordinates
      For images: path (str)
      For text: text, font, font_size, color (hex str), align
                 ("left"/"center"/"right"), bold, italic, underline, effect
                 ("none"/"shadow"/"outline")
    """

    def __init__(
        self,
        layout: CoverLayout,
        layers: List[Dict[str, Any]],
        background_color: str = "#FFFFFF",
        title: str = "",
        author: str = "",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ):
        self.layout = layout
        self.layers = layers or []
        self.background_color = background_color or "#FFFFFF"
        self.title = title
        self.author = author
        self.progress_callback = progress_callback

    def _report(self, step: int, total: int, message: str):
        if self.progress_callback:
            try:
                self.progress_callback(step, total, message)
            except Exception:
                pass

    # ─── Shared helpers ─────────────────────────────────────────────────────

    def _layers_sorted(self) -> List[Dict[str, Any]]:
        return sorted(self.layers, key=lambda l: l.get("z", 0))

    @staticmethod
    def _hex_to_rl_color(hex_str: str) -> Color:
        try:
            return HexColor(hex_str)
        except Exception:
            return white

    @staticmethod
    def _hex_to_rgb(hex_str: str):
        try:
            h = hex_str.lstrip("#")
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        except Exception:
            return (255, 255, 255)

    # ─── Vector export (ReportLab) ─────────────────────────────────────────

    def build_full_wrap_pdf(self, output_path: str, draw_barcode: bool = True,
                             draw_fold_guides: bool = True, draw_trim_marks: bool = True) -> str:
        """Build a vector full-wrap PDF (back + spine + front on one page)."""
        lo = self.layout
        total_steps = len(self.layers) + 2
        step = 0

        c = rl_canvas.Canvas(output_path, pagesize=(lo.total_w, lo.total_h))
        c.setTitle(self.title or "Cover")
        c.setAuthor(self.author or "")

        step += 1
        self._report(step, total_steps, "Painting background...")
        c.setFillColor(self._hex_to_rl_color(self.background_color))
        c.rect(0, 0, lo.total_w, lo.total_h, fill=1, stroke=0)

        for layer in self._layers_sorted():
            step += 1
            self._report(step, total_steps, f"Drawing layer ({layer.get('type')})...")
            try:
                self._draw_layer_vector(c, layer)
            except Exception as e:
                logger.warning(f"Failed to draw layer on full wrap PDF: {e}")

        if draw_fold_guides:
            self._draw_fold_guides(c)
        if draw_barcode:
            self._draw_barcode_placeholder(c)
        if draw_trim_marks and lo.use_bleed:
            self._draw_trim_marks(c)

        step += 1
        self._report(step, total_steps, "Saving PDF...")
        c.showPage()
        c.save()
        logger.info(f"Full wrap PDF generated: {output_path}")
        return output_path

    def _draw_layer_vector(self, c, layer: Dict[str, Any]):
        x, y = layer.get("x", 0), layer.get("y", 0)
        w, h = layer.get("width", 10), layer.get("height", 10)

        if layer.get("type") == "image":
            path = layer.get("path", "")
            if path and Path(path).exists() and PIL_AVAILABLE:
                img = Image.open(path)
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA")
                c.drawImage(ImageReader(img), x, y, width=w, height=h,
                            preserveAspectRatio=False, mask="auto")
            return

        if layer.get("type") == "text":
            self._draw_text_vector(c, layer)

    def _draw_text_vector(self, c, layer: Dict[str, Any]):
        text = layer.get("text", "")
        if not text:
            return
        font = layer.get("font", "Helvetica-Bold")
        size = float(layer.get("font_size", 24))
        color = self._hex_to_rl_color(layer.get("color", "#000000"))
        align = layer.get("align", "center")
        effect = layer.get("effect", "none")
        x, y, w, h = layer.get("x", 0), layer.get("y", 0), layer.get("width", 100), layer.get("height", 30)

        cx = x + w / 2
        draw_x = {"left": x, "center": cx, "right": x + w}.get(align, cx)
        draw_y = y + h / 2 - size * 0.35  # roughly vertically center the baseline

        def _draw_string(px, py, fill_color):
            c.setFont(font, size)
            c.setFillColor(fill_color)
            if align == "left":
                c.drawString(px, py, text)
            elif align == "right":
                c.drawRightString(px, py, text)
            else:
                c.drawCentredString(px, py, text)

        if effect == "shadow":
            _draw_string(draw_x + 2, draw_y - 2, Color(0, 0, 0, alpha=0.45))
        elif effect == "outline":
            outline_color = black
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                _draw_string(draw_x + dx, draw_y + dy, outline_color)

        _draw_string(draw_x, draw_y, color)

        if layer.get("underline"):
            c.setStrokeColor(color)
            c.setLineWidth(max(size * 0.05, 1))
            text_w = c.stringWidth(text, font, size)
            if align == "left":
                ux0, ux1 = x, x + text_w
            elif align == "right":
                ux0, ux1 = x + w - text_w, x + w
            else:
                ux0, ux1 = cx - text_w / 2, cx + text_w / 2
            c.line(ux0, draw_y - size * 0.15, ux1, draw_y - size * 0.15)

    def _draw_fold_guides(self, c):
        """Draw non-printing dashed guide lines at the spine/panel boundaries."""
        lo = self.layout
        c.saveState()
        c.setStrokeColor(Color(0.6, 0.6, 0.6))
        c.setLineWidth(0.5)
        c.setDash(3, 3)
        for x in (lo.spine_x0, lo.spine_x1):
            c.line(x, 0, x, lo.total_h)
        c.restoreState()

    def _draw_barcode_placeholder(self, c):
        """Draw the standard KDP barcode placeholder box on the back cover."""
        lo = self.layout
        box_w, box_h = 2.0 * 72, 1.2 * 72
        margin = 0.25 * 72
        x = lo.back_x1 - margin - box_w
        y = lo.bleed + margin

        c.saveState()
        c.setFillColor(white)
        c.rect(x, y, box_w, box_h, fill=1, stroke=0)
        c.setStrokeColor(black)
        c.setLineWidth(1)
        c.rect(x, y, box_w, box_h, fill=0, stroke=1)
        c.setFont("Helvetica", 9)
        c.setFillColor(Color(0.3, 0.3, 0.3))
        c.drawCentredString(x + box_w / 2, y + box_h / 2, "ISBN Barcode")
        c.drawCentredString(x + box_w / 2, y + box_h / 2 - 12, "(placeholder)")
        c.restoreState()

    def _draw_trim_marks(self, c):
        lo = self.layout
        c.saveState()
        c.setStrokeColor(black)
        c.setLineWidth(0.25)
        bleed = lo.bleed
        corners = [
            (bleed, bleed), (lo.total_w - bleed, bleed),
            (bleed, lo.total_h - bleed), (lo.total_w - bleed, lo.total_h - bleed),
        ]
        for cx, cy in corners:
            if cx == bleed:
                c.line(0, cy, bleed - 2, cy)
            else:
                c.line(lo.total_w, cy, lo.total_w - bleed + 2, cy)
            if cy == bleed:
                c.line(cx, 0, cx, bleed - 2)
            else:
                c.line(cx, lo.total_h, cx, lo.total_h - bleed + 2)
        c.restoreState()

    # ─── Raster export (Pillow, 300 DPI) ───────────────────────────────────

    def _render_composite_image(self, dpi: int = 300):
        """Render the full wrap as a single high-resolution PIL Image."""
        if not PIL_AVAILABLE:
            raise RuntimeError("Pillow is required for raster export.")

        lo = self.layout
        scale = dpi / 72.0
        px_w = max(int(round(lo.total_w * scale)), 1)
        px_h = max(int(round(lo.total_h * scale)), 1)

        canvas_img = Image.new("RGB", (px_w, px_h), self._hex_to_rgb(self.background_color))

        total_steps = len(self.layers) + 1
        step = 0

        for layer in self._layers_sorted():
            step += 1
            self._report(step, total_steps, f"Rendering layer ({layer.get('type')})...")
            try:
                self._draw_layer_raster(canvas_img, layer, scale, px_h)
            except Exception as e:
                logger.warning(f"Failed to draw layer on raster export: {e}")

        self._draw_barcode_raster(canvas_img, scale, px_h)
        return canvas_img

    def _to_px_rect(self, layer, scale, px_h):
        """Convert a points-space layer rect to a top-left-origin pixel rect."""
        x = layer.get("x", 0) * scale
        y = layer.get("y", 0) * scale
        w = layer.get("width", 10) * scale
        h = layer.get("height", 10) * scale
        # Flip y (ReportLab origin is bottom-left, PIL is top-left)
        top = px_h - (y + h)
        return int(x), int(top), int(w), int(h)

    def _draw_layer_raster(self, canvas_img, layer, scale, px_h):
        x, top, w, h = self._to_px_rect(layer, scale, px_h)
        if w <= 0 or h <= 0:
            return

        if layer.get("type") == "image":
            path = layer.get("path", "")
            if path and Path(path).exists():
                img = Image.open(path)
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                img = img.resize((w, h), Image.Resampling.LANCZOS)
                canvas_img.paste(img, (x, top), img)
            return

        if layer.get("type") == "text":
            self._draw_text_raster(canvas_img, layer, x, top, w, h, scale)

    def _draw_text_raster(self, canvas_img, layer, x, top, w, h, scale):
        text = layer.get("text", "")
        if not text:
            return
        font_name = layer.get("font", "Helvetica-Bold")
        size_pt = float(layer.get("font_size", 24))
        size_px = max(int(round(size_pt * scale)), 1)
        font = _resolve_ttf(font_name, size_px)
        rgb = self._hex_to_rgb(layer.get("color", "#000000"))
        align = layer.get("align", "center")
        effect = layer.get("effect", "none")

        draw = ImageDraw.Draw(canvas_img, "RGBA")
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            text_w, text_h = draw.textsize(text, font=font) if hasattr(draw, "textsize") else (len(text) * size_px // 2, size_px)

        if align == "left":
            tx = x
        elif align == "right":
            tx = x + w - text_w
        else:
            tx = x + (w - text_w) / 2
        ty = top + (h - text_h) / 2

        if effect == "shadow":
            draw.text((tx + 3, ty + 3), text, font=font, fill=(0, 0, 0, 130))
        elif effect == "outline":
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                draw.text((tx + dx, ty + dy), text, font=font, fill=(0, 0, 0, 255))

        draw.text((tx, ty), text, font=font, fill=rgb)

        if layer.get("underline"):
            draw.line((tx, ty + text_h + 2, tx + text_w, ty + text_h + 2), fill=rgb, width=max(size_px // 18, 1))

    def _draw_barcode_raster(self, canvas_img, scale, px_h):
        lo = self.layout
        box_w, box_h = 2.0 * 72 * scale, 1.2 * 72 * scale
        margin = 0.25 * 72 * scale
        x = (lo.back_x1 * scale) - margin - box_w
        y_pts = lo.bleed + 0.25 * 72
        top = px_h - (y_pts * scale) - box_h

        draw = ImageDraw.Draw(canvas_img)
        x0, y0, x1, y1 = int(x), int(top), int(x + box_w), int(top + box_h)
        draw.rectangle([x0, y0, x1, y1], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        font = _resolve_ttf("Helvetica", max(int(12 * scale / 3), 10))
        draw.text((x0 + 10, y0 + box_h / 2 - 14), "ISBN Barcode", font=font, fill=(90, 90, 90))
        draw.text((x0 + 10, y0 + box_h / 2 + 6), "(placeholder)", font=font, fill=(90, 90, 90))

    def build_front_cover_png(self, output_path: str, dpi: int = 300) -> str:
        """Export just the front-cover panel as a high-resolution PNG."""
        composite = self._render_composite_image(dpi=dpi)
        scale = dpi / 72.0
        lo = self.layout
        px_h = composite.height

        x0 = int(lo.front_x0 * scale)
        x1 = int(lo.front_x1 * scale)
        front_img = composite.crop((x0, 0, x1, px_h))
        front_img.save(output_path, "PNG", dpi=(dpi, dpi))
        logger.info(f"Front cover PNG exported: {output_path}")
        return output_path

    def build_print_ready_pdf(self, output_path: str, dpi: int = 300) -> str:
        """
        Build a flattened, 300 DPI print-ready PDF by rasterizing the full
        composite and embedding it as a single full-bleed image. This
        guarantees consistent print resolution regardless of source assets.
        """
        composite = self._render_composite_image(dpi=dpi)
        lo = self.layout

        c = rl_canvas.Canvas(output_path, pagesize=(lo.total_w, lo.total_h))
        c.setTitle(self.title or "Cover (Print Ready)")
        c.setAuthor(self.author or "")
        c.drawImage(ImageReader(composite), 0, 0, width=lo.total_w, height=lo.total_h)

        # Barcode + fold guides are already baked into the raster composite.
        if lo.use_bleed:
            self._draw_trim_marks(c)

        c.showPage()
        c.save()
        logger.info(f"300 DPI print-ready PDF exported: {output_path}")
        return output_path
