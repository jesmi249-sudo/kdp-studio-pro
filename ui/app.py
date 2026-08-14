import customtkinter as ctk
from ui.theme.theme_manager import ThemeManager
from ui.theme.fonts import Fonts
from ui.theme.spacing import Spacing
from core.logger import get_logger
from core.icon_manager import IconManager
from core.command_dispatcher import CommandDispatcher

logger = get_logger(__name__)

class KDPStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("KDP Studio Pro v6.0")
        self.geometry("1400x900")
        self.minsize(1024, 768)
        
        # Apply theme
        ThemeManager.apply_theme()
        
        self.icon_mgr = IconManager()
        self.dispatcher = CommandDispatcher()
        self.dispatcher.set_global_handler(self) # We handle global commands like 'new'
        self.dispatcher.set_active_view(self)
        
        # Grid layout: 
        # Row 0: Toolbar
        # Row 1: Main Workspace (Sidebar + Content)
        # Row 2: Status Bar
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)
        
        self.views = {}
        self.current_frame = None
        
        self._build_toolbar()
        
        # Workspace container
        self.workspace = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.workspace.grid(row=1, column=0, sticky="nsew")
        self.workspace.grid_rowconfigure(0, weight=1)
        self.workspace.grid_columnconfigure(1, weight=1)
        
        self._build_sidebar()
        
        # Main content area
        self.main_content_frame = ctk.CTkFrame(self.workspace, corner_radius=0, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=1, sticky="nsew")
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        
        self.wizard_bar_frame = ctk.CTkFrame(self.main_content_frame, height=60, corner_radius=0)
        
        self._build_statusbar()
        
        # Pre-register dashboard and load it
        self.select_frame("Dashboard")
        
        # Ensure IBookBuilder is registered globally to prevent DI swallowed exceptions during recovery
        from book_builder.container import Container
        from book_builder.interfaces.core import IBookBuilder
        from book_builder.engine import BookBuilderEngine
        try:
            Container().resolve(IBookBuilder)
        except Exception:
            engine = BookBuilderEngine()
            Container().register(IBookBuilder, engine)



    def _build_toolbar(self):
        self.toolbar = ctk.CTkFrame(self, height=50, corner_radius=0)
        self.toolbar.grid(row=0, column=0, sticky="ew")
        
        buttons = [
            ("New", "new.png", "new"),
            ("Open", "open.png", "open"),
            ("Save", "save.png", "save"),
            ("Save As", "save.png", "save_as"),
            ("|", "", ""),
            ("Undo", "undo.png", "undo"),
            ("Redo", "redo.png", "redo"),
            ("|", "", ""),
            ("Export", "export.png", "export"),
            ("Settings", "settings.png", "settings"),
            ("Help", "help.png", "help")
        ]
        
        for text, icon_name, cmd in buttons:
            if text == "|":
                ctk.CTkFrame(self.toolbar, width=2, height=30, fg_color="gray").pack(side="left", padx=10, pady=10)
                continue
                
            img = self.icon_mgr.get_icon(icon_name)
            btn = ctk.CTkButton(self.toolbar, text=text, image=img, width=60, fg_color="transparent", 
                                text_color=("black", "white"),
                                command=lambda c=cmd: self.dispatcher.execute(c))
            btn.pack(side="left", padx=2, pady=5)

    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self.workspace, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(1, weight=1) # Push bottom items down
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text=" KDP Studio Pro", font=Fonts.heading3(), 
                                       image=self.icon_mgr.get_icon("dashboard.png"), compound="left")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 20), sticky="w")
        
        self.menu_scroll = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.menu_scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        
        menu_groups = [
            ("MY BOOKS", [
                ("Dashboard", "dashboard.png"),
                ("Projects", "projects.png"),
            ]),
            ("CURRENT BOOK", [
                ("Book Workspace", "projects.png"),
            ]),
            ("ADVANCED TOOLS", [
                ("Coloring Book Studio", "coloring.png"),
                ("Planner Studio", "planner.png"),
                ("Story Book Studio", "storybook.png"),
                ("Activity Book Studio", "activity.png"),
                ("Notebook Studio", "projects.png"),
                ("Journal Studio", "projects.png"),
                ("Cover Designer Pro", "cover.png"),
                ("Interior Designer", "interior.png"),
                ("Scene Builder", "metadata.png"),
                ("Prompt Generator", "metadata.png"),
                ("Templates & Assets", "assets.png"),
                ("Metadata", "metadata.png"),
                ("Export Center", "export.png"),
                ("KDP Compliance", "compliance.png"),
            ])
        ]
        
        self.nav_buttons = {}
        for group_name, items in menu_groups:
            ctk.CTkLabel(self.menu_scroll, text=group_name, font=Fonts.small(), text_color="gray").pack(anchor="w", padx=15, pady=(10, 2))
            for name, icon_name in items:
                img = self.icon_mgr.get_icon(icon_name)
                btn = ctk.CTkButton(self.menu_scroll, text=name, image=img, compound="left", anchor="w",
                                    fg_color="transparent", text_color=("gray10", "gray90"), font=Fonts.body(),
                                    command=lambda n=name: self.select_frame(n))
                btn.pack(fill="x", padx=10, pady=1)
                self.nav_buttons[name] = btn
            
        # Settings at bottom
        img = self.icon_mgr.get_icon("settings.png")
        btn = ctk.CTkButton(self.sidebar_frame, text="Settings", image=img, compound="left", anchor="w",
                            fg_color="transparent", text_color=("gray10", "gray90"), font=Fonts.body(),
                            command=lambda: self.select_frame("Settings"))
        btn.grid(row=2, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.nav_buttons["Settings"] = btn
        
        # AI Settings at bottom
        ai_btn = ctk.CTkButton(self.sidebar_frame, text="AI Settings", image=img, compound="left", anchor="w",
                            fg_color="transparent", text_color=("gray10", "gray90"), font=Fonts.body(),
                            command=lambda: self.select_frame("AI Settings"))
        ai_btn.grid(row=3, column=0, padx=10, pady=(5, 20), sticky="ew")
        self.nav_buttons["AI Settings"] = ai_btn

    def _build_statusbar(self):
        self.statusbar = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.statusbar.grid(row=2, column=0, sticky="ew")
        
        self.status_lbl = ctk.CTkLabel(self.statusbar, text="Ready", font=Fonts.small())
        self.status_lbl.pack(side="left", padx=10)
        
        self.version_lbl = ctk.CTkLabel(self.statusbar, text="v2.0 | Theme: Dark | DB: Connected", font=Fonts.small(), text_color="gray")
        self.version_lbl.pack(side="right", padx=10)

    def _lazy_load_view(self, name):
        """Instantiates views only when they are first clicked."""
        if name in self.views:
            return self.views[name]
            
        logger.info(f"Lazy loading view: {name}")
        self.status_lbl.configure(text=f"Loading {name}...")
        self.update()
        
        view = None
        if name == "Dashboard":
            from ui.views.dashboard import DashboardView
            view = DashboardView(self.main_content_frame)
        elif name == "Projects":
            from ui.views.project_manager import ProjectManagerView
            view = ProjectManagerView(self.main_content_frame)
        elif name == "Book Builder":
            from ui.views.book_builder import BookBuilderView
            view = BookBuilderView(self.main_content_frame)
        elif name == "Metadata":
            from ui.views.metadata_view import MetadataView
            view = MetadataView(self.main_content_frame)
        elif name == "Templates & Assets":
            from ui.views.asset_manager_view import AssetManagerView
            view = AssetManagerView(self.main_content_frame)
        elif name == "Coloring Book Studio":
            from ui.views.coloring_studio import ColoringStudioView
            view = ColoringStudioView(self.main_content_frame)
        elif name == "Interior Designer":
            from ui.views.interior_view import InteriorView
            view = InteriorView(self.main_content_frame)
        elif name == "Cover Designer Pro":
            from ui.views.cover_designer import CoverDesignerView
            view = CoverDesignerView(self.main_content_frame)
        elif name == "Scene Builder":
            from ui.views.scene_builder_view import SceneBuilderView
            view = SceneBuilderView(self.main_content_frame)
        elif name == "Book Scene Planner":
            from ui.views.book_scene_planner_view import BookScenePlannerView
            view = BookScenePlannerView(self.main_content_frame)
        elif name == "Production Pipeline":
            from ui.views.production_dashboard import ProductionDashboardView
            view = ProductionDashboardView(self.main_content_frame)
        elif name == "Prompt Generator":
            from ui.views.prompt_generator_view import PromptGeneratorView
            view = PromptGeneratorView(self.main_content_frame)
        elif name == "Export Center":
            from ui.views.export_center import ExportCenterView
            view = ExportCenterView(self.main_content_frame)
        elif name == "KDP Compliance":
            from ui.views.compliance_view import ComplianceView
            view = ComplianceView(self.main_content_frame)
        elif name == "Settings":
            from ui.views.settings import SettingsView
            view = SettingsView(self.main_content_frame)
        elif name == "AI Settings":
            from ui.views.ai_settings_view import AISettingsView
            from book_builder.container import Container
            from book_builder.services.ai.manager import AIManager
            from book_builder.services.credential_service import ICredentialService, KeyringCredentialService
            from core.config import config
            
            try:
                ai_manager = Container().resolve(AIManager)
                cred_service = Container().resolve(ICredentialService)
            except ValueError:
                cred_service = KeyringCredentialService()
                ai_manager = AIManager(credential_service=cred_service)
                ai_cfg = config.get("ai_settings", {})
                provider = ai_cfg.get("provider", "none")
                model = ai_cfg.get("model", "gpt-4o-mini")
                is_enabled = ai_cfg.get("enabled", False)
                if is_enabled:
                    ai_manager.configure(provider, model_name=model)
                Container().register(ICredentialService, cred_service)
                Container().register(AIManager, ai_manager)
            view = AISettingsView(self.main_content_frame, ai_manager, cred_service, config)
        elif name == "Planner Studio":
            from ui.views.planner_studio import PlannerStudioView
            view = PlannerStudioView(self.main_content_frame)
        elif name == "Notebook Studio":
            from ui.views.notebook_studio import NotebookStudioView
            view = NotebookStudioView(self.main_content_frame)
        elif name == "Journal Studio":
            from ui.views.journal_studio import JournalStudioView
            view = JournalStudioView(self.main_content_frame)
        elif name == "Story Book Studio":
            from ui.views.storybook_studio import StoryBookStudioView
            view = StoryBookStudioView(self.main_content_frame)
        elif name == "Activity Book Studio":
            from ui.views.activity_studio import ActivityBookStudioView
            view = ActivityBookStudioView(self.main_content_frame)
        elif name == "Book Workspace":
            from ui.views.book_workspace import BookWorkspaceView
            view = BookWorkspaceView(self.main_content_frame)
        else:
            view = ctk.CTkFrame(self.main_content_frame)
            
        self.views[name] = view
        self.status_lbl.configure(text="Ready")
        return view

    def select_frame(self, name):
        if self.current_frame:
            self.current_frame.grid_forget()
            
        view = self._lazy_load_view(name)
        self.current_frame = view
        self.current_frame.grid(row=0, column=0, sticky="nsew")
        
        # Refresh the view dynamically if it has a refresh_data method
        if hasattr(view, "refresh_data"):
            try:
                view.refresh_data()
            except Exception as e:
                logger.error(f"Failed to auto-refresh view '{name}': {e}")
        
        # Route toolbar commands to the new view
        self.dispatcher.set_active_view(self.current_frame)
        
        # Update sidebar button highlighting
        for btn_name, btn in self.nav_buttons.items():
            btn.configure(fg_color=("gray75", "gray25") if btn_name == name else "transparent")

    # App-level command handlers
    def cmd_navigate(self, target):
        self.select_frame(target)
        
    def cmd_settings(self):
        self.select_frame("Settings")

    def cmd_new(self):
        try:
            from ui.views.book_wizard import BookWizardController
            wizard = BookWizardController(self)
            wizard.start()
        except Exception as e:
            logger.error(f"Failed to launch Book Wizard: {e}")
            from tkinter import messagebox
            messagebox.showerror("Error", f"Could not start Book Wizard: {e}")

    def cmd_open(self):
        """Switches frame to Projects manager and prompts user to load a project."""
        try:
            self.select_frame("Projects")
            from tkinter import messagebox
            messagebox.showinfo(
                "Open Project",
                "Please select a project from the list below and click 'Open' to load it."
            )
        except Exception as e:
            logger.error(f"Error executing open command in main application: {e}")

    def cmd_export(self):
        """Switches frame to Export Center, validating first that projects exist."""
        try:
            from database.db import db
            from tkinter import messagebox
            projects = db.get_all_projects()
            if not projects:
                logger.warning("Attempted to access Export Center, but database has no projects.")
                messagebox.showwarning(
                    "Export Center",
                    "No projects exist in the database. Please create a project before exporting."
                )
                return
            self.select_frame("Export Center")
        except Exception as e:
            logger.error(f"Error executing export command: {e}")
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to load Export Center: {e}")

    def cmd_help(self):
        """Displays user guide documentation dialog."""
        try:
            from ui.components.dialogs import BaseDialog
            dlg = BaseDialog(
                "KDP Studio Pro Help",
                "Welcome to KDP Studio Pro v6.0!\n\n"
                "• Dashboard: Overview of metrics, system health, and quick actions.\n"
                "• Projects: Create, rename, delete and load your existing books.\n"
                "• Metadata: Generate KDP-compliant titles, descriptions, and keywords.\n"
                "• Templates & Assets: Organize and manage interior/cover assets.\n"
                "• Studios: Specialized editors for coloring books, planners, etc.\n"
                "• Export Center: Generate ready-to-upload PDF packages for KDP.",
                master=self
            )
            dlg.geometry("500x320")
            
            import customtkinter as ctk
            btn = ctk.CTkButton(dlg.action_frame, text="Close", command=dlg.destroy)
            btn.pack(side="right")
        except Exception as e:
            logger.error(f"Error displaying help dialog: {e}")

    def open_project(self, project: Any):
        """
        Centralized routing to open a selected project.
        
        Args:
            project (Any): The project row dictionary or BookProject instance.
        """
        import json
        from tkinter import messagebox
        
        # Check if project is a BookProject object
        if hasattr(project, "book_type") and hasattr(project, "name"):
            from book_builder.serializer import ProjectSerializer
            p_type = "book"
            if project.book_type in ("Planner", "Notebook"):
                p_type = project.book_type.lower()
            elif "Activity" in project.book_type:
                p_type = "activity"
            elif "Coloring" in project.book_type:
                p_type = "coloring"
                
            project_dict = {
                "id": project.id,
                "name": project.name,
                "project_type": p_type,
                "data": json.dumps(ProjectSerializer.serialize_project(project))
            }
        else:
            # Safe dict conversion for sqlite3.Row rows
            project_dict = dict(project) if not isinstance(project, dict) else project
        
        p_id = project_dict.get('id')
        p_name = project_dict.get('name')
        p_type = project_dict.get('project_type')
        p_data = project_dict.get('data')
        
        logger.info(f"Centralized load project: id={p_id}, name='{p_name}', type='{p_type}'")
        
        try:
            state = json.loads(p_data) if p_data else {}
            
            if p_type == 'cover':
                self.select_frame('Cover Designer Pro')
                view = self.views.get('Cover Designer Pro')
                if view and hasattr(view, 'load_project'):
                    view.load_project(p_id, p_name, state)
                else:
                    messagebox.showerror("Error", "Cover Designer view is not ready or missing load_project.")
                return

            # Always route standard projects to Book Workspace
            if p_type in ['book', 'wizard', 'notebook', 'journal', 'planner', 'storybook', 'story book', 'activity book', 'activity', 'coloring book', 'coloring']:
                target_studio = "Book Workspace"
            
            if target_studio:
                self.select_frame(target_studio)
                view = self.views.get(target_studio)
                if view:
                    if hasattr(view, 'load_project'):
                        view.load_project(p_id, p_name, state)
                    elif hasattr(view, 'controller') and hasattr(view.controller, 'engine'):
                        view.controller.engine.load_project(p_id)
                    else:
                        messagebox.showerror("Error", f"{target_studio} view does not support project loading.")
                else:
                    messagebox.showerror("Error", f"{target_studio} view is not ready.")
            else:
                messagebox.showinfo("Not Supported", f"Opening '{p_type}' projects is not fully implemented yet.")
        except Exception as e:
            logger.error(f"Error in centralized open_project: {e}")
            messagebox.showerror("Error", f"Failed to open project: {e}")
