import os
import random
from typing import Any, Dict, List, Optional
import customtkinter as ctk
from tkinter import messagebox

from book_builder.studio_registry import StudioRegistry, StudioMetadata
from book_builder.templates.activity import ActivityTemplateGenerator
from ui.views.book_builder import BookBuilderView, WorkspaceController
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts
from ui.theme.spacing import Spacing
from core.logger import get_logger

logger = get_logger(__name__)


class ActivitySettingsPanel(ctk.CTkFrame):
    """
    Settings panel containing configuration controls for generating low-content activity/puzzle books.
    Hosted inside the PropertiesPanel of BookBuilderView.
    """
    def __init__(self, master: Any, controller: WorkspaceController, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self._build_ui()
        self._load_saved_settings()

    def _load_saved_settings(self) -> None:
        project = self.controller.engine.get_active_project()
        if not project or "activity_settings" not in project.custom_settings:
            return
        settings = project.custom_settings["activity_settings"]
        if "activity_type" in settings:
            self.type_var.set(settings["activity_type"])
        if "difficulty" in settings:
            self.diff_var.set(settings["difficulty"])
        if "age_group" in settings:
            self.age_var.set(settings["age_group"])
        if "grid_rows" in settings:
            self.grid_sz_entry.delete(0, "end")
            self.grid_sz_entry.insert(0, str(settings["grid_rows"]))
        if "seed" in settings:
            self.seed_entry.delete(0, "end")
            self.seed_entry.insert(0, str(settings["seed"]))
        if "has_bleed" in settings:
            self.bleed_var.set(settings["has_bleed"])
        if "include_answer_key" in settings:
            self.key_var.set(settings["include_answer_key"])
        if "pack_answers" in settings:
            self.pack_answers_var.set(settings["pack_answers"])
        if "start_marker" in settings:
            self.start_marker_var.set(settings["start_marker"])
        if "finish_marker" in settings:
            self.finish_marker_var.set(settings["finish_marker"])
        if "font_family" in settings:
            self.font_var.set(settings["font_family"])
        if "page_count" in settings:
            self.page_count_entry.delete(0, "end")
            self.page_count_entry.insert(0, str(settings["page_count"]))

    def _build_ui(self) -> None:
        # Title
        ctk.CTkLabel(self, text="Activity Design System", font=Fonts.heading3()).pack(anchor="w", pady=(0, Spacing.S))
        
        # 1. Activity Type & Puzzle Settings
        self._add_group_header("1. Puzzle Configuration")
        puzzle_f = ctk.CTkFrame(self, fg_color="transparent")
        puzzle_f.pack(fill="x", pady=2)
        
        ctk.CTkLabel(puzzle_f, text="Activity / Puzzle Type:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.type_var = ctk.StringVar(value="Mazes")
        self.type_dropdown = ctk.CTkOptionMenu(
            puzzle_f, variable=self.type_var,
            values=[
                "Mazes", "Word Search", "Crossword", "Sudoku", "Dot-to-Dot",
                "Letter Tracing", "Number Tracing", "Alphabet Practice", "Number Practice",
                "Shape Tracing", "Matching Activities", "Spot the Difference",
                "Coloring + Activity Combo", "Cut and Paste", "Puzzle Pages", "Custom Activity Templates"
            ]
        )
        self.type_dropdown.pack(fill="x", pady=2)
        
        # Difficulty selection
        ctk.CTkLabel(puzzle_f, text="Difficulty Level:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.diff_var = ctk.StringVar(value="Medium")
        self.diff_dropdown = ctk.CTkOptionMenu(
            puzzle_f, variable=self.diff_var,
            values=["Easy", "Medium", "Hard"]
        )
        self.diff_dropdown.pack(fill="x", pady=2)
        
        # Age Group
        ctk.CTkLabel(puzzle_f, text="Target Age Group:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.age_var = ctk.StringVar(value="Kids (6-10)")
        self.age_dropdown = ctk.CTkOptionMenu(
            puzzle_f, variable=self.age_var,
            values=["Toddlers (2-5)", "Kids (6-10)", "Adults (16+)"]
        )
        self.age_dropdown.pack(fill="x", pady=2)
        
        # Grid sizes or custom counts
        grid_f = ctk.CTkFrame(puzzle_f, fg_color="transparent")
        grid_f.pack(fill="x", pady=4)
        
        ctk.CTkLabel(grid_f, text="Grid Size (NxN):", font=Fonts.body_bold()).pack(anchor="w", pady=(2, 0))
        self.grid_sz_entry = ctk.CTkEntry(grid_f, placeholder_text="e.g. 12 or 15")
        self.grid_sz_entry.insert(0, "12")
        self.grid_sz_entry.pack(fill="x", pady=2)
        
        # Seed & Randomization
        seed_f = ctk.CTkFrame(puzzle_f, fg_color="transparent")
        seed_f.pack(fill="x", pady=4)
        ctk.CTkLabel(seed_f, text="Random Seed:", font=Fonts.body_bold()).pack(anchor="w", pady=(2, 0))
        self.seed_entry = ctk.CTkEntry(seed_f, width=120)
        self.seed_entry.insert(0, "1000")
        self.seed_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        self.roll_btn = ctk.CTkButton(
            seed_f, text="Roll", width=50, fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1], command=self._on_roll_seed
        )
        self.roll_btn.pack(side="right")
        
        # Toggles
        self.bleed_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(puzzle_f, text="Has Bleed", variable=self.bleed_var, font=Fonts.body()).pack(anchor="w", pady=4)
        
        self.key_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(puzzle_f, text="Include Answer Key Pages", variable=self.key_var, font=Fonts.body()).pack(anchor="w", pady=4)
        
        self.pack_answers_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(puzzle_f, text="Pack Answers (2x2 Grid)", variable=self.pack_answers_var, font=Fonts.body()).pack(anchor="w", pady=4)
        
        # Start/Finish markers
        ctk.CTkLabel(puzzle_f, text="Start Marker Type:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.start_marker_var = ctk.StringVar(value="text")
        self.start_marker_dropdown = ctk.CTkOptionMenu(
            puzzle_f, variable=self.start_marker_var,
            values=["text", "flag", "arrow", "star", "circle"]
        )
        self.start_marker_dropdown.pack(fill="x", pady=2)
        
        ctk.CTkLabel(puzzle_f, text="Finish Marker Type:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.finish_marker_var = ctk.StringVar(value="text")
        self.finish_marker_dropdown = ctk.CTkOptionMenu(
            puzzle_f, variable=self.finish_marker_var,
            values=["text", "flag", "arrow", "star", "circle"]
        )
        self.finish_marker_dropdown.pack(fill="x", pady=2)
        
        # 2. General Book Settings
        self._add_group_header("2. Layout & Styles")
        layout_f = ctk.CTkFrame(self, fg_color="transparent")
        layout_f.pack(fill="x", pady=2)
        
        ctk.CTkLabel(layout_f, text="Header/Instruction Font:", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.font_var = ctk.StringVar(value="Helvetica")
        self.font_dropdown = ctk.CTkOptionMenu(
            layout_f, variable=self.font_var,
            values=["Helvetica", "Times-Roman", "Courier", "Bookman", "Garamond"]
        )
        self.font_dropdown.pack(fill="x", pady=2)
        
        ctk.CTkLabel(layout_f, text="Total Page Count (puzzles):", font=Fonts.body_bold()).pack(anchor="w", pady=(4, 0))
        self.page_count_entry = ctk.CTkEntry(layout_f)
        self.page_count_entry.insert(0, "20")
        self.page_count_entry.pack(fill="x", pady=2)
        
        # 3. Actions & Operations
        self._add_group_header("3. Design Actions")
        actions_f = ctk.CTkFrame(self, fg_color="transparent")
        actions_f.pack(fill="x", pady=2)
        
        self.regen_page_btn = ctk.CTkButton(
            actions_f, text="Regenerate Active Page", fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1], command=self._on_regenerate_active_page
        )
        self.regen_page_btn.pack(fill="x", pady=2)
        
        self.shuffle_page_btn = ctk.CTkButton(
            actions_f, text="Shuffle Active Page", fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1], command=self._on_shuffle_active_page
        )
        self.shuffle_page_btn.pack(fill="x", pady=2)
        
        self.dup_page_btn = ctk.CTkButton(
            actions_f, text="Duplicate Selected Page", fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1], command=self._on_duplicate_active_page
        )
        self.dup_page_btn.pack(fill="x", pady=2)
        
        self.del_page_btn = ctk.CTkButton(
            actions_f, text="Delete Selected Page", fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1], command=self._on_delete_active_page
        )
        self.del_page_btn.pack(fill="x", pady=2)
        
        # Big Apply/Generate Buttons
        self.apply_single_btn = ctk.CTkButton(
            self, text="Generate Puzzle Pages", fg_color=Colors.PRIMARY[0], command=self._on_generate_single_type
        )
        self.apply_single_btn.pack(fill="x", pady=(Spacing.L, 2))
        
        self.apply_batch_btn = ctk.CTkButton(
            self, text="Batch Generate Mixed Puzzles", fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1], command=self._on_generate_batch_mixed
        )
        self.apply_batch_btn.pack(fill="x", pady=2)

    def _add_group_header(self, text: str) -> None:
        header = ctk.CTkLabel(self, text=text, font=Fonts.body_bold(), text_color=Colors.PRIMARY[0])
        header.pack(anchor="w", pady=(Spacing.M, 2))
        sep = ctk.CTkFrame(self, height=2, fg_color=("gray85", "gray25"))
        sep.pack(fill="x", pady=(0, Spacing.S))

    def _on_roll_seed(self) -> None:
        self.seed_entry.delete(0, "end")
        self.seed_entry.insert(0, str(random.randint(1000, 9999)))

    def _get_active_settings(self) -> Dict[str, Any]:
        try:
            sz = int(self.grid_sz_entry.get().strip())
        except ValueError:
            sz = 12
            
        try:
            seed_val = int(self.seed_entry.get().strip())
        except ValueError:
            seed_val = 1000
            
        try:
            pc = int(self.page_count_entry.get().strip())
        except ValueError:
            pc = 20

        # Default Matching Pairs
        matching_pairs = [
            ("Apple", "Fruit"), ("Carrot", "Vegetable"), ("Dog", "Animal"),
            ("Eagle", "Bird"), ("Salmon", "Fish"), ("Rose", "Flower")
        ]
        # Default Crossword Clues
        crossword_clues = [
            ("MAZE", "A puzzle of pathways"),
            ("GRID", "Sudoku is played on it"),
            ("WORD", "A unit of language"),
            ("PLAY", "To engage in activity for enjoyment"),
            ("EASY", "Not difficult")
        ]
        # Default WordSearch words
        words_list = ["PYTHON", "COFFEE", "GRID", "MAZE", "PUZZLE", "SUDOKU", "TRACING"]
        
        return {
            "difficulty": self.diff_var.get(),
            "age_group": self.age_var.get(),
            "grid_rows": sz,
            "grid_cols": sz,
            "seed": seed_val,
            "font_family": self.font_var.get(),
            "include_answer_key": self.key_var.get(),
            "pack_answers": self.pack_answers_var.get(),
            "start_marker": self.start_marker_var.get(),
            "finish_marker": self.finish_marker_var.get(),
            "matching_pairs": matching_pairs,
            "crossword_clues": crossword_clues,
            "words_list": words_list,
            "trace_character": "A",
            "trace_shape": "star",
            "dot_shape": "star",
            "theme_color": "#000000",
            "line_color": "#A0A0A0",
            "text_color": "#000000",
            "show_page_number": True,
            "mirror_margins": True,
            "gutter_pt": 9.0,
            "activity_type": self.type_var.get(),
            "page_count": pc,
            "has_bleed": self.bleed_var.get()
        }

    def _on_regenerate_active_page(self) -> None:
        project = self.controller.engine.get_active_project()
        if not project: return
        active_idx = self.controller.engine.state_manager.project_state.active_page_index if self.controller.engine.state_manager.project_state else 0
        settings = self._get_active_settings()
        self.controller.regenerate_puzzle(active_idx, settings)
        messagebox.showinfo("Regenerated", f"Regenerated layout for page {active_idx + 1}")

    def _on_shuffle_active_page(self) -> None:
        project = self.controller.engine.get_active_project()
        if not project: return
        active_idx = self.controller.engine.state_manager.project_state.active_page_index if self.controller.engine.state_manager.project_state else 0
        settings = self._get_active_settings()
        self.controller.shuffle_puzzle(active_idx, settings)
        messagebox.showinfo("Shuffled", f"Shuffled elements on page {active_idx + 1}")

    def _on_duplicate_active_page(self) -> None:
        project = self.controller.engine.get_active_project()
        if not project: return
        active_idx = self.controller.engine.state_manager.project_state.active_page_index if self.controller.engine.state_manager.project_state else 0
        self.controller.duplicate_activity_page(active_idx)
        messagebox.showinfo("Duplicated", f"Duplicated page {active_idx + 1}")

    def _on_delete_active_page(self) -> None:
        project = self.controller.engine.get_active_project()
        if not project or len(project.pages) <= 1: return
        active_idx = self.controller.engine.state_manager.project_state.active_page_index if self.controller.engine.state_manager.project_state else 0
        
        confirm = messagebox.askyesno("Delete Page", f"Delete page {active_idx + 1}?")
        if confirm:
            self.controller.delete_activity_page(active_idx)
            messagebox.showinfo("Success", f"Deleted page {active_idx + 1}")

    def _on_generate_single_type(self) -> None:
        try:
            page_count = int(self.page_count_entry.get().strip())
            if page_count <= 0: raise ValueError("Page count must be positive.")
            
            settings = self._get_active_settings()
            act_type = self.type_var.get()
            
            confirm = messagebox.askyesno(
                "Generate Puzzles",
                f"Overwrite all page structures and generate {page_count} puzzle pages of type '{act_type}'?"
            )
            if not confirm: return
            
            project = self.controller.engine.get_active_project()
            if project:
                project.custom_settings["activity_settings"] = settings
                
            self.controller.generate_activity(
                page_count=page_count,
                trim_width_in=8.5,
                trim_height_in=11.0,
                margin_top_in=0.5,
                margin_bottom_in=0.5,
                margin_inside_in=0.5,
                margin_outside_in=0.5,
                has_bleed=self.bleed_var.get(),
                activity_type=act_type,
                settings=settings
            )
            self.controller.select_page(0)
            messagebox.showinfo("Success", f"Activity book puzzle pages generated: {page_count} pages.")
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Error: {e}")

    def _on_generate_batch_mixed(self) -> None:
        try:
            page_count = int(self.page_count_entry.get().strip())
            if page_count <= 0: raise ValueError("Page count must be positive.")
            
            settings = self._get_active_settings()
            
            confirm = messagebox.askyesno(
                "Batch Generate Mixed",
                f"Overwrite all page structures and batch generate {page_count} mixed puzzle pages?"
            )
            if not confirm: return
            
            project = self.controller.engine.get_active_project()
            if project:
                project.custom_settings["activity_settings"] = settings
                
            # Mix list
            activity_types = ["Mazes", "Sudoku", "Word Search", "Crossword", "Dot-to-Dot", "Matching Activities"]
            
            self.controller.batch_generate_activities(
                page_count=page_count,
                trim_width_in=8.5,
                trim_height_in=11.0,
                margin_top_in=0.5,
                margin_bottom_in=0.5,
                margin_inside_in=0.5,
                margin_outside_in=0.5,
                has_bleed=self.bleed_var.get(),
                activity_types=activity_types,
                settings=settings
            )
            self.controller.select_page(0)
            messagebox.showinfo("Success", f"Batch generated {page_count} mixed activity pages.")
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Error: {e}")


class ActivityBookStudioView(BookBuilderView):
    """
    Subclass wrapper of BookBuilderView acting as the Activity Book Studio workspace.
    """
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        logger.info("ActivityBookStudioView: workspace initialized.")


# Register Activity Studio plugin in Registry
StudioRegistry().register_studio(
    "Activity Book",
    StudioMetadata(
        name="Activity Book Studio",
        settings_panel_class=ActivitySettingsPanel,
        template_generator_class=ActivityTemplateGenerator
    )
)
