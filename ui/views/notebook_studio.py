import os
from typing import Any, Dict, Optional
import customtkinter as ctk
from tkinter import messagebox

from book_builder.studio_registry import StudioRegistry, StudioMetadata
from book_builder.templates.notebook import NotebookTemplateGenerator
from ui.views.book_builder import BookBuilderView, WorkspaceController
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts
from ui.theme.spacing import Spacing
from core.logger import get_logger

logger = get_logger(__name__)


class NotebookSettingsPanel(ctk.CTkFrame):
    """
    Settings panel containing configuration controls for generating notebook pages.
    Hosted inside the PropertiesPanel of BookBuilderView.
    """
    def __init__(self, master: Any, controller: WorkspaceController, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self._build_ui()
        self._load_saved_settings()

    def _load_saved_settings(self) -> None:
        project = self.controller.engine.get_active_project()
        if not project or "notebook_settings" not in project.custom_settings:
            return
        settings = project.custom_settings["notebook_settings"]
        
        if "preset" in settings:
            self.preset_var.set(settings["preset"])
        if "trim" in settings:
            self.trim_var.set(settings["trim"])
        if "custom_w" in settings:
            self.custom_w.delete(0, "end")
            self.custom_w.insert(0, settings["custom_w"])
        if "custom_h" in settings:
            self.custom_h.delete(0, "end")
            self.custom_h.insert(0, settings["custom_h"])
        if "page_count" in settings:
            self.page_count_entry.delete(0, "end")
            self.page_count_entry.insert(0, settings["page_count"])
        if "has_bleed" in settings:
            self.bleed_var.set(settings["has_bleed"])
        if "mirror_margins" in settings:
            self.mirror_var.set(settings["mirror_margins"])
        if "first_page_different" in settings:
            self.first_different_var.set(settings["first_page_different"])
        if "margin_top" in settings:
            self.margin_top.delete(0, "end")
            self.margin_top.insert(0, settings["margin_top"])
        if "margin_bottom" in settings:
            self.margin_bottom.delete(0, "end")
            self.margin_bottom.insert(0, settings["margin_bottom"])
        if "margin_inside" in settings:
            self.margin_inside.delete(0, "end")
            self.margin_inside.insert(0, settings["margin_inside"])
        if "margin_outside" in settings:
            self.margin_outside.delete(0, "end")
            self.margin_outside.insert(0, settings["margin_outside"])
        if "header_text" in settings:
            self.header_entry.delete(0, "end")
            self.header_entry.insert(0, settings["header_text"])
        if "show_header_line" in settings:
            self.header_line_var.set(settings["show_header_line"])
        if "footer_text" in settings:
            self.footer_entry.delete(0, "end")
            self.footer_entry.insert(0, settings["footer_text"])
        if "show_footer_line" in settings:
            self.footer_line_var.set(settings["show_footer_line"])
        if "show_page_numbers" in settings:
            self.num_var.set(settings["show_page_numbers"])
        if "page_number_alignment" in settings:
            self.num_align_var.set(settings["page_number_alignment"])
        if "show_date_field" in settings:
            self.date_var.set(settings["show_date_field"])
        if "show_title_field" in settings:
            self.title_prompt_var.set(settings["show_title_field"])
        if "spacing_val" in settings:
            self.spacing_entry.delete(0, "end")
            self.spacing_entry.insert(0, settings["spacing_val"])
        if "line_thickness_val" in settings:
            self.thick_var.set(settings["line_thickness_val"])
        if "line_color_val" in settings:
            self.color_var.set(settings["line_color_val"])
            self._on_color_selected(settings["line_color_val"])
        if "custom_color_hex" in settings and self.custom_color_entry.winfo_exists():
            self.custom_color_entry.delete(0, "end")
            self.custom_color_entry.insert(0, settings["custom_color_hex"])

    def _build_ui(self) -> None:
        # Title
        ctk.CTkLabel(self, text="Notebook Layout Engine", font=Fonts.heading3()).pack(anchor="w", pady=(0, Spacing.S))
        
        # 1. Document Structure Group
        self._add_group_header("1. Document Structure")
        struct_frame = ctk.CTkFrame(self, fg_color="transparent")
        struct_frame.pack(fill="x", pady=2)
        
        # Preset selection
        ctk.CTkLabel(struct_frame, text="Layout Preset:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.preset_var = ctk.StringVar(value="College Ruled")
        self.preset_dropdown = ctk.CTkOptionMenu(
            struct_frame, variable=self.preset_var,
            values=["Blank", "Ruled", "College Ruled", "Wide Ruled", "Narrow Ruled", "Graph", "Dot Grid", "Cornell Notes", "Music Sheet", "Handwriting Practice"],
            command=self._on_preset_selected
        )
        self.preset_dropdown.pack(fill="x", pady=2)
        
        # Trim size
        ctk.CTkLabel(struct_frame, text="Trim Size Preset:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.trim_var = ctk.StringVar(value="6 x 9 in")
        self.trim_dropdown = ctk.CTkOptionMenu(
            struct_frame, variable=self.trim_var,
            values=["6 x 9 in", "8.5 x 11 in", "5.5 x 8.5 in", "5 x 8 in", "Custom..."],
            command=self._on_trim_selected
        )
        self.trim_dropdown.pack(fill="x", pady=2)
        
        # Custom trim size entries
        self.custom_trim_frame = ctk.CTkFrame(struct_frame, fg_color="transparent")
        ctk.CTkLabel(self.custom_trim_frame, text="Custom W (in):", font=Fonts.small()).grid(row=0, column=0, padx=2)
        self.custom_w = ctk.CTkEntry(self.custom_trim_frame, width=50, font=Fonts.small())
        self.custom_w.insert(0, "6.0")
        self.custom_w.grid(row=0, column=1, padx=2)
        
        ctk.CTkLabel(self.custom_trim_frame, text="H (in):", font=Fonts.small()).grid(row=0, column=2, padx=2)
        self.custom_h = ctk.CTkEntry(self.custom_trim_frame, width=50, font=Fonts.small())
        self.custom_h.insert(0, "9.0")
        self.custom_h.grid(row=0, column=3, padx=2)
        
        # Page count
        ctk.CTkLabel(struct_frame, text="Total Page Count:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.page_count_entry = ctk.CTkEntry(struct_frame)
        self.page_count_entry.insert(0, "100")
        self.page_count_entry.pack(fill="x", pady=2)
        
        # Bleed Toggle
        self.bleed_var = ctk.BooleanVar(value=False)
        self.bleed_switch = ctk.CTkSwitch(
            struct_frame, text="Has Bleed", variable=self.bleed_var, font=Fonts.body()
        )
        self.bleed_switch.pack(anchor="w", pady=4)

        # 2. Margins & Gutter Group
        self._add_group_header("2. Margins & Gutter")
        margin_frame = ctk.CTkFrame(self, fg_color="transparent")
        margin_frame.pack(fill="x", pady=2)
        
        # Mirror margins & First page different
        self.mirror_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(margin_frame, text="Mirror Margins", variable=self.mirror_var, font=Fonts.body()).pack(anchor="w", pady=2)
        
        self.first_different_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(margin_frame, text="First Page Different", variable=self.first_different_var, font=Fonts.body()).pack(anchor="w", pady=2)
        
        # Gutter entry
        gutter_f = ctk.CTkFrame(margin_frame, fg_color="transparent")
        gutter_f.pack(fill="x", pady=2)
        ctk.CTkLabel(gutter_f, text="Gutter (in):", font=Fonts.body_bold()).pack(side="left", padx=(0, 10))
        self.gutter_entry = ctk.CTkEntry(gutter_f, width=60)
        self.gutter_entry.insert(0, "0.125")
        self.gutter_entry.pack(side="left")
        
        # Margins inputs
        ctk.CTkLabel(margin_frame, text="Margins (inches):", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 2))
        inputs_f = ctk.CTkFrame(margin_frame, fg_color="transparent")
        inputs_f.pack(fill="x", pady=2)
        inputs_f.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        ctk.CTkLabel(inputs_f, text="Top", font=Fonts.small()).grid(row=0, column=0, padx=2)
        self.margin_top = ctk.CTkEntry(inputs_f, width=45, font=Fonts.small())
        self.margin_top.insert(0, "0.5")
        self.margin_top.grid(row=1, column=0, padx=2)
        
        ctk.CTkLabel(inputs_f, text="Bottom", font=Fonts.small()).grid(row=0, column=1, padx=2)
        self.margin_bottom = ctk.CTkEntry(inputs_f, width=45, font=Fonts.small())
        self.margin_bottom.insert(0, "0.5")
        self.margin_bottom.grid(row=1, column=1, padx=2)
        
        ctk.CTkLabel(inputs_f, text="Inside", font=Fonts.small()).grid(row=0, column=2, padx=2)
        self.margin_inside = ctk.CTkEntry(inputs_f, width=45, font=Fonts.small())
        self.margin_inside.insert(0, "0.5")
        self.margin_inside.grid(row=1, column=2, padx=2)
        
        ctk.CTkLabel(inputs_f, text="Outside", font=Fonts.small()).grid(row=0, column=3, padx=2)
        self.margin_outside = ctk.CTkEntry(inputs_f, width=45, font=Fonts.small())
        self.margin_outside.insert(0, "0.5")
        self.margin_outside.grid(row=1, column=3, padx=2)

        # 3. Decorations (Headers, Footers, Page Numbering) Group
        self._add_group_header("3. Headers & Footers")
        decor_frame = ctk.CTkFrame(self, fg_color="transparent")
        decor_frame.pack(fill="x", pady=2)
        
        # Header text
        ctk.CTkLabel(decor_frame, text="Header Text:", font=Fonts.body_bold()).pack(anchor="w", pady=(2, 0))
        self.header_entry = ctk.CTkEntry(decor_frame)
        self.header_entry.pack(fill="x", pady=2)
        
        # Header line & Footer line
        self.header_line_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(decor_frame, text="Header Divider Line", variable=self.header_line_var, font=Fonts.body()).pack(anchor="w", pady=2)
        
        # Footer text
        ctk.CTkLabel(decor_frame, text="Footer Text:", font=Fonts.body_bold()).pack(anchor="w", pady=(2, 0))
        self.footer_entry = ctk.CTkEntry(decor_frame)
        self.footer_entry.pack(fill="x", pady=2)
        
        self.footer_line_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(decor_frame, text="Footer Divider Line", variable=self.footer_line_var, font=Fonts.body()).pack(anchor="w", pady=2)
        
        # Page numbering
        self.num_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(decor_frame, text="Show Page Numbers", variable=self.num_var, font=Fonts.body()).pack(anchor="w", pady=2)
        
        ctk.CTkLabel(decor_frame, text="Numbering Position:", font=Fonts.body_bold()).pack(anchor="w", pady=(2, 0))
        self.num_align_var = ctk.StringVar(value="Center")
        self.num_align_dropdown = ctk.CTkOptionMenu(
            decor_frame, variable=self.num_align_var,
            values=["Center", "Outside", "Inside"]
        )
        self.num_align_dropdown.pack(fill="x", pady=2)
        
        # Prompts (Date / Title fields)
        self.date_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(decor_frame, text="Show Date Prompt", variable=self.date_var, font=Fonts.body()).pack(anchor="w", pady=2)
        
        self.title_prompt_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(decor_frame, text="Show Title Prompt", variable=self.title_prompt_var, font=Fonts.body()).pack(anchor="w", pady=2)

        # 4. Styling (Color, Spacing, Thickness) Group
        self._add_group_header("4. Spacing & Styling")
        style_frame = ctk.CTkFrame(self, fg_color="transparent")
        style_frame.pack(fill="x", pady=2)
        
        # Spacing input (label changes dynamically)
        self.spacing_label = ctk.CTkLabel(style_frame, text="Spacing (points):", font=Fonts.body_bold())
        self.spacing_label.pack(anchor="w", pady=(2, 0))
        self.spacing_entry = ctk.CTkEntry(style_frame)
        self.spacing_entry.insert(0, "20.25")
        self.spacing_entry.pack(fill="x", pady=2)
        
        # Grid thickness
        ctk.CTkLabel(style_frame, text="Line / Dot Weight:", font=Fonts.body_bold()).pack(anchor="w", pady=(2, 0))
        self.thick_var = ctk.StringVar(value="0.75 pt")
        self.thick_dropdown = ctk.CTkOptionMenu(
            style_frame, variable=self.thick_var,
            values=["0.5 pt", "0.75 pt", "1.0 pt", "1.5 pt"]
        )
        self.thick_dropdown.pack(fill="x", pady=2)
        
        # Line color selection
        ctk.CTkLabel(style_frame, text="Line Color:", font=Fonts.body_bold()).pack(anchor="w", pady=(2, 0))
        self.color_var = ctk.StringVar(value="Soft Gray")
        self.color_dropdown = ctk.CTkOptionMenu(
            style_frame, variable=self.color_var,
            values=["Soft Gray", "Charcoal", "Light Blue", "Custom Hex..."],
            command=self._on_color_selected
        )
        self.color_dropdown.pack(fill="x", pady=2)
        
        self.custom_color_entry = ctk.CTkEntry(style_frame, placeholder_text="#HEXCOLOR")
        
        # 5. Apply changes button
        self.apply_btn = ctk.CTkButton(
            self, text="Regenerate Notebook", fg_color=Colors.PRIMARY[0], command=self._on_apply_template
        )
        self.apply_btn.pack(fill="x", pady=(Spacing.L, Spacing.M))

    def _add_group_header(self, text: str) -> None:
        header = ctk.CTkLabel(self, text=text, font=Fonts.body_bold(), text_color=Colors.PRIMARY[0])
        header.pack(anchor="w", pady=(Spacing.M, 2))
        sep = ctk.CTkFrame(self, height=2, fg_color=("gray85", "gray25"))
        sep.pack(fill="x", pady=(0, Spacing.S))

    def _on_preset_selected(self, choice: str) -> None:
        """Autofills settings based on preset selection choice."""
        # Set spacing & label based on layout type
        p = choice.lower().replace(" ", "_")
        
        if "ruled" in p:
            self.spacing_label.configure(text="Line Spacing (pt):")
            self.spacing_entry.delete(0, "end")
            if p == "college_ruled":
                self.spacing_entry.insert(0, "20.25")
            elif p == "wide_ruled":
                self.spacing_entry.insert(0, "24.75")
            elif p == "narrow_ruled":
                self.spacing_entry.insert(0, "18.0")
            else:
                self.spacing_entry.insert(0, "24.0")
        elif p == "graph":
            self.spacing_label.configure(text="Grid Square Spacing (pt):")
            self.spacing_entry.delete(0, "end")
            self.spacing_entry.insert(0, "18.0")
        elif p == "dot_grid":
            self.spacing_label.configure(text="Dot Grid Spacing (pt):")
            self.spacing_entry.delete(0, "end")
            self.spacing_entry.insert(0, "18.0")
        elif p == "cornell_notes":
            self.spacing_label.configure(text="Line Spacing (pt):")
            self.spacing_entry.delete(0, "end")
            self.spacing_entry.insert(0, "20.25")
        elif p == "music_sheet":
            self.spacing_label.configure(text="Staff Line Spacing (pt):")
            self.spacing_entry.delete(0, "end")
            self.spacing_entry.insert(0, "6.0")
        elif p == "handwriting_practice":
            self.spacing_label.configure(text="Practice Line Spacing (pt):")
            self.spacing_entry.delete(0, "end")
            self.spacing_entry.insert(0, "9.0")
        else:
            # Blank
            self.spacing_entry.delete(0, "end")
            self.spacing_entry.insert(0, "0.0")

    def _on_trim_selected(self, choice: str) -> None:
        if choice == "Custom...":
            self.custom_trim_frame.pack(fill="x", pady=2)
        else:
            self.custom_trim_frame.pack_forget()

    def _on_color_selected(self, choice: str) -> None:
        if choice == "Custom Hex...":
            self.custom_color_entry.pack(fill="x", pady=2)
        else:
            self.custom_color_entry.pack_forget()

    def _on_apply_template(self) -> None:
        try:
            # Page count
            page_count = int(self.page_count_entry.get().strip())
            if page_count <= 0:
                raise ValueError("Page count must be positive.")
                
            # Trim dimensions
            trim_preset = self.trim_var.get()
            if trim_preset == "Custom...":
                w_in = float(self.custom_w.get().strip())
                h_in = float(self.custom_h.get().strip())
            else:
                parts = trim_preset.replace(" in", "").split("x")
                w_in = float(parts[0].strip())
                h_in = float(parts[1].strip())
                
            # Margins & Gutter
            m_top = float(self.margin_top.get().strip())
            m_bottom = float(self.margin_bottom.get().strip())
            m_inside = float(self.margin_inside.get().strip())
            m_outside = float(self.margin_outside.get().strip())
            gutter_val = float(self.gutter_entry.get().strip())
            
            bleed = self.bleed_var.get()
            preset_name = self.preset_var.get()
            
            # Line Thickness
            thick = float(self.thick_var.get().replace(" pt", "").strip())
            
            # Line Color mapping
            color_choice = self.color_var.get()
            if color_choice == "Soft Gray":
                color_hex = "#D0D4DC"
            elif color_choice == "Charcoal":
                color_hex = "#404040"
            elif color_choice == "Light Blue":
                color_hex = "#ADD8E6"
            else:
                color_hex = self.custom_color_entry.get().strip()
                if not color_hex.startswith("#"):
                    color_hex = f"#{color_hex}"
                if len(color_hex) != 7:
                    raise ValueError("Custom line color must be a valid 6-character hex string (e.g. #FF0000)")
                    
            spacing_val = float(self.spacing_entry.get().strip()) if self.spacing_entry.get().strip() else 0.0
            
            # Build detailed settings dictionary
            settings = {
                "gutter_pt": gutter_val * 72.0,
                "mirror_margins": self.mirror_var.get(),
                "first_page_different": self.first_different_var.get(),
                "header_text": self.header_entry.get(),
                "show_header_line": self.header_line_var.get(),
                "footer_text": self.footer_entry.get(),
                "show_footer_line": self.footer_line_var.get(),
                "show_page_numbers": self.num_var.get(),
                "page_number_alignment": self.num_align_var.get(),
                "show_date_field": self.date_var.get(),
                "show_title_field": self.title_prompt_var.get(),
                "line_thickness": thick,
                "line_color": color_hex,
                "graph_spacing": spacing_val,
                "dot_spacing": spacing_val,
                "dot_size": 1.5,
                "line_spacing_pt": spacing_val,
                "staff_gap_pt": 28.0,
                "practice_gap_pt": 24.0
            }
            
            # Execute template generation
            project = self.controller.engine.get_active_project()
            if project:
                ui_settings = {
                    "preset": self.preset_var.get(),
                    "trim": self.trim_var.get(),
                    "custom_w": self.custom_w.get(),
                    "custom_h": self.custom_h.get(),
                    "page_count": self.page_count_entry.get(),
                    "has_bleed": self.bleed_var.get(),
                    "margin_top": self.margin_top.get(),
                    "margin_bottom": self.margin_bottom.get(),
                    "margin_inside": self.margin_inside.get(),
                    "margin_outside": self.margin_outside.get(),
                    "line_thickness_val": self.thick_var.get(),
                    "line_color_val": self.color_var.get(),
                    "custom_color_hex": self.custom_color_entry.get() if self.custom_color_entry.winfo_exists() else "",
                    "spacing_val": self.spacing_entry.get(),
                    **settings
                }
                project.custom_settings["notebook_settings"] = ui_settings

            self.controller.generate_notebook(
                page_count=page_count,
                trim_width_in=w_in,
                trim_height_in=h_in,
                margin_top_in=m_top,
                margin_bottom_in=m_bottom,
                margin_inside_in=m_inside,
                margin_outside_in=m_outside,
                has_bleed=bleed,
                template_type=preset_name,
                settings=settings
            )
            
            # Select first page to render
            self.controller.select_page(0)
            messagebox.showinfo("Notebook Template", f"Successfully generated {page_count} layout pages.")
            
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Error in layouts input fields: {e}")
        except Exception as e:
            logger.error(f"Failed to generate notebook template pages: {e}")
            messagebox.showerror("Error", f"Failed to generate pages: {e}")


class NotebookStudioView(BookBuilderView):
    """
    Subclass wrapper of BookBuilderView that acts as the entrypoint for KDP Wizard Notebook routing.
    Inherits all workspaces widgets (toolbar, canvas, thumbnails, assets) natively.
    """
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        logger.info("NotebookStudioView: initialized wrapper workspace frame.")




# Self-register in StudioRegistry on import
StudioRegistry().register_studio(
    "notebook",
    StudioMetadata(
        name="Notebook Studio",
        settings_panel_class=NotebookSettingsPanel,
        template_generator_class=NotebookTemplateGenerator
    )
)
