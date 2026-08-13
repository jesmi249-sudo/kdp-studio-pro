"""
Project Manager Frame - Manage coloring book projects.
Supports creating, opening, deleting, and viewing project metadata.
Projects are stored as JSON locally for unlimited offline use.
"""

import customtkinter as ctk
from datetime import datetime
import uuid


class ProjectManagerFrame(ctk.CTkFrame):
    """Project management view with project list and CRUD operations."""

    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.app = app
        self.selected_project_id = None

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        self._create_header()
        self._create_project_list()
        self._create_detail_panel()

    def _create_header(self):
        """Create the page header with title and action buttons."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, padx=32, pady=(28, 16), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(
            header_frame,
            text="Project Manager",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="Create and manage your coloring book projects",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray60"),
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        # Action buttons
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, rowspan=2, sticky="e")

        self.new_btn = ctk.CTkButton(
            btn_frame,
            text="➕  New Project",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            width=150,
            corner_radius=8,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self.create_new_project,
        )
        self.new_btn.grid(row=0, column=0, padx=(0, 8))

        self.delete_btn = ctk.CTkButton(
            btn_frame,
            text="🗑️  Delete",
            font=ctk.CTkFont(size=13),
            height=38,
            width=110,
            corner_radius=8,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self._delete_selected_project,
        )
        self.delete_btn.grid(row=0, column=1)

    def _create_project_list(self):
        """Create the scrollable project list panel."""
        list_frame = ctk.CTkFrame(self, corner_radius=12)
        list_frame.grid(row=1, column=0, padx=(32, 8), pady=(0, 28), sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)

        # Search bar
        search_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        search_frame.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍  Search projects...",
            height=36,
            corner_radius=8,
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # Project list scrollable frame
        self.project_scroll = ctk.CTkScrollableFrame(
            list_frame, fg_color="transparent", corner_radius=0
        )
        self.project_scroll.grid(row=1, column=0, padx=8, pady=(4, 12), sticky="nsew")
        self.project_scroll.grid_columnconfigure(0, weight=1)

        self._populate_project_list()

    def _create_detail_panel(self):
        """Create the project detail/metadata panel."""
        self.detail_frame = ctk.CTkFrame(self, corner_radius=12)
        self.detail_frame.grid(row=1, column=1, padx=(8, 32), pady=(0, 28), sticky="nsew")
        self.detail_frame.grid_columnconfigure(0, weight=1)

        # Detail header
        detail_title = ctk.CTkLabel(
            self.detail_frame,
            text="Project Details",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        detail_title.grid(row=0, column=0, padx=20, pady=(20, 16), sticky="w")

        # Separator
        sep = ctk.CTkFrame(self.detail_frame, height=1, fg_color=("gray80", "gray25"))
        sep.grid(row=1, column=0, padx=16, sticky="ew")

        # Detail content area
        self.detail_content = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        self.detail_content.grid(row=2, column=0, padx=20, pady=16, sticky="nsew")
        self.detail_content.grid_columnconfigure(1, weight=1)

        self._show_no_selection()

    def _show_no_selection(self):
        """Show placeholder when no project is selected."""
        for widget in self.detail_content.winfo_children():
            widget.destroy()

        placeholder = ctk.CTkLabel(
            self.detail_content,
            text="Select a project to view details\nor create a new one.",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray50"),
            justify="center",
        )
        placeholder.grid(row=0, column=0, columnspan=2, pady=60)

    def _show_project_details(self, project: dict):
        """Display details for the selected project."""
        for widget in self.detail_content.winfo_children():
            widget.destroy()

        fields = [
            ("Name", project.get("name", "Untitled")),
            ("Status", project.get("status", "draft").replace("_", " ").title()),
            ("Pages", str(project.get("page_count", 0))),
            ("Page Size", project.get("page_size", "8.5 x 11 in")),
            ("Author", project.get("author", "—")),
            ("Created", self._format_date(project.get("created_at", ""))),
            ("Modified", self._format_date(project.get("modified_at", ""))),
            ("Description", project.get("description", "—")),
        ]

        for i, (label, value) in enumerate(fields):
            lbl = ctk.CTkLabel(
                self.detail_content,
                text=f"{label}:",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("gray40", "gray60"),
            )
            lbl.grid(row=i, column=0, padx=(0, 12), pady=6, sticky="nw")

            val = ctk.CTkLabel(
                self.detail_content,
                text=value,
                font=ctk.CTkFont(size=12),
                wraplength=200,
                justify="left",
            )
            val.grid(row=i, column=1, pady=6, sticky="nw")

        # Edit status button
        status_frame = ctk.CTkFrame(self.detail_content, fg_color="transparent")
        status_frame.grid(row=len(fields), column=0, columnspan=2, pady=(20, 0), sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)

        status_menu = ctk.CTkOptionMenu(
            status_frame,
            values=["Draft", "In Progress", "Completed"],
            command=lambda val, pid=project["id"]: self._update_status(pid, val),
            width=160,
            height=32,
        )
        current_status = project.get("status", "draft").replace("_", " ").title()
        status_menu.set(current_status)
        status_menu.grid(row=0, column=0, pady=(0, 8), sticky="w")

        # Open in Generator button
        open_gen_btn = ctk.CTkButton(
            status_frame,
            text="📖  Open in Generator",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=34,
            width=170,
            corner_radius=8,
            fg_color="#10b981",
            hover_color="#059669",
            command=lambda p=project: self._open_in_generator(p),
        )
        open_gen_btn.grid(row=1, column=0, pady=(8, 0), sticky="w")

    def _populate_project_list(self, filter_text: str = ""):
        """Populate the project list, optionally filtered."""
        for widget in self.project_scroll.winfo_children():
            widget.destroy()

        projects = self.app.get_projects()

        # Apply search filter
        if filter_text:
            projects = [
                p for p in projects
                if filter_text.lower() in p.get("name", "").lower()
                or filter_text.lower() in p.get("description", "").lower()
            ]

        # Sort by modified date (newest first)
        projects = sorted(
            projects,
            key=lambda p: p.get("modified_at", ""),
            reverse=True,
        )

        if not projects:
            empty_label = ctk.CTkLabel(
                self.project_scroll,
                text="No projects found." if filter_text else "No projects yet.\nClick 'New Project' to get started!",
                font=ctk.CTkFont(size=13),
                text_color=("gray50", "gray50"),
                justify="center",
            )
            empty_label.grid(row=0, column=0, pady=60)
            return

        for i, project in enumerate(projects):
            self._create_project_card(i, project)

    def _create_project_card(self, index: int, project: dict):
        """Create a clickable project card in the list."""
        is_selected = project.get("id") == self.selected_project_id

        card = ctk.CTkFrame(
            self.project_scroll,
            height=72,
            corner_radius=10,
            fg_color=("gray82", "gray25") if is_selected else ("gray90", "gray20"),
            border_width=2 if is_selected else 0,
            border_color=("#2563eb", "#3b82f6") if is_selected else ("gray80", "gray30"),
        )
        card.grid(row=index, column=0, padx=4, pady=4, sticky="ew")
        card.grid_columnconfigure(1, weight=1)
        card.grid_propagate(False)

        # Bind click event to the card and all its children
        card.bind("<Button-1>", lambda e, p=project: self._select_project(p))

        # Icon
        icon = ctk.CTkLabel(card, text="📖", font=ctk.CTkFont(size=22))
        icon.grid(row=0, column=0, rowspan=2, padx=(14, 10), pady=12, sticky="w")
        icon.bind("<Button-1>", lambda e, p=project: self._select_project(p))

        # Project name
        name_label = ctk.CTkLabel(
            card,
            text=project.get("name", "Untitled"),
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        name_label.grid(row=0, column=1, pady=(14, 0), sticky="w")
        name_label.bind("<Button-1>", lambda e, p=project: self._select_project(p))

        # Subtitle line
        pages = project.get("page_count", 0)
        status = project.get("status", "draft").replace("_", " ").title()
        modified = self._format_date(project.get("modified_at", ""))
        subtitle_text = f"{pages} pages  •  {status}  •  {modified}"

        subtitle = ctk.CTkLabel(
            card,
            text=subtitle_text,
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray55"),
            anchor="w",
        )
        subtitle.grid(row=1, column=1, pady=(0, 14), sticky="w")
        subtitle.bind("<Button-1>", lambda e, p=project: self._select_project(p))

    def _select_project(self, project: dict):
        """Handle project selection."""
        self.selected_project_id = project.get("id")
        self._populate_project_list(self.search_entry.get())
        self._show_project_details(project)

    def create_new_project(self):
        """Open dialog to create a new project."""
        dialog = NewProjectDialog(self, self.app)
        self.wait_window(dialog)

        if dialog.result:
            self.app.add_project(dialog.result)
            self.selected_project_id = dialog.result["id"]
            self._populate_project_list()
            self._show_project_details(dialog.result)

    def _delete_selected_project(self):
        """Delete the currently selected project."""
        if not self.selected_project_id:
            return

        # Confirm deletion
        dialog = ConfirmDialog(
            self,
            title="Delete Project",
            message="Are you sure you want to delete this project?\nThis action cannot be undone.",
        )
        self.wait_window(dialog)

        if dialog.result:
            self.app.delete_project(self.selected_project_id)
            self.selected_project_id = None
            self._populate_project_list()
            self._show_no_selection()

    def _update_status(self, project_id: str, new_status: str):
        """Update a project's status."""
        status_map = {
            "Draft": "draft",
            "In Progress": "in_progress",
            "Completed": "completed",
        }
        self.app.update_project(project_id, {
            "status": status_map.get(new_status, "draft"),
            "modified_at": datetime.now().isoformat(),
        })
        self._populate_project_list(self.search_entry.get())

    def _open_in_generator(self, project: dict):
        """Open the selected project in the Generator frame."""
        if hasattr(self.app, "open_project_in_generator"):
            self.app.open_project_in_generator(project)

    def _on_search(self, event=None):
        """Handle search input changes."""
        self._populate_project_list(self.search_entry.get())

    def refresh(self):
        """Refresh the project list."""
        self._populate_project_list(self.search_entry.get())
        if self.selected_project_id:
            projects = self.app.get_projects()
            project = next(
                (p for p in projects if p.get("id") == self.selected_project_id),
                None,
            )
            if project:
                self._show_project_details(project)
            else:
                self._show_no_selection()

    @staticmethod
    def _format_date(iso_str: str) -> str:
        """Format an ISO date string for display."""
        if not iso_str:
            return "—"
        try:
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime("%b %d, %Y %I:%M %p")
        except ValueError:
            return iso_str


