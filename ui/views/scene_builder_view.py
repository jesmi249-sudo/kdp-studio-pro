import customtkinter as ctk
from tkinter import messagebox
from ui.components.character_selector import CharacterSelectorDialog
from core.character_prompt_service import CharacterPromptService
from core.prompt_template_service import PromptTemplateService

class SceneBuilderView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.prompt_service = CharacterPromptService()
        self.template_service = PromptTemplateService()
        self.selected_character = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self._build_left_panel()
        self._build_right_panel()
        
    def _build_left_panel(self):
        left_panel = ctk.CTkScrollableFrame(self)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Header
        ctk.CTkLabel(left_panel, text="Scene Builder", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10, anchor="w")
        
        # Character Selection
        char_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        char_frame.pack(fill="x", pady=10)
        
        self.char_lbl = ctk.CTkLabel(char_frame, text="No Character Selected", text_color="gray")
        self.char_lbl.pack(side="left", padx=10)
        
        ctk.CTkButton(char_frame, text="Select Character", command=self._select_character).pack(side="right")
        
        # Template Selection
        ctk.CTkLabel(left_panel, text="Prompt Template").pack(anchor="w", pady=(10, 0))
        templates = self.template_service.get_all_templates()
        self.template_var = ctk.StringVar(value=templates[0]["name"])
        
        template_menu = ctk.CTkOptionMenu(
            left_panel, 
            values=[t["name"] for t in templates],
            variable=self.template_var,
            command=self._on_template_selected
        )
        template_menu.pack(fill="x", pady=5)
        
        # Controls Dictionary
        self.controls = {}
        
        def add_dropdown(label, key, values):
            ctk.CTkLabel(left_panel, text=label).pack(anchor="w", pady=(10, 0))
            var = ctk.StringVar(value=values[0] if values else "")
            menu = ctk.CTkOptionMenu(left_panel, values=values, variable=var)
            menu.pack(fill="x", pady=5)
            self.controls[key] = var
            return var
            
        def add_entry(label, key):
            ctk.CTkLabel(left_panel, text=label).pack(anchor="w", pady=(10, 0))
            entry = ctk.CTkEntry(left_panel)
            entry.pack(fill="x", pady=5)
            self.controls[key] = entry
            return entry
            
        def add_textbox(label, key, height=60):
            ctk.CTkLabel(left_panel, text=label).pack(anchor="w", pady=(10, 0))
            textbox = ctk.CTkTextbox(left_panel, height=height)
            textbox.pack(fill="x", pady=5)
            self.controls[key] = textbox
            return textbox
            
        self.view_var = add_dropdown("View", "view", ["front", "left side", "right side", "back", "3/4 view"])
        self.pose_var = add_dropdown("Pose", "pose", ["standing", "sitting", "walking", "running", "waving", "reading", "dynamic action pose", "relaxed pose", "active pose", "sitting or kneeling", ""])
        self.expr_var = add_dropdown("Expression", "expression", ["happy", "smiling", "surprised", "curious", "excited", "calm", ""])
        self.action_var = add_entry("Action (Free-text)", "action")
        self.location_var = add_dropdown("Location", "location", ["garden", "classroom", "bedroom", "park", "playground", "library", ""])
        self.props_var = add_entry("Props (Free-text)", "props")
        self.bg_var = add_dropdown("Background", "background", ["simple white background", "detailed storybook background", "minimal background", "white background with floating coloring items", ""])
        self.comp_var = add_dropdown("Composition", "composition", ["full body", "medium shot", "close-up portrait, centered", "centered character", "full scene, rule of thirds, character interacting with environment", ""])
        self.style_var = add_textbox("Coloring-page requirements", "style", height=80)
        
        # Action Buttons
        btn_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        
        ctk.CTkButton(btn_frame, text="Reset Fields", command=self._reset, fg_color="gray").pack(side="left")
        ctk.CTkButton(btn_frame, text="Generate Prompt", command=self._generate, fg_color="green").pack(side="right")
        
        # Load initial template
        self._on_template_selected(templates[0]["name"])

    def _build_right_panel(self):
        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(right_panel, text="Generated Prompt", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5), anchor="w", padx=10)
        
        self.prompt_text = ctk.CTkTextbox(right_panel, height=200)
        self.prompt_text.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(right_panel, text="Copy Prompt", command=lambda: self._copy(self.prompt_text.get("1.0", "end-1c"))).pack(anchor="e", padx=10, pady=5)
        
        ctk.CTkLabel(right_panel, text="Negative Prompt", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 5), anchor="w", padx=10)
        
        self.neg_prompt_text = ctk.CTkTextbox(right_panel, height=150)
        self.neg_prompt_text.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(right_panel, text="Copy Negative", command=lambda: self._copy(self.neg_prompt_text.get("1.0", "end-1c"))).pack(anchor="e", padx=10, pady=5)

    def _select_character(self):
        dialog = CharacterSelectorDialog(self)
        char = dialog.get_selected_character()
        if char:
            self.selected_character = char
            name = char.character or char.name
            self.char_lbl.configure(text=f"Selected: {name}", text_color="black")

    def _on_template_selected(self, template_name):
        templates = self.template_service.get_all_templates()
        selected = next((t for t in templates if t["name"] == template_name), templates[0])
        defaults = selected["defaults"]
        
        self._set_val(self.controls["composition"], defaults.get("composition", ""))
        self._set_val(self.controls["background"], defaults.get("background", ""))
        self._set_val(self.controls["action"], defaults.get("action", ""))
        self._set_val(self.controls["pose"], defaults.get("pose", ""))
        self._set_val(self.controls["view"], defaults.get("view", "front"))
        self._set_val(self.controls["style"], defaults.get("style", ""))
        
        # Clear others
        self._set_val(self.controls["expression"], "")
        self._set_val(self.controls["location"], "")
        self._set_val(self.controls["props"], "")
        
    def _set_val(self, widget, val):
        if isinstance(widget, ctk.CTkTextbox):
            widget.delete("1.0", "end")
            widget.insert("1.0", val)
        elif isinstance(widget, ctk.CTkEntry):
            widget.delete(0, "end")
            widget.insert(0, val)
        elif isinstance(widget, ctk.StringVar):
            # check if val in options, if not just set it
            widget.set(val)

    def _reset(self):
        self._on_template_selected(self.template_var.get())

    def _generate(self):
        if not self.selected_character:
            messagebox.showwarning("Warning", "Please select a character first.")
            return
            
        config = {}
        for k, widget in self.controls.items():
            if isinstance(widget, ctk.CTkTextbox):
                val = widget.get("1.0", "end-1c").strip()
            elif hasattr(widget, "get"):
                val = widget.get().strip()
            else:
                val = ""
            config[k] = val
            
        prompt, neg_prompt = self.prompt_service.generate_prompt(self.selected_character.id, config)
        
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", prompt)
        
        self.neg_prompt_text.delete("1.0", "end")
        self.neg_prompt_text.insert("1.0", neg_prompt)
        
    def _copy(self, text):
        if text.strip():
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Copied", "Copied to clipboard!")
