import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from PIL import Image
from generators.interior_generator import InteriorGenerator
from core.logger import get_logger

logger = get_logger(__name__)

class InteriorView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.generator = InteriorGenerator()
        
        self.grid_columnconfigure(0, weight=1, minsize=350)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)
        
        self.preview_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "temp_preview.png")
        if not os.path.exists(os.path.dirname(self.preview_path)):
            os.makedirs(os.path.dirname(self.preview_path))
            
        self._build_controls()
        self._build_preview()
        self.update_preview()
        
    def _build_controls(self):
        ctrl = ctk.CTkScrollableFrame(self)
        ctrl.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(ctrl, text="Interior Designer", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=15)
        
        # Template
        self.template_var = ctk.StringVar(value="College Ruled")
        self._create_dropdown(ctrl, "Template", [
            "Blank", "College Ruled", "Wide Ruled", "Narrow Ruled", "Dot Grid", 
            "Graph Paper", "Handwriting Practice", "Story Paper", "Music Staff", 
            "Daily Journal", "Planner Page"
        ], self.template_var)
        
        # Size
        self.size_var = ctk.StringVar(value="8.5 x 11")
        self._create_dropdown(ctrl, "Page Size", ["8.5 x 11", "8 x 10", "7 x 10", "6 x 9", "A4", "A5"], self.size_var)
        
        # Orientation
        self.orient_var = ctk.StringVar(value="Portrait")
        self._create_dropdown(ctrl, "Orientation", ["Portrait", "Landscape"], self.orient_var)
        
        # Bleed
        self.bleed_var = ctk.StringVar(value="Off")
        self._create_dropdown(ctrl, "Bleed", ["Off", "On"], self.bleed_var)
        
        # Page Numbers
        self.pgnum_var = ctk.StringVar(value="None")
        self._create_dropdown(ctrl, "Page Numbers", ["None", "Top Center", "Bottom Center", "Bottom Left", "Bottom Right"], self.pgnum_var)
        
        # Margins (inches)
        margin_frame = ctk.CTkFrame(ctrl)
        margin_frame.pack(fill="x", pady=10, padx=10)
        ctk.CTkLabel(margin_frame, text="Margins (inches)").pack()
        
        self.m_top = self._create_margin_input(margin_frame, "Top", "0.5")
        self.m_bot = self._create_margin_input(margin_frame, "Bottom", "0.5")
        self.m_in = self._create_margin_input(margin_frame, "Inside", "0.5")
        self.m_out = self._create_margin_input(margin_frame, "Outside", "0.5")
        
        # Pages
        page_frame = ctk.CTkFrame(ctrl)
        page_frame.pack(fill="x", pady=10, padx=10)
        ctk.CTkLabel(page_frame, text="Page Count (1-500):").pack(side="left", padx=10)
        self.page_count = ctk.CTkEntry(page_frame, width=80)
        self.page_count.insert(0, "100")
        self.page_count.pack(side="right", padx=10)
        
        # Buttons
        ctk.CTkButton(ctrl, text="Update Preview", command=self.update_preview).pack(pady=10, fill="x", padx=10)
        ctk.CTkButton(ctrl, text="Generate PDF", command=self.generate, fg_color="green", hover_color="darkgreen").pack(pady=10, fill="x", padx=10)
        
    def _create_dropdown(self, parent, label, values, var):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(frame, text=label).pack(side="left")
        menu = ctk.CTkOptionMenu(frame, values=values, variable=var, command=lambda v: self.update_preview())
        menu.pack(side="right")
        
    def _create_margin_input(self, parent, label, default):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label).pack(side="left")
        entry = ctk.CTkEntry(frame, width=60)
        entry.insert(0, default)
        entry.pack(side="right")
        return entry

    def _build_preview(self):
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.preview_frame, text="Live Preview (Margin Guides in Red)").grid(row=0, column=0, pady=10)
        self.preview_lbl = ctk.CTkLabel(self.preview_frame, text="")
        self.preview_lbl.grid(row=1, column=0, padx=10, pady=10)
        
    def update_preview(self):
        try:
            margins = {
                'top': float(self.m_top.get()),
                'bottom': float(self.m_bot.get()),
                'inside': float(self.m_in.get()),
                'outside': float(self.m_out.get())
            }
            bleed = (self.bleed_var.get() == "On")
            
            self.generator.generate_preview(
                self.preview_path, self.size_var.get(), self.orient_var.get(),
                margins, bleed, self.template_var.get()
            )
            
            if os.path.exists(self.preview_path):
                img = Image.open(self.preview_path)
                # resize to fit
                img.thumbnail((500, 700), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self.preview_lbl.configure(image=ctk_img)
                
        except ValueError as e:
            logger.debug(f"Ignoring ValueError during preview update (likely incomplete typing): {e}")
            
    def generate(self):
        try:
            pages = int(self.page_count.get())
            if pages < 1 or pages > 500:
                raise ValueError("Page count must be 1-500")
                
            margins = {
                'top': float(self.m_top.get()),
                'bottom': float(self.m_bot.get()),
                'inside': float(self.m_in.get()),
                'outside': float(self.m_out.get())
            }
            
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
            if path:
                success = self.generator.generate_pdf(
                    path, self.size_var.get(), self.orient_var.get(), margins,
                    (self.bleed_var.get() == "On"), self.pgnum_var.get(), 
                    self.template_var.get(), pages
                )
                
                if success:
                    messagebox.showinfo("Success", f"Interior PDF generated:\n{path}")
                else:
                    messagebox.showerror("Error", "Failed to generate interior.")
                    
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")

    def refresh_data(self):
        """Auto-loads interior design from active book project if present."""
        pass

    def load_project(self, project_id, project_name, state):
        """Called by UI framework when switching projects."""
        logger.info(f"InteriorView: load_project stub called for {project_name}")
