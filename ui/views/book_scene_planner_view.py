import customtkinter as ctk
from tkinter import messagebox
from core.book_scene_planner import BookScenePlanner, Scene
from core.prompt_batch_service import PromptBatchService
from core.prompt_template_service import PromptTemplateService
from ui.components.character_selector import CharacterSelectorDialog
from core.character_service import CharacterService
from book_builder.container import Container
from book_builder.interfaces.core import IBookBuilder

class BookScenePlannerView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.engine = Container().resolve(IBookBuilder)
        self.planner = BookScenePlanner()
        self.batch_service = PromptBatchService(self.planner)
        self.template_service = PromptTemplateService()
        self.char_service = CharacterService()
        
        self.current_scene_id = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)
        
        self._build_sidebar()
        self._build_editor()
        
        self._refresh_scene_list()

    def load_project(self, project_id: str, name: str, state: dict):
        """Called by UI framework when switching projects."""
        self.planner = self.engine.get_scene_planner()
        self.batch_service = PromptBatchService(self.planner)
        self.current_scene_id = None
        self._set_editor_state("disabled")
        self._refresh_scene_list()

    def refresh_data(self):
        """Called by UI framework when navigating to this tab, ensuring state is synced with the active project."""
        project = self.engine.get_active_project()
        if project:
            self.load_project(str(project.id), project.name, {})
        else:
            self.planner = BookScenePlanner()
            self.batch_service = PromptBatchService(self.planner)
            self.current_scene_id = None
            self._set_editor_state("disabled")
            self._refresh_scene_list()
        
    def _persist_state(self):
        """Helper to save the current planner state to the active project."""
        self.engine.save_scene_planner(self.planner)

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.sidebar.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.sidebar, text="Book Scene Planner", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, pady=10, padx=10, sticky="w")
        
        # Scene List
        self.listbox_frame = ctk.CTkScrollableFrame(self.sidebar)
        self.listbox_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.scene_buttons = {}
        
        # List controls
        controls_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        controls_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkButton(controls_frame, text="Add Scene", command=self._add_scene).pack(fill="x", pady=2)
        ctk.CTkButton(controls_frame, text="Duplicate", command=self._duplicate_scene).pack(fill="x", pady=2)
        ctk.CTkButton(controls_frame, text="Move Up", command=self._move_up).pack(fill="x", pady=2)
        ctk.CTkButton(controls_frame, text="Move Down", command=self._move_down).pack(fill="x", pady=2)
        ctk.CTkButton(controls_frame, text="Delete", command=self._delete_scene, fg_color="#c0392b", hover_color="#e74c3c").pack(fill="x", pady=2)
        
        ctk.CTkButton(self.sidebar, text="Generate All Prompts", command=self._generate_all, fg_color="green").grid(row=3, column=0, padx=10, pady=(10, 20), sticky="ew")

    def _build_editor(self):
        self.editor = ctk.CTkScrollableFrame(self)
        self.editor.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # Header Info
        header_frame = ctk.CTkFrame(self.editor, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))
        
        self.page_lbl = ctk.CTkLabel(header_frame, text="No Scene Selected", font=ctk.CTkFont(size=18, weight="bold"))
        self.page_lbl.pack(side="left")
        
        self.status_lbl = ctk.CTkLabel(header_frame, text="", text_color="gray")
        self.status_lbl.pack(side="left", padx=10)
        
        # Guided Workflow Next Step
        next_step_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        next_step_frame.pack(side="right")
        btn = ctk.CTkButton(next_step_frame, text="Next Step: Production Pipeline", fg_color="green", hover_color="darkgreen",
                            command=lambda: self.master.master.select_frame("Production Pipeline"))
        btn.pack(side="right", padx=5)

        # Character Selection
        char_frame = ctk.CTkFrame(self.editor)
        char_frame.pack(fill="x", pady=5)
        self.char_lbl = ctk.CTkLabel(char_frame, text="No Character Selected")
        self.char_lbl.pack(side="left", padx=10, pady=10)
        ctk.CTkButton(char_frame, text="Select Character", command=self._select_character).pack(side="right", padx=10, pady=10)

        # Template Selection
        template_frame = ctk.CTkFrame(self.editor, fg_color="transparent")
        template_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(template_frame, text="Template:").pack(side="left", padx=(0, 10))
        
        templates = self.template_service.get_all_templates()
        self.template_var = ctk.StringVar(value=templates[0]["name"])
        self.template_menu = ctk.CTkOptionMenu(
            template_frame, 
            values=[t["name"] for t in templates],
            variable=self.template_var,
            command=self._on_template_selected
        )
        self.template_menu.pack(side="left", fill="x", expand=True)

        # Config Inputs
        self.controls = {}
        
        def add_input(label, key, options=None):
            frame = ctk.CTkFrame(self.editor, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            ctk.CTkLabel(frame, text=label, width=120, anchor="w").pack(side="left")
            if options is not None:
                var = ctk.StringVar()
                widget = ctk.CTkOptionMenu(frame, values=options, variable=var)
                widget.pack(side="left", fill="x", expand=True)
                self.controls[key] = var
            else:
                widget = ctk.CTkEntry(frame)
                widget.pack(side="left", fill="x", expand=True)
                self.controls[key] = widget

        add_input("View", "view", ["front", "left side", "right side", "back", "3/4 view", ""])
        add_input("Pose", "pose", ["standing", "sitting", "walking", "running", "waving", "reading", "dynamic action pose", "relaxed pose", ""])
        add_input("Expression", "expression", ["happy", "smiling", "surprised", "curious", "excited", "calm", ""])
        add_input("Action", "action")
        add_input("Location", "location", ["garden", "classroom", "bedroom", "park", "playground", "library", ""])
        add_input("Props", "props")
        add_input("Background", "background", ["simple white background", "detailed storybook background", "minimal background", ""])
        add_input("Composition", "composition", ["full body", "medium shot", "close-up portrait, centered", "centered character", ""])
        add_input("Style Rules", "style")

        # Save/Generate Actions
        action_frame = ctk.CTkFrame(self.editor, fg_color="transparent")
        action_frame.pack(fill="x", pady=20)
        ctk.CTkButton(action_frame, text="Save Changes", command=self._save_scene_config).pack(side="left", padx=5)
        ctk.CTkButton(action_frame, text="Generate Prompt", command=self._generate_single).pack(side="left", padx=5)

        # Preview Pane
        ctk.CTkLabel(self.editor, text="Main Prompt", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 0))
        self.main_prompt_text = ctk.CTkTextbox(self.editor, height=100)
        self.main_prompt_text.pack(fill="x", pady=5)
        ctk.CTkButton(self.editor, text="Copy Main", command=lambda: self._copy(self.main_prompt_text.get("1.0", "end-1c"))).pack(anchor="e")

        ctk.CTkLabel(self.editor, text="Negative Prompt", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 0))
        self.neg_prompt_text = ctk.CTkTextbox(self.editor, height=80)
        self.neg_prompt_text.pack(fill="x", pady=5)
        ctk.CTkButton(self.editor, text="Copy Negative", command=lambda: self._copy(self.neg_prompt_text.get("1.0", "end-1c"))).pack(anchor="e")

        self._set_editor_state("disabled")

    def _set_editor_state(self, state):
        for widget in self.controls.values():
            if hasattr(widget, "configure"):
                widget.configure(state=state)
        self.template_menu.configure(state=state)
        self.main_prompt_text.configure(state=state)
        self.neg_prompt_text.configure(state=state)

    def _refresh_scene_list(self):
        for child in self.listbox_frame.winfo_children():
            child.destroy()
            
        self.scene_buttons.clear()
        
        for scene in self.planner.scenes:
            char_name = "No Character"
            if scene.character_id:
                asset = self.char_service.asset_manager.get_asset(scene.character_id)
                if asset:
                    char_name = asset.character or asset.name
                    
            btn_text = f"Page {scene.page_number} ({char_name})"
            btn = ctk.CTkButton(
                self.listbox_frame, 
                text=btn_text,
                anchor="w",
                fg_color=("gray75", "gray25") if scene.id == self.current_scene_id else "transparent",
                text_color=("gray10", "gray90"),
                command=lambda sid=scene.id: self._select_scene(sid)
            )
            btn.pack(fill="x", pady=1)
            self.scene_buttons[scene.id] = btn

    def _select_scene(self, scene_id):
        self._save_scene_config() # save current before switching
        self.current_scene_id = scene_id
        self._refresh_scene_list()
        
        scene = self.planner.get_scene(scene_id)
        if not scene:
            return
            
        self._set_editor_state("normal")
        self.page_lbl.configure(text=f"Page {scene.page_number}")
        self.status_lbl.configure(text=scene.status)
        
        if scene.character_id:
            asset = self.char_service.asset_manager.get_asset(scene.character_id)
            if asset:
                self.char_lbl.configure(text=f"Selected: {asset.character or asset.name}")
        else:
            self.char_lbl.configure(text="No Character Selected")
            
        # Set template
        templates = self.template_service.get_all_templates()
        selected_t = next((t for t in templates if t["id"] == scene.template_id), templates[0])
        self.template_var.set(selected_t["name"])
        
        # Load config
        config = scene.config
        for k, widget in self.controls.items():
            val = config.get(k, "")
            if isinstance(widget, ctk.StringVar):
                widget.set(val)
            else:
                widget.delete(0, "end")
                widget.insert(0, val)
                
        # Load prompts
        self.main_prompt_text.delete("1.0", "end")
        self.main_prompt_text.insert("1.0", scene.main_prompt)
        
        self.neg_prompt_text.delete("1.0", "end")
        self.neg_prompt_text.insert("1.0", scene.negative_prompt)

    def _save_scene_config(self):
        if not self.current_scene_id:
            return
        scene = self.planner.get_scene(self.current_scene_id)
        if not scene:
            return
            
        for k, widget in self.controls.items():
            if isinstance(widget, ctk.StringVar):
                scene.config[k] = widget.get().strip()
            else:
                scene.config[k] = widget.get().strip()
        self._persist_state()

    def _add_scene(self):
        self._save_scene_config()
        page_num = len(self.planner.scenes) + 1
        new_scene = Scene(page_number=page_num)
        self.planner.add_scene(new_scene)
        self._persist_state()
        self._select_scene(new_scene.id)

    def _duplicate_scene(self):
        if self.current_scene_id:
            self._save_scene_config()
            self.planner.duplicate_scene(self.current_scene_id)
            self._persist_state()
            self._refresh_scene_list()

    def _delete_scene(self):
        if self.current_scene_id:
            self.planner.delete_scene(self.current_scene_id)
            self.current_scene_id = None
            self._persist_state()
            self._set_editor_state("disabled")
            self._refresh_scene_list()

    def _move_up(self):
        if self.current_scene_id:
            self._save_scene_config()
            self.planner.move_scene_up(self.current_scene_id)
            self._persist_state()
            self._refresh_scene_list()

    def _move_down(self):
        if self.current_scene_id:
            self._save_scene_config()
            self.planner.move_scene_down(self.current_scene_id)
            self._persist_state()
            self._refresh_scene_list()

    def _select_character(self):
        if not self.current_scene_id:
            return
        scene = self.planner.get_scene(self.current_scene_id)
        dialog = CharacterSelectorDialog(self)
        char = dialog.get_selected_character()
        if char and scene:
            scene.character_id = char.id
            self.char_lbl.configure(text=f"Selected: {char.character or char.name}")
            self._persist_state()
            self._refresh_scene_list()

    def _on_template_selected(self, template_name):
        if not self.current_scene_id:
            return
        scene = self.planner.get_scene(self.current_scene_id)
        
        templates = self.template_service.get_all_templates()
        selected = next((t for t in templates if t["name"] == template_name), templates[0])
        scene.template_id = selected["id"]
        
        defaults = selected["defaults"]
        
        for k in ["composition", "background", "action", "pose", "view", "style"]:
            if k in self.controls:
                widget = self.controls[k]
                val = defaults.get(k, "")
                if isinstance(widget, ctk.StringVar):
                    widget.set(val)
                else:
                    widget.delete(0, "end")
                    widget.insert(0, val)
                    
        for k in ["expression", "location", "props"]:
            if k in self.controls:
                widget = self.controls[k]
                if isinstance(widget, ctk.StringVar):
                    widget.set("")
                else:
                    widget.delete(0, "end")
                    
        self._save_scene_config()

    def _generate_single(self):
        if not self.current_scene_id:
            return
        self._save_scene_config()
        
        success = self.batch_service.generate_single_prompt(self.current_scene_id)
        self._persist_state()
        self._select_scene(self.current_scene_id) # reload ui
        
        if success:
            messagebox.showinfo("Success", "Prompt generated successfully.")
        else:
            messagebox.showwarning("Warning", "Failed to generate prompt. Ensure a character is selected.")

    def _generate_all(self):
        self._save_scene_config()
        if not self.planner.scenes:
            messagebox.showinfo("Info", "No scenes to generate.")
            return
            
        results = self.batch_service.generate_all_prompts()
        self._persist_state()
        
        success_count = sum(1 for r in results if "Success" in r["status"])
        msg = f"Generated {success_count} of {len(results)} prompts.\n\n"
        for r in results:
            msg += f"Page {r['page']}: {r['status']}\n"
            
        messagebox.showinfo("Batch Complete", msg)
        
        if self.current_scene_id:
            self._select_scene(self.current_scene_id)
        self._refresh_scene_list()

    def _copy(self, text):
        if text.strip():
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Copied", "Copied to clipboard!")
