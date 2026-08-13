import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import inch
from core.master_page import MasterPageEngine
from core.variable_engine import VariableEngine
from models.planner import PlannerProject
from core.logger import get_logger

logger = get_logger(__name__)

class PlannerEngine:
    """Renders a PlannerProject to a PDF using ReportLab."""
    
    @staticmethod
    def export_pdf(project: PlannerProject, output_path: str) -> bool:
        try:
            logger.info(f"Starting PDF export for planner: {project.name}")
            
            w_pts = project.trim_width * inch
            h_pts = project.trim_height * inch
            
            c = canvas.Canvas(output_path, pagesize=(w_pts, h_pts))
            
            for page in project.pages:
                logger.debug(f"Rendering page {page.page_number}")
                
                # Merge with master page
                objects = MasterPageEngine.get_merged_objects(page, project)
                
                for obj in objects:
                    # Resolve variables
                    resolved_text = VariableEngine.resolve_text(obj.text, page.page_number, page.date_context)
                    
                    x_pts = obj.x
                    # ReportLab origin is bottom-left, our UI is top-left
                    y_pts = h_pts - obj.y - obj.height
                    
                    # Draw Object based on type
                    if obj.type == "text":
                        c.setFillColor(obj.fill_color)
                        c.setFont(obj.font_family, obj.font_size)
                        c.drawString(x_pts, y_pts + obj.height - obj.font_size, resolved_text) # Adjust y for baseline
                        
                    elif obj.type == "rect":
                        c.setStrokeColor(obj.stroke_color)
                        c.setLineWidth(obj.stroke_width)
                        c.setFillColor(obj.fill_color)
                        # Reportlab rect: (x, y, width, height)
                        if obj.fill_color and obj.fill_color != "none":
                            c.rect(x_pts, y_pts, obj.width, obj.height, stroke=1, fill=1)
                        else:
                            c.rect(x_pts, y_pts, obj.width, obj.height, stroke=1, fill=0)
                            
                    elif obj.type == "image":
                        if obj.image_path and os.path.exists(obj.image_path):
                            c.drawImage(obj.image_path, x_pts, y_pts, width=obj.width, height=obj.height, mask='auto')
                            
                    elif obj.type == "habit_tracker":
                        # Simple grid drawing for habit tracker
                        c.setStrokeColor(obj.stroke_color)
                        c.setLineWidth(obj.stroke_width)
                        cell_w = obj.width / obj.columns
                        cell_h = obj.height / obj.rows
                        for r in range(obj.rows):
                            for col in range(obj.columns):
                                c.rect(x_pts + (col * cell_w), y_pts + (r * cell_h), cell_w, cell_h, stroke=1, fill=0)
                                
                    elif obj.type == "ruled_lines":
                        c.setStrokeColor(obj.stroke_color)
                        c.setLineWidth(obj.stroke_width)
                        num_lines = int(obj.height // obj.spacing)
                        for i in range(num_lines):
                            line_y = y_pts + (i * obj.spacing)
                            c.line(x_pts, line_y, x_pts + obj.width, line_y)

                # End of page
                c.showPage()
                
            c.save()
            logger.info(f"Successfully exported PDF to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export planner PDF: {e}")
            return False
