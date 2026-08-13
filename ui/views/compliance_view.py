import customtkinter as ctk
import time
import threading
import os
from tkinter import filedialog, messagebox
from core.compliance_checker import ComplianceChecker
from core.report_generator import ReportGenerator

class ComplianceView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.app = self.master.master
        self.checker = ComplianceChecker(self.app)
        self.current_result = None
        self.current_filter = "All"
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(header_frame, text="KDP Compliance", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w")
        
        self.run_btn = ctk.CTkButton(header_frame, text="Run Inspection", command=self.run_inspection, fg_color="green", hover_color="darkgreen")
        self.run_btn.grid(row=0, column=2, sticky="e")
        
        # Summary & Score Area
        self.summary_frame = ctk.CTkFrame(self)
        self.summary_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        self.summary_frame.grid_columnconfigure(0, weight=1)
        self.summary_frame.grid_columnconfigure(1, weight=1)
        
        self.score_lbl = ctk.CTkLabel(self.summary_frame, text="Score: -- / 100", font=ctk.CTkFont(size=30, weight="bold"))
        self.score_lbl.grid(row=0, column=0, pady=20, padx=20, sticky="w")
        
        self.status_lbl = ctk.CTkLabel(self.summary_frame, text="Not Scanned Yet", font=ctk.CTkFont(size=18))
        self.status_lbl.grid(row=0, column=1, pady=20, padx=20, sticky="e")
        
        self.progress_bar = ctk.CTkProgressBar(self.summary_frame)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))
        self.progress_bar.set(0)
        self.progress_bar.grid_remove() # Hide initially
        
        # Filter Bar
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=2, column=0, sticky="new", padx=20, pady=(10, 0))
        
        ctk.CTkLabel(filter_frame, text="Filter:").pack(side="left", padx=(0, 10))
        self.filter_var = ctk.StringVar(value="All")
        self.filter_menu = ctk.CTkOptionMenu(filter_frame, values=["All", "INFO", "WARNING", "ERROR", "CRITICAL"], variable=self.filter_var, command=self.apply_filter)
        self.filter_menu.pack(side="left")
        
        # Export Buttons
        self.export_pdf_btn = ctk.CTkButton(filter_frame, text="Export PDF", command=lambda: self.export_report("pdf"), width=100)
        self.export_pdf_btn.pack(side="right", padx=5)
        self.export_html_btn = ctk.CTkButton(filter_frame, text="Export HTML", command=lambda: self.export_report("html"), width=100)
        self.export_html_btn.pack(side="right", padx=5)
        self.export_json_btn = ctk.CTkButton(filter_frame, text="Export JSON", command=lambda: self.export_report("json"), width=100)
        self.export_json_btn.pack(side="right", padx=5)
        self.disable_exports()
        
        # Issues List
        self.issues_frame = ctk.CTkScrollableFrame(self)
        self.issues_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=10)
        self.grid_rowconfigure(3, weight=1)
        
    def disable_exports(self):
        self.export_pdf_btn.configure(state="disabled")
        self.export_html_btn.configure(state="disabled")
        self.export_json_btn.configure(state="disabled")
        
    def enable_exports(self):
        self.export_pdf_btn.configure(state="normal")
        self.export_html_btn.configure(state="normal")
        self.export_json_btn.configure(state="normal")
        
    def run_inspection(self):
        self.run_btn.configure(state="disabled")
        self.progress_bar.grid()
        self.progress_bar.set(0)
        self.status_lbl.configure(text="Scanning...", text_color="white")
        self.score_lbl.configure(text="Score: Calculating...")
        self.disable_exports()
        
        # Clear existing issues
        for widget in self.issues_frame.winfo_children():
            widget.destroy()
            
        threading.Thread(target=self._scan_thread, daemon=True).start()
        
    def _scan_thread(self):
        # Simulate scanning steps for visual effect
        for i in range(1, 101, 10):
            time.sleep(0.05)
            self.progress_bar.set(i / 100.0)
            
        # Actually run inspection
        self.current_result = self.checker.run_inspection()
        
        # Update UI in main thread
        self.after(0, self._on_scan_complete)
        
    def _on_scan_complete(self):
        self.progress_bar.grid_remove()
        self.run_btn.configure(state="normal")
        self.enable_exports()
        
        score = self.current_result.health_score
        status = self.current_result.status_message
        
        color = "green" if score >= 90 else "orange" if score >= 70 else "red"
        
        self.score_lbl.configure(text=f"Score: {score} / 100", text_color=color)
        self.status_lbl.configure(text=status, text_color=color)
        
        self.apply_filter(self.filter_var.get())
        
    def apply_filter(self, filter_val):
        self.current_filter = filter_val
        self._render_issues()
        
    def _render_issues(self):
        # Clear
        for widget in self.issues_frame.winfo_children():
            widget.destroy()
            
        if not self.current_result:
            return
            
        issues_to_show = self.current_result.issues
        if self.current_filter != "All":
            issues_to_show = [i for i in issues_to_show if i.severity == self.current_filter]
            
        if not issues_to_show:
            ctk.CTkLabel(self.issues_frame, text="No issues found for this filter.", font=ctk.CTkFont(style="italic")).pack(pady=20)
            return
            
        colors = {
            "INFO": "#2196F3",
            "WARNING": "#FFC107",
            "ERROR": "#F44336",
            "CRITICAL": "#9C27B0"
        }
        
        for issue in issues_to_show:
            frame = ctk.CTkFrame(self.issues_frame)
            frame.pack(fill="x", pady=5, padx=5)
            
            # Severity color bar
            color_bar = ctk.CTkFrame(frame, width=5, fg_color=colors.get(issue.severity, "gray"))
            color_bar.pack(side="left", fill="y", padx=(0, 10))
            
            content = ctk.CTkFrame(frame, fg_color="transparent")
            content.pack(side="left", fill="x", expand=True, pady=10)
            
            # Title line
            header = ctk.CTkFrame(content, fg_color="transparent")
            header.pack(fill="x")
            
            ctk.CTkLabel(header, text=f"[{issue.severity}]", font=ctk.CTkFont(weight="bold", size=14), text_color=colors.get(issue.severity)).pack(side="left", padx=(0,10))
            ctk.CTkLabel(header, text=f"[{issue.category}] {issue.rule_name}", font=ctk.CTkFont(weight="bold", size=14)).pack(side="left")
            
            # Explanation
            ctk.CTkLabel(content, text=f"Explanation: {issue.explanation}", justify="left", anchor="w", wraplength=800).pack(fill="x", pady=(5,0))
            
            # Fix
            ctk.CTkLabel(content, text=f"Suggested Fix: {issue.suggested_fix}", justify="left", anchor="w", wraplength=800, text_color="gray75").pack(fill="x", pady=(2,0))

    def export_report(self, format_type):
        if not self.current_result:
            return
            
        exts = {
            "pdf": [("PDF Files", "*.pdf")],
            "html": [("HTML Files", "*.html")],
            "json": [("JSON Files", "*.json")]
        }
        
        path = filedialog.asksaveasfilename(defaultextension=f".{format_type}", filetypes=exts[format_type])
        if path:
            success = False
            if format_type == "pdf":
                success = ReportGenerator.export_pdf(self.current_result, path)
            elif format_type == "html":
                success = ReportGenerator.export_html(self.current_result, path)
            elif format_type == "json":
                success = ReportGenerator.export_json(self.current_result, path)
                
            if success:
                messagebox.showinfo("Success", f"Report exported to {os.path.basename(path)}")
            else:
                messagebox.showerror("Error", f"Failed to export {format_type.upper()} report.")
