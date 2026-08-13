import customtkinter as ctk
from tkinter import messagebox
from core.production_pipeline import ProductionWorkflow
from core.book_scene_planner import BookScenePlanner
from core.prompt_batch_service import PromptBatchService
from core.asset_manager import AssetManager
from book_builder.engine import BookBuilderEngine
from core.book_assembly_service import BookAssemblyService
from core.image_processing_service import ImageProcessingService
from core.publishing_package_service import PublishingPackageService
from exporters.validation import KDPValidator
from ui.views.asset_manager_view import AssetManagerView
from ui.components.dialogs import BaseDialog
from PIL import Image
import os
import sys
import subprocess
from book_builder.container import Container
from book_builder.interfaces.core import IBookBuilder

class AssetSelectionDialog(BaseDialog):
    def __init__(self, master, asset_manager):
        self.asset_manager = asset_manager
        self.selected_asset_id = None
        super().__init__("Select Artwork", "Choose an image from the library.", master)
        
    def _create_content(self, parent):
        self.geometry("500x400")
        
        self.scroll = ctk.CTkScrollableFrame(parent)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        assets = self.asset_manager.get_all_assets()
        # Filter for images
        assets = [a for a in assets if a.file_type.lower() in ['.png', '.jpg', '.jpeg']]
        
        for asset in assets:
            btn = ctk.CTkButton(
                self.scroll, 
                text=f"{asset.name} (ID: {asset.id})", 
                anchor="w",
                command=lambda a=asset.id: self._select(a)
            )
            btn.pack(fill="x", pady=2)
            
        ctk.CTkButton(self.action_frame, text="Cancel", command=self.destroy).pack(side="right", padx=5)

    def _select(self, asset_id):
        self.selected_asset_id = asset_id
        self.destroy()

