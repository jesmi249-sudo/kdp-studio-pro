import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Dict, Any, Callable, Optional

from book_builder.models.export import ExportProfile
from book_builder.models.book import BookProject
from ui.theme.fonts import Fonts
from ui.theme.colors import Colors
from ui.theme.spacing import Spacing

class ExportSettingsDialog(ctk.CTkToplevel):
    """
    Settings configuration dialog allowing users to adjust resolution, color spaces,
    bleed margins, compression factors, and output naming templates.
    """
    
    def __init__(self, parent: Any, project: BookProject, current_profile: Optional[ExportProfile] = None, on_save_callback: Optional[Callable[[ExportProfile], None]] = None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.project = project
        self.on_save = on_save_callback
        
        # Load or create profile
        self.profile = current_profile or (project.export_profiles[0] if project.export_profiles else ExportProfile())
        
        self.title("KDP Production Export Settings")
        self.geometry("550x650")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set() # Modal dialog behaviour
        
        # Center dialog
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")
        
        self._build_ui()
        self._load_profile_data()

    def _build_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)
        
        # Scrollable configuration area
        scroll = ctk.CTkScrollableFrame(self)
        scroll.grid(row=0, column=0, sticky="nsew", padx=Spacing.M, pady=Spacing.M)
        scroll.grid_columnconfigure(1, weight=1)
        
        # 1. Profile Name
        ctk.CTkLabel(scroll, text="Profile Presets Name:", font=Fonts.body_bold()).grid(row=0, column=0, sticky="w", pady=10)
        self.name_var = ctk.StringVar(value=self.profile.profile_name)
        ctk.CTkEntry(scroll, textvariable=self.name_var).grid(row=0, column=1, sticky="ew", padx=10)
        
        # 2. Output Format
        ctk.CTkLabel(scroll, text="Output Document Format:", font=Fonts.body_bold()).grid(row=1, column=0, sticky="w", pady=10)
        self.format_var = ctk.StringVar()
        self.format_menu = ctk.CTkOptionMenu(scroll, variable=self.format_var, values=[
            "KDP Interior PDF",
            "KDP Cover PDF",
            "Preview PDF",
            "ZIP Package",
            "PNG Image Sequence",
            "JPEG Image Sequence",
            "SVG Vector Sheets"
        ])
        self.format_menu.grid(row=1, column=1, sticky="ew", padx=10)
        
        # 3. DPI / Resolution
        ctk.CTkLabel(scroll, text="Output Resolution (DPI):", font=Fonts.body_bold()).grid(row=2, column=0, sticky="w", pady=10)
        self.dpi_var = ctk.StringVar()
        self.dpi_menu = ctk.CTkOptionMenu(scroll, variable=self.dpi_var, values=["72", "150", "300", "600"])
        self.dpi_menu.grid(row=2, column=1, sticky="ew", padx=10)
        
        # 4. Color Mode
        ctk.CTkLabel(scroll, text="Target Color Space:", font=Fonts.body_bold()).grid(row=3, column=0, sticky="w", pady=10)
        self.color_var = ctk.StringVar()
        self.color_menu = ctk.CTkOptionMenu(scroll, variable=self.color_var, values=["CMYK", "RGB", "Grayscale"])
        self.color_menu.grid(row=3, column=1, sticky="ew", padx=10)
        
        # 5. Bleed Option
        ctk.CTkLabel(scroll, text="Bleed Options:", font=Fonts.body_bold()).grid(row=4, column=0, sticky="w", pady=10)
        self.bleed_var = ctk.StringVar()
        self.bleed_menu = ctk.CTkOptionMenu(scroll, variable=self.bleed_var, values=["Bleed", "No Bleed"])
        self.bleed_menu.grid(row=4, column=1, sticky="ew", padx=10)
        
        # 6. Crop Marks Checkbox
        self.crop_var = ctk.BooleanVar(value=self.profile.include_crop_marks)
        self.crop_chk = ctk.CTkCheckBox(scroll, text="Include Crop Marks & Alignments", variable=self.crop_var)
        self.crop_chk.grid(row=5, column=0, columnspan=2, sticky="w", pady=15)
        
        # 7. Compression Factor Slider
        ctk.CTkLabel(scroll, text="Compression Factor (Quality):", font=Fonts.body_bold()).grid(row=6, column=0, sticky="w", pady=10)
        self.compress_lbl = ctk.CTkLabel(scroll, text="80%")
        self.compress_lbl.grid(row=6, column=1, sticky="e", padx=10)
        
        self.compress_var = ctk.DoubleVar(value=self.profile.compression_level)
        self.compress_slider = ctk.CTkSlider(scroll, from_=0.1, to=1.0, variable=self.compress_var, command=self._update_compress_label)
        self.compress_slider.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # 8. Output Directory
        ctk.CTkLabel(scroll, text="Target Destination Folder:", font=Fonts.body_bold()).grid(row=8, column=0, columnspan=2, sticky="w", pady=(15, 5))
        
        dir_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        dir_frame.grid(row=9, column=0, columnspan=2, sticky="ew")
        dir_frame.grid_columnconfigure(0, weight=1)
        
        self.dir_var = ctk.StringVar()
        ctk.CTkEntry(dir_frame, textvariable=self.dir_var).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(dir_frame, text="Browse", width=80, command=self._browse_folder).grid(row=0, column=1)
        
        # 9. Naming Templates
        ctk.CTkLabel(scroll, text="File Naming Template:", font=Fonts.body_bold()).grid(row=10, column=0, columnspan=2, sticky="w", pady=(15, 5))
        self.naming_var = ctk.StringVar()
        ctk.CTkEntry(scroll, textvariable=self.naming_var).grid(row=11, column=0, columnspan=2, sticky="ew", pady=5)
        
        hint = "Placeholders: {project_name}, {timestamp}, {page_number}, {dpi}, {format}, {color_mode}"
        ctk.CTkLabel(scroll, text=hint, font=Fonts.small(), text_color="gray").grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        # Actions Panel
        act_frame = ctk.CTkFrame(self, height=60, fg_color="transparent")
        act_frame.grid(row=1, column=0, sticky="ew", padx=Spacing.M, pady=(0, Spacing.M))
        
        ctk.CTkButton(act_frame, text="Save Preset Profile", fg_color=Colors.SUCCESS[0], hover_color=Colors.SUCCESS[1], command=self._save_profile).pack(side="right", padx=(Spacing.S, 0))
        ctk.CTkButton(act_frame, text="Cancel", fg_color="transparent", border_width=1, command=self.destroy).pack(side="right")

    def _update_compress_label(self, val: float) -> None:
        self.compress_lbl.configure(text=f"{int(val * 100)}%")

    def _browse_folder(self) -> None:
        d = filedialog.askdirectory(parent=self)
        if d:
            self.dir_var.set(d)

    def _load_profile_data(self) -> None:
        # Map values back to UI
        format_map = {
            "KDP_PDF": "KDP Interior PDF",
            "COVER_PDF": "KDP Cover PDF",
            "PREVIEW_PDF": "Preview PDF",
            "ZIP": "ZIP Package",
            "PNG": "PNG Image Sequence",
            "JPEG": "JPEG Image Sequence",
            "SVG": "SVG Vector Sheets"
        }
        self.format_var.set(format_map.get(self.profile.export_format, "KDP Interior PDF"))
        self.dpi_var.set(str(self.profile.dpi))
        self.color_var.set(self.profile.color_space)
        
        bleed = self.profile.custom_options.get("bleed_option", "Bleed" if self.project.has_bleed else "No Bleed")
        self.bleed_var.set(bleed)
        
        default_dir = os.path.join(os.path.expanduser("~"), "Documents", "Books")
        self.dir_var.set(self.profile.custom_options.get("output_folder", default_dir))
        
        self.naming_var.set(self.profile.custom_options.get("naming_template", "{project_name}_interior_{timestamp}"))
        self._update_compress_label(self.profile.compression_level)

    def _save_profile(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Profile name cannot be empty.")
            return
            
        # Map values back to profile model
        format_map = {
            "KDP Interior PDF": "KDP_PDF",
            "KDP Cover PDF": "COVER_PDF",
            "Preview PDF": "PREVIEW_PDF",
            "ZIP Package": "ZIP",
            "PNG Image Sequence": "PNG",
            "JPEG Image Sequence": "JPEG",
            "SVG Vector Sheets": "SVG"
        }
        
        self.profile.profile_name = name
        self.profile.export_format = format_map.get(self.format_var.get(), "KDP_PDF")
        self.profile.dpi = int(self.dpi_var.get())
        self.profile.color_space = self.color_var.get()
        self.profile.include_crop_marks = self.crop_var.get()
        self.profile.compression_level = float(self.compress_slider.get())
        
        # Save custom options dictionary
        self.profile.custom_options = {
            "output_folder": self.dir_var.get(),
            "naming_template": self.naming_var.get(),
            "bleed_option": self.bleed_var.get()
        }
        
        # Add to project lists if not already present
        if self.profile not in self.project.export_profiles:
            # Check if name already exists
            existing = [p for p in self.project.export_profiles if p.profile_name == name]
            if existing:
                self.project.export_profiles.remove(existing[0])
            self.project.export_profiles.append(self.profile)
            
        # Save project using DB repository
        from book_builder.repository import ProjectRepository
        ProjectRepository.save(self.project)
        
        if self.on_save:
            self.on_save(self.profile)
            
        self.destroy()
