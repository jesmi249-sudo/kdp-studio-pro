import os
from typing import Any, Dict, Optional
import customtkinter as ctk
from tkinter import messagebox
import json

from book_builder.studio_registry import StudioRegistry, StudioMetadata
from book_builder.templates.storybook import StorybookTemplateGenerator
from book_builder.commands.storybook_commands import GenerateStorybookPagesCommand
from ui.views.book_builder import BookBuilderView, WorkspaceController
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts
from ui.theme.spacing import Spacing
from core.logger import get_logger

logger = get_logger(__name__)


class StoryBookSettingsPanel(ctk.CTkFrame):
    """
    Settings panel containing configuration controls for generating Storybook pages.
    Hosted inside the PropertiesPanel of BookBuilderView.
    """
    def __init__(self, master: Any, controller: WorkspaceController, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
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
            
        pages_data = settings.get("pages", [])
        self.pages_data_textbox.delete("0.0", "end")
        self.pages_data_textbox.insert("0.0", json.dumps(pages_data, indent=2))

    def _build_ui(self) -> None:
        # Title
        ctk.CTkLabel(self, text="Storybook Layout Engine", font=Fonts.heading3()).pack(anchor="w", pady=(0, Spacing.S))
        
        # 1. Global Settings Group
        self._add_group_header("1. Typography")
        
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
        
        # 2. Pages JSON Editor Group (Simulating AI data)
        self._add_group_header("2. Story Sequence (JSON)")
        
        self.pages_data_textbox = ctk.CTkTextbox(self, height=250, font=("Consolas", 11))
        self.pages_data_textbox.pack(fill="x", pady=(0, Spacing.S))
        
        default_data = [
            {
                "layout": "title_page",
                "title": "My Great Story",
                "author": "Antigravity AI"
            },
            {
                "layout": "image_top_text_bottom",
                "text": "Once upon a time in a digital world...",
                "image_path": ""
            },
            {
                "layout": "text_overlay",
                "text": "There lived an AI building a book.",
                "image_path": ""
            },
            {
                "layout": "ending_page"
            }
        ]
        self.pages_data_textbox.insert("0.0", json.dumps(default_data, indent=2))

        # 3. Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(Spacing.M, 0))
        
        ctk.CTkButton(btn_frame, text="Generate Storybook", fg_color=Colors.PRIMARY[0], hover_color=Colors.PRIMARY[1], command=self._on_generate).pack(fill="x")

    def _add_group_header(self, text: str) -> None:
        ctk.CTkLabel(self, text=text, font=Fonts.ui_bold(), text_color=Colors.TEXT_MAIN[1]).pack(anchor="w", pady=(Spacing.M, Spacing.XS))
        ctk.CTkFrame(self, height=1, fg_color=Colors.BORDER).pack(fill="x", pady=(0, Spacing.S))

    def _on_generate(self) -> None:
        project = self.controller.engine.get_active_project()
        if not project:
            messagebox.showwarning("No Project", "No active project found.")
            return

        # Parse JSON
        try:
            pages_data = json.loads(self.pages_data_textbox.get("0.0", "end").strip())
            if not isinstance(pages_data, list):
                raise ValueError("Story sequence must be a JSON array.")
        except json.JSONDecodeError as e:
            messagebox.showerror("Invalid JSON", f"Could not parse story sequence:\n\n{e}")
            return
        except ValueError as e:
            messagebox.showerror("Invalid Data", str(e))
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
            "pages": pages_data
        }

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
