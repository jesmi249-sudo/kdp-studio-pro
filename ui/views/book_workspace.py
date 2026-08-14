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
        self.top_nav = ctk.CTkFrame(self, height=60, fg_color=Colors.BG_CARD)
        self.top_nav.grid(row=0, column=0, sticky="ew")
        
        self.nav_buttons = []
        for i, title in enumerate(self.steps):
            btn = ctk.CTkButton(
                self.top_nav, 
                text=f"{i+1}. {title}",
                fg_color="transparent",
                text_color=Colors.TEXT_MUTED[1],
                hover_color=Colors.BG_SIDEBAR,
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
        
        # Spacer
        ctk.CTkFrame(self.bottom_nav, width=20, fg_color="transparent").pack(side="left")
        
        self.lbl_progress = ctk.CTkLabel(self.bottom_nav, text="Step 1 of 8", font=Fonts.body_bold())
        self.lbl_progress.pack(side="left")
        
        # Center spacing
        ctk.CTkFrame(self.bottom_nav, fg_color="transparent").pack(side="left", expand=True, fill="x")
        
        # Autosave indicator
        self.lbl_autosave = ctk.CTkLabel(self.bottom_nav, text="✓ Saved", text_color="gray", font=Fonts.body())
        self.lbl_autosave.pack(side="left", padx=20)
        
        self.btn_next = ctk.CTkButton(self.bottom_nav, text="Next →", command=self.next_step)
        self.btn_next.pack(side="right")
        
        self._autosave_timer = None

    def trigger_autosave(self):
        self.lbl_autosave.configure(text="Saving...")
        if self._autosave_timer:
            self.after_cancel(self._autosave_timer)
        self._autosave_timer = self.after(1000, self._perform_autosave)
        
    def _perform_autosave(self):
        if self.engine and self.project_id:
            try:
                # Assuming state changes have been applied to engine.get_active_project()
                project = self.engine.get_active_project()
                if project:
                    project.save_to_disk()
                self.lbl_autosave.configure(text="✓ All changes saved")
            except Exception as e:
                logger.error(f"Autosave failed: {e}")
                self.lbl_autosave.configure(text="⚠ Unable to save")

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
        
        form = ctk.CTkFrame(content, fg_color=Colors.BG_CARD)
        form.pack(fill="x", pady=10, padx=10)
        
        fields = ["Project Name", "Book Type", "Trim Size", "Page Count", "Bleed"]
        self.setup_entries = {}
        for i, field in enumerate(fields):
            ctk.CTkLabel(form, text=field, font=Fonts.body_bold()).grid(row=i, column=0, padx=20, pady=15, sticky="e")
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
        
        form = ctk.CTkFrame(f, fg_color=Colors.BG_CARD)
        form.pack(fill="x", pady=10)
        
        ctk.CTkLabel(form, text="Describe the book you want to create:", font=Fonts.body_bold()).pack(anchor="w", padx=20, pady=(20, 5))
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
            card = ctk.CTkFrame(self.plan_result_frame, fg_color=Colors.BG_SIDEBAR)
            card.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(card, text=f"Page {i+1}: {p.get('layout_type', '')}", font=Fonts.body_bold()).pack(anchor="w", padx=10, pady=(5,0))
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
            card = ctk.CTkFrame(scroll, fg_color=Colors.BG_CARD)
            card.pack(fill="x", pady=5, padx=10)
            
            ctk.CTkLabel(card, text=f"Page {i+1} - {p.get('layout', '')}", font=Fonts.body_bold()).pack(anchor="w", padx=10, pady=5)
            if "text" in p:
                entry = ctk.CTkEntry(card, width=600)
                entry.insert(0, p["text"])
                entry.pack(anchor="w", padx=10, pady=(0, 10))
                # Store it so we can save later
                
    def _build_images_tab(self):
        f = self.step_frames[4]
        for w in f.winfo_children(): w.destroy()
        
        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=20, padx=20)
        ctk.CTkLabel(header, text="Image Inspector & Generation", font=Fonts.heading2()).pack(side="left")
        
        self.btn_generate_images = ctk.CTkButton(header, text="Generate Missing Images", command=self._prompt_generate_images)
        self.btn_generate_images.pack(side="right")
        
        self.images_scroll = ctk.CTkScrollableFrame(f)
        self.images_scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        project = self.engine.get_active_project()
        if not project or not project.pages:
            ctk.CTkLabel(self.images_scroll, text="No pages available. Generate content first.").pack(pady=50)
            return
            
        for i, page in enumerate(project.pages):
            card = ctk.CTkFrame(self.images_scroll, fg_color=Colors.BG_CARD)
            card.pack(fill="x", pady=10)
            
            # Left: Thumbnail
            thumb_frame = ctk.CTkFrame(card, width=150, height=150, fg_color=Colors.BG_SIDEBAR)
            thumb_frame.pack(side="left", padx=10, pady=10)
            thumb_frame.pack_propagate(False)
            
            if page.image_path:
                try:
                    from PIL import Image
                    img = Image.open(page.image_path)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(130, 130))
                    lbl = ctk.CTkLabel(thumb_frame, text="", image=ctk_img)
                    lbl.image = ctk_img
                    lbl.pack(expand=True)
                except:
                    ctk.CTkLabel(thumb_frame, text="Corrupt\nImage", text_color="red").pack(expand=True)
            else:
                ctk.CTkLabel(thumb_frame, text="No Image", text_color="gray").pack(expand=True)
                
            # Right: Details
            details_frame = ctk.CTkFrame(card, fg_color="transparent")
            details_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
            
            ctk.CTkLabel(details_frame, text=f"Page {i+1}", font=Fonts.body_bold()).pack(anchor="w")
            
            # Find prompt from storybook data if available
            prompt = "No prompt specified."
            status = "pending"
            if "storybook_data" in project.custom_settings:
                pages_data = project.custom_settings["storybook_data"].get("pages", [])
                if i < len(pages_data):
                    p_data = pages_data[i]
                    prompt = p_data.get("image_prompt", prompt)
                    if "image_reference" in p_data:
                        status = p_data["image_reference"].get("status", status)
                        
            ctk.CTkLabel(details_frame, text=f"Prompt: {prompt}", wraplength=400, justify="left").pack(anchor="w", pady=5)
            
            status_color = "orange" if status == "pending" else "red" if status == "failed" else "green"
            if page.image_path:
                status = "completed"
                status_color = "green"
                
            ctk.CTkLabel(details_frame, text=f"Status: {status}", text_color=status_color).pack(anchor="w")
            
            # Action button
            if status != "completed":
                ctk.CTkButton(details_frame, text="Generate", width=80, command=lambda idx=i: self._generate_single_image(idx)).pack(anchor="w", pady=10)
            else:
                ctk.CTkButton(details_frame, text="Regenerate", width=80, fg_color="transparent", border_width=1, text_color=Colors.TEXT_MAIN[1], command=lambda idx=i: self._generate_single_image(idx)).pack(anchor="w", pady=10)
                
    def _prompt_generate_images(self):
        project = self.engine.get_active_project()
        if not project: return
        
        missing_indices = []
        for i, p in enumerate(project.pages):
            if not p.image_path:
                missing_indices.append(i)
                
        if not missing_indices:
            messagebox.showinfo("Done", "All pages already have images.")
            return
            
        count = len(missing_indices)
        
        # Display cost protection prompt (F7)
        confirm = messagebox.askyesno(
            "Confirm Generation",
            f"{count} images need to be generated.\n\nEstimated provider usage: {count} image generations.\n\nDo you want to proceed?"
        )
        if confirm:
            self.btn_generate_images.configure(state="disabled", text="Generating...")
            self._execute_batch_generation(missing_indices)
            
    def _generate_single_image(self, index):
        confirm = messagebox.askyesno(
            "Confirm Regeneration",
            "Estimated provider usage: 1 image generation.\nDo you want to proceed?"
        )
        if confirm:
            self._execute_batch_generation([index])
            
    def _execute_batch_generation(self, indices):
        def worker():
            project = self.engine.get_active_project()
            try:
                from book_builder.container import Container
                from book_builder.services.ai.manager import AIManager
                ai = Container().resolve(AIManager)
                
                # Fetch storybook data properly
                pages_data = project.custom_settings.get("storybook_data", {}).get("pages", [])
                
                for idx in indices:
                    # Update status
                    if idx < len(pages_data):
                        if "image_reference" not in pages_data[idx]:
                            pages_data[idx]["image_reference"] = {}
                        pages_data[idx]["image_reference"]["status"] = "generating"
                    self.after(0, self._build_images_tab)
                    
                    # Call AI
                    prompt = pages_data[idx].get("image_prompt", "")
                    if prompt:
                        result = ai.generate_image_prompt(prompt, "storybook_style")
                        if result.success and result.content:
                            project.pages[idx].image_path = result.content
                            pages_data[idx]["image_path"] = result.content
                            pages_data[idx]["image_reference"]["status"] = "completed"
                            self.after(0, self.trigger_autosave)
                        else:
                            pages_data[idx]["image_reference"]["status"] = "failed"
                            
                    self.after(0, self._build_images_tab)
                    
            except Exception as e:
                logger.error(f"Image generation failed: {e}")
            finally:
                self.after(0, lambda: self.btn_generate_images.configure(state="normal", text="Generate Missing Images"))
                self.after(0, self._build_images_tab)
                
        threading.Thread(target=worker, daemon=True).start()
        
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
        
        # Top toolbar
        toolbar = ctk.CTkFrame(f, fg_color="transparent")
        toolbar.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkLabel(toolbar, text="Book Preview", font=Fonts.heading2()).pack(side="left")
        
        self.preview_mode = ctk.StringVar(value="Single Page")
        mode_btn = ctk.CTkSegmentedButton(toolbar, values=["Single Page", "Two-Page Spread"], variable=self.preview_mode, command=self._refresh_preview)
        mode_btn.pack(side="left", padx=20)
        
        self.preview_zoom = ctk.DoubleVar(value=1.0)
        
        btn_zoom_out = ctk.CTkButton(toolbar, text="-", width=30, command=lambda: self._set_preview_zoom(-0.2))
        btn_zoom_out.pack(side="left", padx=5)
        
        self.lbl_zoom = ctk.CTkLabel(toolbar, text="100%", width=40)
        self.lbl_zoom.pack(side="left")
        
        btn_zoom_in = ctk.CTkButton(toolbar, text="+", width=30, command=lambda: self._set_preview_zoom(0.2))
        btn_zoom_in.pack(side="left", padx=5)
        
        btn_fit = ctk.CTkButton(toolbar, text="Fit", width=50, command=lambda: self._set_preview_zoom(0, fit=True))
        btn_fit.pack(side="left", padx=5)
        
        # Main layout: Left thumbnails, Right preview
        main_pane = ctk.CTkFrame(f, fg_color="transparent")
        main_pane.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left Panel (Thumbnails)
        self.preview_thumb_frame = ctk.CTkScrollableFrame(main_pane, width=150)
        self.preview_thumb_frame.pack(side="left", fill="y", padx=(0, 10))
        
        # Center Panel (Large Preview)
        self.preview_canvas_frame = ctk.CTkScrollableFrame(main_pane, fg_color=Colors.BG_SIDEBAR)
        self.preview_canvas_frame.pack(side="left", fill="both", expand=True)
        
        self.preview_image_label = ctk.CTkLabel(self.preview_canvas_frame, text="")
        self.preview_image_label.pack(expand=True, pady=20)
        
        # Bottom controls
        bottom_ctrls = ctk.CTkFrame(f, fg_color="transparent")
        bottom_ctrls.pack(fill="x", pady=10, padx=10)
        
        self.btn_prev_page = ctk.CTkButton(bottom_ctrls, text="← Previous", command=self._preview_prev_page)
        self.btn_prev_page.pack(side="left")
        
        self.lbl_page_num = ctk.CTkLabel(bottom_ctrls, text="Page 1 of ?", font=Fonts.body_bold())
        self.lbl_page_num.pack(side="left", expand=True)
        
        self.btn_next_page = ctk.CTkButton(bottom_ctrls, text="Next →", command=self._preview_next_page)
        self.btn_next_page.pack(side="right")
        
        self.current_preview_index = 0
        self.preview_cache_svc = None
        self.thumbnail_svc = None
        
    def _init_preview_services(self):
        if not self.preview_cache_svc:
            from book_builder.rendering.service import PreviewService
            from book_builder.rendering.thumbnail import PageThumbnailGenerator
            self.preview_cache_svc = PreviewService(rendering_engine=self.engine.rendering_engine)
            self.thumbnail_svc = PageThumbnailGenerator(rendering_engine=self.engine.rendering_engine)
            
    def _set_preview_zoom(self, delta, fit=False):
        if fit:
            self.preview_zoom.set(1.0)
        else:
            new_z = max(0.2, min(3.0, self.preview_zoom.get() + delta))
            self.preview_zoom.set(new_z)
        self.lbl_zoom.configure(text=f"{int(self.preview_zoom.get() * 100)}%")
        self._refresh_preview()

    def _preview_prev_page(self):
        step = 2 if self.preview_mode.get() == "Two-Page Spread" else 1
        self.current_preview_index = max(0, self.current_preview_index - step)
        self._refresh_preview()
        
    def _preview_next_page(self):
        step = 2 if self.preview_mode.get() == "Two-Page Spread" else 1
        project = self.engine.get_active_project()
        if project:
            self.current_preview_index = min(len(project.pages) - 1, self.current_preview_index + step)
        self._refresh_preview()

    def _refresh_preview(self, *_):
        project = self.engine.get_active_project()
        if not project or not project.pages:
            self.preview_image_label.configure(text="No pages in project.", image="")
            return
            
        self._init_preview_services()
        self.preview_image_label.configure(text="Preparing preview...", image="")
        
        def render_worker():
            try:
                pages = project.pages
                idx = self.current_preview_index
                
                # Ensure idx is valid
                if idx >= len(pages):
                    idx = len(pages) - 1
                
                is_spread = self.preview_mode.get() == "Two-Page Spread"
                zoom = self.preview_zoom.get()
                
                # Render logic
                img1 = self.preview_cache_svc.generate_preview(pages[idx], zoom_level=zoom)
                
                if is_spread and idx + 1 < len(pages):
                    img2 = self.preview_cache_svc.generate_preview(pages[idx+1], zoom_level=zoom)
                    from PIL import Image
                    spread = Image.new('RGB', (img1.width + img2.width, max(img1.height, img2.height)), (255,255,255))
                    spread.paste(img1, (0, 0))
                    spread.paste(img2, (img1.width, 0))
                    final_img = spread
                    display_text = f"Pages {idx+1}-{idx+2} of {len(pages)}"
                else:
                    final_img = img1
                    display_text = f"Page {idx+1} of {len(pages)}"
                
                ctk_img = ctk.CTkImage(light_image=final_img, dark_image=final_img, size=(final_img.width, final_img.height))
                
                self.after(0, lambda: self._update_preview_canvas(ctk_img, display_text))
            except Exception as e:
                logger.error(f"Preview render failed: {e}")
                self.after(0, lambda: self.preview_image_label.configure(text="Render Error"))
                
        threading.Thread(target=render_worker, daemon=True).start()
        self._refresh_thumbnails()

    def _update_preview_canvas(self, img, text):
        self.preview_image_label.configure(text="", image=img)
        self.preview_image_label.image = img
        self.lbl_page_num.configure(text=text)

    def _refresh_thumbnails(self):
        project = self.engine.get_active_project()
        if not project: return
        
        # Clear existing
        for w in self.preview_thumb_frame.winfo_children():
            w.destroy()
            
        def thumb_worker():
            for i, p in enumerate(project.pages):
                try:
                    path = self.thumbnail_svc.get_thumbnail_path(p, size=(100, 100))
                    if path:
                        from PIL import Image
                        img = Image.open(path)
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 100))
                        
                        def on_click(event, idx=i):
                            self.current_preview_index = idx
                            self._refresh_preview()
                            
                        self.after(0, lambda idx=i, ci=ctk_img: self._add_thumbnail_ui(idx, ci, on_click))
                except Exception as e:
                    logger.error(f"Thumbnail failed for page {p.id}: {e}")
                    
        threading.Thread(target=thumb_worker, daemon=True).start()

    def _add_thumbnail_ui(self, idx, ctk_img, on_click):
        card = ctk.CTkFrame(self.preview_thumb_frame)
        card.pack(pady=5, padx=5, fill="x")
        lbl = ctk.CTkLabel(card, text="", image=ctk_img)
        lbl.image = ctk_img
        lbl.pack(pady=5)
        lbl.bind("<Button-1>", on_click)
        
        # Status indicators (F4)
        project = self.engine.get_active_project()
        p = project.pages[idx]
        status = "✓"
        color = "green"
        if not p.image_path:
            status = "⚠ Missing Image"
            color = "orange"
        if not p.text_content:
            status = "⚠ Missing Text"
            color = "orange"
            
        ctk.CTkLabel(card, text=f"Page {idx+1}\n{status}", text_color=color, font=Fonts.small()).pack()

    def _build_kdp_check_tab(self):
        f = self.step_frames[7]
        for w in f.winfo_children(): w.destroy()
        
        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=20, padx=20)
        ctk.CTkLabel(header, text="KDP Quality Assurance", font=Fonts.heading2()).pack(side="left")
        
        self.qa_btn = ctk.CTkButton(header, text="Run Inspection", command=self._run_qa_inspection)
        self.qa_btn.pack(side="right")
        
        self.qa_results_frame = ctk.CTkScrollableFrame(f, fg_color="transparent")
        self.qa_results_frame.pack(fill="both", expand=True, padx=20)
        
        ctk.CTkLabel(self.qa_results_frame, text="Click 'Run Inspection' to verify your book.", font=Fonts.body()).pack(pady=50)

    def _run_qa_inspection(self):
        self.qa_btn.configure(state="disabled", text="Inspecting...")
        for w in self.qa_results_frame.winfo_children(): w.destroy()
        ctk.CTkLabel(self.qa_results_frame, text="Running checks...", font=Fonts.body()).pack(pady=50)
        
        def worker():
            try:
                from core.compliance_checker import ComplianceChecker
                app = self.winfo_toplevel()
                checker = ComplianceChecker(app)
                result = checker.run_inspection()
                self.after(0, lambda: self._render_qa_results(result))
            except Exception as e:
                logger.error(f"QA Failed: {e}")
                self.after(0, lambda: self._render_qa_error(str(e)))
                
        threading.Thread(target=worker, daemon=True).start()

    def _render_qa_error(self, err):
        self.qa_btn.configure(state="normal", text="Run Inspection")
        for w in self.qa_results_frame.winfo_children(): w.destroy()
        ctk.CTkLabel(self.qa_results_frame, text=f"Inspection Error: {err}", text_color="red").pack(pady=20)

    def _render_qa_results(self, result):
        self.qa_btn.configure(state="normal", text="Run Inspection")
        for w in self.qa_results_frame.winfo_children(): w.destroy()
        
        score_color = "green" if result.health_score > 90 else "orange" if result.health_score > 70 else "red"
        ctk.CTkLabel(self.qa_results_frame, text=f"Health Score: {result.health_score}/100", font=Fonts.heading2(), text_color=score_color).pack(pady=10)
        
        # Group issues
        groups = {"Book": [], "Layout": [], "Content": [], "Images": [], "Export": []}
        
        for issue in result.issues:
            # Simple heuristic categorization
            if "dimension" in issue.detail.lower() or "margin" in issue.detail.lower() or "bleed" in issue.detail.lower():
                groups["Layout"].append(issue)
            elif "image" in issue.detail.lower() or "resolution" in issue.detail.lower() or "corrupt" in issue.detail.lower():
                groups["Images"].append(issue)
            elif "text" in issue.detail.lower() or "missing" in issue.detail.lower():
                groups["Content"].append(issue)
            else:
                groups["Book"].append(issue)
                
        # Render groups
        for g_name, g_issues in groups.items():
            g_frame = ctk.CTkFrame(self.qa_results_frame, fg_color=Colors.BG_CARD)
            g_frame.pack(fill="x", pady=10, padx=10)
            
            ctk.CTkLabel(g_frame, text=g_name, font=Fonts.body_bold()).pack(anchor="w", padx=10, pady=5)
            
            if not g_issues:
                ctk.CTkLabel(g_frame, text=f"✓ {g_name} checks passed.", text_color="green").pack(anchor="w", padx=20, pady=5)
            else:
                for issue in g_issues:
                    issue_f = ctk.CTkFrame(g_frame, fg_color="transparent")
                    issue_f.pack(fill="x", padx=20, pady=2)
                    
                    icon = "⚠" if issue.severity == "WARNING" else "✕"
                    color = "orange" if issue.severity == "WARNING" else "red"
                    
                    ctk.CTkLabel(issue_f, text=f"{icon} {issue.description}: {issue.detail}", text_color=color, wraplength=500, justify="left").pack(side="left")
                    
                    # Actionable fix routing
                    if "image" in issue.detail.lower():
                        ctk.CTkButton(issue_f, text="Fix Image", width=80, command=lambda: self.go_to_step(4)).pack(side="right")
                    elif "text" in issue.detail.lower():
                        ctk.CTkButton(issue_f, text="Fix Text", width=80, command=lambda: self.go_to_step(3)).pack(side="right")
                    elif "dimension" in issue.detail.lower() or "bleed" in issue.detail.lower():
                        ctk.CTkButton(issue_f, text="Check Setup", width=80, command=lambda: self.go_to_step(1)).pack(side="right")

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
                btn.configure(text_color=Colors.TEXT_MAIN[1], font=Fonts.body_bold())
            else:
                btn.configure(text_color=Colors.TEXT_MUTED[1], font=Fonts.body())
                
        # Update Bottom Nav
        self.btn_back.configure(state="normal" if step > 1 else "disabled")
        self.btn_next.configure(state="normal" if step < len(self.steps) else "disabled")
        self.lbl_progress.configure(text=f"Step {step} of {len(self.steps)} - {self.steps[step-1]}")

    def next_step(self):
        self.go_to_step(self.current_step + 1)
        
    def prev_step(self):
        self.go_to_step(self.current_step - 1)
