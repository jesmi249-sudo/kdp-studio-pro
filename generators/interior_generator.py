import os
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import landscape as rl_landscape
from core.logger import get_logger

logger = get_logger(__name__)

class InteriorGenerator:
    """Generates KDP interior pages (ruled, dotted, graph, blank, etc.) using ReportLab."""
    
    def __init__(self):
        # Base mapping of page sizes to inches (Width, Height) in portrait
        self.sizes = {
            "8.5 x 11": (8.5, 11.0),
            "8 x 10": (8.0, 10.0),
            "7 x 10": (7.0, 10.0),
            "6 x 9": (6.0, 9.0),
            "A4": (8.27, 11.69),
            "A5": (5.83, 8.27)
        }

    def _get_page_size_pt(self, size_name: str, is_landscape: bool, bleed: bool):
        w_in, h_in = self.sizes.get(size_name, (8.5, 11.0))
        
        # KDP Bleed adds 0.125" to top, bottom, and outside edges
        if bleed:
            # For a single interior page (assuming symmetric bleed for simplicity in generation, 
            # though true KDP bleed is 0.125 top/bottom/outside, we'll add 0.125 to all sides)
            w_in += 0.25
            h_in += 0.25
            
        if is_landscape:
            w_in, h_in = h_in, w_in
            
        return w_in * 72.0, h_in * 72.0

    def generate_pdf(self, output_path: str, size: str, orientation: str, margins: dict, 
                     bleed: bool, page_numbers: str, template: str, page_count: int):
        """Generates a multi-page PDF based on settings."""
        try:
            is_landscape = (orientation == "Landscape")
            w_pt, h_pt = self._get_page_size_pt(size, is_landscape, bleed)
            
            c = canvas.Canvas(output_path, pagesize=(w_pt, h_pt))
            
            # Margins in points
            m_top = margins.get('top', 0.5) * 72
            m_bottom = margins.get('bottom', 0.5) * 72
            m_inside = margins.get('inside', 0.5) * 72
            m_outside = margins.get('outside', 0.5) * 72
            
            for page_num in range(1, page_count + 1):
                # Calculate effective margins based on odd/even pages (for inside/outside)
                if page_num % 2 != 0:
                    # Odd (Right page)
                    left_margin = m_inside
                    right_margin = m_outside
                else:
                    # Even (Left page)
                    left_margin = m_outside
                    right_margin = m_inside
                    
                self._draw_template(c, template, w_pt, h_pt, m_top, m_bottom, left_margin, right_margin)
                self._draw_page_number(c, page_numbers, page_num, w_pt, h_pt, m_bottom, left_margin, right_margin)
                
                c.showPage()
                
            c.save()
            logger.info(f"Interior generated successfully: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to generate interior PDF: {e}")
            return False

    def _draw_template(self, c: canvas.Canvas, template: str, w: float, h: float, 
                       mt: float, mb: float, ml: float, mr: float):
        """Draws the selected template onto the canvas."""
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.setLineWidth(0.5)
        
        draw_w = w - ml - mr
        draw_h = h - mt - mb
        start_x = ml
        start_y = h - mt # ReportLab origin is bottom-left
        
        if template == "Blank":
            return
            
        elif template in ["College Ruled", "Wide Ruled", "Narrow Ruled"]:
            spacing = {
                "College Ruled": 0.28 * 72, # 9/32 inch
                "Wide Ruled": 0.34 * 72,    # 11/32 inch
                "Narrow Ruled": 0.25 * 72   # 1/4 inch
            }.get(template, 0.28 * 72)
            
            # Draw margin line (typically pink/red in notebooks, we'll stick to gray)
            c.setStrokeColorRGB(0.8, 0.8, 0.8)
            c.setLineWidth(1)
            c.line(start_x + (1.25 * 72), mb, start_x + (1.25 * 72), h - mt)
            
            # Draw horizontal lines
            c.setStrokeColorRGB(0.6, 0.6, 0.6)
            c.setLineWidth(0.5)
            y = start_y - spacing
            while y > mb:
                c.line(start_x, y, w - mr, y)
                y -= spacing
                
        elif template == "Dot Grid":
            spacing = 0.2 * 72 # 5mm spacing approx
            c.setFillColorRGB(0.6, 0.6, 0.6)
            
            y = start_y
            while y >= mb:
                x = start_x
                while x <= w - mr:
                    c.circle(x, y, 0.5, stroke=0, fill=1)
                    x += spacing
                y -= spacing
                
        elif template == "Graph Paper":
            spacing = 0.25 * 72 # 1/4 inch
            
            # Vertical lines
            x = start_x
            while x <= w - mr:
                c.line(x, mb, x, start_y)
                x += spacing
                
            # Horizontal lines
            y = mb
            while y <= start_y:
                c.line(start_x, y, w - mr, y)
                y += spacing
                
        elif template == "Story Paper":
            # Blank box at top, lines at bottom
            box_h = draw_h * 0.4
            c.rect(start_x, start_y - box_h, draw_w, box_h)
            
            spacing = 0.3 * 72
            y = start_y - box_h - spacing
            while y > mb:
                c.line(start_x, y, w - mr, y)
                y -= spacing
                
        # Other templates (Handwriting Practice, Music Staff, Daily Journal, Planner Page)
        # would follow similar drawing logic. We'll default to Blank for unhandled ones to keep it modular.

    def _draw_page_number(self, c: canvas.Canvas, position: str, num: int, 
                          w: float, h: float, mb: float, ml: float, mr: float):
        if position == "None":
            return
            
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0, 0, 0)
        text = str(num)
        
        y = mb / 2 # Center vertically in bottom margin
        
        if position == "Bottom Center":
            c.drawCentredString(w / 2, y, text)
        elif position == "Top Center":
            c.drawCentredString(w / 2, h - (mb / 2), text) # assuming top margin roughly equals bottom margin
        elif position == "Bottom Left":
            c.drawString(ml, y, text)
        elif position == "Bottom Right":
            # approximate width of text
            c.drawRightString(w - mr, y, text)

    def generate_preview(self, output_path: str, size: str, orientation: str, margins: dict, 
                         bleed: bool, template: str):
        """Generates a single page preview image using a temporary PDF."""
        # Since we don't have fitz (PyMuPDF) in requirements by default, 
        # we will generate a high-res PIL Image natively for the preview, mapping ReportLab logic to PIL.
        # However, to save complexity, we can just use the generic PIL drawing for previews.
        w_in, h_in = self.sizes.get(size, (8.5, 11.0))
        if orientation == "Landscape":
            w_in, h_in = h_in, w_in
            
        dpi = 72 # screen preview
        w_px = int(w_in * dpi)
        h_px = int(h_in * dpi)
        
        from PIL import ImageDraw
        img = Image.new('RGB', (w_px, h_px), color='white')
        d = ImageDraw.Draw(img)
        
        # Draw margins box for preview
        ml = int(margins.get('inside', 0.5) * dpi)
        mr = int(margins.get('outside', 0.5) * dpi)
        mt = int(margins.get('top', 0.5) * dpi)
        mb = int(margins.get('bottom', 0.5) * dpi)
        
        d.rectangle([ml, mt, w_px - mr, h_px - mb], outline='red', width=1)
        
        if template != "Blank":
            d.text((w_px/2, h_px/2), f"Template: {template}", fill='gray', anchor="mm")
            
        img.save(output_path)
        return True
