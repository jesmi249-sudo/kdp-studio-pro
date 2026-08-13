import os
from typing import Any, Dict, List
import customtkinter as ctk
from tkinter import messagebox, filedialog

from book_builder.studio_registry import StudioRegistry, StudioMetadata
from book_builder.templates.coloring import ColoringTemplateGenerator
from ui.views.book_builder import BookBuilderView, WorkspaceController
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts
from ui.theme.spacing import Spacing
from core.logger import get_logger

logger = get_logger(__name__)


class ColoringSettingsPanel(ctk.CTkFrame):
    """
    Settings panel containing configuration controls for importing and placing coloring artwork.
    Hosted inside the PropertiesPanel of BookBuilderView.
    """
    def __init__(self, master: Any, controller: WorkspaceController, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self._build_ui()

    def _build_ui(self) -> None:
        # Title
        ctk.CTkLabel(self, text="Coloring Layout Settings", font=Fonts.heading3()).pack(anchor="w", pady=(0, Spacing.S))
        
        # 1. Project structure controls
        self._add_group_header("1. Book Layout")
        layout_f = ctk.CTkFrame(self, fg_color="transparent")
        layout_f.pack(fill="x", pady=2)
        
        ctk.CTkLabel(layout_f, text="Trim Size Preset:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.trim_var = ctk.StringVar(value="8.5 x 11 in")
        self.trim_dropdown = ctk.CTkOptionMenu(
            layout_f, variable=self.trim_var,
            values=["8.5 x 11 in", "6 x 9 in", "8 x 10 in", "5 x 8 in"]
        )
        self.trim_dropdown.pack(fill="x", pady=2)
        
        # Page count
        ctk.CTkLabel(layout_f, text="Total Page Count:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.page_count_entry = ctk.CTkEntry(layout_f)
        self.page_count_entry.insert(0, "40")
        self.page_count_entry.pack(fill="x", pady=2)
        
        # Toggles
        self.bleed_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(layout_f, text="Has Bleed", variable=self.bleed_var, font=Fonts.body()).pack(anchor="w", pady=4)
        
        self.single_sided_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(layout_f, text="Single-Sided Print (Blank Backs)", variable=self.single_sided_var, font=Fonts.body()).pack(anchor="w", pady=4)
        
        # 2. Border & Scaling Style
        self._add_group_header("2. Artwork Options")
        art_f = ctk.CTkFrame(self, fg_color="transparent")
        art_f.pack(fill="x", pady=2)
        
        ctk.CTkLabel(art_f, text="Artwork Fit Style:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.scale_var = ctk.StringVar(value="Fit")
        self.scale_dropdown = ctk.CTkOptionMenu(
            art_f, variable=self.scale_var,
            values=["Fit", "Fill", "Stretch"]
        )
        self.scale_dropdown.pack(fill="x", pady=2)
        
        ctk.CTkLabel(art_f, text="Border Frame:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.border_var = ctk.StringVar(value="Bold")
        self.border_dropdown = ctk.CTkOptionMenu(
            art_f, variable=self.border_var,
            values=["None", "Thin", "Bold"]
        )
        self.border_dropdown.pack(fill="x", pady=2)
        
        ctk.CTkLabel(art_f, text="Footer Caption:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.caption_entry = ctk.CTkEntry(art_f, placeholder_text="e.g. Color me! (Optional)")
        self.caption_entry.pack(fill="x", pady=2)
        
        # 3. Actions Group
        self._add_group_header("3. Imports & Actions")
        actions_f = ctk.CTkFrame(self, fg_color="transparent")
        actions_f.pack(fill="x", pady=2)
        
        # Button: Replace artwork on selected page
        self.replace_btn = ctk.CTkButton(
            actions_f, text="Replace Page Artwork...", fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1], command=self._on_replace_artwork
        )
        self.replace_btn.pack(fill="x", pady=2)
        
        # Button: Batch Import folder
        self.batch_btn = ctk.CTkButton(
            actions_f, text="Batch Import Folder...", fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1], command=self._on_batch_import
        )
        self.batch_btn.pack(fill="x", pady=2)
        
        # Button: Shuffle
        self.shuffle_btn = ctk.CTkButton(
            actions_f, text="Shuffle Order", fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1], command=self._on_shuffle_artwork
        )
        self.shuffle_btn.pack(fill="x", pady=2)
        
        # Button: Duplicate page
        self.dup_btn = ctk.CTkButton(
            actions_f, text="Duplicate Selected Page", fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1], command=self.controller.duplicate_page
        )
        self.dup_btn.pack(fill="x", pady=2)
        
        # 4. Generate Book Button
        self.apply_btn = ctk.CTkButton(
            self, text="Regenerate Coloring Book", fg_color=Colors.PRIMARY[0], command=self._on_apply_settings
        )
        self.apply_btn.pack(fill="x", pady=(Spacing.L, Spacing.M))

    def _add_group_header(self, text: str) -> None:
        header = ctk.CTkLabel(self, text=text, font=Fonts.body_bold(), text_color=Colors.PRIMARY[0])
        header.pack(anchor="w", pady=(Spacing.M, 2))
        sep = ctk.CTkFrame(self, height=2, fg_color=("gray85", "gray25"))
        sep.pack(fill="x", pady=(0, Spacing.S))

    def _get_active_settings(self) -> Dict[str, Any]:
        return {
            "scale_mode": self.scale_var.get(),
            "border_style": self.border_var.get(),
            "caption_text": self.caption_entry.get(),
            "single_sided": self.single_sided_var.get(),
            "gutter_pt": 9.0, # default binding gutter
            "mirror_margins": True
        }

    def _on_replace_artwork(self) -> None:
        project = self.controller.engine.get_active_project()
        if not project:
            return
            
        active_idx = self.controller.engine.state_manager.project_state.active_page_index if self.controller.engine.state_manager.project_state else 0
        if active_idx < 0 or active_idx >= len(project.pages):
            return
            
        file_path = filedialog.askopenfilename(
            title="Select Coloring Artwork",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.svg"), ("All Files", "*.*")]
        )
        if not file_path:
            return
            
        settings = self._get_active_settings()
        self.controller.replace_artwork(active_idx, file_path, settings)
        messagebox.showinfo("Artwork Replaced", f"Successfully updated artwork on Page {active_idx + 1}")

    def _on_batch_import(self) -> None:
        dir_path = filedialog.askdirectory(title="Select Folder containing Coloring Illustrations")
        if not dir_path:
            return
            
        valid_extensions = {".png", ".jpg", ".jpeg", ".svg"}
        artwork_paths = []
        for file in os.listdir(dir_path):
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_extensions:
                artwork_paths.append(os.path.join(dir_path, file))
                
        if not artwork_paths:
            messagebox.showwarning("No Images Found", f"No valid PNG/JPG/SVG images found inside folder: {dir_path}")
            return
            
        # Confirm import
        confirm = messagebox.askyesno(
            "Batch Import", 
            f"Found {len(artwork_paths)} illustrations to import.\n\nDo you want to import them into the project?"
        )
        if not confirm:
            return
            
        settings = self._get_active_settings()
        self.controller.batch_import_artwork(artwork_paths, settings)
        messagebox.showinfo("Import Complete", f"Successfully imported {len(artwork_paths)} pages.")

    def _on_shuffle_artwork(self) -> None:
        confirm = messagebox.askyesno(
            "Shuffle Illustrations",
            "This will shuffle the order of all illustration pages in the book.\n\nDo you wish to proceed?"
        )
        if not confirm:
            return
            
        settings = self._get_active_settings()
        self.controller.shuffle_artwork(settings)
        messagebox.showinfo("Shuffled", "Artwork order shuffled successfully.")

    def _on_apply_settings(self) -> None:
        try:
            page_count = int(self.page_count_entry.get().strip())
            if page_count <= 0:
                raise ValueError("Page count must be positive.")
                
            # Trim preset parsing
            trim = self.trim_var.get().replace(" in", "").strip()
            parts = trim.split("x")
            w_in = float(parts[0].strip())
            h_in = float(parts[1].strip())
            
            bleed = self.bleed_var.get()
            settings = self._get_active_settings()
            
            confirm = messagebox.askyesno(
                "Regenerate Project", 
                "Applying global changes will replace current layout bounds and structures.\n\nDo you wish to continue?"
            )
            if not confirm:
                return
                
            # Default safe coloring book margins: Top/Bottom=0.5", Inside/Outside=0.5"
            self.controller.generate_coloring(
                page_count=page_count,
                trim_width_in=w_in,
                trim_height_in=h_in,
                margin_top_in=0.5,
                margin_bottom_in=0.5,
                margin_inside_in=0.5,
                margin_outside_in=0.5,
                has_bleed=bleed,
                settings=settings
            )
            
            self.controller.select_page(0)
            messagebox.showinfo("Coloring Book Template", f"Successfully generated {page_count} layout pages.")
            
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Error in layouts input fields: {e}")
        except Exception as e:
            logger.error(f"Failed to generate coloring template: {e}")
            messagebox.showerror("Error", f"Failed to generate layout pages: {e}")


class ColoringStudioView(BookBuilderView):
    """
    Subclass wrapper of BookBuilderView acting as the Coloring Book Studio workspace.
    """
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        logger.info("ColoringStudioView: workspace initialized.")




# Self-register in StudioRegistry on import
StudioRegistry().register_studio(
    "Coloring Book",
    StudioMetadata(
        name="Coloring Book Studio",
        settings_panel_class=ColoringSettingsPanel,
        template_generator_class=ColoringTemplateGenerator
    )
)
