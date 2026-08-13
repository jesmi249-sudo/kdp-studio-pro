import os
from typing import Any, Dict, List, Optional
import customtkinter as ctk
from tkinter import messagebox, filedialog

from book_builder.studio_registry import StudioRegistry, StudioMetadata
from book_builder.templates.planner import PlannerTemplateGenerator
from ui.views.book_builder import BookBuilderView, WorkspaceController
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts
from ui.theme.spacing import Spacing
from core.logger import get_logger

logger = get_logger(__name__)


class PlannerSettingsPanel(ctk.CTkFrame):
    """
    Settings panel containing configuration controls for generating low-content planner layouts.
    Hosted inside the PropertiesPanel of BookBuilderView.
    """
    def __init__(self, master: Any, controller: WorkspaceController, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self._build_ui()
        self._load_saved_settings()

    def _load_saved_settings(self) -> None:
        project = self.controller.engine.get_active_project()
        if not project or "planner_settings" not in project.custom_settings:
            return
        settings = project.custom_settings["planner_settings"]
        if "start_date" in settings:
            self.start_date_entry.delete(0, "end")
            self.start_date_entry.insert(0, settings["start_date"])
        if "start_weekday" in settings:
            self.weekday_var.set("Monday" if settings["start_weekday"] == 0 else "Sunday")
        if "show_holidays" in settings:
            self.holidays_var.set(settings["show_holidays"])
        if "header_text" in settings:
            self.header_text_entry.delete(0, "end")
            self.header_text_entry.insert(0, settings["header_text"])
        if "show_page_number" in settings:
            self.show_page_num_var.set(settings["show_page_number"])
        if "theme_name" in settings:
            self.theme_var.set(settings["theme_name"])
        if "planner_type" in settings:
            self.type_var.set(settings["planner_type"])
        if "page_count" in settings:
            self.page_count_entry.delete(0, "end")
            self.page_count_entry.insert(0, str(settings["page_count"]))
        if "has_bleed" in settings:
            self.bleed_var.set(settings["has_bleed"])

    def _build_ui(self) -> None:
        # Title
        ctk.CTkLabel(self, text="Planner Design System", font=Fonts.heading3()).pack(anchor="w", pady=(0, Spacing.S))
        
        # 1. Structure
        self._add_group_header("1. Document Structure")
        struct_f = ctk.CTkFrame(self, fg_color="transparent")
        struct_f.pack(fill="x", pady=2)
        
        ctk.CTkLabel(struct_f, text="Planner Type:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.type_var = ctk.StringVar(value="Daily Planner")
        self.type_dropdown = ctk.CTkOptionMenu(
            struct_f, variable=self.type_var,
            values=[
                "Daily Planner", "Weekly Planner", "Monthly Planner", "Yearly Planner",
                "Habit Tracker", "Goal Tracker", "Budget Planner", "Meal Planner",
                "Fitness Planner", "Reading Log", "Project Planner", "Appointment Planner",
                "Custom Planner"
            ]
        )
        self.type_dropdown.pack(fill="x", pady=2)
        
        # Date range
        ctk.CTkLabel(struct_f, text="Start Date (YYYY-MM-DD):", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.start_date_entry = ctk.CTkEntry(struct_f)
        self.start_date_entry.insert(0, "2026-01-01")
        self.start_date_entry.pack(fill="x", pady=2)
        
        # Start weekday
        ctk.CTkLabel(struct_f, text="Start Weekday:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.weekday_var = ctk.StringVar(value="Monday")
        self.weekday_dropdown = ctk.CTkOptionMenu(
            struct_f, variable=self.weekday_var,
            values=["Monday", "Sunday"]
        )
        self.weekday_dropdown.pack(fill="x", pady=2)
        
        # Total pages count
        ctk.CTkLabel(struct_f, text="Page Count:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.page_count_entry = ctk.CTkEntry(struct_f)
        self.page_count_entry.insert(0, "50")
        self.page_count_entry.pack(fill="x", pady=2)
        
        # Toggles
        self.bleed_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(struct_f, text="Has Bleed", variable=self.bleed_var, font=Fonts.body()).pack(anchor="w", pady=4)
        
        self.holidays_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(struct_f, text="Show US Holidays", variable=self.holidays_var, font=Fonts.body()).pack(anchor="w", pady=4)
        
        # 2. Theme & Customization
        self._add_group_header("2. Custom Layout Styling")
        style_f = ctk.CTkFrame(self, fg_color="transparent")
        style_f.pack(fill="x", pady=2)
        
        ctk.CTkLabel(style_f, text="Theme Palette:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.theme_var = ctk.StringVar(value="Charcoal Black")
        self.theme_dropdown = ctk.CTkOptionMenu(
            style_f, variable=self.theme_var,
            values=["Charcoal Black", "Slate Gray", "Ocean Blue", "Forest Green", "Rose Pink"]
        )
        self.theme_dropdown.pack(fill="x", pady=2)
        
        ctk.CTkLabel(style_f, text="Custom Header Text:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.header_text_entry = ctk.CTkEntry(style_f, placeholder_text="e.g. My Personal Journal")
        self.header_text_entry.pack(fill="x", pady=2)
        
        self.show_page_num_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(style_f, text="Show Page Numbers", variable=self.show_page_num_var, font=Fonts.body()).pack(anchor="w", pady=4)
        
        # 3. Sections & Actions
        self._add_group_header("3. Section Actions")
        actions_f = ctk.CTkFrame(self, fg_color="transparent")
        actions_f.pack(fill="x", pady=2)
        
        # Add section button
        self.insert_btn = ctk.CTkButton(
            actions_f, text="Insert Planner Section...", fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1], command=self._on_insert_section
        )
        self.insert_btn.pack(fill="x", pady=2)
        
        # Delete section button
        self.delete_btn = ctk.CTkButton(
            actions_f, text="Delete Pages Range...", fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1], command=self._on_delete_section
        )
        self.delete_btn.pack(fill="x", pady=2)
        
        # Duplicate page button
        self.dup_btn = ctk.CTkButton(
            actions_f, text="Duplicate Selected Page", fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1], command=self._on_duplicate_page
        )
        self.dup_btn.pack(fill="x", pady=2)
        
        # Apply button
        self.apply_btn = ctk.CTkButton(
            self, text="Regenerate Planner Book", fg_color=Colors.PRIMARY[0], command=self._on_apply_settings
        )
        self.apply_btn.pack(fill="x", pady=(Spacing.L, Spacing.M))

    def _add_group_header(self, text: str) -> None:
        header = ctk.CTkLabel(self, text=text, font=Fonts.body_bold(), text_color=Colors.PRIMARY[0])
        header.pack(anchor="w", pady=(Spacing.M, 2))
        sep = ctk.CTkFrame(self, height=2, fg_color=("gray85", "gray25"))
        sep.pack(fill="x", pady=(0, Spacing.S))

    def _resolve_colors(self) -> Dict[str, str]:
        theme = self.theme_var.get()
        if theme == "Slate Gray":
            return {"theme_color": "#4A4A4A", "line_color": "#D3D3D3", "text_color": "#333333"}
        elif theme == "Ocean Blue":
            return {"theme_color": "#1A365D", "line_color": "#BEE3F8", "text_color": "#2C5282"}
        elif theme == "Forest Green":
            return {"theme_color": "#1C3D24", "line_color": "#C6F6D5", "text_color": "#276749"}
        elif theme == "Rose Pink":
            return {"theme_color": "#702459", "line_color": "#FED7E2", "text_color": "#97266D"}
        else: # Charcoal Black
            return {"theme_color": "#000000", "line_color": "#D3D3D3", "text_color": "#333333"}

    def _get_active_settings(self) -> Dict[str, Any]:
        colors = self._resolve_colors()
        start_w = 0 if self.weekday_var.get() == "Monday" else 6
        try:
            pc = int(self.page_count_entry.get().strip())
        except ValueError:
            pc = 50
        return {
            "start_date": self.start_date_entry.get().strip(),
            "start_weekday": start_w,
            "show_holidays": self.holidays_var.get(),
            "header_text": self.header_text_entry.get().strip(),
            "show_page_number": self.show_page_num_var.get(),
            "mirror_margins": True,
            "gutter_pt": 9.0, # default 0.125" binding gutter
            "theme_name": self.theme_var.get(),
            "planner_type": self.type_var.get(),
            "page_count": pc,
            "has_bleed": self.bleed_var.get(),
            **colors
        }

    def _on_duplicate_page(self) -> None:
        project = self.controller.engine.get_active_project()
        if not project:
            return
        active_idx = self.controller.engine.state_manager.project_state.active_page_index if self.controller.engine.state_manager.project_state else 0
        self.controller.duplicate_planner_page(active_idx)
        messagebox.showinfo("Duplicated", f"Duplicated page {active_idx + 1}")

    def _on_insert_section(self) -> None:
        # Prompt user dialog inside custom inputs or simple prompt
        # We can implement a clean insert section input
        try:
            start_num = int(self.controller.engine.state_manager.project_state.active_page_index + 1)
        except Exception:
            start_num = 1
            
        settings = self._get_active_settings()
        planner_type = self.type_var.get()
        
        # Simple confirmation dialog
        confirm = messagebox.askyesno(
            "Insert Planner Section",
            f"Insert 5 pages of '{planner_type}' starting at page number {start_num}?"
        )
        if confirm:
            self.controller.insert_planner_section(
                start_page_number=start_num,
                page_count=5,
                planner_type=planner_type,
                settings=settings
            )
            messagebox.showinfo("Success", f"Inserted 5 planner pages at Page {start_num}")

    def _on_delete_section(self) -> None:
        try:
            total_pages = len(self.controller.engine.get_active_project().pages)
        except Exception:
            return
            
        confirm = messagebox.askyesno(
            "Delete Pages",
            f"Remove the last 5 pages of the project? (Total pages remaining: {total_pages - 5})"
        )
        if confirm and total_pages > 5:
            self.controller.delete_planner_section(total_pages - 4, total_pages)
            messagebox.showinfo("Success", "Deleted page range successfully.")

    def _on_apply_settings(self) -> None:
        try:
            page_count = int(self.page_count_entry.get().strip())
            if page_count <= 0:
                raise ValueError("Page count must be positive.")
                
            settings = self._get_active_settings()
            planner_type = self.type_var.get()
            
            confirm = messagebox.askyesno(
                "Apply Planner Book",
                f"This will overwrite all existing page structures and generate {page_count} pages of '{planner_type}'.\n\nContinue?"
            )
            if not confirm:
                return
                
            project = self.controller.engine.get_active_project()
            if project:
                project.custom_settings["planner_settings"] = settings
                
            self.controller.generate_planner(
                page_count=page_count,
                trim_width_in=8.5,
                trim_height_in=11.0,
                margin_top_in=0.5,
                margin_bottom_in=0.5,
                margin_inside_in=0.5,
                margin_outside_in=0.5,
                has_bleed=self.bleed_var.get(),
                planner_type=planner_type,
                settings=settings
            )
            self.controller.select_page(0)
            messagebox.showinfo("Success", f"Planner book generated: {page_count} pages.")
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Error: {e}")
        except Exception as e:
            logger.error(f"Failed to apply planner: {e}")
            messagebox.showerror("Error", f"Failed to generate layout pages: {e}")


class PlannerStudioView(BookBuilderView):
    """
    Subclass wrapper of BookBuilderView acting as the Planner Studio workspace.
    """
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        logger.info("PlannerStudioView: workspace initialized.")


# Register in Registry
StudioRegistry().register_studio(
    "Planner",
    StudioMetadata(
        name="Planner Studio",
        settings_panel_class=PlannerSettingsPanel,
        template_generator_class=PlannerTemplateGenerator
    )
)
