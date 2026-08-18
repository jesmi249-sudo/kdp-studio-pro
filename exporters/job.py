import os
import time
from typing import Callable, Optional, Any, List
from book_builder.jobs.base import Task, CancellationToken, ProgressEvent
from book_builder.models.book import BookProject
from book_builder.models.export import ExportProfile
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from book_builder.repository import ProjectRepository
from book_builder.autosave import AutosaveManager

from exporters.export_engine import ExportEngine
from exporters.validation import KDPValidator

class ExportJob(Task):
    """
    Asynchronous Task that executes KDP pre-flight validation checks,
    flushes recovery checkpoints, and processes PDF/raster/vector layouts.
    """
    
    def __init__(self, project: BookProject, profile: ExportProfile, cover_design: Optional[dict] = None, priority: int = 10) -> None:
        super().__init__(priority=priority)
        self.project = project
        self.profile = profile
        self.cover_design = cover_design
        self.event_bus = EventBus()
        self.validator = KDPValidator()
        self.export_engine = ExportEngine()

    def execute(self, progress_callback: Callable[[ProgressEvent], None], token: CancellationToken) -> str:
        """
        Executes the export pipeline in the background.
        """
        task_id = self.id
        start_time = time.time()
        
        self.event_bus.publish(Event("EXPORT_STARTED", "ExportJob", {
            "project_id": str(self.project.id),
            "task_id": task_id,
            "profile_name": self.profile.profile_name
        }))
        
        def update_progress(ratio: float, msg: str) -> None:
            progress_callback(ProgressEvent(task_id, ratio, msg))
            self.event_bus.publish(Event("EXPORT_PROGRESS", "ExportJob", {
                "project_id": str(self.project.id),
                "task_id": task_id,
                "progress": ratio,
                "message": msg
            }))
            
        try:
            # --- Phase 1: Pre-flight Validation ---
            update_progress(0.1, "Running KDP pre-flight validation...")
            if token.is_cancelled():
                raise RuntimeError("Export task cancelled.")
                
            issues = self.validator.run_full_preflight_audit(self.project, self.cover_design)
            
            # Check for ERROR/CRITICAL issues
            errors = [i for i in issues if i.severity in ("ERROR", "CRITICAL")]
            if errors:
                err_msg = f"Validation failed with {len(errors)} critical KDP error(s)."
                self.event_bus.publish(Event("EXPORT_VALIDATION_FAILED", "ExportJob", {
                    "project_id": str(self.project.id),
                    "task_id": task_id,
                    "errors": [err_msg] + [f"- {e.explanation}" for e in errors]
                }))
                raise ValueError(err_msg)
                
            warnings = [w for w in issues if w.severity == "WARNING"]
            if warnings:
                self.event_bus.publish(Event("EXPORT_VALIDATION_WARNING", "ExportJob", {
                    "project_id": str(self.project.id),
                    "task_id": task_id,
                    "warnings": [f"- {w.explanation}" for w in warnings]
                }))
                
            # --- Phase 2: Save Recovery Checkpoint ---
            update_progress(0.2, "Flushing recovery database state...")
            if token.is_cancelled():
                raise RuntimeError("Export task cancelled.")
                
            # Atomic checkpoint write
            AutosaveManager.create_checkpoint(self.project)
            ProjectRepository.save(self.project)
            
            # --- Phase 3: Document Compilation ---
            update_progress(0.4, "Compiling layout rendering buffers...")
            if token.is_cancelled():
                raise RuntimeError("Export task cancelled.")
                
            fmt = self.profile.export_format.upper()
            output_files: List[str] = []
            
            if fmt == "KDP_PDF" or fmt == "PDF":
                # Export Interior PDF
                pdf_file = self.export_engine.compile_pdf(self.project, self.profile)
                output_files.append(pdf_file)
                update_progress(0.8, "Interior PDF successfully compiled.")
                
            elif fmt == "COVER_PDF":
                cover_file = self.export_engine.compile_cover(self.project, self.profile)
                output_files.append(cover_file)
                update_progress(0.8, "Cover PDF successfully compiled.")
                
            elif fmt == "PREVIEW_PDF":
                preview_file = self.export_engine.compile_preview_pdf(self.project, self.profile)
                output_files.append(preview_file)
                update_progress(0.8, "Preview PDF successfully compiled.")
                
            elif fmt == "ZIP":
                out_dir = self.profile.custom_options.get("output_folder", os.path.join(os.path.expanduser("~"), "Documents", "Books"))
                zip_file = self.export_engine.build_zip_package(self.project, self.profile, out_dir)
                output_files.append(zip_file)
                update_progress(0.8, "ZIP package package completed.")
                
            elif fmt == "PNG" or fmt == "JPEG" or fmt == "JPG":
                img_files = self.export_pages_to_images_safe(token, update_progress)
                output_files.extend(img_files)
                
            elif fmt == "SVG":
                svg_files = self.export_engine.export_pages_to_svg(self.project, self.profile)
                output_files.extend(svg_files)
                update_progress(0.8, "SVG pages successfully exported.")
                
            else:
                raise NotImplementedError(f"Export format '{fmt}' is not supported.")
                
            # Complete
            duration = round(time.time() - start_time, 2)
            update_progress(1.0, "Export completed successfully.")
            
            # Store in history logs
            self._write_history_log(self.project, self.profile, output_files, duration)
            
            self.event_bus.publish(Event("EXPORT_COMPLETED", "ExportJob", {
                "project_id": str(self.project.id),
                "task_id": task_id,
                "files": output_files,
                "duration": duration
            }))
            
            return output_files[0] if output_files else ""
            
        except Exception as e:
            err_str = str(e)
            if "cancelled" in err_str.lower():
                self.event_bus.publish(Event("EXPORT_CANCELLED", "ExportJob", {
                    "project_id": str(self.project.id),
                    "task_id": task_id
                }))
            else:
                self.event_bus.publish(Event("EXPORT_FAILED", "ExportJob", {
                    "project_id": str(self.project.id),
                    "task_id": task_id,
                    "error": err_str
                }))
            raise e

    def export_pages_to_images_safe(self, token: CancellationToken, update_progress: Callable[[float, str], None]) -> List[str]:
        output_dir = self.profile.custom_options.get("output_folder", os.path.join(os.path.expanduser("~"), "Documents", "Books"))
        os.makedirs(output_dir, exist_ok=True)
        
        generated_paths = []
        dpi = self.profile.dpi
        ext = ".png" if self.profile.export_format.upper() == "PNG" else ".jpg"
        total = len(self.project.pages)
        
        for idx, page in enumerate(self.project.pages):
            if token.is_cancelled():
                raise RuntimeError("Export task cancelled.")
                
            update_progress(0.4 + (0.4 * (idx / total)), f"Rendering page {page.page_number} of {total}...")
            
            rendered_img = self.export_engine.rendering_engine.render(page, dpi=dpi)
            
            # Convert color space
            if self.profile.color_space.upper() == "GRAYSCALE":
                rendered_img = rendered_img.convert("L")
            else:
                rendered_img = rendered_img.convert("RGB")
                
            filename = self.export_engine._resolve_naming_template(
                self.profile.custom_options.get("naming_template", "{project_name}_page_{page_number}_{timestamp}"),
                self.project.name,
                self.profile
            ).replace("{page_number}", str(page.page_number)) + ext
            
            output_path = os.path.join(output_dir, filename)
            
            quality = int(self.profile.compression_level * 100)
            if ext == ".jpg":
                rendered_img.save(output_path, "JPEG", quality=quality)
            else:
                rendered_img.save(output_path, "PNG")
                
            generated_paths.append(output_path)
            
        update_progress(0.8, "Image pages successfully exported.")
        return generated_paths

    def _write_history_log(self, project: BookProject, profile: ExportProfile, files: List[str], duration: float) -> None:
        """
        Saves a local history entry of completed exports inside target directories.
        """
        history_dir = os.path.join("settings", "export_history")
        os.makedirs(history_dir, exist_ok=True)
        log_file = os.path.join(history_dir, "exports.log")
        
        entry = (
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Project: {project.name} | "
            f"Type: {project.book_type} | "
            f"Format: {profile.export_format} | "
            f"Files: {', '.join([os.path.basename(f) for f in files])} | "
            f"Duration: {duration}s\n"
        )
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)
