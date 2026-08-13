"""
KDP Coloring Book Generator - Main Application
A professional Windows desktop application for generating KDP coloring books.
Built with Python and CustomTkinter. Works completely offline.
"""

import sys
import os
import json
from pathlib import Path

import customtkinter as ctk

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.dashboard import DashboardFrame
from ui.project_manager import ProjectManagerFrame
from ui.settings import SettingsFrame
from ui.generator import GeneratorFrame
from ui.cover_generator import CoverGeneratorFrame
from ui.epub_generator import EpubGeneratorFrame


class App(ctk.CTk):
    """Main application window with sidebar navigation."""

    APP_NAME = "KDP Coloring Book Generator"
    APP_VERSION = "1.0.0"
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 750
    SIDEBAR_WIDTH = 220

    def __init__(self):
        super().__init__()

        # Paths
        self.base_dir = Path(__file__).resolve().parent.parent
        self.data_dir = self.base_dir / "data"
        self.assets_dir = self.base_dir / "assets"
        self.data_dir.mkdir(exist_ok=True)

        # Load settings and projects
        self.settings = self._load_settings()
        self.projects = self._load_projects()

        # Apply settings
        ctk.set_appearance_mode(self.settings.get("appearance_mode", "Dark"))
        ctk.set_default_color_theme("blue")

        # Window configuration
        self.title(self.APP_NAME)
        self.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.minsize(900, 600)

        # Center window on screen
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - self.WINDOW_WIDTH) // 2
        y = (screen_h - self.WINDOW_HEIGHT) // 2
        self.geometry(f"+{x}+{y}")

        # Configure grid layout
        self.grid_columnconfigure(0, weight=0)  # Sidebar
        self.grid_columnconfigure(1, weight=1)  # Main content
        self.grid_rowconfigure(0, weight=1)

        # Build UI
        self._create_sidebar()
        self._create_main_content()

        # Show dashboard by default
        self._show_frame("dashboard")

    # ─── Sidebar ────────────────────────────────────────────────────────────────

    def _create_sidebar(self):
        """Create the navigation sidebar."""
        self.sidebar = ctk.CTkFrame(
            self,
            width=self.SIDEBAR_WIDTH,
            corner_radius=0,
            fg_color=("gray92", "gray14"),
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(10, weight=1)  # Spacer row

        # App logo / title
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="📖  KDP Generator",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("gray10", "gray90"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(28, 8), sticky="w")

        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            self.sidebar,
            text="Coloring Book Studio",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
        )
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 24), sticky="w")

        # Separator
        self.sep1 = ctk.CTkFrame(self.sidebar, height=1, fg_color=("gray80", "gray25"))
        self.sep1.grid(row=2, column=0, padx=16, pady=(0, 16), sticky="ew")

        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "🏠  Dashboard", 3),
            ("generator", "📖  Generator", 4),
            ("cover", "🎨  Cover Generator", 5),
            ("epub", "📚  EPUB Generator", 6),
            ("projects", "📁  Projects", 7),
            ("settings", "⚙️  Settings", 8),
        ]

        for key, label, row in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                font=ctk.CTkFont(size=14),
                height=42,
                anchor="w",
                corner_radius=8,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray82", "gray25"),
                command=lambda k=key: self._show_frame(k),
            )
            btn.grid(row=row, column=0, padx=12, pady=3, sticky="ew")
            self.nav_buttons[key] = btn

        # Bottom section - version info
        self.version_label = ctk.CTkLabel(
            self.sidebar,
            text=f"v{self.APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray50"),
        )
        self.version_label.grid(row=11, column=0, padx=20, pady=(8, 12), sticky="sw")

        # Appearance mode toggle at bottom
        self.appearance_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Light", "Dark", "System"],
            command=self._change_appearance,
            width=140,
            height=30,
            font=ctk.CTkFont(size=12),
        )
        self.appearance_menu.set(self.settings.get("appearance_mode", "Dark"))
        self.appearance_menu.grid(row=12, column=0, padx=20, pady=(4, 20), sticky="sw")

    # ─── Main Content ───────────────────────────────────────────────────────────

    def _create_main_content(self):
        """Create the main content area with all frames."""
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # Create all page frames
        self.frames = {}
        self.frames["dashboard"] = DashboardFrame(self.main_container, self)
        self.frames["generator"] = GeneratorFrame(self.main_container, self)
        self.frames["cover"] = CoverGeneratorFrame(self.main_container, self)
        self.frames["epub"] = EpubGeneratorFrame(self.main_container, self)
        self.frames["projects"] = ProjectManagerFrame(self.main_container, self)
        self.frames["settings"] = SettingsFrame(self.main_container, self)

        # Place all frames in the same grid cell
        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

    def _show_frame(self, name: str):
        """Show the specified frame and highlight its nav button."""
        # Update nav button styles
        for key, btn in self.nav_buttons.items():
            if key == name:
                btn.configure(
                    fg_color=("gray75", "gray28"),
                    text_color=("gray10", "white"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("gray10", "gray90"),
                )

        # Raise the selected frame
        frame = self.frames[name]
        frame.tkraise()

        # Refresh frame data if it has a refresh method
        if hasattr(frame, "refresh"):
            frame.refresh()

    # ─── Appearance ─────────────────────────────────────────────────────────────

    def _change_appearance(self, mode: str):
        """Change the application appearance mode."""
        ctk.set_appearance_mode(mode)
        self.settings["appearance_mode"] = mode
        self._save_settings()

    # ─── Data Persistence ───────────────────────────────────────────────────────

    def _load_settings(self) -> dict:
        """Load application settings from JSON file."""
        settings_file = self.data_dir / "settings.json"
        default_settings = {
            "appearance_mode": "Dark",
            "ui_scaling": "100%",
            "default_export_path": str(Path.home() / "Documents" / "KDP_Exports"),
            "author_name": "",
            "default_page_size": "8.5 x 11 inches",
            "default_bleed": "0.125 inches",
        }
        if settings_file.exists():
            try:
                with open(settings_file, "r") as f:
                    loaded = json.load(f)
                    default_settings.update(loaded)
            except (json.JSONDecodeError, IOError):
                pass
        return default_settings

    def _save_settings(self):
        """Save application settings to JSON file."""
        settings_file = self.data_dir / "settings.json"
        try:
            with open(settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except IOError as e:
            print(f"Error saving settings: {e}")

    def _load_projects(self) -> list:
        """Load projects list from JSON file."""
        projects_file = self.data_dir / "projects.json"
        if projects_file.exists():
            try:
                with open(projects_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return []

    def _save_projects(self):
        """Save projects list to JSON file."""
        projects_file = self.data_dir / "projects.json"
        try:
            with open(projects_file, "w") as f:
                json.dump(self.projects, f, indent=2)
        except IOError as e:
            print(f"Error saving projects: {e}")

    # ─── Public API for child frames ───────────────────────────────────────────

    def get_projects(self) -> list:
        """Return the list of projects."""
        return self.projects

    def add_project(self, project: dict):
        """Add a new project and save."""
        self.projects.append(project)
        self._save_projects()

    def delete_project(self, project_id: str):
        """Delete a project by ID and save."""
        self.projects = [p for p in self.projects if p.get("id") != project_id]
        self._save_projects()

    def update_project(self, project_id: str, updates: dict):
        """Update a project's data and save."""
        for p in self.projects:
            if p.get("id") == project_id:
                p.update(updates)
                break
        self._save_projects()

    def get_settings(self) -> dict:
        """Return current settings."""
        return self.settings

    def update_settings(self, new_settings: dict):
        """Update settings and save."""
        self.settings.update(new_settings)
        self._save_settings()

    def navigate_to(self, frame_name: str):
        """Navigate to a specific frame (used by child frames)."""
        self._show_frame(frame_name)

    def open_project_in_generator(self, project: dict):
        """Open a project in the generator frame for editing."""
        generator_frame = self.frames.get("generator")
        if generator_frame and hasattr(generator_frame, "load_project"):
            generator_frame.load_project(project)
            self._show_frame("generator")

    def open_project_in_cover_generator(self, project: dict):
        """Open a project's cover_data in the Cover Generator frame for editing."""
        cover_frame = self.frames.get("cover")
        if cover_frame and hasattr(cover_frame, "load_project"):
            cover_frame.load_project(project)
            self._show_frame("cover")

    def open_project_in_epub_generator(self, project: dict):
        """Open a project's epub_data in the EPUB Generator frame for editing."""
        epub_frame = self.frames.get("epub")
        if epub_frame and hasattr(epub_frame, "load_project"):
            epub_frame.load_project(project)
            self._show_frame("epub")


def main():
    """Application entry point."""
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
