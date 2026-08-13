"""
Settings Frame - Application configuration page.
Handles appearance, UI scaling, export paths, author info, and page defaults.
All settings are persisted locally in JSON format.
"""

import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog


class SettingsFrame(ctk.CTkFrame):
    """Settings view for configuring application preferences."""

    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.app = app

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_header()
        self._create_settings_content()

    def _create_header(self):
        """Create the settings page header."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=32, pady=(28, 16), sticky="ew")

        title = ctk.CTkLabel(
            header_frame,
            text="Settings",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="Configure application preferences and defaults",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray60"),
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _create_settings_content(self):
        """Create the scrollable settings content area."""
        scroll_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        scroll_frame.grid(row=1, column=0, padx=24, pady=(0, 28), sticky="nsew")
        scroll_frame.grid_columnconfigure(0, weight=1)

        settings = self.app.get_settings()

        # ── Appearance Section ──────────────────────────────────────────────────
        self._create_section_header(scroll_frame, "Appearance", 0)

        appearance_card = ctk.CTkFrame(scroll_frame, corner_radius=12)
        appearance_card.grid(row=1, column=0, padx=8, pady=(0, 20), sticky="ew")
        appearance_card.grid_columnconfigure(1, weight=1)

        # Appearance mode
        ctk.CTkLabel(
            appearance_card,
            text="Theme Mode",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(20, 4), sticky="w")

        ctk.CTkLabel(
            appearance_card,
            text="Choose between light, dark, or system theme",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray55"),
        ).grid(row=1, column=0, padx=20, pady=(0, 8), sticky="w")

        self.appearance_var = ctk.StringVar(value=settings.get("appearance_mode", "Dark"))
        appearance_menu = ctk.CTkOptionMenu(
            appearance_card,
            values=["Light", "Dark", "System"],
            variable=self.appearance_var,
            command=self._on_appearance_change,
            width=160,
            height=32,
        )
        appearance_menu.grid(row=0, column=1, rowspan=2, padx=20, pady=(20, 8), sticky="e")

        # UI Scaling
        ctk.CTkLabel(
            appearance_card,
            text="UI Scaling",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=2, column=0, padx=20, pady=(16, 4), sticky="w")

        ctk.CTkLabel(
            appearance_card,
            text="Adjust the size of UI elements",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray55"),
        ).grid(row=3, column=0, padx=20, pady=(0, 8), sticky="w")

        self.scaling_var = ctk.StringVar(value=settings.get("ui_scaling", "100%"))
        scaling_menu = ctk.CTkOptionMenu(
            appearance_card,
            values=["80%", "90%", "100%", "110%", "120%", "130%"],
            variable=self.scaling_var,
            command=self._on_scaling_change,
            width=160,
            height=32,
        )
        scaling_menu.grid(row=2, column=1, rowspan=2, padx=20, pady=(16, 8), sticky="e")

        # Padding at bottom of card
        ctk.CTkLabel(appearance_card, text="").grid(row=4, column=0, pady=(0, 12))

        # ── Author Section ──────────────────────────────────────────────────────
        self._create_section_header(scroll_frame, "Author Information", 2)

        author_card = ctk.CTkFrame(scroll_frame, corner_radius=12)
        author_card.grid(row=3, column=0, padx=8, pady=(0, 20), sticky="ew")
        author_card.grid_columnconfigure(1, weight=1)

        # Author name
        ctk.CTkLabel(
            author_card,
            text="Author Name",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(20, 4), sticky="w")

        ctk.CTkLabel(
            author_card,
            text="Default author name for new projects",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray55"),
        ).grid(row=1, column=0, padx=20, pady=(0, 8), sticky="w")

        self.author_entry = ctk.CTkEntry(
            author_card,
            placeholder_text="Enter your name",
            width=220,
            height=34,
        )
        self.author_entry.grid(row=0, column=1, rowspan=2, padx=20, pady=(20, 8), sticky="e")
        author_name = settings.get("author_name", "")
        if author_name:
            self.author_entry.insert(0, author_name)

        # Padding
        ctk.CTkLabel(author_card, text="").grid(row=2, column=0, pady=(0, 12))

        # ── Export Section ──────────────────────────────────────────────────────
        self._create_section_header(scroll_frame, "Export Settings", 4)

        export_card = ctk.CTkFrame(scroll_frame, corner_radius=12)
        export_card.grid(row=5, column=0, padx=8, pady=(0, 20), sticky="ew")
        export_card.grid_columnconfigure(1, weight=1)

        # Default export path
        ctk.CTkLabel(
            export_card,
            text="Default Export Path",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(20, 4), sticky="w")

        ctk.CTkLabel(
            export_card,
            text="Where exported PDFs will be saved by default",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray55"),
        ).grid(row=1, column=0, padx=20, pady=(0, 8), sticky="w")

        path_frame = ctk.CTkFrame(export_card, fg_color="transparent")
        path_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(4, 20), sticky="ew")
        path_frame.grid_columnconfigure(0, weight=1)

        self.export_path_entry = ctk.CTkEntry(
            path_frame,
            placeholder_text="Select export directory...",
            height=34,
        )
        self.export_path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        export_path = settings.get("default_export_path", "")
        if export_path:
            self.export_path_entry.insert(0, export_path)

        browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse",
            width=80,
            height=34,
            corner_radius=8,
            command=self._browse_export_path,
        )
        browse_btn.grid(row=0, column=1, sticky="e")

        # ── Page Defaults Section ───────────────────────────────────────────────
        self._create_section_header(scroll_frame, "Page Defaults", 6)

        page_card = ctk.CTkFrame(scroll_frame, corner_radius=12)
        page_card.grid(row=7, column=0, padx=8, pady=(0, 20), sticky="ew")
        page_card.grid_columnconfigure(1, weight=1)

        # Default page size
        ctk.CTkLabel(
            page_card,
            text="Default Page Size",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(20, 4), sticky="w")

        ctk.CTkLabel(
            page_card,
            text="Default page dimensions for new projects",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray55"),
        ).grid(row=1, column=0, padx=20, pady=(0, 8), sticky="w")

        self.page_size_var = ctk.StringVar(
            value=settings.get("default_page_size", "8.5 x 11 inches")
        )
        page_size_menu = ctk.CTkOptionMenu(
            page_card,
            values=[
                "8.5 x 11 inches",
                "8.5 x 8.5 inches",
                "6 x 9 inches",
                "8 x 10 inches",
            ],
            variable=self.page_size_var,
            width=180,
            height=32,
        )
        page_size_menu.grid(row=0, column=1, rowspan=2, padx=20, pady=(20, 8), sticky="e")

        # Default bleed
        ctk.CTkLabel(
            page_card,
            text="Default Bleed",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=2, column=0, padx=20, pady=(16, 4), sticky="w")

        ctk.CTkLabel(
            page_card,
            text="Bleed area for print-ready PDFs",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray55"),
        ).grid(row=3, column=0, padx=20, pady=(0, 8), sticky="w")

        self.bleed_var = ctk.StringVar(
            value=settings.get("default_bleed", "0.125 inches")
        )
        bleed_menu = ctk.CTkOptionMenu(
            page_card,
            values=["None", "0.0625 inches", "0.125 inches", "0.25 inches"],
            variable=self.bleed_var,
            width=180,
            height=32,
        )
        bleed_menu.grid(row=2, column=1, rowspan=2, padx=20, pady=(16, 8), sticky="e")

        # Padding
        ctk.CTkLabel(page_card, text="").grid(row=4, column=0, pady=(0, 12))

        # ── Save Button ─────────────────────────────────────────────────────────
        save_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        save_frame.grid(row=8, column=0, padx=8, pady=(8, 20), sticky="ew")
        save_frame.grid_columnconfigure(0, weight=1)

        self.save_btn = ctk.CTkButton(
            save_frame,
            text="💾  Save Settings",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            width=180,
            corner_radius=8,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._save_settings,
        )
        self.save_btn.grid(row=0, column=0, sticky="e")

        self.save_status = ctk.CTkLabel(
            save_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#10b981",
        )
        self.save_status.grid(row=0, column=0, sticky="w")

    def _create_section_header(self, parent, text: str, row: int):
        """Create a section header label."""
        header = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header.grid(row=row, column=0, padx=12, pady=(16, 8), sticky="w")

    def _on_appearance_change(self, mode: str):
        """Handle appearance mode change."""
        ctk.set_appearance_mode(mode)

    def _on_scaling_change(self, scaling: str):
        """Handle UI scaling change."""
        scale_value = int(scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(scale_value)

    def _browse_export_path(self):
        """Open file dialog to select export directory."""
        directory = filedialog.askdirectory(
            title="Select Default Export Directory",
            initialdir=self.export_path_entry.get() or str(Path.home()),
        )
        if directory:
            self.export_path_entry.delete(0, "end")
            self.export_path_entry.insert(0, directory)

    def _save_settings(self):
        """Save all settings."""
        new_settings = {
            "appearance_mode": self.appearance_var.get(),
            "ui_scaling": self.scaling_var.get(),
            "author_name": self.author_entry.get().strip(),
            "default_export_path": self.export_path_entry.get().strip(),
            "default_page_size": self.page_size_var.get(),
            "default_bleed": self.bleed_var.get(),
        }
        self.app.update_settings(new_settings)

        # Show success feedback
        self.save_status.configure(text="✓ Settings saved successfully!")
        self.after(3000, lambda: self.save_status.configure(text=""))

    def refresh(self):
        """Refresh settings from app state (called when navigating to this page)."""
        settings = self.app.get_settings()
        self.appearance_var.set(settings.get("appearance_mode", "Dark"))
        self.scaling_var.set(settings.get("ui_scaling", "100%"))

        # Update author entry
        self.author_entry.delete(0, "end")
        author = settings.get("author_name", "")
        if author:
            self.author_entry.insert(0, author)

        # Update export path entry
        self.export_path_entry.delete(0, "end")
        export_path = settings.get("default_export_path", "")
        if export_path:
            self.export_path_entry.insert(0, export_path)

        self.page_size_var.set(settings.get("default_page_size", "8.5 x 11 inches"))
        self.bleed_var.set(settings.get("default_bleed", "0.125 inches"))
