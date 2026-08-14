import customtkinter as ctk
from tkinter import messagebox
import json
import threading

from book_builder.container import Container
from book_builder.interfaces.core import IBookBuilder
from core.logger import get_logger
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts
from ui.theme.spacing import Spacing

logger = get_logger(__name__)

class BookWorkspaceView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.project_id = None
        self.project_name = ""
        self.state = {}
        
        self.current_step = 1
        
        # Step titles
        self.steps = [
            "Setup",
            "Planner",
            "Content",
            "Images",
            "Layout",
            "Preview",
            "KDP Check",
            "Export"
        ]
        
        self.step_frames = {}
        
        self._build_top_nav()
        self._build_main_area()
        self._build_step_frames()
        self._build_bottom_nav()
        
    def _build_top_nav(self):
        self.top_nav = ctk.CTkFrame(self, height=60, fg_color=Colors.SURFACE)
        self.top_nav.grid(row=0, column=0, sticky="ew")
        
        self.nav_buttons = []
        for i, title in enumerate(self.steps):
            btn = ctk.CTkButton(
                self.top_nav, 
                text=f"{i+1}. {title}",
                fg_color="transparent",
                text_color=Colors.TEXT_MUTED[1],
                hover_color=Colors.SURFACE_HOVER,
                command=lambda idx=i+1: self.go_to_step(idx)
            )
            btn.pack(side="left", padx=10, pady=15)
            self.nav_buttons.append(btn)
            
    def _build_main_area(self):
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=1, column=0, sticky="nsew", padx=Spacing.M, pady=Spacing.M)
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)
        
    def _build_bottom_nav(self):
        self.bottom_nav = ctk.CTkFrame(self, height=50, fg_color="transparent")
        self.bottom_nav.grid(row=2, column=0, sticky="ew", padx=Spacing.M, pady=Spacing.M)
        
        self.btn_back = ctk.CTkButton(self.bottom_nav, text="← Back", command=self.prev_step)
        self.btn_back.pack(side="left")
        
        self.lbl_progress = ctk.CTkLabel(self.bottom_nav, text="Step 1 of 8", font=Fonts.ui_bold())
        self.lbl_progress.pack(side="left", expand=True)
        
        self.btn_next = ctk.CTkButton(self.bottom_nav, text="Next →", command=self.next_step)
        self.btn_next.pack(side="right")

    def _build_step_frames(self):
        # Initialize empty frames for each step
        for i in range(1, 9):
            frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
            frame.grid_rowconfigure(1, weight=1)
            frame.grid_columnconfigure(0, weight=1)
            self.step_frames[i] = frame

    def _build_setup_tab(self):
        f = self.step_frames[1]
        for w in f.winfo_children(): w.destroy()
        
        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=20)
        ctk.CTkLabel(header, text="Project Setup", font=Fonts.heading2()).pack(side="left")
        
        content = ctk.CTkScrollableFrame(f, fg_color="transparent")
        content.pack(fill="both", expand=True)
        
        form = ctk.CTkFrame(content, fg_color=Colors.SURFACE)
        form.pack(fill="x", pady=10, padx=10)
        
        fields = ["Project Name", "Book Type", "Trim Size", "Page Count", "Bleed"]
        self.setup_entries = {}
        for i, field in enumerate(fields):
            ctk.CTkLabel(form, text=field, font=Fonts.ui_bold()).grid(row=i, column=0, padx=20, pady=15, sticky="e")
            entry = ctk.CTkEntry(form, width=300)
            entry.grid(row=i, column=1, padx=20, pady=15, sticky="w")
            
            key = field.lower().replace(" ", "_")
            val = ""
            if key == "project_name":
                val = self.project_name
            elif key == "book_type":
                val = self.engine.get_active_project().book_type
            elif key == "page_count":
                val = str(self.engine.get_active_project().settings.get("page_count", 0))
            elif key == "trim_size":
                w = self.engine.get_active_project().settings.get("trim_width_in", 8.5)
                h = self.engine.get_active_project().settings.get("trim_height_in", 11.0)
                val = f"{w} x {h}"
            elif key == "bleed":
                val = "Yes" if self.engine.get_active_project().settings.get("has_bleed", False) else "No"
                
            entry.insert(0, val)
            entry.configure(state="disabled") # Setup is read-only in this phase for simplicity
            
    def _build_planner_tab(self):
        f = self.step_frames[2]
        for w in f.winfo_children(): w.destroy()
        
        # We reuse BookScenePlannerView or build a simpler AI planner interface here.
        # The prompt asked for "What kind of book do you want to create?"
        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=20)
        ctk.CTkLabel(header, text="AI Book Planner", font=Fonts.heading2()).pack(side="left")
        
        form = ctk.CTkFrame(f, fg_color=Colors.SURFACE)
        form.pack(fill="x", pady=10)
        
        ctk.CTkLabel(form, text="Describe the book you want to create:", font=Fonts.ui_bold()).pack(anchor="w", padx=20, pady=(20, 5))
        self.ai_prompt = ctk.CTkEntry(form, placeholder_text="e.g. A 24-page children's story about Lilly...", width=500)
        self.ai_prompt.pack(anchor="w", padx=20, pady=(0, 20))
        
        self.btn_plan = ctk.CTkButton(form, text="✨ Create Plan", command=self._generate_ai_plan)
        self.btn_plan.pack(anchor="w", padx=20, pady=(0, 20))
        
        self.plan_result_frame = ctk.CTkScrollableFrame(f)
        self.plan_result_frame.pack(fill="both", expand=True, pady=10)
        
        # Load existing plan if present
        project = self.engine.get_active_project()
        if project and "ai_plan" in project.custom_settings:
            self._display_ai_plan(project.custom_settings["ai_plan"])
            
    def _generate_ai_plan(self):
        prompt = self.ai_prompt.get().strip()
        if not prompt: return
        
        self.btn_plan.configure(state="disabled", text="Generating...")
        
        def worker():
            try:
                from book_builder.services.ai.manager import AIManager
                from book_builder.services.ai.planner import AIBookPlannerService
                ai_manager = Container().resolve(AIManager)
                planner = AIBookPlannerService(ai_manager)
                
                project = self.engine.get_active_project()
                b_type = project.book_type.lower()
                count = project.settings.get("page_count", 10)
                
                spec = planner.generate_book_plan(prompt, book_type=b_type, page_count=count)
                self.after(0, self._on_ai_plan_success, spec)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("AI Error", str(e)))
                self.after(0, lambda: self.btn_plan.configure(state="normal", text="✨ Create Plan"))
                
        threading.Thread(target=worker, daemon=True).start()

    def _on_ai_plan_success(self, spec):
        self.btn_plan.configure(state="normal", text="✨ Create Plan")
        project = self.engine.get_active_project()
        project.custom_settings["ai_plan"] = spec.model_dump()
        project.save_to_disk()
        self._display_ai_plan(spec.model_dump())
        
        # Also sync to storybook_data so Content/Images tab can use it
        pages_data = []
        for p in spec.pages:
            p_dict = {"layout": p.layout_type, "text": p.text_content or ""}
            if p.image_prompt:
                p_dict["image_prompt"] = p.image_prompt
                p_dict["image_reference"] = {"image_prompt": p.image_prompt, "status": "pending"}
                p_dict["image_path"] = ""
            pages_data.append(p_dict)
            
        project.custom_settings["storybook_data"] = {
            "global_settings": {"font_family": "Georgia.ttf", "font_size": 18.0},
            "pages": pages_data
        }
        project.save_to_disk()
        self._build_content_tab()
        self._build_images_tab()

    def _display_ai_plan(self, plan_dict):
        for w in self.plan_result_frame.winfo_children(): w.destroy()
        
        title = plan_dict.get("title", "Untitled")
        ctk.CTkLabel(self.plan_result_frame, text=f"Title: {title}", font=Fonts.heading3()).pack(anchor="w", pady=10, padx=10)
        
        pages = plan_dict.get("pages", [])
        for i, p in enumerate(pages):
            card = ctk.CTkFrame(self.plan_result_frame, fg_color=Colors.SURFACE_HOVER)
            card.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(card, text=f"Page {i+1}: {p.get('layout_type', '')}", font=Fonts.ui_bold()).pack(anchor="w", padx=10, pady=(5,0))
            if p.get("text_content"):
                ctk.CTkLabel(card, text=f"Text: {p.get('text_content')}", wraplength=600, justify="left").pack(anchor="w", padx=10)
            if p.get("image_prompt"):
                ctk.CTkLabel(card, text=f"Image: {p.get('image_prompt')}", wraplength=600, justify="left", text_color="gray").pack(anchor="w", padx=10, pady=(0,5))

    def _build_content_tab(self):
        f = self.step_frames[3]
        for w in f.winfo_children(): w.destroy()
        
        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=20)
        ctk.CTkLabel(header, text="Content Editor", font=Fonts.heading2()).pack(side="left")
        
        scroll = ctk.CTkScrollableFrame(f)
        scroll.pack(fill="both", expand=True)
        
        project = self.engine.get_active_project()
        if not project or "storybook_data" not in project.custom_settings:
            ctk.CTkLabel(scroll, text="No content available. Generate an AI Plan first.").pack(pady=20)
            return
            
        pages = project.custom_settings["storybook_data"].get("pages", [])
        for i, p in enumerate(pages):
            card = ctk.CTkFrame(scroll, fg_color=Colors.SURFACE)
            card.pack(fill="x", pady=5, padx=10)
            
            ctk.CTkLabel(card, text=f"Page {i+1} - {p.get('layout', '')}", font=Fonts.ui_bold()).pack(anchor="w", padx=10, pady=5)
            if "text" in p:
                entry = ctk.CTkEntry(card, width=600)
                entry.insert(0, p["text"])
                entry.pack(anchor="w", padx=10, pady=(0, 10))
                # Store it so we can save later
                
    def _build_images_tab(self):
        f = self.step_frames[4]
        for w in f.winfo_children(): w.destroy()
        
        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=20)
        ctk.CTkLabel(header, text="Image Generation", font=Fonts.heading2()).pack(side="left")
        
        # We reuse the visual sequence from StoryBookSettingsPanel
        from ui.views.storybook_studio import StoryBookSettingsPanel
        # Mocking the controller interface enough for the panel
        class DummyController:
            def __init__(self, engine):
                self.engine = engine
        
        panel = StoryBookSettingsPanel(f, DummyController(self.engine))
        panel.pack(fill="both", expand=True)
        
    def _build_layout_tab(self):
        f = self.step_frames[5]
        for w in f.winfo_children(): w.destroy()
        
        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(header, text="Layout Editor", font=Fonts.heading2()).pack(side="left")
        
        from ui.views.book_builder import BookBuilderView
        builder = BookBuilderView(f)
        builder.pack(fill="both", expand=True)
        
        # Load the project directly into the embedded BookBuilderView
        builder.controller.engine = self.engine
        builder.controller.active_project_id = self.project_id
        builder.refresh_data()

    def _build_preview_tab(self):
        f = self.step_frames[6]
        for w in f.winfo_children(): w.destroy()
        
        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=20)
        ctk.CTkLabel(header, text="Book Preview", font=Fonts.heading2()).pack(side="left")
        
        scroll = ctk.CTkScrollableFrame(f)
        scroll.pack(fill="both", expand=True)
        ctk.CTkLabel(scroll, text="PDF Preview will be rendered here. (Feature coming soon)").pack(pady=50)

    def _build_kdp_check_tab(self):
        f = self.step_frames[7]
        for w in f.winfo_children(): w.destroy()
        
        from ui.views.compliance_view import ComplianceView
        cv = ComplianceView(f)
        cv.app = self.winfo_toplevel()
        cv.pack(fill="both", expand=True)

    def _build_export_tab(self):
        f = self.step_frames[8]
        for w in f.winfo_children(): w.destroy()
        
        from ui.views.export_center import ExportCenterView
        ev = ExportCenterView(f)
        ev.pack(fill="both", expand=True)

    def _populate_step_frames(self):
        self._build_setup_tab()
        self._build_planner_tab()
        self._build_content_tab()
        self._build_images_tab()
        self._build_layout_tab()
        self._build_preview_tab()
        self._build_kdp_check_tab()
        self._build_export_tab()

    def go_to_step(self, step):
        if step < 1 or step > len(self.steps):
            return
            
        # Hide all
        for f in self.step_frames.values():
            f.grid_forget()
            
        # Show target
        self.step_frames[step].grid(row=0, column=0, sticky="nsew")
        self.current_step = step
        
        # Update Nav UI
        for i, btn in enumerate(self.nav_buttons):
            if i + 1 == step:
                btn.configure(text_color=Colors.TEXT_MAIN[1], font=Fonts.ui_bold())
            else:
                btn.configure(text_color=Colors.TEXT_MUTED[1], font=Fonts.ui())
                
        # Update Bottom Nav
        self.btn_back.configure(state="normal" if step > 1 else "disabled")
        self.btn_next.configure(state="normal" if step < len(self.steps) else "disabled")
        self.lbl_progress.configure(text=f"Step {step} of {len(self.steps)} - {self.steps[step-1]}")

    def next_step(self):
        self.go_to_step(self.current_step + 1)
        
    def prev_step(self):
        self.go_to_step(self.current_step - 1)
