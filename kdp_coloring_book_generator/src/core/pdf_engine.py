"""
PDF Generation Engine for KDP Coloring Book Generator.
Generates print-ready PDFs with title page, copyright page,
'This Book Belongs To' page, coloring pages, and thank you page.
Fully offline, Amazon KDP compliant.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional, List

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import Color, black, gray

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .logger import get_logger

logger = get_logger("pdf_engine")

# ─── Trim Size Definitions (in points, 1 inch = 72 points) ──────────────────

TRIM_SIZES = {
    "5 x 8 inches": (5 * 72, 8 * 72),
    "5.5 x 8.5 inches": (5.5 * 72, 8.5 * 72),
    "6 x 9 inches": (6 * 72, 9 * 72),
    "7 x 10 inches": (7 * 72, 10 * 72),
    "8 x 10 inches": (8 * 72, 10 * 72),
    "8.5 x 8.5 inches (Square)": (8.5 * 72, 8.5 * 72),
    "8.5 x 11 inches (Letter)": (8.5 * 72, 11 * 72),
}

BLEED_SIZE = 0.125 * 72  # 0.125 inches in points


class PDFEngine:
    """
    Generates a complete KDP-compliant coloring book PDF.
    
    Pages generated (in order):
      1. Title Page
      2. Copyright Page
      3. 'This Book Belongs To' Page
      4. Coloring Pages (one image per page, numbered)
      5. Thank You Page
    """

    def __init__(
        self,
        output_path: str,
        title: str,
        subtitle: str = "",
        author: str = "",
        trim_size: str = "8.5 x 11 inches (Letter)",
        use_bleed: bool = True,
        images: Optional[List[str]] = None,
        num_pages: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ):
        """
        Initialize the PDF engine.
        
        Args:
            output_path: Full path for the output PDF file.
            title: Book title.
            subtitle: Book subtitle.
            author: Author name.
            trim_size: One of the TRIM_SIZES keys.
            use_bleed: Whether to add 0.125" bleed on each edge.
            images: List of image file paths for coloring pages.
            num_pages: Max number of coloring pages (None = use all images).
            progress_callback: Function(current, total, message) for progress updates.
        """
        self.output_path = output_path
        self.title = title
        self.subtitle = subtitle
        self.author = author
        self.use_bleed = use_bleed
        self.images = images or []
        self.num_pages = num_pages
        self.progress_callback = progress_callback

        # Resolve trim dimensions
        self.trim_w, self.trim_h = TRIM_SIZES.get(trim_size, (8.5 * 72, 11 * 72))
        self.bleed = BLEED_SIZE if use_bleed else 0

        # Page dimensions (trim + bleed on each side)
        self.page_w = self.trim_w + (2 * self.bleed)
        self.page_h = self.trim_h + (2 * self.bleed)

        # Determine actual number of coloring pages
        if self.num_pages and self.num_pages > 0:
            self.actual_pages = min(self.num_pages, len(self.images))
        else:
            self.actual_pages = len(self.images)

        # Total pages: title + copyright + belongs_to + coloring_pages + thank_you
        self.total_steps = self.actual_pages + 4

        logger.info(
            f"PDFEngine initialized: '{title}', {self.actual_pages} coloring pages, "
            f"trim={trim_size}, bleed={'Yes' if use_bleed else 'No'}"
        )

    def _report_progress(self, current: int, message: str):
        """Report progress via callback if available."""
        if self.progress_callback:
            try:
                self.progress_callback(current, self.total_steps, message)
            except Exception:
                pass

    def generate(self) -> str:
        """
        Generate the complete PDF.
        
        Returns:
            The output file path on success.
            
        Raises:
            RuntimeError: If generation fails.
        """
        logger.info(f"Starting PDF generation: {self.output_path}")

        try:
            c = canvas.Canvas(self.output_path, pagesize=(self.page_w, self.page_h))
            c.setTitle(self.title)
            c.setAuthor(self.author)
            c.setSubject(f"Coloring Book - {self.title}")
            c.setCreator("KDP Coloring Book Generator")

            step = 0

            # 1. Title Page
            step += 1
            self._report_progress(step, "Generating title page...")
            self._draw_title_page(c)
            c.showPage()

            # 2. Copyright Page
            step += 1
            self._report_progress(step, "Generating copyright page...")
            self._draw_copyright_page(c)
            c.showPage()

            # 3. 'This Book Belongs To' Page
            step += 1
            self._report_progress(step, "Generating 'belongs to' page...")
            self._draw_belongs_to_page(c)
            c.showPage()

            # 4. Coloring Pages
            for i in range(self.actual_pages):
                step += 1
                self._report_progress(step, f"Processing image {i + 1} of {self.actual_pages}...")
                self._draw_coloring_page(c, self.images[i], i + 1)
                c.showPage()

            # 5. Thank You Page
            step += 1
            self._report_progress(step, "Generating thank you page...")
            self._draw_thank_you_page(c)
            c.showPage()

            c.save()
            logger.info(f"PDF generated successfully: {self.output_path}")
            self._report_progress(self.total_steps, "Complete!")
            return self.output_path

        except Exception as e:
            logger.error(f"PDF generation failed: {e}", exc_info=True)
            raise RuntimeError(f"PDF generation failed: {e}") from e

    # ─── Title Page ────────────────────────────────────────────────────────────

    def _draw_title_page(self, c):
        """Draw the title page with title, subtitle, and author centered."""
        cx = self.page_w / 2
        cy = self.page_h / 2

        # Title
        c.setFont("Helvetica-Bold", 36)
        c.setFillColor(black)

        # Word-wrap title if too long
        title_lines = self._wrap_text(self.title, 36, self.trim_w - 2 * 72)
        title_y = cy + 60
        for line in title_lines:
            c.drawCentredString(cx, title_y, line)
            title_y -= 44

        # Subtitle
        if self.subtitle:
            c.setFont("Helvetica", 18)
            c.setFillColor(Color(0.3, 0.3, 0.3))
            subtitle_lines = self._wrap_text(self.subtitle, 18, self.trim_w - 2 * 72)
            sub_y = title_y - 20
            for line in subtitle_lines:
                c.drawCentredString(cx, sub_y, line)
                sub_y -= 24

        # Author
        if self.author:
            c.setFont("Helvetica", 16)
            c.setFillColor(Color(0.4, 0.4, 0.4))
            c.drawCentredString(cx, self.bleed + 1.5 * 72, f"by {self.author}")

        # Decorative line
        c.setStrokeColor(Color(0.7, 0.7, 0.7))
        c.setLineWidth(1)
        line_y = cy - 40
        c.line(cx - 100, line_y, cx + 100, line_y)

        # Draw trim marks
        if self.use_bleed:
            self._draw_trim_marks(c)

    # ─── Copyright Page ────────────────────────────────────────────────────────

    def _draw_copyright_page(self, c):
        """Draw the copyright page."""
        cx = self.page_w / 2
        year = datetime.now().year

        c.setFont("Helvetica", 11)
        c.setFillColor(Color(0.3, 0.3, 0.3))

        lines = [
            f"\u00A9 {year} {self.author}" if self.author else f"\u00A9 {year}",
            "",
            "All rights reserved.",
            "",
            "No part of this publication may be reproduced,",
            "distributed, or transmitted in any form or by any means,",
            "without the prior written permission of the author.",
            "",
            "",
            f"Title: {self.title}",
        ]
        if self.author:
            lines.append(f"Author: {self.author}")
        lines.extend([
            "",
            "Printed in the United States of America",
            "",
            "First Edition",
        ])

        # Position text in the lower third of the page
        start_y = self.page_h * 0.45
        line_height = 16

        for i, line in enumerate(lines):
            c.drawCentredString(cx, start_y - (i * line_height), line)

        if self.use_bleed:
            self._draw_trim_marks(c)

    # ─── 'This Book Belongs To' Page ──────────────────────────────────────────

    def _draw_belongs_to_page(self, c):
        """Draw the 'This Book Belongs To' page with a decorative layout."""
        cx = self.page_w / 2
        cy = self.page_h / 2

        # Header text
        c.setFont("Helvetica-Bold", 28)
        c.setFillColor(black)
        c.drawCentredString(cx, cy + 80, "This Book")
        c.drawCentredString(cx, cy + 44, "Belongs To:")

        # Decorative line for name
        c.setStrokeColor(Color(0.4, 0.4, 0.4))
        c.setLineWidth(1.5)
        line_y = cy - 20
        c.line(cx - 120, line_y, cx + 120, line_y)

        # Small decorative dots
        c.setFillColor(Color(0.5, 0.5, 0.5))
        c.circle(cx - 130, line_y, 3, fill=1, stroke=0)
        c.circle(cx + 130, line_y, 3, fill=1, stroke=0)

        # Date line
        c.setFont("Helvetica", 12)
        c.setFillColor(Color(0.5, 0.5, 0.5))
        c.drawCentredString(cx, cy - 80, "Date: _______________")

        # Decorative border (simple rectangle inside trim)
        c.setStrokeColor(Color(0.8, 0.8, 0.8))
        c.setLineWidth(2)
        margin = 0.75 * 72
        c.rect(
            self.bleed + margin,
            self.bleed + margin,
            self.trim_w - 2 * margin,
            self.trim_h - 2 * margin,
            fill=0,
        )

        if self.use_bleed:
            self._draw_trim_marks(c)

    # ─── Coloring Page ─────────────────────────────────────────────────────────

    def _draw_coloring_page(self, c, img_path: str, page_number: int):
        """
        Draw a single coloring page with the image centered and page number.
        
        Args:
            c: ReportLab canvas.
            img_path: Path to the image file.
            page_number: Page number to display.
        """
        # Margins for image placement (inside trim area)
        margin = 0.5 * 72  # 0.5 inch from trim edge
        page_num_space = 0.4 * 72  # Space reserved for page number at bottom

        img_area_w = self.trim_w - (2 * margin)
        img_area_h = self.trim_h - (2 * margin) - page_num_space

        try:
            if not Path(img_path).exists():
                raise FileNotFoundError(f"Image not found: {img_path}")

            if not PIL_AVAILABLE:
                raise ImportError("Pillow is required for image processing")

            img = Image.open(img_path)

            # Convert to RGB if necessary
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            elif img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Calculate scaling to fit while maintaining aspect ratio
            img_w, img_h = img.size
            scale_x = img_area_w / img_w
            scale_y = img_area_h / img_h
            scale = min(scale_x, scale_y)

            new_w = img_w * scale
            new_h = img_h * scale

            # Center position (accounting for bleed offset)
            x = self.bleed + margin + (img_area_w - new_w) / 2
            y = self.bleed + margin + page_num_space + (img_area_h - new_h) / 2

            # Draw image
            img_reader = ImageReader(img)
            c.drawImage(img_reader, x, y, width=new_w, height=new_h)

            logger.debug(f"Drew image: {Path(img_path).name} at ({x:.1f}, {y:.1f}) "
                        f"size=({new_w:.1f}, {new_h:.1f})")

        except Exception as e:
            # Draw placeholder text if image fails
            logger.warning(f"Failed to draw image '{img_path}': {e}")
            c.setFont("Helvetica", 12)
            c.setFillColor(Color(0.5, 0.5, 0.5))
            c.drawCentredString(
                self.page_w / 2, self.page_h / 2,
                f"[Image not available: {Path(img_path).name}]"
            )

        # Draw page number (centered at bottom, inside trim area)
        c.setFont("Helvetica", 10)
        c.setFillColor(Color(0.4, 0.4, 0.4))
        page_num_y = self.bleed + (0.35 * 72)
        c.drawCentredString(self.page_w / 2, page_num_y, str(page_number))

        # Draw trim marks
        if self.use_bleed:
            self._draw_trim_marks(c)

        # Reset fill color
        c.setFillColor(black)

    # ─── Thank You Page ────────────────────────────────────────────────────────

    def _draw_thank_you_page(self, c):
        """Draw the thank you page."""
        cx = self.page_w / 2
        cy = self.page_h / 2

        # Main thank you text
        c.setFont("Helvetica-Bold", 32)
        c.setFillColor(black)
        c.drawCentredString(cx, cy + 40, "Thank You!")

        # Subtitle
        c.setFont("Helvetica", 16)
        c.setFillColor(Color(0.3, 0.3, 0.3))
        c.drawCentredString(cx, cy - 10, "We hope you enjoyed this coloring book.")

        # Additional message
        c.setFont("Helvetica", 13)
        c.setFillColor(Color(0.4, 0.4, 0.4))
        c.drawCentredString(cx, cy - 50, "If you loved it, please leave a review!")

        # Decorative elements
        c.setStrokeColor(Color(0.7, 0.7, 0.7))
        c.setLineWidth(1)
        c.line(cx - 80, cy + 70, cx + 80, cy + 70)
        c.line(cx - 80, cy - 80, cx + 80, cy - 80)

        # Author credit
        if self.author:
            c.setFont("Helvetica", 12)
            c.setFillColor(Color(0.5, 0.5, 0.5))
            c.drawCentredString(cx, self.bleed + 1.2 * 72, f"- {self.author}")

        if self.use_bleed:
            self._draw_trim_marks(c)

    # ─── Trim Marks ───────────────────────────────────────────────────────────

    def _draw_trim_marks(self, c):
        """Draw trim marks at the corners of the trim area (outside trim, in bleed)."""
        c.saveState()
        c.setStrokeColor(black)
        c.setLineWidth(0.25)

        bleed = self.bleed
        # Trim area corners
        corners = [
            (bleed, bleed),                          # Bottom-left
            (self.page_w - bleed, bleed),             # Bottom-right
            (bleed, self.page_h - bleed),             # Top-left
            (self.page_w - bleed, self.page_h - bleed),  # Top-right
        ]

        for corner_x, corner_y in corners:
            # Horizontal marks
            if corner_x == bleed:
                c.line(0, corner_y, bleed - 2, corner_y)
            else:
                c.line(self.page_w, corner_y, self.page_w - bleed + 2, corner_y)

            # Vertical marks
            if corner_y == bleed:
                c.line(corner_x, 0, corner_x, bleed - 2)
            else:
                c.line(corner_x, self.page_h, corner_x, self.page_h - bleed + 2)

        c.restoreState()

    # ─── Utility ──────────────────────────────────────────────────────────────

    @staticmethod
    def _wrap_text(text: str, font_size: int, max_width: float) -> list:
        """
        Simple word-wrap for centered text.
        Approximates character width as 0.5 * font_size.
        """
        if not text:
            return []

        char_width = font_size * 0.5
        max_chars = int(max_width / char_width)

        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            if len(test_line) <= max_chars:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines if lines else [text]