class NewProjectDialog(ctk.CTkToplevel):
    """Dialog window for creating a new project."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.result = None

        self.title("Create New Project")
        self.geometry("480x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + 100
        y = parent.winfo_rooty() + 50
        self.geometry(f"+{x}+{y}")

        self.grid_columnconfigure(0, weight=1)

        # Title
        title = ctk.CTkLabel(
            self,
            text="Create New Project",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, padx=28, pady=(24, 20), sticky="w")

        # Form fields
        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.grid(row=1, column=0, padx=28, sticky="ew")
        form_frame.grid_columnconfigure(0, weight=1)

        # Project name
        ctk.CTkLabel(
            form_frame, text="Project Name *", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.name_entry = ctk.CTkEntry(
            form_frame, placeholder_text="My Coloring Book", height=36
        )
        self.name_entry.grid(row=1, column=0, sticky="ew", pady=(0, 16))

        # Description
        ctk.CTkLabel(
            form_frame, text="Description", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        self.desc_entry = ctk.CTkTextbox(form_frame, height=80, corner_radius=8)
        self.desc_entry.grid(row=3, column=0, sticky="ew", pady=(0, 16))

        # Page size
        ctk.CTkLabel(
            form_frame, text="Page Size", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=4, column=0, sticky="w", pady=(0, 4))

        self.page_size_menu = ctk.CTkOptionMenu(
            form_frame,
            values=[
                "8.5 x 11 inches (Letter)",
                "8.5 x 8.5 inches (Square)",
                "6 x 9 inches",
                "8 x 10 inches",
            ],
            width=260,
            height=34,
        )
        self.page_size_menu.grid(row=5, column=0, sticky="w", pady=(0, 16))

        # Author
        ctk.CTkLabel(
            form_frame, text="Author", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=6, column=0, sticky="w", pady=(0, 4))

        self.author_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Author name",
            height=36,
        )
        self.author_entry.grid(row=7, column=0, sticky="ew", pady=(0, 16))

        # Pre-fill author from settings
        author = self.app.get_settings().get("author_name", "")
        if author:
            self.author_entry.insert(0, author)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=28, pady=(20, 24), sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            height=38,
            fg_color="transparent",
            border_width=1,
            border_color=("gray60", "gray40"),
            text_color=("gray20", "gray80"),
            hover_color=("gray85", "gray30"),
            command=self.destroy,
        )
        cancel_btn.grid(row=0, column=0, sticky="e", padx=(0, 8))

        create_btn = ctk.CTkButton(
            btn_frame,
            text="Create Project",
            width=140,
            height=38,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(weight="bold"),
            command=self._on_create,
        )
        create_btn.grid(row=0, column=1, sticky="e")

    def _on_create(self):
        """Handle project creation."""
        name = self.name_entry.get().strip()
        if not name:
            self.name_entry.configure(border_color="#dc2626")
            return

        now = datetime.now().isoformat()
        self.result = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": self.desc_entry.get("1.0", "end-1c").strip(),
            "page_size": self.page_size_menu.get(),
            "author": self.author_entry.get().strip(),
            "page_count": 0,
            "status": "draft",
            "created_at": now,
            "modified_at": now,
            "pages": [],
        }
        self.destroy()


class ConfirmDialog(ctk.CTkToplevel):
    """Simple confirmation dialog."""

    def __init__(self, parent, title: str = "Confirm", message: str = "Are you sure?"):
        super().__init__(parent)
        self.result = False

        self.title(title)
        self.geometry("380x180")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + 150
        y = parent.winfo_rooty() + 100
        self.geometry(f"+{x}+{y}")

        self.grid_columnconfigure(0, weight=1)

        # Message
        msg_label = ctk.CTkLabel(
            self,
            text=message,
            font=ctk.CTkFont(size=13),
            justify="center",
        )
        msg_label.grid(row=0, column=0, padx=28, pady=(28, 20))

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, padx=28, pady=(0, 20))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            height=36,
            fg_color="transparent",
            border_width=1,
            border_color=("gray60", "gray40"),
            text_color=("gray20", "gray80"),
            hover_color=("gray85", "gray30"),
            command=self.destroy,
        )
        cancel_btn.grid(row=0, column=0, padx=(0, 8))

        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="Delete",
            width=100,
            height=36,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self._on_confirm,
        )
        confirm_btn.grid(row=0, column=1)

    def _on_confirm(self):
        """Handle confirmation."""
        self.result = True
        self.destroy()

