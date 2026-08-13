import os
import shutil
import zipfile
import json
import time
from core.logger import get_logger

logger = get_logger(__name__)

class ExportManager:
    def __init__(self, app):
        self.app = app
        self.output_dir = ""
        
    def validate_state(self):
        """Checks the live UI views to determine what is ready to export."""
        status = {
            "cover": False,
            "interior": False,
            "metadata": False,
            "errors": []
        }
        
        # Check Cover
        cover_view = self.app.views.get("Cover Designer Pro")
        if cover_view and getattr(cover_view, 'canvas_objects', None):
            if len(cover_view.canvas_objects) > 0:
                status["cover"] = True
            else:
                status["errors"].append("Cover canvas is empty.")
        else:
            status["errors"].append("Cover Designer module not found or empty.")
            
        # Check Interior
        interior_view = self.app.views.get("Interior Designer")
        if interior_view and hasattr(interior_view, 'page_count'):
            try:
                pages = int(interior_view.page_count.get())
                if pages > 0:
                    status["interior"] = True
                else:
                    status["errors"].append("Interior page count is invalid.")
            except ValueError:
                status["errors"].append("Interior page count is invalid.")
        else:
            status["errors"].append("Interior Designer module not found.")
            
        # Check Metadata
        meta_view = self.app.views.get("Metadata")
        if meta_view and hasattr(meta_view, 'generator'):
            meta_view._update_generator_data() # force sync
            m_data = meta_view.generator.get_metadata()
            if m_data.get("title") and m_data.get("author"):
                status["metadata"] = True
            else:
                status["errors"].append("Metadata requires at least Title and Author.")
        else:
            status["errors"].append("Metadata module not found.")
            
        return status

    def run_export(self, options, output_folder, progress_callback):
        self.output_dir = output_folder
        os.makedirs(self.output_dir, exist_ok=True)
        
        generated_files = []
        total_tasks = sum([1 for k, v in options.items() if v])
        if total_tasks == 0:
            progress_callback(1.0, "No options selected.")
            return True, []
            
        current_task = 0
        
        def update_progress(msg):
            nonlocal current_task
            current_task += 1
            progress_callback(current_task / total_tasks, msg)

        try:
            # INTERIOR
            if options.get("interior"):
                interior_view = self.app.views.get("Interior Designer")
                generator = interior_view.generator
                
                size = interior_view.size_var.get()
                orientation = interior_view.orient_var.get()
                bleed = interior_view.bleed_var.get()
                page_numbers = interior_view.page_num_var.get()
                template = interior_view.template_var.get()
                pages = int(interior_view.page_count.get())
                margins = {
                    "top": float(interior_view.m_top.get()),
                    "bottom": float(interior_view.m_bottom.get()),
                    "inside": float(interior_view.m_inside.get()),
                    "outside": float(interior_view.m_outside.get())
                }
                
                out_pdf = os.path.join(self.output_dir, "Interior.pdf")
                generator.generate_pdf(out_pdf, size, orientation, margins, bleed, page_numbers, template, pages)
                generated_files.append(out_pdf)
                update_progress("Generated Interior.pdf")
                
            # COVER
            if options.get("cover"):
                cover_view = self.app.views.get("Cover Designer Pro")
                generator = cover_view.generator
                out_pdf = os.path.join(self.output_dir, "Cover.pdf")
                
                generator.export(
                    objects=cover_view.canvas_objects,
                    dims=cover_view.dims,
                    bg_color=cover_view.bg_color,
                    output_path=out_pdf,
                    format="pdf"
                )
                generated_files.append(out_pdf)
                update_progress("Generated Cover.pdf")
                
            # METADATA (CSV & JSON)
            meta_view = self.app.views.get("Metadata")
            if options.get("metadata_csv"):
                out_csv = os.path.join(self.output_dir, "Metadata.csv")
                meta_view.generator.export_csv(out_csv)
                generated_files.append(out_csv)
                update_progress("Generated Metadata.csv")
                
            if options.get("metadata_json"):
                out_json = os.path.join(self.output_dir, "Metadata.json")
                meta_view.generator.export_json(out_json)
                generated_files.append(out_json)
                update_progress("Generated Metadata.json")
                
            # KEYWORDS TXT
            if options.get("keywords"):
                m_data = meta_view.generator.get_metadata()
                out_txt = os.path.join(self.output_dir, "Keywords.txt")
                with open(out_txt, "w") as f:
                    f.write("\n".join(m_data.get("keywords", [])))
                generated_files.append(out_txt)
                update_progress("Generated Keywords.txt")
                
            # BOOK PREVIEW PDF
            if options.get("preview"):
                # We'll just copy the cover and call it preview for this demonstration
                out_prev = os.path.join(self.output_dir, "Book_Preview.pdf")
                if options.get("cover"):
                    shutil.copy(os.path.join(self.output_dir, "Cover.pdf"), out_prev)
                    generated_files.append(out_prev)
                update_progress("Generated Book_Preview.pdf")
                
            # ZIP PACKAGE
            if options.get("zip"):
                zip_path = os.path.join(self.output_dir, "KDP_Project_Package.zip")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for f in generated_files:
                        if os.path.exists(f):
                            zipf.write(f, os.path.basename(f))
                generated_files.append(zip_path)
                update_progress("Created ZIP Package")

            # Increment export counter on success
            try:
                from core.config import config
                current_count = config.get("export_count", 0)
                config.set("export_count", current_count + 1)
                logger.info(f"Incremented export count in config. New count: {current_count + 1}")
            except Exception as config_err:
                logger.error(f"Failed to increment export count: {config_err}")

            return True, generated_files
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            progress_callback(1.0, f"Error: {str(e)}")
            return False, []
