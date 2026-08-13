import customtkinter as ctk
from tkinter import messagebox
from ui.components.character_selector import CharacterSelectorDialog
from core.character_prompt_service import CharacterPromptService

class PromptGeneratorView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.service = CharacterPromptService()
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
        ctk.CTkLabel(left_panel, text="Prompt Generator", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10, anchor="w")
        
        # Character Selection
        char_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        char_frame.pack(fill="x", pady=10)
        
        self.char_lbl = ctk.CTkLabel(char_frame, text="No Character Selected", text_color="gray")
        self.char_lbl.pack(side="left", padx=10)
        
        ctk.CTkButton(char_frame, text="Select Character", command=self._select_character).pack(side="right")
        
        # Inputs
        self.inputs = {}
        
        def add_input(label_text, key, placeholder="", is_textbox=False):
            ctk.CTkLabel(left_panel, text=label_text).pack(anchor="w", pady=(10, 0))
            if is_textbox:
                widget = ctk.CTkTextbox(left_panel, height=60)
                widget.insert("1.0", placeholder)
            else:
                widget = ctk.CTkEntry(left_panel, placeholder_text=placeholder)
            widget.pack(fill="x", pady=5)
            self.inputs[key] = widget
            
        add_input("Scene Description", "scene_description", "e.g., walking through a magical forest", is_textbox=True)
        add_input("Background", "background", "e.g., tall trees, glowing mushrooms")
        add_input("Action", "action", "e.g., holding a lantern")
        add_input("Mood", "mood", "e.g., mysterious, peaceful")
        add_input("Camera/View", "camera", "e.g., front view, full body, cinematic lighting")
        add_input("Composition", "composition", "e.g., centered, rule of thirds")
        add_input("Pose Override", "pose", "e.g., looking up (leave blank to use character default)")
        add_input("Expression Override", "expression", "e.g., smiling (leave blank to use character default)")
        add_input("Outfit Override", "outfit", "e.g., winter coat (leave blank to use character default)")
        add_input("Style", "style", "line art, coloring book page, black and white, clean lines, no shading")
        
        ctk.CTkButton(left_panel, text="Generate Prompt", command=self._generate, fg_color="green").pack(pady=20, fill="x")
        
    def _build_right_panel(self):
        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(right_panel, text="Generated Prompt", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5), anchor="w", padx=10)
        
        self.prompt_text = ctk.CTkTextbox(right_panel, height=150)
        self.prompt_text.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(right_panel, text="Copy Prompt", command=lambda: self._copy(self.prompt_text.get("1.0", "end-1c"))).pack(anchor="e", padx=10, pady=5)
        
        ctk.CTkLabel(right_panel, text="Negative Prompt", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 5), anchor="w", padx=10)
        
        self.neg_prompt_text = ctk.CTkTextbox(right_panel, height=100)
        self.neg_prompt_text.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(right_panel, text="Copy Negative", command=lambda: self._copy(self.neg_prompt_text.get("1.0", "end-1c"))).pack(anchor="e", padx=10, pady=5)

    def _select_character(self):
        dialog = CharacterSelectorDialog(self)
        char = dialog.get_selected_character()
        if char:
            self.selected_character = char
            name = char.character or char.name
            self.char_lbl.configure(text=f"Selected: {name}", text_color="black")
            
    def _generate(self):
        if not self.selected_character:
            messagebox.showwarning("Warning", "Please select a character first.")
            return
            
        config = {}
        for k, widget in self.inputs.items():
            if isinstance(widget, ctk.CTkTextbox):
                val = widget.get("1.0", "end-1c").strip()
            else:
                val = widget.get().strip()
            config[k] = val
            
        prompt, neg_prompt = self.service.generate_prompt(self.selected_character.id, config)
        
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", prompt)
        
        self.neg_prompt_text.delete("1.0", "end")
        self.neg_prompt_text.insert("1.0", neg_prompt)
        
    def _copy(self, text):
        if text.strip():
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Copied", "Copied to clipboard!")
