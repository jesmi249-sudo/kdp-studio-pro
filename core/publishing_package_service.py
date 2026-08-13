import os
import time
import json
from typing import Dict, Any, List

from core.logger import get_logger
from book_builder.models.book import BookProject
from book_builder.models.export import ExportProfile
from exporters.validation import KDPValidator
from book_builder.interfaces.services import IExportService
from book_builder.container import Container

logger = get_logger(__name__)

class PublishingPackageService:
    """
    Coordinates the final KDP publishing package structure, combining metadata manifests,
    validation reports, interior PDFs, and cover PDFs into a submission-ready folder.
    """
    def __init__(self, validator: KDPValidator = None, export_engine: IExportService = None):
        self.validator = validator or KDPValidator()
        
        # Try resolving IExportService if not provided
        if not export_engine:
            try:
                self.export_engine = Container().resolve(IExportService)
            except Exception:
                # Fallback to local import if DI fails
                from exporters.export_engine import ExportEngine
                self.export_engine = ExportEngine()
        else:
            self.export_engine = export_engine

    def check_package_readiness(self, project: BookProject) -> Dict[str, Any]:
        """
        Runs the final pre-publishing check and returns the aggregate status.
        """
        issues = self.validator.run_full_preflight_audit(project)
        
        errors = [i for i in issues if i.severity == "ERROR"]
        warnings = [i for i in issues if i.severity == "WARNING"]
        
        if errors:
            status = "BLOCKED"
        elif warnings:
            status = "WARNING"
        else:
            status = "READY"
            
        return {
            "status": status,
            "issues": issues,
            "errors_count": len(errors),
            "warnings_count": len(warnings)
        }

    def _generate_manifest(self, project: BookProject, status: str, dest_path: str):
        """
        Generates a lightweight JSON manifest detailing the publishing package.
        """
        manifest = {
            "book_title": project.metadata.title or "Untitled",
            "author": project.metadata.author or "Unknown Author",
            "book_type": project.book_type,
            "trim_size": f"{project.trim_width_in}x{project.trim_height_in} in",
            "page_count": len(project.pages),
            "validation_status": status,
            "export_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "paper_type": project.paper_type,
            "has_bleed": project.has_bleed
        }
        
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4)

    def _generate_validation_report(self, issues: List[Any], dest_path: str):
        """
        Generates a human-readable text report of the pre-flight checks.
        """
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write("KDP STUDIO PRO - VALIDATION REPORT\n")
            f.write("="*40 + "\n\n")
            
            if not issues:
                f.write("PASS: No issues detected. Project perfectly conforms to KDP rules.\n")
                return
                
            errors = [i for i in issues if i.severity == "ERROR"]
            warnings = [i for i in issues if i.severity == "WARNING"]
            
            f.write(f"SUMMARY: {len(errors)} ERRORS | {len(warnings)} WARNINGS\n\n")
            
            if errors:
                f.write("--- ERRORS (Must be fixed) ---\n")
                for e in errors:
                    f.write(f"[{e.category}] {e.rule_name}\n")
                    f.write(f"Message: {e.explanation}\n")
                    f.write(f"Action : {e.suggested_fix}\n\n")
                    
            if warnings:
                f.write("--- WARNINGS (Recommended to fix) ---\n")
                for w in warnings:
                    f.write(f"[{w.category}] {w.rule_name}\n")
                    f.write(f"Message: {w.explanation}\n")
                    f.write(f"Action : {w.suggested_fix}\n\n")

    def build_publishing_package(self, project: BookProject, profile: ExportProfile, base_output_dir: str) -> str:
        """
        Assembles the complete package. Creates a timestamped parent folder to prevent overwrites.
        """
        if not project:
            raise ValueError("No project provided for packaging.")
            
        readiness = self.check_package_readiness(project)
        if readiness["status"] == "BLOCKED":
            raise RuntimeError("Cannot build package. KDP Validation returned BLOCKED status.")
            
        safe_name = "".join([c if c.isalnum() else "_" for c in project.name]) if project.name else "Project"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        package_dir = os.path.join(base_output_dir, f"KDP_Package_{safe_name}_{timestamp}")
        
        # 1. Ensure package architecture
        interior_dir = os.path.join(package_dir, "Interior")
        cover_dir = os.path.join(package_dir, "Cover")
        meta_dir = os.path.join(package_dir, "Metadata")
        reports_dir = os.path.join(package_dir, "Reports")
        
        for d in [interior_dir, cover_dir, meta_dir, reports_dir]:
            os.makedirs(d, exist_ok=True)
            
        try:
            # 2. Compile Interior PDF
            profile.custom_options["output_folder"] = interior_dir
            interior_pdf = self.export_engine.compile_pdf(project, profile)
            
            # 3. Compile Cover PDF (if applicable/configured)
            # Some book types like Interior Designer might not have a cover. We wrap in try block.
            try:
                profile.custom_options["output_folder"] = cover_dir
                self.export_engine.compile_cover(project, profile)
            except Exception as e:
                logger.warning(f"Could not generate cover PDF: {e}")
                
            # 4. Generate Metadata Manifest
            manifest_path = os.path.join(meta_dir, "manifest.json")
            self._generate_manifest(project, readiness["status"], manifest_path)
            
            # 5. Generate Validation Report
            report_path = os.path.join(reports_dir, "Validation_Report.txt")
            self._generate_validation_report(readiness["issues"], report_path)
            
            return package_dir
            
        except Exception as e:
            logger.error(f"Failed to build publishing package: {e}")
            raise e
