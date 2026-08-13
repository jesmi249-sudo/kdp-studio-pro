from reportlab.pdfgen import canvas
from reportlab.lib import colors

class CropMarksDrawer:
    """
    Utility class to draw print crop marks and alignment registration symbols
    on ReportLab canvas objects for KDP print-ready PDF configurations.
    """

    @staticmethod
    def draw_crop_marks(c: canvas.Canvas, width_pt: float, height_pt: float, offset_pt: float = 18.0) -> None:
        """
        Draws crop marks at the 4 corners of the trim box.
        - c: The ReportLab canvas
        - width_pt: The page width including offset margins (trimmed_width + 2 * offset_pt)
        - height_pt: The page height including offset margins (trimmed_height + 2 * offset_pt)
        - offset_pt: The extra page border size (default 18pt = 0.25 inches)
        """
        x_min = offset_pt
        x_max = width_pt - offset_pt
        y_min = offset_pt
        y_max = height_pt - offset_pt
        
        # Line length and gap properties
        mark_len = 12.0
        gap = 3.0
        
        c.saveState()
        c.setStrokeColor(colors.HexColor("#000000"))
        c.setLineWidth(0.5)
        
        # --- 1. Draw corner crop marks ---
        # Bottom-Left
        c.line(x_min - mark_len - gap, y_min, x_min - gap, y_min) # Horiz
        c.line(x_min, y_min - mark_len - gap, x_min, y_min - gap) # Vert
        
        # Bottom-Right
        c.line(x_max + gap, y_min, x_max + mark_len + gap, y_min) # Horiz
        c.line(x_max, y_min - mark_len - gap, x_max, y_min - gap) # Vert
        
        # Top-Left
        c.line(x_min - mark_len - gap, y_max, x_min - gap, y_max) # Horiz
        c.line(x_min, y_max + gap, x_min, y_max + mark_len + gap) # Vert
        
        # Top-Right
        c.line(x_max + gap, y_max, x_max + mark_len + gap, y_max) # Horiz
        c.line(x_max, y_max + gap, x_max, y_max + mark_len + gap) # Vert
        
        # --- 2. Draw registration marks (crosshairs inside circles) at margins ---
        # Draw on 4 sides (center of margins)
        cx = width_pt / 2.0
        cy = height_pt / 2.0
        r = 4.0
        
        centers = [
            (cx, y_min / 2.0), # Bottom
            (cx, height_pt - (offset_pt / 2.0)), # Top
            (x_min / 2.0, cy), # Left
            (width_pt - (offset_pt / 2.0), cy) # Right
        ]
        
        for x, y in centers:
            # Circle
            c.circle(x, y, r, stroke=1, fill=0)
            # Crosshair lines
            c.line(x - r - 3, y, x + r + 3, y)
            c.line(x, y - r - 3, x, y + r + 3)
            
        # --- 3. Draw a color calibration strip at the top margin center ---
        c.restoreState()
