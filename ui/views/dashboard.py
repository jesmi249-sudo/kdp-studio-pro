import customtkinter as ctk
import json
from typing import Dict, Any, List, Tuple
from ui.theme.fonts import Fonts
from ui.theme.spacing import Spacing
from ui.theme.colors import Colors
from core.command_dispatcher import CommandDispatcher
from core.dashboard_service import DashboardService
from core.logger import get_logger

logger = get_logger(__name__)

class DashboardView(ctk.CTkFrame):
    """
    DashboardView serves as a lightweight view controller representing the KDP Studio Pro dashboard.
    It delegates all business actions and connection audits to the DashboardService.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Configure layout grids (Left: weight=3, Right: weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._build_header()
        self._build_content_layout()
        self.refresh_data()
        
    def _build_header(self) -> None:
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=Spacing.L, pady=(Spacing.L, Spacing.M))
        
        ctk.CTkLabel(header_frame, text="Dashboard", font=Fonts.heading1()).pack(side="left")
        
        # Refresh button to trigger manual reloading
        self.refresh_btn = ctk.CTkButton(
            header_frame, 
            text="Refresh", 
            width=80, 
            font=Fonts.body_bold(), 
            command=self.refresh_data
        )
        self.refresh_btn.pack(side="right", padx=(Spacing.M, 0), pady=(5, 0))
        
        ctk.CTkLabel(header_frame, text="Welcome to KDP Studio Pro", font=Fonts.body(), text_color="gray").pack(side="right", pady=(10, 0))
        
    def _build_content_layout(self) -> None:
        # Left container: Statistics row, Quick Actions row, and Recent Projects row
        self.left_container = ctk.CTkFrame(self, fg_color="transparent")
        self.left_container.grid(row=1, column=0, sticky="nsew", padx=(Spacing.L, Spacing.M), pady=(0, Spacing.L))
        self.left_container.grid_columnconfigure(0, weight=1)
        
        self._build_statistics_card_containers()
        self._build_quick_actions_container()
        self._build_recent_projects_container()
        
        # Right container: System Health diagnostics
        self.right_container = ctk.CTkFrame(self, fg_color="transparent")
        self.right_container.grid(row=1, column=1, sticky="nsew", padx=(0, Spacing.L), pady=(0, Spacing.L))
        self.right_container.grid_columnconfigure(0, weight=1)
        
        self._build_system_health_container()
        self._build_notifications_console()

    def _build_statistics_card_containers(self) -> None:
        stats_outer = ctk.CTkFrame(self.left_container)
        stats_outer.pack(fill="x", pady=(0, Spacing.M))
        
        ctk.CTkLabel(stats_outer, text="Statistics Overview", font=Fonts.heading3()).pack(anchor="w", padx=Spacing.M, pady=(Spacing.M, Spacing.S))
        
        cards_grid = ctk.CTkFrame(stats_outer, fg_color="transparent")
        cards_grid.pack(fill="x", padx=Spacing.M, pady=(0, Spacing.M))
        cards_grid.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Project count card
        self.proj_card = ctk.CTkFrame(cards_grid, border_width=1, border_color=Colors.BORDER[1])
        self.proj_card.grid(row=0, column=0, padx=Spacing.S, pady=Spacing.S, sticky="nsew")
        ctk.CTkLabel(self.proj_card, text="Total Projects", font=Fonts.body(), text_color="gray").pack(pady=(Spacing.M, 0))
        self.proj_count_lbl = ctk.CTkLabel(self.proj_card, text="0", font=Fonts.get_font(24, "bold"))
        self.proj_count_lbl.pack(pady=(5, Spacing.M))
        
        # Book count card
        self.book_card = ctk.CTkFrame(cards_grid, border_width=1, border_color=Colors.BORDER[1])
        self.book_card.grid(row=0, column=1, padx=Spacing.S, pady=Spacing.S, sticky="nsew")
        ctk.CTkLabel(self.book_card, text="Books Generated", font=Fonts.body(), text_color="gray").pack(pady=(Spacing.M, 0))
        self.book_count_lbl = ctk.CTkLabel(self.book_card, text="0", font=Fonts.get_font(24, "bold"))
        self.book_count_lbl.pack(pady=(5, Spacing.M))
        
        # Export count card
        self.export_card = ctk.CTkFrame(cards_grid, border_width=1, border_color=Colors.BORDER[1])
        self.export_card.grid(row=0, column=2, padx=Spacing.S, pady=Spacing.S, sticky="nsew")
        ctk.CTkLabel(self.export_card, text="Ready Exports", font=Fonts.body(), text_color="gray").pack(pady=(Spacing.M, 0))
        self.export_count_lbl = ctk.CTkLabel(self.export_card, text="0", font=Fonts.get_font(24, "bold"))
        self.export_count_lbl.pack(pady=(5, Spacing.M))

    def _build_quick_actions_container(self) -> None:
        actions_frame = ctk.CTkFrame(self.left_container)
        actions_frame.pack(fill="x", pady=(0, Spacing.M))
        
        ctk.CTkLabel(actions_frame, text="Quick Actions", font=Fonts.heading3()).pack(anchor="w", padx=Spacing.M, pady=Spacing.M)
        
        grid = ctk.CTkFrame(actions_frame, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=Spacing.M, pady=(0, Spacing.M))
        
        actions: List[Tuple[str, str]] = [
            ("New Project", "new"),
            ("Open Project", "open"),
            ("Coloring Book Studio", "Coloring Book"),
            ("Planner Studio", "Planner Studio"),
            ("Story Book Studio", "Story Book"),
            ("Activity Book Studio", "Activity Book"),
            ("Export Center", "Export Center")
        ]
        
        row_idx, col_idx = 0, 0
        for text, cmd in actions:
            btn = ctk.CTkButton(
                grid, 
                text=text, 
                height=45, 
                font=Fonts.body_bold(),
                command=lambda c=cmd: self._trigger_action(c)
            )
            btn.grid(row=row_idx, column=col_idx, padx=Spacing.S, pady=Spacing.S, sticky="ew")
            grid.grid_columnconfigure(col_idx, weight=1)
            col_idx += 1
            if col_idx > 2:
                col_idx = 0
                row_idx += 1

    def _build_recent_projects_container(self) -> None:
        recent_frame = ctk.CTkFrame(self.left_container)
        recent_frame.pack(fill="both", expand=True, pady=(0, Spacing.M))
        
        ctk.CTkLabel(recent_frame, text="Recent Projects", font=Fonts.heading3()).pack(anchor="w", padx=Spacing.M, pady=Spacing.M)
        
        self.recent_list_container = ctk.CTkFrame(recent_frame, fg_color="transparent")
        self.recent_list_container.pack(fill="both", expand=True, padx=Spacing.M, pady=(0, Spacing.M))

    def _build_system_health_container(self) -> None:
        health_frame = ctk.CTkFrame(self.right_container)
        health_frame.pack(fill="x", pady=(0, Spacing.M))
        
        ctk.CTkLabel(health_frame, text="System Health", font=Fonts.heading3()).pack(anchor="w", padx=Spacing.M, pady=Spacing.M)
        
        self.health_list_container = ctk.CTkFrame(health_frame, fg_color="transparent")
        self.health_list_container.pack(fill="x", padx=Spacing.M, pady=(0, Spacing.M))

    def _build_notifications_console(self) -> None:
        notif_frame = ctk.CTkFrame(self.right_container)
        notif_frame.pack(fill="both", expand=True)
        
        ctk.CTkLabel(notif_frame, text="System Notifications", font=Fonts.heading3()).pack(anchor="w", padx=Spacing.M, pady=Spacing.M)
        
        self.notif_content = ctk.CTkTextbox(notif_frame, height=150, font=Fonts.small(), state="disabled")
        self.notif_content.pack(fill="both", expand=True, padx=Spacing.M, pady=(0, Spacing.M))
        
        self._add_notification("Dashboard service initialized.")

    def _add_notification(self, message: str) -> None:
        """Appends a new logging message to the notifications text widget."""
        self.notif_content.configure(state="normal")
        self.notif_content.insert("end", f"• {message}\n")
        self.notif_content.configure(state="disabled")
        self.notif_content.see("end")

    def refresh_data(self) -> None:
        """
        Refreshes all components dynamically by executing data calls to DashboardService.
        Catches and manages exceptions to prevent UI crashes.
        """
        logger.info("Refreshing Dashboard View data...")
        try:
            self._refresh_statistics()
            self._refresh_recent_projects()
            self._refresh_system_health()
        except Exception as e:
            logger.error(f"Error during Dashboard refresh: {e}")
            self._add_notification(f"Refresh failed: {e}")

    def _refresh_statistics(self) -> None:
        proj_count, book_count, export_count = DashboardService.get_statistics()
        self.proj_count_lbl.configure(text=str(proj_count))
        self.book_count_lbl.configure(text=str(book_count))
        self.export_count_lbl.configure(text=str(export_count))

    def _refresh_recent_projects(self) -> None:
        # Clear existing list items
        for widget in self.recent_list_container.winfo_children():
            widget.destroy()
            
        recent_projects = DashboardService.get_recent_projects(limit=3)
        
        if not recent_projects:
            lbl = ctk.CTkLabel(
                self.recent_list_container, 
                text="No recent projects found. Click 'New Project' to start!", 
                font=Fonts.body(),
                text_color="gray"
            )
            lbl.pack(pady=Spacing.L)
            return
            
        for p in recent_projects:
            p_id = p["id"]
            p_name = p["name"]
            p_type = p["project_type"]
            p_date = p["last_modified"]
            book_type = p["book_type"]
            status = p["status"]
            
            card = ctk.CTkFrame(self.recent_list_container, fg_color=Colors.BG_CARD)
            card.pack(fill="x", pady=Spacing.XS, padx=Spacing.XS)
            
            # Icon selection
            icon_str = "📁"
            if p_type == 'cover':
                icon_str = "🎨"
            elif p_type == 'planner':
                icon_str = "📅"
            elif 'Coloring' in book_type:
                icon_str = "✏️"
            elif 'Story' in book_type:
                icon_str = "📖"
            elif 'Planner' in book_type or 'Journal' in book_type:
                icon_str = "📓"
                
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=Spacing.M, pady=Spacing.S)
            
            ctk.CTkLabel(info_frame, text=f"{icon_str}  {p_name}", font=Fonts.body_bold(), anchor="w").pack(fill="x")
            
            meta_str = f"Type: {book_type}  |  Modified: {p_date}"
            ctk.CTkLabel(info_frame, text=meta_str, font=Fonts.small(), text_color="gray", anchor="w").pack(fill="x")
            
            # Status Indicator
            color = "green" if status.lower() == "exported" else ("blue" if status.lower() == "active" else "gray")
            status_lbl = ctk.CTkLabel(card, text=status.upper(), font=Fonts.small(), text_color=color, width=80)
            status_lbl.pack(side="right", padx=Spacing.M)
            
            # Open Button
            btn = ctk.CTkButton(
                card, 
                text="Open", 
                width=60, 
                font=Fonts.small(),
                command=lambda proj=p["raw_data"]: self._open_project(proj)
            )
            btn.pack(side="right", padx=(0, Spacing.S))

    def _refresh_system_health(self) -> None:
        # Clear health list items
        for widget in self.health_list_container.winfo_children():
            widget.destroy()
            
        health_status = DashboardService.check_system_health()
        
        for name, status, color in health_status:
            row = ctk.CTkFrame(self.health_list_container, fg_color="transparent")
            row.pack(fill="x", pady=Spacing.XS)
            ctk.CTkLabel(row, text=name, font=Fonts.body()).pack(side="left")
            ctk.CTkLabel(row, text=status, font=Fonts.body_bold(), text_color=color).pack(side="right")
            
            # Alert in notifications if a service is down
            if color == "red":
                self._add_notification(f"Warning: {name} diagnostics reported status: {status}")

    def _open_project(self, project: dict) -> None:
        try:
            app = self.winfo_toplevel()
            if hasattr(app, "open_project"):
                app.open_project(project)
            else:
                from tkinter import messagebox
                messagebox.showerror("Error", "Core application open_project route was not found.")
        except Exception as e:
            logger.error(f"Error executing open_project action from dashboard: {e}")

    def _trigger_action(self, target: str) -> None:
        dispatcher = CommandDispatcher()
        if target in ["new", "open"]:
            dispatcher.execute(target)
        else:
            dispatcher.execute("navigate", target=target)
