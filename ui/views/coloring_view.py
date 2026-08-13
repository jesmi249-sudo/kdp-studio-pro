import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import os
from generators.coloring_generator import ColoringGenerator
from core.logger import get_logger

logger = get_logger(__name__)

class ColoringView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.generator = ColoringGenerator()
        
        # Grid layout: 1 col for controls (left), 1 col for preview (right)
        self.grid_columnconfigure(0, weight=1, minsize=300)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)
        
        self._build_controls_panel()
        self._build_preview_panel()
        
        self.original_image_path = None
        self.preview_size = (400, 400) # Max preview size
        
    def _build_controls_panel(self):
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        title = ctk.CTkLabel(ctrl_frame, text="Coloring Book Generator", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=15, padx=10)
        
        # Import
        self.btn_import = ctk.CTkButton(ctrl_frame, text="Import Image", command=self.import_image)
        self.btn_import.pack(pady=10, padx=20, fill="x")
        
        # Sliders
        self.brightness_slider, self.brightness_lbl = self._create_slider(ctrl_frame, "Brightness", -100, 100, 0)
        self.contrast_slider, self.contrast_lbl = self._create_slider(ctrl_frame, "Contrast", 0.1, 3.0, 1.0)
        self.threshold_block_slider, self.thresh_b_lbl = self._create_slider(ctrl_frame, "Threshold Block Size", 3, 51, 11)
        self.threshold_c_slider, self.thresh_c_lbl = self._create_slider(ctrl_frame, "Threshold C", -10, 10, 2)
        self.morph_slider, self.morph_lbl = self._create_slider(ctrl_frame, "Line Thickness (Morph)", 0, 3, 0)
        
        # Convert
        self.btn_convert = ctk.CTkButton(ctrl_frame, text="Convert", command=self.convert_image, fg_color="green", hover_color="darkgreen")
        self.btn_convert.pack(pady=20, padx=20, fill="x")
        
        # Export Settings
        export_frame = ctk.CTkFrame(ctrl_frame)
        export_frame.pack(pady=10, padx=10, fill="x")
        
        ctk.CTkLabel(export_frame, text="Export Settings").pack(pady=5)
        
        self.format_var = ctk.StringVar(value="PDF")
        self.format_menu = ctk.CTkOptionMenu(export_frame, values=["PDF", "PNG", "JPG"], variable=self.format_var)
        self.format_menu.pack(pady=5, padx=10, fill="x")
        
        self.size_var = ctk.StringVar(value="8.5 x 11")
        self.size_menu = ctk.CTkOptionMenu(export_frame, values=["8.5 x 11", "A4", "6 x 9"], variable=self.size_var)
        self.size_menu.pack(pady=5, padx=10, fill="x")
        
        # Export Button
        self.btn_export = ctk.CTkButton(ctrl_frame, text="Export", command=self.export_image)
        self.btn_export.pack(pady=10, padx=20, fill="x")

    def _create_slider(self, parent, label_text, min_val, max_val, default_val):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=5)
        
        lbl = ctk.CTkLabel(frame, text=f"{label_text}: {default_val}")
        lbl.pack(anchor="w")
        
        slider = ctk.CTkSlider(frame, from_=min_val, to=max_val, command=lambda v: lbl.configure(text=f"{label_text}: {int(v) if isinstance(default_val, int) else round(v, 2)}"))
        slider.set(default_val)
        slider.pack(fill="x")
        return slider, lbl

    def _build_preview_panel(self):
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.preview_frame, text="Original Image").grid(row=0, column=0, pady=5)
        ctk.CTkLabel(self.preview_frame, text="Converted Image").grid(row=0, column=1, pady=5)
        
        self.orig_canvas_lbl = ctk.CTkLabel(self.preview_frame, text="No Image", width=300, height=400, fg_color="gray30")
        self.orig_canvas_lbl.grid(row=1, column=0, padx=10, pady=10)
        
        self.conv_canvas_lbl = ctk.CTkLabel(self.preview_frame, text="No Image", width=300, height=400, fg_color="gray30")
        self.conv_canvas_lbl.grid(row=1, column=1, padx=10, pady=10)
        
    def import_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if path:
            if self.generator.load_image(path):
                self.original_image_path = path
                self._update_preview(self.orig_canvas_lbl, Image.open(path))
                self.conv_canvas_lbl.configure(image=None, text="Click Convert")
            else:
                messagebox.showerror("Error", "Failed to load image.")

    def convert_image(self):
        if not self.original_image_path:
            messagebox.showwarning("Warning", "Please import an image first.")
            return
            
        b = int(self.brightness_slider.get())
        c = float(self.contrast_slider.get())
        t_b = int(self.threshold_block_slider.get())
        t_c = int(self.threshold_c_slider.get())
        m = int(self.morph_slider.get())
        
        success = self.generator.process_image(
            brightness=b, 
            contrast=c, 
            blur_ksize=5, # Fixed standard blur
            threshold_block=t_b, 
            threshold_c=t_c, 
            morph_iters=m
        )
        
        if success:
            pil_img = self.generator.get_processed_pil_image()
            self._update_preview(self.conv_canvas_lbl, pil_img)
        else:
            messagebox.showerror("Error", "Failed to process image.")

    def _update_preview(self, label, pil_image):
        # Resize for preview
        pil_image.thumbnail(self.preview_size, Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=pil_image.size)
        label.configure(image=ctk_img, text="")

    def export_image(self):
        if self.generator.processed_image is None:
            messagebox.showwarning("Warning", "Please convert an image first.")
            return
            
        fmt = self.format_var.get()
        size = self.size_var.get()
        
        path = filedialog.asksaveasfilename(
            defaultextension=f".{fmt.lower()}",
            filetypes=[(f"{fmt} Files", f"*.{fmt.lower()}")]
        )
        
        if path:
            if self.generator.export(path, fmt, size):
                messagebox.showinfo("Success", f"Exported successfully to:\n{path}")
            else:
                messagebox.showerror("Error", "Export failed.")

    def load_project(self, project_id, project_name, state):
        self.project_id = project_id
        self.project_name = project_name
        # The coloring book doesn't store canvas state in the DB in this simplified model,
        # but it satisfies the requirement to load the project without error.
