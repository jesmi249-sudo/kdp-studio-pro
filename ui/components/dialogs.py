import customtkinter as ctk
from ui.theme.fonts import Fonts
from ui.theme.colors import Colors
from ui.theme.spacing import Spacing

class BaseDialog(ctk.CTkToplevel):
    def __init__(self, title, message, **kwargs):
        super().__init__(**kwargs)
        self.title(title)
        self.geometry("400x200")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        # Center on screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)
        
        # Content frame
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=0, sticky="nsew", padx=Spacing.L, pady=Spacing.L)
        
        self.msg_label = ctk.CTkLabel(self.content_frame, text=message, font=Fonts.body(), wraplength=350)
        self.msg_label.pack(expand=True)
        
        # Action frame
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent", height=50)
        self.action_frame.grid(row=1, column=0, sticky="ew", padx=Spacing.L, pady=(0, Spacing.L))

class Dialogs:
    @staticmethod
    def show_success(message):
        dlg = BaseDialog("Success", message)
        btn = ctk.CTkButton(dlg.action_frame, text="OK", command=dlg.destroy, fg_color=Colors.SUCCESS[0], hover_color=Colors.SUCCESS[1])
        btn.pack(side="right")
        
    @staticmethod
    def show_error(message):
        dlg = BaseDialog("Error", message)
        btn = ctk.CTkButton(dlg.action_frame, text="OK", command=dlg.destroy, fg_color=Colors.ERROR[0], hover_color=Colors.ERROR[1])
        btn.pack(side="right")
        
    @staticmethod
    def ask_confirm(title, message, callback):
        dlg = BaseDialog(title, message)
        
        def on_yes():
            dlg.destroy()
            callback(True)
            
        def on_no():
            dlg.destroy()
            callback(False)
            
        btn_yes = ctk.CTkButton(dlg.action_frame, text="Yes", command=on_yes, fg_color=Colors.PRIMARY[0])
        btn_yes.pack(side="right", padx=(Spacing.S, 0))
        
        btn_no = ctk.CTkButton(dlg.action_frame, text="No", command=on_no, fg_color="transparent", border_width=1)
        btn_no.pack(side="right")