class ProductionDashboardView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.engine = Container().resolve(IBookBuilder)
        self.planner = BookScenePlanner()
        self.asset_manager = AssetManager()
        self.batch_service = PromptBatchService(self.planner)
        self.pipeline = ProductionWorkflow(self.planner, self.asset_manager)
        
        self.assembly_service = BookAssemblyService(self.engine) # this requires IBookBuilder mock in legacy, but BookBuilderEngine works
        self.kdp_validator = KDPValidator()
        self.package_service = PublishingPackageService(self.kdp_validator)
        self.export_ready = False
        self.last_package_path = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)
        
        self._build_sidebar()
        self._build_main_pane()
        
        self.refresh()

    def load_project(self, project_id: str, name: str, state: dict):
        """Called by UI framework when switching projects."""
        self.planner = self.engine.get_scene_planner()
        self.pipeline = self.engine.get_production_workflow(self.asset_manager)
        self.batch_service = PromptBatchService(self.planner)
        self.refresh()
        
    def refresh_data(self):
        """Called by UI framework when navigating to this tab, ensuring state is synced with the active project."""
        project = self.engine.get_active_project()
        if project:
            self.load_project(str(project.id), project.name, {})
        else:
            self.planner = BookScenePlanner()
            self.pipeline = ProductionWorkflow(self.planner, self.asset_manager)
            self.batch_service = PromptBatchService(self.planner)
            self.refresh()
        
    def _persist_state(self):
        """Helper to save the current pipeline state to the active project."""
        self.engine.save_production_workflow(self.pipeline)


    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.sidebar, text="Production Pipeline", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10, padx=10, anchor="w")
        
        self.progress_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=10, pady=10)
        
        self.lbl_scenes = ctk.CTkLabel(self.progress_frame, text="Scenes: 0/0", anchor="w")
        self.lbl_scenes.pack(fill="x")
        
        self.lbl_prompts = ctk.CTkLabel(self.progress_frame, text="Prompts: 0/0", anchor="w")
        self.lbl_prompts.pack(fill="x")
        
        self.lbl_artwork = ctk.CTkLabel(self.progress_frame, text="Artwork: 0/0", anchor="w")
        self.lbl_artwork.pack(fill="x")
        
        self.lbl_validated = ctk.CTkLabel(self.progress_frame, text="Validated Pages: 0/0", anchor="w")
        self.lbl_validated.pack(fill="x")
        
        self.lbl_kdp_status = ctk.CTkLabel(self.progress_frame, text="KDP Validation: Pending", anchor="w", text_color="gray")
        self.lbl_kdp_status.pack(fill="x", pady=(10, 0))
        
        self.lbl_export_status = ctk.CTkLabel(self.progress_frame, text="Export Readiness: Not Ready", anchor="w", text_color="#c0392b")
        self.lbl_export_status.pack(fill="x")
        
        ctk.CTkLabel(self.progress_frame, text="PUBLISHING PACKAGE", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(fill="x", pady=(15, 5))
        
        self.lbl_pkg_interior = ctk.CTkLabel(self.progress_frame, text="Interior: Pending", anchor="w")
        self.lbl_pkg_interior.pack(fill="x")
        self.lbl_pkg_cover = ctk.CTkLabel(self.progress_frame, text="Cover: Pending", anchor="w")
        self.lbl_pkg_cover.pack(fill="x")
        
        ctk.CTkButton(self.sidebar, text="Refresh Status", command=self.refresh).pack(pady=(20, 5), padx=10, fill="x")
        ctk.CTkButton(self.sidebar, text="Run Final Check", command=self._run_final_check, fg_color="#f39c12", hover_color="#d68910").pack(pady=5, padx=10, fill="x")
        
        self.btn_prepare_pkg = ctk.CTkButton(self.sidebar, text="Prepare Publishing Package", command=self._prepare_export, fg_color="green", hover_color="darkgreen")
        self.btn_prepare_pkg.pack(pady=10, padx=10, fill="x")
        
        self.btn_open_pkg = ctk.CTkButton(self.sidebar, text="Open Output Folder", command=self._open_output_folder, fg_color="#3498db", hover_color="#2980b9")
        # Keep hidden until package is generated


    def _build_main_pane(self):
        self.main_pane = ctk.CTkScrollableFrame(self)
        self.main_pane.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.main_pane, text="Page Assembly & Artwork Assignment", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10, anchor="w")
        
        self.list_container = ctk.CTkFrame(self.main_pane, fg_color="transparent")
        self.list_container.pack(fill="both", expand=True)
        
        # Guided Workflow Next Step
        next_step_frame = ctk.CTkFrame(self.main_pane, fg_color="#2b2b2b", corner_radius=8)
        next_step_frame.pack(fill="x", pady=(20, 10))
        ctk.CTkLabel(next_step_frame, text="Ready to publish?").pack(side="left", padx=15, pady=10)
        btn = ctk.CTkButton(next_step_frame, text="Next Step: Export Center", fg_color="green", hover_color="darkgreen",
                            command=lambda: self.master.master.select_frame("Export Center"))
        btn.pack(side="right", padx=15, pady=10)

    def refresh(self):
        stats = self.pipeline.get_progress_summary()
        
        tot = stats["total_scenes"]
        self.lbl_scenes.configure(text=f"Scenes: {tot}/{tot}" if tot else "Scenes: 0/0")
        self.lbl_prompts.configure(text=f"Prompts: {stats['prompts_ready']}/{tot}")
        self.lbl_artwork.configure(text=f"Imported: {stats['artwork_imported']} | Processed: {stats['artwork_processed']} | Missing: {stats['artwork_missing']} | Errors: {stats.get('artwork_errors', 0)}")
        
        export_ready_str = "YES" if stats.get("export_ready", False) else "NO"
        self.lbl_validated.configure(text=f"Validated Pages: {stats['pages_validated']}/{tot} | Export Ready: {export_ready_str}")
        
        # Rebuild list
        for widget in self.list_container.winfo_children():
            widget.destroy()
            
        for scene in self.planner.scenes:
            page = self.pipeline.pages.get(scene.id)
            if not page:
                continue
                
            row = ctk.CTkFrame(self.list_container)
            row.pack(fill="x", pady=5)
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=3)
            row.grid_columnconfigure(2, weight=2)
            
            # Left side: Page number and checkboxes
            left_frame = ctk.CTkFrame(row, fg_color="transparent")
            left_frame.grid(row=0, column=0, sticky="w", padx=10, pady=10)
            
            # Checkbox equivalent symbol
            page_ready = page.status == "Validated & Ready"
            check_mark = "✓" if page_ready else "○"
            ctk.CTkLabel(left_frame, text=f"PAGE {scene.page_number}  {check_mark}", font=ctk.CTkFont(weight="bold"), text_color="green" if page_ready else "gray").pack(anchor="w")
            
            # Middle side: Detailed Statuses
            mid_frame = ctk.CTkFrame(row, fg_color="transparent")
            mid_frame.grid(row=0, column=1, sticky="w", padx=10, pady=5)
            
            orig_art_status = page.artwork_status if page.artwork_status in ["ARTWORK IMPORTED", "PROCESSED", "VALIDATED", "ERROR"] else "MISSING"
            val_status = "PASS" if page.status == "Validated & Ready" else ("WARNING" if page.validation_errors else "PENDING")
            exp_status = "READY" if self.export_ready and page.status == "Validated & Ready" else "PENDING"
            
            def get_color(s):
                if s in ["PASS", "READY", "VALIDATED", "PROCESSED", "ARTWORK IMPORTED"]: return "green"
                if s.startswith("WARNING"): return "#e67e22"
                if s in ["PENDING", "MISSING", "ARTWORK MISSING"]: return "gray"
                return "#c0392b"
                
            ctk.CTkLabel(mid_frame, text=f"Artwork Status: {page.artwork_status}", text_color=get_color(page.artwork_status)).pack(anchor="w")
            ctk.CTkLabel(mid_frame, text=f"Validation: {val_status}", text_color=get_color(val_status)).pack(anchor="w")
            ctk.CTkLabel(mid_frame, text=f"Export: {exp_status}", text_color=get_color(exp_status)).pack(anchor="w")
            
            # Right side: Actions
            right_frame = ctk.CTkFrame(row, fg_color="transparent")
            right_frame.grid(row=0, column=2, sticky="e", padx=10, pady=10)
            
            ctk.CTkButton(right_frame, text="Import Artwork", width=100, command=lambda sid=scene.id: self._assign_artwork(sid)).pack(side="left", padx=5)
            if page.original_asset_id:
                ctk.CTkButton(right_frame, text="Remove", width=60, fg_color="#c0392b", hover_color="#e74c3c", command=lambda sid=scene.id: self._remove_artwork(sid)).pack(side="left", padx=5)
                if page.artwork_status in ["ARTWORK IMPORTED", "ERROR"]:
                    ctk.CTkButton(right_frame, text="Process Selected", width=100, fg_color="#e67e22", hover_color="#d35400", command=lambda sid=scene.id: self._process_line_art(sid)).pack(side="left", padx=5)
            if page.asset_id:
                ctk.CTkButton(right_frame, text="Preview", width=60, fg_color="#3498db", hover_color="#2980b9", command=lambda aid=page.asset_id: self._preview_page(aid)).pack(side="left", padx=5)

    def _assign_artwork(self, scene_id):
        # Allow selection from disk to test import
        file_path = ctk.filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if file_path:
            self.pipeline.import_artwork(scene_id, file_path)
            self._persist_state()
            self.refresh()

    def _remove_artwork(self, scene_id):
        if messagebox.askyesno("Confirm", "Remove assigned artwork from this scene?"):
            self.pipeline.remove_asset(scene_id)
            self._persist_state()
            self.refresh()
        
    def _process_line_art(self, scene_id):
        self.pipeline.process_artwork(scene_id)
        self._persist_state()
        self.refresh()
        page = self.pipeline.pages.get(scene_id)
        if page and page.artwork_status == "PROCESSED":
            messagebox.showinfo("Success", "Line-art successfully processed.")
        elif page and page.validation_errors:
            messagebox.showerror("Error", f"Failed to process line art: {page.validation_errors[0]}")
            
    def _preview_page(self, asset_id):
        asset = self.asset_manager.get_asset(asset_id)
        if not asset or not os.path.exists(asset.file_path):
            messagebox.showerror("Error", "Artwork file not found.")
            return
            
        try:
            # Very lightweight preview window
            preview_win = ctk.CTkToplevel(self)
            preview_win.title("Page Preview")
            preview_win.geometry("450x600")
            
            with Image.open(asset.file_path) as img:
                img.thumbnail((400, 550), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                
            lbl = ctk.CTkLabel(preview_win, image=ctk_img, text="")
            lbl.pack(expand=True, fill="both", padx=10, pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate preview: {e}")

    def _run_final_check(self):
        self.pipeline.validate_all()
        stats = self.pipeline.get_progress_summary()
        
        if stats["pages_validated"] == 0 or stats["total_scenes"] == 0:
            messagebox.showwarning("Warning", "No validated pages found. Ensure artwork is assigned first.")
            self.lbl_kdp_status.configure(text="KDP Validation: Pending", text_color="gray")
            self.lbl_export_status.configure(text="Export Readiness: Not Ready", text_color="#c0392b")
            self.export_ready = False
            return
            
        try:
            # 1. Assemble Project in memory
            project = self.assembly_service.build_project(self.pipeline)
            if not project:
                messagebox.showerror("Error", "Failed to build project assembly.")
                return
                
            # 2. Run KDP Validator
            issues = self.kdp_validator.run_full_preflight_audit(project)
            
            errors = [i for i in issues if i.severity == "ERROR"]
            warnings = [i for i in issues if i.severity == "WARNING"]
            
            if errors:
                msg = f"Found {len(errors)} ERROR(S) blocking export:\n\n"
                for e in errors:
                    msg += f"- [{e.category}] {e.rule_name}: {e.explanation}\n  Action: {e.suggested_fix}\n\n"
                messagebox.showerror("KDP Validation Failed", msg)
                self.lbl_kdp_status.configure(text="KDP Validation: ERROR", text_color="#c0392b")
                self.lbl_export_status.configure(text="Export Readiness: BLOCKED", text_color="#c0392b")
                self.export_ready = False
            elif warnings:
                msg = f"Passed with {len(warnings)} WARNING(S):\n\n"
                for w in warnings:
                    msg += f"- [{w.category}] {w.rule_name}: {w.explanation}\n\n"
                msg += "You can proceed to export, but you should review these warnings."
                messagebox.showwarning("KDP Validation Warning", msg)
                self.lbl_kdp_status.configure(text="KDP Validation: WARNING", text_color="#e67e22")
                self.lbl_export_status.configure(text="Export Readiness: READY", text_color="green")
                self.export_ready = True
            else:
                messagebox.showinfo("KDP Validation Passed", "Perfect! Your book passes all pre-flight checks and is ready for export.")
                self.lbl_kdp_status.configure(text="KDP Validation: PASS", text_color="green")
                self.lbl_export_status.configure(text="Export Readiness: READY", text_color="green")
                self.export_ready = True
                
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during validation: {e}")

    def _prepare_export(self):
        if not self.export_ready:
            messagebox.showwarning("Export Blocked", "Please run Final Check and resolve ERRORs before packaging.")
            return
            
        try:
            project = self.assembly_service.build_project(self.pipeline)
            if not project:
                messagebox.showerror("Error", "Failed to build project.")
                return
                
            from book_builder.models.export import ExportProfile
            # Construct a basic Print Quality profile for the packaging
            profile = ExportProfile(
                profile_name="KDP Package Profile",
                export_format="KDP_PDF",
                color_space="CMYK",
                dpi=300
            )
            
            output_base = os.path.join(os.path.expanduser("~"), "Documents", "Books")
            package_path = self.package_service.build_publishing_package(project, profile, output_base)
            
            self.last_package_path = package_path
            
            self.lbl_pkg_interior.configure(text="Interior: Generated", text_color="green")
            self.lbl_pkg_cover.configure(text="Cover: Generated", text_color="green")
            
            self.btn_open_pkg.pack(pady=5, padx=10, fill="x")
            
            messagebox.showinfo("Success", f"Publishing Package successfully generated at:\n\n{package_path}\n\nIt is now ready for upload to KDP.")
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during export preparation: {e}")

    def _open_output_folder(self):
        if self.last_package_path and os.path.exists(self.last_package_path):
            if sys.platform == "win32":
                os.startfile(self.last_package_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.last_package_path])
            else:
                subprocess.Popen(["xdg-open", self.last_package_path])
