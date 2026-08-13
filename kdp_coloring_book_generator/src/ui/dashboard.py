"""
Dashboard Frame - Main landing page of the application.
Displays project statistics, recent projects, and quick action buttons.
"""

import customtkinter as ctk
from datetime import datetime


class DashboardFrame(ctk.CTkFrame):
    """Dashboard view showing overview stats and quick actions."""

    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.app = app

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._create_header()
        self._create_stats_cards()
        self._create_quick_actions()
        self._create_recent_projects()

    def _create_header(self):
        """Create the dashboard header section."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=32, pady=(28, 8), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        # Welcome title
        title = ctk.CTkLabel(
            header_frame,
            text="Dashboard",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        # Subtitle with date
        today = datetime.now().strftime("%A, %B %d, %Y")
        subtitle = ctk.CTkLabel(
            header_frame,
            text=f"Welcome back  •  {today}",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray60"),
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _create_stats_cards(self):
        """Create statistics cards row."""
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.grid(row=1, column=0, padx=32, pady=(20, 8), sticky="ew")
        cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Stats data
        projects = self.app.get_projects()
        total_projects = len(projects)
        total_pages = sum(p.get("page_count", 0) for p in projects)
        completed = len([p for p in projects if p.get("status") == "completed"])
        in_progress = len([p for p in projects if p.get("status") == "in_progress"])

        stats = [
            ("Total Projects", str(total_projects), "📚"),
            ("Total Pages", str(total_pages), "📄"),
            ("Completed", str(completed), "✅"),
            ("In Progress", str(in_progress), "🔄"),
        ]

        self.stat_labels = {}
        for i, (label, value, icon) in enumerate(stats):
            card = ctk.CTkFrame(cards_frame, corner_radius=12, height=110)
            card.grid(row=0, column=i, padx=8, pady=4, sticky="nsew")
            card.grid_propagate(False)
            card.grid_columnconfigure(0, weight=1)

            icon_label = ctk.CTkLabel(
                card, text=icon, font=ctk.CTkFont(size=24)
            )
            icon_label.grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")

            value_label = ctk.CTkLabel(
                card, text=value, font=ctk.CTkFont(size=26, weight="bold")
            )
            value_label.grid(row=1, column=0, padx=16, pady=(0, 2), sticky="w")

            name_label = ctk.CTkLabel(
                card,
                text=label,
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray60"),
            )
            name_label.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="w")

            self.stat_labels[label] = value_label

    def _create_quick_actions(self):
        """Create quick action buttons."""
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.grid(row=2, column=0, padx=32, pady=(16, 8), sticky="ew")
        actions_frame.grid_columnconfigure(3, weight=1)

        section_label = ctk.CTkLabel(
            actions_frame,
            text="Quick Actions",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        section_label.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 12))

        actions = [
            ("➕  New Project", self._on_new_project, "#2563eb"),
            ("📁  Open Projects", self._on_open_projects, "#7c3aed"),
            ("⚙️  Settings", self._on_open_settings, "#64748b"),
        ]

        for i, (text, command, color) in enumerate(actions):
            btn = ctk.CTkButton(
                actions_frame,
                text=text,
                font=ctk.CTkFont(size=13, weight="bold"),
                height=40,
                width=160,
                corner_radius=8,
                fg_color=color,
                hover_color=self._darken_color(color),
                command=command,
            )
            btn.grid(row=1, column=i, padx=(0, 12), sticky="w")

    def _create_recent_projects(self):
        """Create recent projects list."""
        recent_frame = ctk.CTkFrame(self, corner_radius=12)
        recent_frame.grid(row=3, column=0, padx=32, pady=(16, 28), sticky="nsew")
        recent_frame.grid_columnconfigure(0, weight=1)
        recent_frame.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            recent_frame,
            text="Recent Projects",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header.grid(row=0, column=0, padx=20, pady=(16, 8), sticky="w")

        # Scrollable area for recent projects
        self.recent_scroll = ctk.CTkScrollableFrame(
            recent_frame, fg_color="transparent", corner_radius=0
        )
        self.recent_scroll.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.recent_scroll.grid_columnconfigure(0, weight=1)

        self._populate_recent_projects()

    def _populate_recent_projects(self):
        """Populate the recent projects list."""
        # Clear existing items
        for widget in self.recent_scroll.winfo_children():
            widget.destroy()

        projects = self.app.get_projects()

        if not projects:
            empty_label = ctk.CTkLabel(
                self.recent_scroll,
                text="No projects yet. Create your first coloring book project!",
                font=ctk.CTkFont(size=13),
                text_color=("gray50", "gray50"),
            )
            empty_label.grid(row=0, column=0, pady=40)
            return

        # Sort by last modified, show up to 8 recent
        sorted_projects = sorted(
            projects,
            key=lambda p: p.get("modified_at", ""),
            reverse=True,
        )[:8]

        for i, project in enumerate(sorted_projects):
            row_frame = ctk.CTkFrame(
                self.recent_scroll,
                height=50,
                corner_radius=8,
                fg_color=("gray88", "gray20"),
            )
            row_frame.grid(row=i, column=0, padx=4, pady=3, sticky="ew")
            row_frame.grid_columnconfigure(1, weight=1)
            row_frame.grid_propagate(False)

            # Project icon
            icon = ctk.CTkLabel(
                row_frame, text="📖", font=ctk.CTkFont(size=16)
            )
            icon.grid(row=0, column=0, padx=(14, 8), pady=12, sticky="w")

            # Project name
            name = ctk.CTkLabel(
                row_frame,
                text=project.get("name", "Untitled"),
                font=ctk.CTkFont(size=13, weight="bold"),
            )
            name.grid(row=0, column=1, pady=12, sticky="w")

            # Status badge
            status = project.get("status", "draft")
            status_colors = {
                "draft": "#f59e0b",
                "in_progress": "#3b82f6",
                "completed": "#10b981",
            }
            status_label = ctk.CTkLabel(
                row_frame,
                text=f"  {status.replace('_', ' ').title()}  ",
                font=ctk.CTkFont(size=11),
                corner_radius=4,
                fg_color=status_colors.get(status, "#64748b"),
                text_color="white",
            )
            status_label.grid(row=0, column=2, padx=8, pady=12, sticky="e")

            # Modified date
            modified = project.get("modified_at", "")
            if modified:
                try:
                    dt = datetime.fromisoformat(modified)
                    modified_str = dt.strftime("%b %d, %Y")
                except ValueError:
                    modified_str = modified
            else:
                modified_str = "—"

            date_label = ctk.CTkLabel(
                row_frame,
                text=modified_str,
                font=ctk.CTkFont(size=11),
                text_color=("gray50", "gray55"),
            )
            date_label.grid(row=0, column=3, padx=(8, 16), pady=12, sticky="e")

    def refresh(self):
        """Refresh dashboard data."""
        projects = self.app.get_projects()
        total_projects = len(projects)
        total_pages = sum(p.get("page_count", 0) for p in projects)
        completed = len([p for p in projects if p.get("status") == "completed"])
        in_progress = len([p for p in projects if p.get("status") == "in_progress"])

        self.stat_labels["Total Projects"].configure(text=str(total_projects))
        self.stat_labels["Total Pages"].configure(text=str(total_pages))
        self.stat_labels["Completed"].configure(text=str(completed))
        self.stat_labels["In Progress"].configure(text=str(in_progress))

        self._populate_recent_projects()

    def _on_new_project(self):
        """Navigate to project manager to create a new project."""
        self.app.navigate_to("projects")
        # Trigger new project dialog in project manager
        projects_frame = self.app.frames["projects"]
        if hasattr(projects_frame, "create_new_project"):
            projects_frame.create_new_project()

    def _on_open_projects(self):
        """Navigate to project manager."""
        self.app.navigate_to("projects")

    def _on_open_settings(self):
        """Navigate to settings."""
        self.app.navigate_to("settings")

    @staticmethod
    def _darken_color(hex_color: str) -> str:
        """Darken a hex color by 20% for hover effects."""
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        factor = 0.8
        r, g, b = int(r * factor), int(g * factor), int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
