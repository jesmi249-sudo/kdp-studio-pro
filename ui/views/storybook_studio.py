import os
import json
import threading
from typing import Any, Dict, Optional, List
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image

from book_builder.studio_registry import StudioRegistry, StudioMetadata
from book_builder.templates.storybook import StorybookTemplateGenerator
from book_builder.commands.storybook_commands import GenerateStorybookPagesCommand
from book_builder.container import Container
from book_builder.services.ai.manager import AIManager
from book_builder.services.ai.planner import AIBookPlannerService
from book_builder.services.ai.schemas import BookSpecification, GeneratedImageReference
from book_builder.services.ai.image_service import ImageGenerationService
from book_builder.jobs.image_tasks import GenerateImageTask
from book_builder.jobs.queue import TaskQueue
from ui.views.book_builder import BookBuilderView, WorkspaceController
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts
from ui.theme.spacing import Spacing
from core.logger import get_logger
from core.asset_manager import AssetManager

logger = get_logger(__name__)


class StoryBookSettingsPanel(ctk.CTkFrame):
    """
    Settings panel containing configuration controls for generating Storybook pages.
    Hosted inside the PropertiesPanel of BookBuilderView.
    """
    def __init__(self, master: Any, controller: WorkspaceController, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.pages_data = [] # List of dicts representing the pages
        self._build_ui()
        self._load_saved_settings()

    def _load_saved_settings(self) -> None:
        project = self.controller.engine.get_active_project()
        if not project or "storybook_data" not in project.custom_settings:
            return
        
        settings = project.custom_settings["storybook_data"]
        global_settings = settings.get("global_settings", {})
        
        if "font_family" in global_settings:
            self.font_var.set(global_settings["font_family"])
        if "font_size" in global_settings:
            self.size_entry.delete(0, "end")
            self.size_entry.insert(0, str(global_settings["font_size"]))
            
        self.pages_data = settings.get("pages", [])
        self._refresh_sequence_ui()

    def _build_ui(self) -> None:
        # Title
        ctk.CTkLabel(self, text="Storybook Layout Engine", font=Fonts.heading3()).pack(anchor="w", pady=(0, Spacing.S))
        
        # 1. AI Book Planner
        self._add_group_header("1. AI Book Planner")
        
        ai_frame = ctk.CTkFrame(self, fg_color="transparent")
        ai_frame.pack(fill="x", pady=(0, Spacing.S))
        
        ctk.CTkLabel(ai_frame, text="Book Idea:").pack(anchor="w")
        self.ai_prompt_entry = ctk.CTkEntry(ai_frame, placeholder_text="A story about a brave knight...")
        self.ai_prompt_entry.pack(fill="x", pady=(Spacing.XS, Spacing.XS))
        
        self.ai_btn = ctk.CTkButton(ai_frame, text="Generate AI Plan", command=self._on_generate_ai_plan)
        self.ai_btn.pack(fill="x")
        
        # 2. Global Settings Group
        self._add_group_header("2. Typography")
        
        font_frame = ctk.CTkFrame(self, fg_color="transparent")
        font_frame.pack(fill="x", pady=(0, Spacing.S))
        
        ctk.CTkLabel(font_frame, text="Font Family:").pack(side="left")
        self.font_var = ctk.StringVar(value="Georgia.ttf")
        ctk.CTkOptionMenu(font_frame, variable=self.font_var, values=["Georgia.ttf", "Arial.ttf", "Times.ttf", "Courier.ttf"], width=120).pack(side="right")
        
        size_frame = ctk.CTkFrame(self, fg_color="transparent")
        size_frame.pack(fill="x", pady=(0, Spacing.S))
        
        ctk.CTkLabel(size_frame, text="Font Size (pt):").pack(side="left")
        self.size_entry = ctk.CTkEntry(size_frame, width=60)
        self.size_entry.pack(side="right")
        self.size_entry.insert(0, "18.0")
        
        # 3. Story Sequence UI
        self._add_group_header("3. Story Sequence")
        
        # Batch Generate Button
        self.batch_btn = ctk.CTkButton(self, text="Generate All Missing Images", command=self._on_batch_generate_images, fg_color=Colors.INFO[0], hover_color=Colors.INFO[1])
        self.batch_btn.pack(fill="x", pady=(0, Spacing.S))
        
        self.sequence_frame = ctk.CTkScrollableFrame(self, height=350)
        self.sequence_frame.pack(fill="x", pady=(0, Spacing.S))
        
        default_data = [
            {"layout": "title_page", "title": "My Great Story", "author": "Antigravity AI"},
            {"layout": "image_top_text_bottom", "text": "Once upon a time in a digital world...", "image_path": "", "image_prompt": "A digital world with glowing circuits, cinematic lighting"},
            {"layout": "text_overlay", "text": "There lived an AI building a book.", "image_path": "", "image_prompt": "A robot reading a glowing magical book"},
            {"layout": "ending_page"}
        ]
        if not self.pages_data:
            self.pages_data = default_data
            
        self._refresh_sequence_ui()

        # 4. Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(Spacing.M, 0))
        
        ctk.CTkButton(btn_frame, text="Apply & Render Book", fg_color=Colors.PRIMARY[0], hover_color=Colors.PRIMARY[1], command=self._on_generate).pack(fill="x")

    def _add_group_header(self, text: str) -> None:
        ctk.CTkLabel(self, text=text, font=Fonts.ui_bold(), text_color=Colors.TEXT_MAIN[1]).pack(anchor="w", pady=(Spacing.M, Spacing.XS))
        ctk.CTkFrame(self, height=1, fg_color=Colors.BORDER).pack(fill="x", pady=(0, Spacing.S))

    def _refresh_sequence_ui(self):
        for widget in self.sequence_frame.winfo_children():
            widget.destroy()
            
        for i, page in enumerate(self.pages_data):
            card = ctk.CTkFrame(self.sequence_frame, fg_color=Colors.SURFACE, corner_radius=6)
            card.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)
            
            layout = page.get("layout", "unknown")
            header_text = f"Page {i+1} ({layout})"
            ctk.CTkLabel(card, text=header_text, font=Fonts.ui_bold()).pack(anchor="w", padx=Spacing.S, pady=(Spacing.S, 0))
            
            if "text" in page:
                ctk.CTkLabel(card, text=f"Text: {page['text'][:30]}...", text_color=Colors.TEXT_MUTED[1]).pack(anchor="w", padx=Spacing.S)
                
            if "image_prompt" in page:
                prompt = page["image_prompt"]
                ctk.CTkLabel(card, text=f"Prompt: {prompt}", wraplength=200, justify="left", font=("Arial", 10)).pack(anchor="w", padx=Spacing.S, pady=Spacing.XS)
                
                ref_dict = page.get("image_reference")
                
                status_text = "Pending"
                if ref_dict:
                    status_text = ref_dict.get("status", "pending")
                
                status_lbl = ctk.CTkLabel(card, text=f"Status: {status_text}", text_color=Colors.INFO[0] if status_text == "ready" else Colors.TEXT_MUTED[1])
                status_lbl.pack(anchor="w", padx=Spacing.S)
                
                btn_text = "Regenerate Image" if status_text == "ready" else "Generate Image"
                
                # Capture i correctly for lambda
                gen_btn = ctk.CTkButton(card, text=btn_text, width=120, height=24,
                                        command=lambda idx=i, lbl=status_lbl, b=None: self._on_generate_single_image(idx, lbl))
                gen_btn.pack(anchor="e", padx=Spacing.S, pady=(0, Spacing.S))

    def _on_generate_ai_plan(self) -> None:
        project = self.controller.engine.get_active_project()
        if not project:
            messagebox.showwarning("No Project", "No active project found.")
            return
            
        prompt = self.ai_prompt_entry.get().strip()
        if not prompt:
            messagebox.showwarning("Empty Idea", "Please enter a book idea first.")
            return
            
        try:
            ai_manager = Container().resolve(AIManager)
            planner = AIBookPlannerService(ai_manager)
        except ValueError:
            messagebox.showerror("AI Disabled", "AI features are disabled or not configured in settings.")
            return
            
        self.ai_btn.configure(state="disabled", text="Generating plan...")
        
        def _worker():
            try:
                spec = planner.generate_book_plan(prompt, book_type="storybook", page_count=6)
                self.after(0, self._on_ai_plan_success, project, spec)
            except Exception as e:
                self.after(0, self._on_ai_plan_error, str(e))
                
        threading.Thread(target=_worker, daemon=True).start()

    def _on_ai_plan_success(self, project, spec: BookSpecification) -> None:
        self.ai_btn.configure(state="normal", text="Generate AI Plan")
        
        project.custom_settings["ai_plan"] = spec.model_dump()
        if spec.title:
            project.name = spec.title
            
        self.pages_data = []
        for p in spec.pages:
            p_dict = {
                "layout": p.layout_type,
                "text": p.text_content or ""
            }
            if p.image_prompt:
                p_dict["image_prompt"] = p.image_prompt
                # Create a pending reference
                ref = GeneratedImageReference(image_prompt=p.image_prompt)
                p_dict["image_reference"] = ref.model_dump()
                p_dict["image_path"] = ""
                
            self.pages_data.append(p_dict)
            
        self._refresh_sequence_ui()
        
        if spec.global_style_instructions:
            logger.info(f"AI Style suggestion: {spec.global_style_instructions}")
            
        messagebox.showinfo("AI Plan Generated", "Plan generated successfully! You can now generate images.")

    def _on_ai_plan_error(self, err_msg: str) -> None:
        self.ai_btn.configure(state="normal", text="Generate AI Plan")
        messagebox.showerror("AI Generation Failed", err_msg)

    def _determine_aspect_ratio(self, layout: str) -> str:
        if layout in ["image_top_text_bottom", "text_top_image_bottom", "split"]:
            return "landscape"
        elif layout in ["full_bleed_image", "image_only"]:
            return "portrait"
        return "square"

    def _on_generate_single_image(self, page_index: int, status_lbl: ctk.CTkLabel) -> None:
        try:
            ai_manager = Container().resolve(AIManager)
            asset_manager = Container().resolve(AssetManager)
            task_queue = Container().resolve(TaskQueue)
        except ValueError:
            messagebox.showerror("System Error", "Services not fully initialized.")
            return

        if not ai_manager.is_image_enabled:
            messagebox.showerror("AI Images Disabled", "Please configure an Image Provider in AI Settings.")
            return

        project = self.controller.engine.get_active_project()
        if not project:
            return

        page = self.pages_data[page_index]
        
        # Construct or restore Reference
        ref_dict = page.get("image_reference")
        if ref_dict:
            # Pydantic 2 parsing
            ref = GeneratedImageReference.model_validate(ref_dict)
        else:
            ref = GeneratedImageReference(image_prompt=page["image_prompt"])

        img_service = ImageGenerationService(ai_manager, asset_manager)
        aspect = self._determine_aspect_ratio(page.get("layout", "square"))
        
        status_lbl.configure(text="Status: generating", text_color=Colors.WARNING[0])
        
        task = GenerateImageTask(
            reference=ref,
            aspect_ratio=aspect,
            image_service=img_service,
            project_id=project.id
        )
        
        def _on_progress(evt):
            pass # We could update a progress bar here
            
        def _worker():
            try:
                updated_ref = task.execute(_on_progress, task_queue._get_token(task.id) if hasattr(task_queue, '_get_token') else None)
                self.after(0, self._on_image_generated, page_index, updated_ref)
            except Exception as e:
                self.after(0, self._on_image_failed, page_index, str(e), status_lbl)
                
        # In a real app we'd enqueue in TaskQueue. To easily bypass threading complexity in Tkinter we run locally in thread, 
        # or use TaskQueue if fully exposed. TaskQueue doesn't natively callback to UI easily without custom events.
        threading.Thread(target=_worker, daemon=True).start()

    def _on_image_generated(self, page_index: int, ref: GeneratedImageReference):
        page = self.pages_data[page_index]
        page["image_reference"] = ref.model_dump()
        page["image_path"] = ref.image_path
        self._refresh_sequence_ui()
        
    def _on_image_failed(self, page_index: int, error: str, status_lbl: ctk.CTkLabel):
        logger.error(f"Image generation failed for page {page_index}: {error}")
        status_lbl.configure(text="Status: failed", text_color=Colors.DANGER[0])
        messagebox.showerror("Generation Failed", error)

    def _on_batch_generate_images(self):
        missing_indices = []
        for i, page in enumerate(self.pages_data):
            if "image_prompt" in page:
                ref = page.get("image_reference", {})
                if ref.get("status") != "ready":
                    missing_indices.append(i)
                    
        if not missing_indices:
            messagebox.showinfo("Batch Complete", "All images are already generated.")
            return
            
        # Cost-safety confirmation
        est_cost = len(missing_indices) * 0.04
        msg = f"You are about to generate {len(missing_indices)} missing images.\n\nEstimated provider cost: ~${est_cost:.2f}\n\nDo you want to proceed?"
        if not messagebox.askyesno("Confirm Batch Generation", msg):
            return
            
        # Queue them up sequentially (for simplicity in demo)
        def _batch_worker():
            try:
                ai_manager = Container().resolve(AIManager)
                asset_manager = Container().resolve(AssetManager)
            except ValueError:
                return
                
            img_service = ImageGenerationService(ai_manager, asset_manager)
            project = self.controller.engine.get_active_project()
            
            for idx in missing_indices:
                page = self.pages_data[idx]
                ref_dict = page.get("image_reference")
                if ref_dict:
                    ref = GeneratedImageReference.model_validate(ref_dict)
                else:
                    ref = GeneratedImageReference(image_prompt=page["image_prompt"])
                    
                aspect = self._determine_aspect_ratio(page.get("layout", "square"))
                
                try:
                    updated_ref = img_service.generate_and_ingest(
                        reference=ref,
                        aspect_ratio=aspect,
                        project_id=project.id if project else None
                    )
                    self.after(0, self._on_image_generated, idx, updated_ref)
                except Exception as e:
                    self.after(0, lambda e=e, i=idx: messagebox.showerror("Batch Error", f"Failed on page {i}: {str(e)}"))
                    break # Stop batch on first error for safety
                    
        threading.Thread(target=_batch_worker, daemon=True).start()

    def _on_generate(self) -> None:
        project = self.controller.engine.get_active_project()
        if not project:
            messagebox.showwarning("No Project", "No active project found.")
            return

        try:
            font_size = float(self.size_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Size", "Please enter a valid numeric font size.")
            return

        global_settings = {
            "font_family": self.font_var.get(),
            "font_size": font_size
        }

        # Save to custom_settings
        project.custom_settings["storybook_data"] = {
            "global_settings": global_settings,
            "pages": self.pages_data
        }
        
        project.save_to_disk()

        # Execute Command
        cmd = GenerateStorybookPagesCommand(project)
        self.controller.engine.execute_command(cmd)


class StoryBookStudioView(BookBuilderView):
    """
    Subclass wrapper of BookBuilderView that acts as the entrypoint for KDP Wizard Story Book routing.
    Inherits all workspaces widgets (toolbar, canvas, thumbnails, assets) natively.
    """
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        logger.info("StoryBookStudioView: initialized wrapper workspace frame.")


# Self-register in StudioRegistry on import
StudioRegistry().register_studio(
    "Story Book",
    StudioMetadata(
        name="Story Book Studio",
        settings_panel_class=StoryBookSettingsPanel,
        template_generator_class=StorybookTemplateGenerator
    )
)
