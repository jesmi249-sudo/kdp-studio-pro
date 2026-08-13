import customtkinter as ctk
from ui.theme.fonts import Fonts
from ui.theme.colors import Colors

class SplashScreen(ctk.CTkToplevel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title("Starting KDP Studio Pro")
        self.geometry("600x400")
        self.overrideredirect(True) # Remove window decorations
        self.attributes("-topmost", True)
        
        # Center on screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
        
        # Background
        self.configure(fg_color=Colors.BG_MAIN[1]) # Default dark
        
        # Content
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)
        
        # Logo/Title
        title_lbl = ctk.CTkLabel(self, text="KDP Studio Pro", font=Fonts.heading1())
        title_lbl.pack(pady=(100, 10))
        
        version_lbl = ctk.CTkLabel(self, text="v2.0", font=Fonts.body_bold(), text_color=Colors.TEXT_MUTED[1])
        version_lbl.pack(pady=5)
        
        # Status & Progress
        self.status_var = ctk.StringVar(value="Initializing...")
        status_lbl = ctk.CTkLabel(self, textvariable=self.status_var, font=Fonts.small())
        status_lbl.pack(side="bottom", pady=(5, 30))
        
        self.progress = ctk.CTkProgressBar(self, width=400, height=4)
        self.progress.set(0)
        self.progress.pack(side="bottom", pady=10)
        
    def update_progress(self, value, text):
        self.progress.set(value)
        self.status_var.set(text)
        self.update()
