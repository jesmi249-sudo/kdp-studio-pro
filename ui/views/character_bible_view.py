import customtkinter as ctk
from core.character_service import CharacterService

class CharacterBibleDialog(ctk.CTkToplevel):
    def __init__(self, master, asset, on_save_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.title(f"Character Bible - {asset.character or asset.name}")
        self.geometry("500x600")
        self.transient(master.winfo_toplevel())
        self.grab_set()
        
        self.asset = asset
        self.on_save_callback = on_save_callback
        self.service = CharacterService()
        
        self._build_ui()
        
    def _build_ui(self):
        # Header
        ctk.CTkLabel(self, text="Character Bible", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        
        # Form frame
        form = ctk.CTkScrollableFrame(self)
        form.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Name
        ctk.CTkLabel(form, text="Character Name:").pack(anchor="w", pady=(10, 0))
        self.name_entry = ctk.CTkEntry(form, width=300)
        self.name_entry.insert(0, self.asset.character or self.asset.name)
        self.name_entry.pack(anchor="w", pady=5)
        
        # Visual Identity (mapped to tags)
        ctk.CTkLabel(form, text="Visual Identity (Description, Age, Hair, etc):").pack(anchor="w", pady=(10, 0))
        self.visual_entry = ctk.CTkTextbox(form, height=60, width=400)
        self.visual_entry.insert("1.0", self.asset.tags or "")
        self.visual_entry.pack(anchor="w", pady=5)
        
        # Clothing (mapped to outfit)
        ctk.CTkLabel(form, text="Clothing & Accessories:").pack(anchor="w", pady=(10, 0))
        self.clothing_entry = ctk.CTkTextbox(form, height=60, width=400)
        self.clothing_entry.insert("1.0", self.asset.outfit or "")
        self.clothing_entry.pack(anchor="w", pady=5)
        
        # Expression/Personality
        ctk.CTkLabel(form, text="Personality / Expressions:").pack(anchor="w", pady=(10, 0))
        self.expr_entry = ctk.CTkTextbox(form, height=60, width=400)
        self.expr_entry.insert("1.0", self.asset.expression or "")
        self.expr_entry.pack(anchor="w", pady=5)
        
        # Pose
        ctk.CTkLabel(form, text="Pose / Posture:").pack(anchor="w", pady=(10, 0))
        self.pose_entry = ctk.CTkTextbox(form, height=60, width=400)
        self.pose_entry.insert("1.0", self.asset.pose or "")
        self.pose_entry.pack(anchor="w", pady=5)
        
        # Consistency (mapped to status)
        ctk.CTkLabel(form, text="Consistency Rules:").pack(anchor="w", pady=(10, 0))
        self.status_entry = ctk.CTkTextbox(form, height=60, width=400)
        self.status_entry.insert("1.0", self.asset.status or "")
        self.status_entry.pack(anchor="w", pady=5)
        
        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", pady=10, padx=20)
        
        ctk.CTkButton(footer, text="Cancel", command=self.destroy, fg_color="gray").pack(side="left")
        ctk.CTkButton(footer, text="Save to Bible", command=self._save, fg_color="green").pack(side="right")
        
    def _save(self):
        # We use the callback to actually invoke the manager's update method
        # This keeps database interactions in the asset manager.
        self.on_save_callback(
            self.asset.id,
            character=self.name_entry.get().strip() or None,
            tags=self.visual_entry.get("1.0", "end-1c").strip() or None,
            outfit=self.clothing_entry.get("1.0", "end-1c").strip() or None,
            expression=self.expr_entry.get("1.0", "end-1c").strip() or None,
            pose=self.pose_entry.get("1.0", "end-1c").strip() or None,
            status=self.status_entry.get("1.0", "end-1c").strip() or None
        )
        self.destroy()
