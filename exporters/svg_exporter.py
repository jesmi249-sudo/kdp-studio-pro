import os
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from book_builder.models.page import Page

class SVGExporter:
    """
    Utility class to compile abstract Page vector layout elements
    and text blocks into a standard W3C SVG XML file.
    """

    @staticmethod
    def page_to_svg(page: Page) -> str:
        """
        Converts the shapes, images, and text of a Page into an SVG string.
        Translates bottom-left Y-axis coordinates into top-left SVG layout format.
        """
        w = page.width_pt
        h = page.height_pt
        
        # Root SVG element
        svg = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "version": "1.1",
            "width": f"{w}pt",
            "height": f"{h}pt",
            "viewBox": f"0 0 {w} {h}"
        })
        
        # 1. Background (if any)
        if getattr(page, "background_asset_id", None):
            ET.SubElement(svg, "rect", {
                "width": str(w),
                "height": str(h),
                "fill": "#FFFFFF"
            })
            
        # Helper to convert y coordinate
        def map_y(y_pt: float, h_pt: float) -> float:
            return h - (y_pt + h_pt)
            
        # Helper to parse hex/rgb/rgba colors for SVG attributes
        def clean_color(val: Any) -> str:
            if not val:
                return "none"
            val_str = str(val).strip()
            if val_str.lower() == "none":
                return "none"
            return val_str
            
        # 2. Draw vector objects
        for obj in page.vector_objects:
            s_type = obj.get("shape_type", "rectangle")
            geom = obj.get("geometry", {})
            props = obj.get("properties", {})
            
            x_pt = geom.get("x", 0.0)
            y_pt = geom.get("y", 0.0)
            w_pt = geom.get("width", 10.0)
            h_pt = geom.get("height", 10.0)
            
            fill = clean_color(props.get("fill_color", "none"))
            stroke = clean_color(props.get("stroke_color", "black"))
            stroke_width = str(props.get("stroke_width", 1.0))
            
            if s_type == "text_block":
                # Render text
                text = obj.get("text", "")
                y_svg = map_y(y_pt, h_pt) + h_pt # SVG text anchor base
                font_sz = str(props.get("font_size", 9.0))
                color = clean_color(props.get("color", "black"))
                align = props.get("alignment", "center")
                
                txt_el = ET.SubElement(svg, "text", {
                    "x": str(x_pt + w_pt / 2) if align == "center" else str(x_pt),
                    "y": str(y_svg - 2), # offset slightly from bottom boundary
                    "font-family": "sans-serif",
                    "font-size": f"{font_sz}px",
                    "fill": color,
                    "text-anchor": "middle" if align == "center" else "start"
                })
                txt_el.text = text
                
            elif s_type == "rectangle":
                y_svg = map_y(y_pt, h_pt)
                ET.SubElement(svg, "rect", {
                    "x": str(x_pt),
                    "y": str(y_svg),
                    "width": str(w_pt),
                    "height": str(h_pt),
                    "fill": fill,
                    "stroke": stroke,
                    "stroke-width": stroke_width
                })
                
            elif s_type == "ellipse":
                cx = x_pt + w_pt / 2.0
                cy = map_y(y_pt, h_pt) + h_pt / 2.0
                ET.SubElement(svg, "ellipse", {
                    "cx": str(cx),
                    "cy": str(cy),
                    "rx": str(w_pt / 2.0),
                    "ry": str(h_pt / 2.0),
                    "fill": fill,
                    "stroke": stroke,
                    "stroke-width": stroke_width
                })
                
            elif s_type == "line":
                # Line y coordinate mapping:
                # y1 is the top boundary, y2 is the bottom boundary
                y_svg_start = map_y(y_pt, h_pt)
                y_svg_end = y_svg_start + h_pt
                
                # Check line direction: usually width and height define start/end offset
                # If width is 0, it's vertical. If height is 0, it's horizontal.
                ET.SubElement(svg, "line", {
                    "x1": str(x_pt),
                    "y1": str(y_svg_start if h_pt == 0 else y_svg_end),
                    "x2": str(x_pt + w_pt),
                    "y2": str(y_svg_start),
                    "stroke": stroke,
                    "stroke-width": stroke_width
                })
                
        # 3. Draw images
        for img_obj in page.images:
            geom = img_obj.get("geometry", {})
            file_path = img_obj.get("file_path", "")
            x_pt = geom.get("x", 0.0)
            y_pt = geom.get("y", 0.0)
            w_pt = geom.get("width", 100.0)
            h_pt = geom.get("height", 100.0)
            
            y_svg = map_y(y_pt, h_pt)
            
            # Use file name as href or absolute link
            href = file_path
            if os.path.exists(file_path):
                # Try to use relative or direct path
                href = "file:///" + os.path.abspath(file_path).replace("\\", "/")
                
            ET.SubElement(svg, "image", {
                "x": str(x_pt),
                "y": str(y_svg),
                "width": str(w_pt),
                "height": str(h_pt),
                "href": href
            })
            
        # 4. Draw text blocks
        for text_obj in page.text_blocks:
            geom = text_obj.get("geometry", {})
            props = text_obj.get("properties", {})
            text = text_obj.get("text", "")
            x_pt = geom.get("x", 0.0)
            y_pt = geom.get("y", 0.0)
            w_pt = geom.get("width", 100.0)
            h_pt = geom.get("height", 20.0)
            
            y_svg = map_y(y_pt, h_pt) + h_pt
            font_sz = str(props.get("font_size", 10.0))
            color = clean_color(props.get("color", "black"))
            
            txt_el = ET.SubElement(svg, "text", {
                "x": str(x_pt),
                "y": str(y_svg - 2),
                "font-family": "sans-serif",
                "font-size": f"{font_sz}px",
                "fill": color
            })
            txt_el.text = text
            
        # Serialize to string
        raw_xml = ET.tostring(svg, encoding="utf-8")
        # Prepend xml declaration
        return '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + raw_xml.decode("utf-8")

    @classmethod
    def export_page_to_svg_file(cls, page: Page, output_path: str) -> bool:
        """
        Saves page layout to the specified output SVG path.
        """
        try:
            svg_content = cls.page_to_svg(page)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
            return True
        except Exception:
            return False
