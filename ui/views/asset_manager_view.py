import customtkinter as ctk
import os
from tkinter import filedialog, messagebox
from PIL import Image
from core.asset_manager import AssetManager
from ui.components.responsive_grid import ResponsiveGrid
from ui.views.character_bible_view import CharacterBibleDialog

class AssetManagerView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._is_ready = False
        self.manager = AssetManager()
        self.current_category = "All"
        self.current_view = "Grid"
        
        self.search_var = ctk.StringVar()
        self.view_var = ctk.StringVar(value="Grid")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._build_sidebar()
        self._build_topbar()
        self._build_main_area()
        self._build_preview_panel()
        
        self._is_ready = True
        self.refresh_assets()
        
    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        
        ctk.CTkLabel(sidebar, text="Library", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20, padx=20, anchor="w")
        
        categories = ["All", "Favorites", "Characters", "Poses", "Expressions", "Outfits", "Backgrounds", "Decorations", "Scenes", "Coloring Artwork"]
        
        self.cat_buttons = {}
        for cat in categories:
            btn = ctk.CTkButton(sidebar, text=cat, fg_color="transparent", text_color=("gray10", "gray90"), anchor="w",
                                command=lambda c=cat: self.select_category(c))
            btn.pack(fill="x", padx=10, pady=2)
            self.cat_buttons[cat] = btn
            
        self.select_category("All")
        
    def select_category(self, cat):
        self.current_category = cat
        for c, btn in self.cat_buttons.items():
            btn.configure(fg_color=("gray75", "gray25") if c == cat else "transparent")
        self.refresh_assets()

    def _build_topbar(self):
        topbar = ctk.CTkFrame(self, height=60, corner_radius=0)
        topbar.grid(row=0, column=1, columnspan=2, sticky="ew")
        
        self.char_filter_var = ctk.StringVar()
        
        search_entry = ctk.CTkEntry(topbar, textvariable=self.search_var, placeholder_text="Search assets...", width=200)
        search_entry.pack(side="left", padx=10, pady=15)
        search_entry.bind("<Return>", lambda e: self.refresh_assets())
        
        char_entry = ctk.CTkEntry(topbar, textvariable=self.char_filter_var, placeholder_text="Filter by Character...", width=150)
        char_entry.pack(side="left", padx=10, pady=15)
        char_entry.bind("<Return>", lambda e: self.refresh_assets())
        
        ctk.CTkButton(topbar, text="Search", command=self.refresh_assets, width=80).pack(side="left")
        
        ctk.CTkButton(topbar, text="Import Asset", command=self.import_asset, fg_color="green", hover_color="darkgreen").pack(side="right", padx=20, pady=15)
        
        view_menu = ctk.CTkOptionMenu(topbar, values=["Grid", "List"], variable=self.view_var, command=self.toggle_view, width=100)
        view_menu.pack(side="right", padx=10, pady=15)

    def _build_main_area(self):
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(0, weight=1)
        
        self.grid_view = ResponsiveGrid(self.main_area)
        self.list_view = ctk.CTkScrollableFrame(self.main_area)
        
        self.toggle_view(self.view_var.get())
        
        # Guided Workflow Next Step
        next_step_frame = ctk.CTkFrame(self.main_area, fg_color="#2b2b2b", corner_radius=8)
        next_step_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        ctk.CTkLabel(next_step_frame, text="Characters created?").pack(side="left", padx=15, pady=10)
        btn = ctk.CTkButton(next_step_frame, text="Next Step: Plan Scenes", fg_color="green", hover_color="darkgreen",
                            command=lambda: self.master.master.select_frame("Book Scene Planner"))
        btn.pack(side="right", padx=15, pady=10)

    def _build_preview_panel(self):
        self.preview_panel = ctk.CTkFrame(self, width=300)
        self.preview_panel.grid(row=1, column=2, sticky="nsew", padx=(0, 10), pady=10)
        self.preview_panel.grid_columnconfigure(0, weight=1)
        
        self.preview_lbl = ctk.CTkLabel(self.preview_panel, text="No Selection")
        self.preview_lbl.pack(pady=20)
        
        self.details_txt = ctk.CTkTextbox(self.preview_panel, height=200, fg_color="transparent")
        self.details_txt.pack(fill="x", padx=10, pady=10)
        
        # Action Buttons
        self.action_frame = ctk.CTkFrame(self.preview_panel, fg_color="transparent")
        
        self.fav_btn = ctk.CTkButton(self.action_frame, text="Favorite", command=self.toggle_favorite)
        self.fav_btn.pack(fill="x", pady=5)
        
        self.edit_btn = ctk.CTkButton(self.action_frame, text="Edit Metadata", command=self.edit_metadata)
        self.edit_btn.pack(fill="x", pady=5)
        
        self.bible_btn = ctk.CTkButton(self.action_frame, text="Character Bible", command=self.open_character_bible, fg_color="#8A2BE2", hover_color="#551A8B")
        # Pack dynamically based on category
        
        self.del_btn = ctk.CTkButton(self.action_frame, text="Delete", command=self.delete_asset, fg_color="red", hover_color="darkred")
        self.del_btn.pack(fill="x", pady=5)
        
        self.selected_asset = None

    def toggle_view(self, view_type):
        self.current_view = view_type
        if view_type == "Grid":
            self.list_view.grid_remove()
            self.grid_view.grid(row=0, column=0, sticky="nsew")
        else:
            self.grid_view.grid_remove()
            self.list_view.grid(row=0, column=0, sticky="nsew")
        self.refresh_assets()

    def import_asset(self):
        path = filedialog.askopenfilename()
        if path:
            cat = self.current_category if self.current_category not in ["All", "Favorites"] else "Characters"
            asset = self.manager.import_asset(path, cat)
            if asset:
                messagebox.showinfo("Success", f"Imported {asset.name}")
                self.refresh_assets()
            else:
                messagebox.showerror("Error", "Failed to import asset.")

    def refresh_assets(self):
        if not getattr(self, '_is_ready', False):
            return
            
        is_fav = (self.current_category == "Favorites")
        cat = "All" if self.current_category in ["All", "Favorites"] else self.current_category
        
        assets = self.manager.get_all_assets(category=cat, search_query=self.search_var.get(), favorites_only=is_fav, character_filter=self.char_filter_var.get())
        
        self.grid_view.clear()
        for widget in self.list_view.winfo_children():
            widget.destroy()
            
        for asset in assets:
            self._create_asset_widget(asset)

    def _create_asset_widget(self, asset):
        # We need to hold image references to prevent GC
        if not hasattr(self, "images"): self.images = {}
        
        img = None
        if asset.thumbnail_path and os.path.exists(asset.thumbnail_path):
            try:
                pil_img = Image.open(asset.thumbnail_path)
                img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(120, 120))
                self.images[asset.id] = img
            except Exception:
                pass
                
        if self.current_view == "Grid":
            card = ctk.CTkFrame(self.grid_view, width=140, height=180)
            lbl = ctk.CTkLabel(card, text="", image=img if img else None)
            lbl.pack(pady=5)
            name_lbl = ctk.CTkLabel(card, text=asset.name[:15] + "..." if len(asset.name)>15 else asset.name)
            name_lbl.pack()
            
            # Bind clicks
            lbl.bind("<Button-1>", lambda e, a=asset: self.select_asset(a))
            name_lbl.bind("<Button-1>", lambda e, a=asset: self.select_asset(a))
            card.bind("<Button-1>", lambda e, a=asset: self.select_asset(a))
            
            self.grid_view.add_item(card)
        else:
            row = ctk.CTkFrame(self.list_view)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=asset.name, width=200, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=asset.category, width=100, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=asset.file_size, width=100, anchor="w").pack(side="left", padx=10)
            
            row.bind("<Button-1>", lambda e, a=asset: self.select_asset(a))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, a=asset: self.select_asset(a))

    def select_asset(self, asset):
        self.selected_asset = asset
        self.action_frame.pack(fill="x", padx=10, pady=10)
        
        # Repack buttons to ensure correct order
        self.fav_btn.pack_forget()
        self.edit_btn.pack_forget()
        self.bible_btn.pack_forget()
        self.del_btn.pack_forget()
        
        self.fav_btn.pack(fill="x", pady=5)
        self.edit_btn.pack(fill="x", pady=5)
        if asset.category == "Characters":
            self.bible_btn.pack(fill="x", pady=5)
        self.del_btn.pack(fill="x", pady=5)
        
        if asset.thumbnail_path and os.path.exists(asset.thumbnail_path):
            pil_img = Image.open(asset.thumbnail_path)
            img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(200, 200))
            self.preview_lbl.configure(image=img, text="")
            self.images['preview'] = img
        else:
            self.preview_lbl.configure(image="", text="No Preview")
            
        self.details_txt.delete("1.0", "end")
        details = f"Name: {asset.name}\n"
        details += f"Category: {asset.category}\n"
        details += f"Project ID: {asset.project_id or 'None'}\n"
        details += f"Character: {asset.character or 'N/A'}\n"
        details += f"Pose: {asset.pose or 'N/A'}\n"
        details += f"Expression: {asset.expression or 'N/A'}\n"
        details += f"Outfit: {asset.outfit or 'N/A'}\n"
        details += f"Scene: {asset.scene or 'N/A'}\n"
        details += f"Status: {asset.status or 'N/A'}\n"
        details += f"Type: {asset.file_type}\n"
        details += f"Size: {asset.file_size} bytes\n"
        details += f"Dimensions: {asset.dimensions}\n"
        details += f"DPI: {asset.dpi}\n"
        self.details_txt.insert("1.0", details)
        
        self.fav_btn.configure(text="Unfavorite" if asset.is_favorite else "Favorite")

    def toggle_favorite(self):
        if self.selected_asset:
            new_status = not self.selected_asset.is_favorite
            self.manager.toggle_favorite(self.selected_asset.id, new_status)
            self.refresh_assets()
            self.select_asset(self.manager.get_asset(self.selected_asset.id)) # Reload selection

    def delete_asset(self):
        if self.selected_asset:
            if messagebox.askyesno("Confirm", f"Delete {self.selected_asset.name}?"):
                self.manager.delete_asset(self.selected_asset.id)
                self.selected_asset = None
                self.action_frame.pack_forget()
                self.details_txt.delete("1.0", "end")
                self.refresh_assets()

    def edit_metadata(self):
        if not self.selected_asset:
            return
            
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Metadata")
        dialog.geometry("400x500")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        fields = {}
        row = 0
        
        for field, current_val in [
            ("name", self.selected_asset.name),
            ("project_id", self.selected_asset.project_id or ""),
            ("character", self.selected_asset.character or ""),
            ("pose", self.selected_asset.pose or ""),
            ("expression", self.selected_asset.expression or ""),
            ("outfit", self.selected_asset.outfit or ""),
            ("scene", self.selected_asset.scene or ""),
            ("status", self.selected_asset.status or "")
        ]:
            ctk.CTkLabel(dialog, text=field.capitalize()).grid(row=row, column=0, padx=10, pady=5, sticky="e")
            entry = ctk.CTkEntry(dialog, width=200)
            entry.insert(0, str(current_val))
            entry.grid(row=row, column=1, padx=10, pady=5, sticky="w")
            fields[field] = entry
            row += 1
            
        def save():
            try:
                pid_val = fields["project_id"].get().strip()
                pid = int(pid_val) if pid_val else None
                
                self.manager.update_metadata(
                    self.selected_asset.id,
                    name=fields["name"].get().strip(),
                    project_id=pid,
                    character=fields["character"].get().strip() or None,
                    pose=fields["pose"].get().strip() or None,
                    expression=fields["expression"].get().strip() or None,
                    outfit=fields["outfit"].get().strip() or None,
                    scene=fields["scene"].get().strip() or None,
                    status=fields["status"].get().strip() or None
                )
                dialog.destroy()
                self.refresh_assets()
                self.select_asset(self.manager.get_asset(self.selected_asset.id))
            except ValueError:
                messagebox.showerror("Error", "Project ID must be a number.", parent=dialog)
                
        ctk.CTkButton(dialog, text="Save", command=save, fg_color="green").grid(row=row, column=0, columnspan=2, pady=20)

    def open_character_bible(self):
        if not self.selected_asset or self.selected_asset.category != "Characters":
            return
            
        def on_save(asset_id, **kwargs):
            self.manager.update_metadata(asset_id, **kwargs)
            self.refresh_assets()
            self.select_asset(self.manager.get_asset(asset_id))
            
        dialog = CharacterBibleDialog(self, self.selected_asset, on_save)
