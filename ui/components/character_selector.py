import customtkinter as ctk
import os
from PIL import Image
from core.character_service import CharacterService

class CharacterSelectorDialog(ctk.CTkToplevel):
    """Reusable component for future studios to select a character from the Asset Library."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Select Character")
        self.geometry("600x400")
        self.transient(master.winfo_toplevel())
        self.grab_set()
        
        self.service = CharacterService()
        self.selected_asset = None
        self.images = {}
        
        self._build_ui()
        self._load_characters()
        
    def _build_ui(self):
        # Header
        ctk.CTkLabel(self, text="Select a Character", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        # Grid area
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", pady=10, padx=20)
        
        ctk.CTkButton(footer, text="Cancel", command=self.destroy, fg_color="gray").pack(side="left")
        
    def _load_characters(self):
        characters = self.service.get_primary_characters()
        
        if not characters:
            ctk.CTkLabel(self.scroll_frame, text="No characters found in Asset Library.", text_color="gray").pack(pady=50)
            return
            
        row, col = 0, 0
        for asset in characters:
            card = self._create_card(asset)
            card.grid(row=row, column=col, padx=10, pady=10)
            col += 1
            if col > 3:
                col = 0
                row += 1
                
    def _create_card(self, asset):
        card = ctk.CTkFrame(self.scroll_frame, width=120, height=150)
        
        img = None
        if asset.thumbnail_path and os.path.exists(asset.thumbnail_path):
            try:
                pil_img = Image.open(asset.thumbnail_path)
                img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(100, 100))
                self.images[asset.id] = img
            except Exception:
                pass
                
        lbl = ctk.CTkLabel(card, text="", image=img if img else None)
        lbl.pack(pady=5)
        
        name = asset.character or asset.name
        name_lbl = ctk.CTkLabel(card, text=name[:15] + "..." if len(name)>15 else name)
        name_lbl.pack()
        
        # Bind clicks to selection
        for widget in [card, lbl, name_lbl]:
            widget.bind("<Button-1>", lambda e, a=asset: self._on_select(a))
            
        return card
        
    def _on_select(self, asset):
        self.selected_asset = asset
        self.destroy()

    def get_selected_character(self):
        self.wait_window()
        return self.selected_asset
