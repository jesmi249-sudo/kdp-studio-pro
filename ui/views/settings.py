import customtkinter as ctk
from ui.theme.theme_manager import ThemeManager

class SettingsView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        self.theme_switch = ctk.CTkSwitch(self, text="Dark Mode", command=self.toggle_theme)
        self.theme_switch.grid(row=1, column=0, padx=20, pady=20, sticky="w")
        
        # Set initial state
        current_mode = ctk.get_appearance_mode().lower()
        if current_mode == "dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()

    def toggle_theme(self):
        new_mode = ThemeManager.toggle_theme()
        if new_mode == "dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
