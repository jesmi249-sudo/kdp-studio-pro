import os
import time
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Dict, Any, List, Optional

from book_builder.container import Container
from book_builder.interfaces.core import IBookBuilder
from book_builder.models.book import BookProject
from book_builder.models.export import ExportProfile
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from book_builder.jobs.queue import TaskQueue
from book_builder.jobs.base import CancellationToken

from ui.theme.fonts import Fonts
from ui.theme.colors import Colors
from ui.theme.spacing import Spacing
from ui.components.export_settings_dialog import ExportSettingsDialog
from ui.components.dialogs import Dialogs

from exporters.validation import KDPValidator
from exporters.job import ExportJob

class ExportCenterView(ctk.CTkFrame):
    """
    KDP Studio Pro Export Center providing interactive pre-flight validation,
    preset profile editors, and EventBus-driven background job control.
    """
    
    def __init__(self, master: Any, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.app = self.master.master # KDPStudioApp root reference
        self.event_bus = EventBus()
        self.validator = KDPValidator()
        self.export_queue = TaskQueue(num_workers=1)
        
        self.current_token: Optional[CancellationToken] = None
        self.current_task_id: Optional[str] = None
        
        # Load active project session
        self.project: Optional[BookProject] = None
        self.active_profile: Optional[ExportProfile] = None
        self._load_active_project()
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=2) # Main Options & Actions
        self.grid_columnconfigure(1, weight=3) # Pre-flight Report & History
        
        self._build_ui()
        self._subscribe_to_events()
        self.refresh_data()

    def _load_active_project(self) -> None:
        try:
            self.engine = Container().resolve(IBookBuilder)
            self.project = self.engine.get_active_project()
        except Exception:
            self.engine = None
            self.project = None
            
        if self.project:
            # Ensure all four standard KDP presets are populated
            preset_names = ["Low Quality", "Standard", "Print Quality", "KDP Ready"]
            existing_names = [p.profile_name for p in self.project.export_profiles]
            
            if not any(name in existing_names for name in preset_names):
                p_low = ExportProfile(
                    profile_name="Low Quality",
                    export_format="PNG",
                    color_space="RGB",
                    dpi=72,
                    compression_level=0.5
                )
                p_std = ExportProfile(
                    profile_name="Standard",
                    export_format="KDP_PDF",
                    color_space="RGB",
                    dpi=150,
                    compression_level=0.8
                )
                p_print = ExportProfile(
                    profile_name="Print Quality",
                    export_format="KDP_PDF",
                    color_space="CMYK",
                    dpi=300,
                    compression_level=0.9
                )
                p_kdp = ExportProfile(
                    profile_name="KDP Ready",
                    export_format="ZIP",
                    color_space="CMYK",
                    dpi=300,
                    compression_level=1.0
                )
                p_kdp.custom_options["barcode_placeholder"] = True
                p_kdp.custom_options["isbn_placeholder"] = True
                
                self.project.export_profiles = [p_low, p_std, p_print, p_kdp]
                
            if not self.active_profile or self.active_profile not in self.project.export_profiles:
                self.active_profile = self.project.export_profiles[-1] # default to KDP Ready


    def _subscribe_to_events(self) -> None:
        self.event_bus.subscribe("EXPORT_STARTED", self._on_export_started)
        self.event_bus.subscribe("EXPORT_PROGRESS", self._on_export_progress)
        self.event_bus.subscribe("EXPORT_COMPLETED", self._on_export_completed)
        self.event_bus.subscribe("EXPORT_FAILED", self._on_export_failed)
        self.event_bus.subscribe("EXPORT_CANCELLED", self._on_export_cancelled)

    def _build_ui(self) -> None:
        # Left Panel - Actions and configuration
        left_panel = ctk.CTkFrame(self)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=Spacing.M, pady=Spacing.M)
        left_panel.grid_columnconfigure(0, weight=1)
        
        # Panel Title
        ctk.CTkLabel(left_panel, text="KDP PRODUCTION EXPORT", font=Fonts.heading2()).grid(row=0, column=0, sticky="w", padx=Spacing.L, pady=Spacing.L)
        
        # 1. Project Info Frame
        info_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        info_frame.grid(row=1, column=0, sticky="ew", padx=Spacing.L, pady=Spacing.S)
        
        self.proj_lbl = ctk.CTkLabel(info_frame, text="Active Project: -", font=Fonts.body_bold())
        self.proj_lbl.pack(anchor="w")
        self.type_lbl = ctk.CTkLabel(info_frame, text="Studio Type: -", font=Fonts.body())
        self.type_lbl.pack(anchor="w")
        self.pages_lbl = ctk.CTkLabel(info_frame, text="Total Interior Pages: -", font=Fonts.body())
        self.pages_lbl.pack(anchor="w")
        
        # 2. Preset Selection Frame
        preset_frame = ctk.CTkFrame(left_panel)
        preset_frame.grid(row=2, column=0, sticky="ew", padx=Spacing.L, pady=Spacing.M)
        preset_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(preset_frame, text="Select Export Profile Preset:", font=Fonts.body_bold()).grid(row=0, column=0, sticky="w", padx=Spacing.M, pady=(Spacing.M, 0))
        
        self.profile_var = ctk.StringVar(value="-")
        self.profile_menu = ctk.CTkOptionMenu(preset_frame, variable=self.profile_var, command=self._on_profile_selected)
        self.profile_menu.grid(row=1, column=0, sticky="ew", padx=Spacing.M, pady=Spacing.S)
        
        btn_frame = ctk.CTkFrame(preset_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=Spacing.M, pady=(0, Spacing.M))
        
        ctk.CTkButton(btn_frame, text="Configure Profile...", command=self._open_settings_dialog).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(btn_frame, text="New Preset", command=self._create_new_preset).pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # 3. Export Action Button and Progress Tracker
        action_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        action_frame.grid(row=3, column=0, sticky="ew", padx=Spacing.L, pady=Spacing.L)
        
        self.export_btn = ctk.CTkButton(action_frame, text="EXPORT PACKAGE", font=Fonts.heading3(), height=50, fg_color=Colors.PRIMARY[0], hover_color=Colors.PRIMARY[1], command=self._start_background_export)
        self.export_btn.pack(fill="x", pady=5)
        
        self.cancel_btn = ctk.CTkButton(action_frame, text="Cancel Current Export", fg_color=Colors.ERROR[0], hover_color=Colors.ERROR[1], command=self._cancel_active_export)
        # Keep cancel hidden until running
        
        # Progress bars
        self.progress_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        self.progress_frame.grid(row=4, column=0, sticky="ew", padx=Spacing.L, pady=Spacing.S)
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.set(0)
        self.progress_lbl = ctk.CTkLabel(self.progress_frame, text="Ready", font=Fonts.body())
        
        # Right Panel - Validation Pre-flight & History log
        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=Spacing.M, pady=Spacing.M)
        right_panel.grid_rowconfigure(1, weight=3) # Validation Report
        right_panel.grid_rowconfigure(3, weight=2) # History list
        right_panel.grid_columnconfigure(0, weight=1)
        
        # 1. Validation Report
        ctk.CTkLabel(right_panel, text="KDP PRE-FLIGHT COMPLIANCE CHECK", font=Fonts.heading3()).grid(row=0, column=0, sticky="w", padx=Spacing.L, pady=(Spacing.L, 0))
        
        self.val_scroll = ctk.CTkScrollableFrame(right_panel)
        self.val_scroll.grid(row=1, column=0, sticky="nsew", padx=Spacing.L, pady=Spacing.S)
        self.val_scroll.grid_columnconfigure(0, weight=1)
        
        # 2. History logs
        ctk.CTkLabel(right_panel, text="EXPORT PRODUCTION LOGS", font=Fonts.heading3()).grid(row=2, column=0, sticky="w", padx=Spacing.L, pady=(Spacing.M, 0))
        
        self.history_text = ctk.CTkTextbox(right_panel)
        self.history_text.grid(row=3, column=0, sticky="nsew", padx=Spacing.L, pady=(Spacing.S, Spacing.L))
        self.history_text.configure(state="disabled")

    def refresh_data(self) -> None:
        self._load_active_project()
        
        if not self.project:
            self.proj_lbl.configure(text="Active Project: None Loaded")
            self.type_lbl.configure(text="Studio Type: -")
            self.pages_lbl.configure(text="Total Interior Pages: -")
            self.profile_menu.configure(values=["-"])
            self.profile_var.set("-")
            self.export_btn.configure(state="disabled")
            self._render_empty_validation("Load a book project from the Book Builder workspace to start exports.")
            return
            
        # Bind values
        self.proj_lbl.configure(text=f"Active Project: {self.project.name}")
        self.type_lbl.configure(text=f"Studio Type: {self.project.book_type}")
        self.pages_lbl.configure(text=f"Total Interior Pages: {len(self.project.pages)}")
        
        profiles = [p.profile_name for p in self.project.export_profiles]
        self.profile_menu.configure(values=profiles)
        
        if self.active_profile:
            self.profile_var.set(self.active_profile.profile_name)
        else:
            self.profile_var.set("-")
            
        self.export_btn.configure(state="normal")
        
        # Refresh pre-flight checks and logs
        self._run_preflight_checks()
        self._refresh_history_log()

    def _on_profile_selected(self, val: str) -> None:
        if self.project:
            matches = [p for p in self.project.export_profiles if p.profile_name == val]
            if matches:
                self.active_profile = matches[0]

    def _open_settings_dialog(self) -> None:
        if not self.project:
            return
        ExportSettingsDialog(self, self.project, self.active_profile, on_save_callback=self._on_profile_updated)

    def _on_profile_updated(self, profile: ExportProfile) -> None:
        self.active_profile = profile
        self.refresh_data()

    def _create_new_preset(self) -> None:
        if not self.project:
            return
        new_prof = ExportProfile(
            profile_name=f"Preset {len(self.project.export_profiles) + 1}",
            export_format="KDP_PDF",
            color_space="CMYK",
            dpi=300
        )
        ExportSettingsDialog(self, self.project, new_prof, on_save_callback=self._on_profile_updated)

    def _render_empty_validation(self, msg: str) -> None:
        # Clear child elements in validation scroll frame
        for child in self.val_scroll.winfo_children():
            child.destroy()
        ctk.CTkLabel(self.val_scroll, text=msg, font=Fonts.body(), text_color="gray").pack(pady=20)

    def _run_preflight_checks(self) -> None:
        if not self.project:
            return
            
        # Clear panel
        for child in self.val_scroll.winfo_children():
            child.destroy()
        cover_design = self.project.custom_settings.get("cover_design", {})
        
        # Override with live embedded view if available
        workspace = self.app.views.get("Book Workspace")
        if workspace and hasattr(workspace, "cover_view") and workspace.cover_view:
            cover_design = {
                "objects": workspace.cover_view.canvas_objects,
                "bg_color": workspace.cover_view.bg_color,
                "dims": workspace.cover_view.dims
            }
        elif not cover_design:
            # Fallback to standalone tool if it was somehow used
            standalone_cover = self.app.views.get("Cover Designer Pro")
            if standalone_cover:
                cover_design = {
                    "objects": standalone_cover.canvas_objects,
                    "bg_color": standalone_cover.bg_color,
                    "dims": standalone_cover.dims
                }
        
        # Run validations
        issues = self.validator.run_full_preflight_audit(self.project, cover_design)
        
        if not issues:
            lbl = ctk.CTkLabel(self.val_scroll, text="✓ Perfect! Ready for Amazon KDP Publish.", font=Fonts.body_bold(), text_color="green")
            lbl.pack(anchor="w", padx=Spacing.M, pady=Spacing.M)
            return
            
        # Categorize and render issues
        for issue in issues:
            card = ctk.CTkFrame(self.val_scroll)
            card.pack(fill="x", padx=Spacing.S, pady=Spacing.S)
            
            # Severity color
            color = "orange" if issue.severity == "WARNING" else ("red" if issue.severity in ("ERROR", "CRITICAL") else "blue")
            
            hdr_frame = ctk.CTkFrame(card, fg_color="transparent")
            hdr_frame.pack(fill="x", padx=Spacing.S, pady=(Spacing.S, 0))
            
            ctk.CTkLabel(hdr_frame, text=f"[{issue.severity}] {issue.rule_name}", font=Fonts.body_bold(), text_color=color).pack(side="left")
            ctk.CTkLabel(hdr_frame, text=f"({issue.category})", font=Fonts.small(), text_color="gray").pack(side="right")
            
            ctk.CTkLabel(card, text=issue.explanation, font=Fonts.body(), wraplength=400, justify="left").pack(anchor="w", padx=Spacing.M, pady=Spacing.S)
            
            if issue.suggested_fix:
                ctk.CTkLabel(card, text=f"Fix: {issue.suggested_fix}", font=Fonts.small(), text_color="gray70", wraplength=400, justify="left").pack(anchor="w", padx=Spacing.M, pady=(0, Spacing.S))

    def _refresh_history_log(self) -> None:
        history_dir = os.path.join("settings", "export_history")
        log_file = os.path.join(history_dir, "exports.log")
        
        self.history_text.configure(state="normal")
        self.history_text.delete("1.0", "end")
        
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    content = f.read()
                self.history_text.insert("1.0", content)
            except Exception:
                self.history_text.insert("1.0", "Failed to load history logs.")
        else:
            self.history_text.insert("1.0", "No export history found.")
            
        self.history_text.configure(state="disabled")

    def _start_background_export(self) -> None:
        if not self.project or not self.active_profile:
            return
            
        self.export_btn.configure(state="disabled")
        self.progress_frame.pack(fill="x", pady=10)
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_lbl.pack()
        self.cancel_btn.pack(fill="x", pady=5)
        
        # Resolve cover objects from DB or live view
        cover_design = self.project.custom_settings.get("cover_design", {})
        
        workspace = self.app.views.get("Book Workspace")
        if workspace and hasattr(workspace, "cover_view") and workspace.cover_view:
            cover_design = {
                "objects": workspace.cover_view.canvas_objects,
                "bg_color": workspace.cover_view.bg_color,
                "dims": workspace.cover_view.dims
            }
        elif not cover_design:
            standalone_cover = self.app.views.get("Cover Designer Pro")
            if standalone_cover:
                cover_design = {
                    "objects": getattr(standalone_cover, "canvas_objects", []),
                    "bg_color": getattr(standalone_cover, "bg_color", "#FFFFFF"),
                    "dims": getattr(standalone_cover, "dims", {})
                }
                
        self.active_profile.custom_options["cover_objects"] = cover_design.get("objects", [])
        self.active_profile.custom_options["cover_bg_color"] = cover_design.get("bg_color", "#FFFFFF")
            
        # Instantiates the job
        job = ExportJob(self.project, self.active_profile, cover_design=cover_design)
        
        # Submit to TaskQueue
        def progress_wrp(event):
            # The EventBus handles UI progress updates directly through subscriber callbacks,
            # but we need this wrapper callback so TaskQueue cleans up
            pass
            
        self.current_task_id = job.id
        self.current_token = self.export_queue.enqueue(job, progress_wrp)

    def _cancel_active_export(self) -> None:
        if self.current_task_id and self.current_token:
            self.export_queue.cancel(self.current_task_id)
            self.current_token.cancel()
            self.progress_lbl.configure(text="Cancelling...")
            self.cancel_btn.pack_forget()

    # --- EventBus Subscriber Callbacks ---
    
    def _on_export_started(self, event: Event) -> None:
        if event.payload.get("task_id") == self.current_task_id:
            self.progress_bar.set(0)
            self.progress_lbl.configure(text="Starting export job...")

    def _on_export_progress(self, event: Event) -> None:
        if event.payload.get("task_id") == self.current_task_id:
            progress = event.payload.get("progress", 0.0)
            msg = event.payload.get("message", "")
            self.progress_bar.set(progress)
            self.progress_lbl.configure(text=msg)

    def _on_export_completed(self, event: Event) -> None:
        if event.payload.get("task_id") == self.current_task_id:
            self.progress_bar.set(1.0)
            self.progress_lbl.configure(text="Export Completed Successfully!", text_color="green")
            
            duration = event.payload.get("duration", 0.0)
            files = event.payload.get("files", [])
            
            # Show success box
            files_str = "\n".join([os.path.basename(f) for f in files])
            Dialogs.show_success(f"Generated {len(files)} file(s) in {duration}s:\n{files_str}")
            
            # Reset UI state
            self._reset_ui_after_job()
            self._refresh_history_log()

    def _on_export_failed(self, event: Event) -> None:
        if event.payload.get("task_id") == self.current_task_id:
            err = event.payload.get("error", "Unknown error")
            self.progress_lbl.configure(text=f"Failed: {err}", text_color="red")
            Dialogs.show_error(f"Export Job Failed:\n{err}")
            self._reset_ui_after_job()
            self._refresh_history_log()

    def _on_export_cancelled(self, event: Event) -> None:
        if event.payload.get("task_id") == self.current_task_id:
            self.progress_lbl.configure(text="Export Cancelled.", text_color="orange")
            Dialogs.show_success("Export job cancelled successfully.")
            self._reset_ui_after_job()
            self._refresh_history_log()

    def _reset_ui_after_job(self) -> None:
        self.export_btn.configure(state="normal")
        self.cancel_btn.pack_forget()
        self.current_task_id = None
        self.current_token = None
        # Keep progress display visible for a moment then hide on next refresh
