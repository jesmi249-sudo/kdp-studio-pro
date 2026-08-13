import os
import time
import zipfile
import shutil
from typing import List, Dict, Any, Optional
from uuid import UUID
from PIL import Image

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

from book_builder.interfaces.services import IExportService, IComplianceService
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.models.export import ExportProfile
from book_builder.rendering.engine import RenderingEngine, RenderContext
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from book_builder.container import Container

from exporters.svg_exporter import SVGExporter
from exporters.crop_marks import CropMarksDrawer
from exporters.validation import KDPValidator

class ExportEngine(IExportService):
    """
    Centralized Export Engine coordinating PDF generation, high-res image output,
    SVG vector exports, and distribution packaging.
    """

    def __init__(self, rendering_engine: Optional[RenderingEngine] = None) -> None:
        self.rendering_engine = rendering_engine or RenderingEngine()
        self.event_bus = EventBus()
        self.validator = KDPValidator()

    def compile_pdf(self, book_project: BookProject, profile: ExportProfile) -> str:
        """
        Generates the interior print PDF matching KDP specifications.
        """
        output_dir = profile.custom_options.get("output_folder", os.path.join(os.path.expanduser("~"), "Documents", "Books"))
        os.makedirs(output_dir, exist_ok=True)
        
        # Resolve naming template
        filename = self._resolve_naming_template(
            profile.custom_options.get("naming_template", "{project_name}_interior_{timestamp}"),
            book_project.name,
            profile
        ) + ".pdf"
        
        pdf_path = os.path.join(output_dir, filename)
        
        # Page dimensions
        trim_w = book_project.trim_width_in
        trim_h = book_project.trim_height_in
        
        # Bleed adjustment
        has_bleed = profile.custom_options.get("bleed_option", "No Bleed") == "Bleed" or book_project.has_bleed
        if has_bleed:
            # Add 0.125 inches to width, 0.25 inches to height
            w_pt = (trim_w + 0.125) * 72.0
            h_pt = (trim_h + 0.250) * 72.0
        else:
            w_pt = trim_w * 72.0
            h_pt = trim_h * 72.0
            
        # Crop marks adjustment: if enabled, we enlarge the canvas to draw marks
        include_crop = profile.include_crop_marks
        offset_pt = 18.0 # 0.25" slug border
        if include_crop:
            canvas_w = w_pt + (offset_pt * 2.0)
            canvas_h = h_pt + (offset_pt * 2.0)
        else:
            canvas_w = w_pt
            canvas_h = h_pt
            
        # Create ReportLab canvas
        c = canvas.Canvas(pdf_path, pagesize=(canvas_w, canvas_h))
        
        # Set page compression
        c.setPageCompression(True)
        
        dpi = profile.dpi
        color_space = profile.color_space.upper() # RGB, CMYK, GRAYSCALE
        
        temp_files: List[str] = []
        
        try:
            for idx, page in enumerate(book_project.pages):
                # Ensure the page dimensions match project expectations
                page.width_pt = w_pt
                page.height_pt = h_pt
                
                # Draw ISBN placeholder on page 2 (copyright page) if enabled
                added_isbn = False
                if idx == 1 and (profile.custom_options.get("isbn_placeholder", True) or book_project.metadata.isbn):
                    isbn_val = book_project.metadata.isbn or ""
                    if not any("ISBN" in tb.get("text", "") for tb in page.text_blocks):
                        page.text_blocks.append({
                            "text": f"ISBN-13: {isbn_val}",
                            "geometry": {"x": 72.0, "y": 72.0, "width": 200.0, "height": 20.0},
                            "properties": {"font": "Helvetica", "size": 10.0}
                        })
                        added_isbn = True

                # 1. Render page layout using RenderingEngine to a PIL Image at target DPI
                rendered_img = self.rendering_engine.render(page, dpi=dpi)
                
                if added_isbn:
                    page.text_blocks.pop()
                
                # Apply Color Space Conversion
                if color_space == "CMYK":
                    if rendered_img.mode != "CMYK":
                        rendered_img = rendered_img.convert("CMYK")
                elif color_space == "GRAYSCALE":
                    rendered_img = rendered_img.convert("L")
                else:
                    if rendered_img.mode != "RGB":
                        rendered_img = rendered_img.convert("RGB")
                        
                # 2. Write PIL Image to a temporary file
                temp_filename = f"temp_export_page_{page.id}_{idx}.png"
                
                # JPEG doesn't support CMYK well in raw PNG, save with quality
                quality = int(profile.compression_level * 100)
                
                if color_space == "CMYK":
                    temp_filename = temp_filename.replace(".png", ".jpg")
                    rendered_img.save(temp_filename, "JPEG", dpi=(dpi, dpi), quality=quality)
                else:
                    rendered_img.save(temp_filename, "PNG", dpi=(dpi, dpi))
                    
                temp_files.append(temp_filename)
                
                # 3. Draw image onto ReportLab canvas
                draw_x = offset_pt if include_crop else 0.0
                draw_y = offset_pt if include_crop else 0.0
                
                c.drawImage(temp_filename, draw_x, draw_y, width=w_pt, height=h_pt)
                
                # 4. If crop marks enabled, draw them on top
                if include_crop:
                    CropMarksDrawer.draw_crop_marks(c, canvas_w, canvas_h, offset_pt)
                    
                # Close page
                c.showPage()
                
            c.save()
            
        finally:
            # Clean up temp files
            for f in temp_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
                        
        return pdf_path

    def compile_cover(self, book_project: BookProject, profile: ExportProfile) -> str:
        """
        Compiles a print-ready cover PDF by calling CoverGenerator or rendering Cover objects.
        """
        output_dir = profile.custom_options.get("output_folder", os.path.join(os.path.expanduser("~"), "Documents", "Books"))
        os.makedirs(output_dir, exist_ok=True)
        
        filename = self._resolve_naming_template(
            profile.custom_options.get("naming_template", "{project_name}_cover_{timestamp}"),
            book_project.name,
            profile
        ) + ".pdf"
        
        pdf_path = os.path.join(output_dir, filename)
        
        # Calculate expected dimensions
        pages = len(book_project.pages)
        paper_type = book_project.paper_type
        trim_w = book_project.trim_width_in
        trim_h = book_project.trim_height_in
        
        from generators.cover_generator import CoverGenerator
        cov_gen = CoverGenerator()
        dims = cov_gen.calculate_dimensions(trim_w, trim_h, pages, paper_type)
        
        # Fetch cover objects from UI view fallback or use placeholder
        cover_objects = list(profile.custom_options.get("cover_objects", []))
        bg_color = profile.custom_options.get("cover_bg_color", "#FFFFFF")
        
        # Inject barcode placeholder if enabled in options
        if profile.custom_options.get("barcode_placeholder", True) or book_project.metadata.isbn:
            if not any(obj.get("type") in ("barcode", "barcode_placeholder") for obj in cover_objects):
                cover_objects.append({
                    "type": "barcode_placeholder",
                    "x": dims["bleed_px"] + dims["safe_zone_px"],
                    "y": dims["full_height_px"] - dims["safe_zone_px"] - int(1.2 * cov_gen.ppi),
                    "width": int(2.0 * cov_gen.ppi),
                    "height": int(1.2 * cov_gen.ppi),
                    "value": book_project.metadata.isbn or ""
                })
        
        success = cov_gen.export(cover_objects, dims, bg_color, pdf_path, format="pdf")
        if not success:
            raise RuntimeError("CoverGenerator failed to compile cover PDF.")
            
        return pdf_path

    def compile_preview_pdf(self, book_project: BookProject, profile: ExportProfile) -> str:
        """
        Generates a combined low-DPI RGB preview document where page 1 is the cover,
        followed by interior pages.
        """
        output_dir = profile.custom_options.get("output_folder", os.path.join(os.path.expanduser("~"), "Documents", "Books"))
        os.makedirs(output_dir, exist_ok=True)
        
        # Resolve naming template
        filename = self._resolve_naming_template(
            profile.custom_options.get("naming_template", "{project_name}_preview_{timestamp}"),
            book_project.name,
            profile
        ) + ".pdf"
        
        pdf_path = os.path.join(output_dir, filename)
        
        # We will use 100 DPI for low resolution preview to save file size and space
        dpi = 100
        
        # Dimensions for interior pages (RGB, no bleed or layout bleed adjusted)
        trim_w = book_project.trim_width_in
        trim_h = book_project.trim_height_in
        
        # For simplicity, standard trim size pages in points
        w_pt = trim_w * 72.0
        h_pt = trim_h * 72.0
        
        # Cover Dimensions
        pages = len(book_project.pages)
        paper_type = book_project.paper_type
        
        from generators.cover_generator import CoverGenerator
        cov_gen = CoverGenerator()
        dims = cov_gen.calculate_dimensions(trim_w, trim_h, pages, paper_type)
        
        # Cover size in points
        cov_w_pt = dims["full_width_inches"] * 72.0
        cov_h_pt = dims["full_height_inches"] * 72.0
        
        # Create ReportLab canvas
        c = canvas.Canvas(pdf_path)
        c.setPageCompression(True)
        
        temp_files: List[str] = []
        
        try:
            # --- 1. RENDER AND DRAW THE COVER AS PAGE 1 ---
            cover_objects = list(profile.custom_options.get("cover_objects", []))
            # Fallback to custom_settings cover_design if present
            if not cover_objects and "cover_design" in book_project.custom_settings:
                cover_objects = list(book_project.custom_settings["cover_design"].get("objects", []))
                
            bg_color = profile.custom_options.get("cover_bg_color", "#FFFFFF")
            if bg_color == "#FFFFFF" and "cover_design" in book_project.custom_settings:
                bg_color = book_project.custom_settings["cover_design"].get("bg_color", "#FFFFFF")
            
            # Inject barcode placeholder if enabled in options
            if profile.custom_options.get("barcode_placeholder", True) or book_project.metadata.isbn:
                if not any(obj.get("type") in ("barcode", "barcode_placeholder") for obj in cover_objects):
                    cover_objects.append({
                        "type": "barcode_placeholder",
                        "x": dims["bleed_px"] + dims["safe_zone_px"],
                        "y": dims["full_height_px"] - dims["safe_zone_px"] - int(1.2 * cov_gen.ppi),
                        "width": int(2.0 * cov_gen.ppi),
                        "height": int(1.2 * cov_gen.ppi),
                        "value": book_project.metadata.isbn or ""
                    })
            
            # Generate cover PIL image
            cover_img = cov_gen.generate_image(cover_objects, dims, bg_color)
            if cover_img.mode != "RGB":
                cover_img = cover_img.convert("RGB")
            
            # Save to temporary file
            cov_temp_filename = f"temp_preview_cover_{book_project.id}.png"
            cover_img.save(cov_temp_filename, "PNG", dpi=(dpi, dpi))
            temp_files.append(cov_temp_filename)
            
            # Set pagesize for cover and draw
            c.setPageSize((cov_w_pt, cov_h_pt))
            c.drawImage(cov_temp_filename, 0, 0, width=cov_w_pt, height=cov_h_pt)
            c.showPage()
            
            # --- 2. RENDER AND DRAW INTERIOR PAGES ---
            for idx, page in enumerate(book_project.pages):
                page.width_pt = w_pt
                page.height_pt = h_pt
                
                # Render page at 100 DPI
                rendered_img = self.rendering_engine.render(page, dpi=dpi)
                if rendered_img.mode != "RGB":
                    rendered_img = rendered_img.convert("RGB")
                    
                temp_filename = f"temp_preview_page_{page.id}_{idx}.png"
                rendered_img.save(temp_filename, "PNG", dpi=(dpi, dpi))
                temp_files.append(temp_filename)
                
                c.setPageSize((w_pt, h_pt))
                c.drawImage(temp_filename, 0, 0, width=w_pt, height=h_pt)
                c.showPage()
                
            c.save()
            
        finally:
            # Clean up temp files
            for f in temp_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
                        
        return pdf_path

    def build_zip_package(self, book_project: BookProject, profile: ExportProfile, output_dir: str) -> str:
        """
        Bundles cover, interior, and metadata package into a distribution archive.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate Interior PDF
        interior_pdf = self.compile_pdf(book_project, profile)
        
        # Generate Cover PDF
        cover_pdf = self.compile_cover(book_project, profile)
        
        # Generate Metadata Files
        meta_csv = os.path.join(output_dir, "Metadata.csv")
        meta_json = os.path.join(output_dir, "Metadata.json")
        keywords_txt = os.path.join(output_dir, "Keywords.txt")
        
        self._export_metadata(book_project, meta_csv, meta_json, keywords_txt)
        
        # ZIP path
        zip_filename = self._resolve_naming_template(
            "{project_name}_kdp_package_{timestamp}",
            book_project.name,
            profile
        ) + ".zip"
        zip_path = os.path.join(output_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(interior_pdf, os.path.basename(interior_pdf))
            z.write(cover_pdf, os.path.basename(cover_pdf))
            z.write(meta_csv, os.path.basename(meta_csv))
            z.write(meta_json, os.path.basename(meta_json))
            z.write(keywords_txt, os.path.basename(keywords_txt))
            
        # Clean up unzipped metadata if desired, but KDP Studio Pro keeps them
        return zip_path

    def export_pages_to_images(self, book_project: BookProject, profile: ExportProfile) -> List[str]:
        """
        Exports all pages of the book project to PNG or JPEG format.
        """
        output_dir = profile.custom_options.get("output_folder", os.path.join(os.path.expanduser("~"), "Documents", "Books"))
        os.makedirs(output_dir, exist_ok=True)
        
        export_format = profile.export_format.upper() # PNG, JPEG
        ext = ".png" if export_format == "PNG" else ".jpg"
        
        generated_paths = []
        dpi = profile.dpi
        
        for idx, page in enumerate(book_project.pages):
            rendered_img = self.rendering_engine.render(page, dpi=dpi)
            
            # Format color space
            if profile.color_space.upper() == "GRAYSCALE":
                rendered_img = rendered_img.convert("L")
            else:
                rendered_img = rendered_img.convert("RGB")
                
            filename = self._resolve_naming_template(
                profile.custom_options.get("naming_template", "{project_name}_page_{page_number}_{timestamp}"),
                book_project.name,
                profile
            ).replace("{page_number}", str(page.page_number)) + ext
            
            output_path = os.path.join(output_dir, filename)
            
            quality = int(profile.compression_level * 100)
            if ext == ".jpg":
                rendered_img.save(output_path, "JPEG", quality=quality)
            else:
                rendered_img.save(output_path, "PNG")
                
            generated_paths.append(output_path)
            
        return generated_paths

    def export_pages_to_svg(self, book_project: BookProject, profile: ExportProfile) -> List[str]:
        """
        Exports vector pages to SVG XML format.
        """
        output_dir = profile.custom_options.get("output_folder", os.path.join(os.path.expanduser("~"), "Documents", "Books"))
        os.makedirs(output_dir, exist_ok=True)
        
        generated_paths = []
        for page in book_project.pages:
            filename = self._resolve_naming_template(
                profile.custom_options.get("naming_template", "{project_name}_page_{page_number}_{timestamp}"),
                book_project.name,
                profile
            ).replace("{page_number}", str(page.page_number)) + ".svg"
            
            output_path = os.path.join(output_dir, filename)
            
            if SVGExporter.export_page_to_svg_file(page, output_path):
                generated_paths.append(output_path)
                
        return generated_paths

    def _resolve_naming_template(self, template: str, project_name: str, profile: ExportProfile) -> str:
        """
        Interpolates template variables like {project_name}, {timestamp}, {dpi}, {format}.
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in project_name])
        
        res = template
        res = res.replace("{project_name}", safe_name)
        res = res.replace("{timestamp}", timestamp)
        res = res.replace("{dpi}", str(profile.dpi))
        res = res.replace("{format}", profile.export_format)
        res = res.replace("{color_mode}", profile.color_space)
        return res

    def _export_metadata(self, book_project: BookProject, csv_path: str, json_path: str, keywords_path: str) -> None:
        """
        Helper method to export book metadata to CSV, JSON and Keywords TXT.
        """
        # Read metadata
        meta = book_project.metadata
        
        # 1. JSON
        import json
        from book_builder.serializer import ProjectSerializer
        meta_dict = ProjectSerializer.serialize_metadata(meta)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meta_dict, f, indent=4)
            
        # 2. CSV
        import csv
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Key", "Value"])
            for k, v in meta_dict.items():
                writer.writerow([k, str(v)])
                
        # 3. Keywords TXT
        with open(keywords_path, "w", encoding="utf-8") as f:
            f.write("\n".join(meta.keywords))

# Register ExportEngine in DI container
Container().register(IExportService, ExportEngine())
