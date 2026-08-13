import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
import json
import os
from PIL import Image, ImageTk
from generators.cover_generator import CoverGenerator
from database.db import db
from core.logger import get_logger

logger = get_logger(__name__)

class CoverDesignerView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.generator = CoverGenerator()
        
        # State
        self.canvas_objects = []
        self.selected_item = None
        self.drag_data = {"x": 0, "y": 0, "item": None}
        self.dims = {}
        self.zoom_factor = 0.2
        self.bg_color = "#FFFFFF"
        self.current_project_id = None
        
        self.grid_columnconfigure(0, minsize=350, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Canvas area
        self.grid_rowconfigure(0, weight=1)
        
        self._build_sidebar()
        self._build_canvas()
        
        self._recalculate_dims()
        
    def _build_sidebar(self):
        ctrl = ctk.CTkScrollableFrame(self)
        ctrl.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(ctrl, text="Cover Designer Pro", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=15)
        
        # Cover Type
        self.cover_type_var = ctk.StringVar(value="Paperback")
        self._create_dropdown(ctrl, "Cover Type", ["Paperback", "Hardcover", "Spiral Notebook"], self.cover_type_var)
        
        # Size
        self.size_var = ctk.StringVar(value="8.5 x 11")
        self._create_dropdown(ctrl, "Trim Size", ["8.5 x 11", "8 x 10", "7 x 10", "6 x 9", "A4", "A5"], self.size_var)
        
        # Pages
        page_frame = ctk.CTkFrame(ctrl)
        page_frame.pack(fill="x", pady=10, padx=10)
        ctk.CTkLabel(page_frame, text="Page Count:").pack(side="left", padx=10)
        self.page_count = ctk.CTkEntry(page_frame, width=80)
        self.page_count.insert(0, "100")
        self.page_count.pack(side="right", padx=10)
        self.page_count.bind("<KeyRelease>", lambda e: self._recalculate_dims())
        
        # Paper Type
        self.paper_type_var = ctk.StringVar(value="White")
        self._create_dropdown(ctrl, "Paper Type", ["White", "Cream", "Color"], self.paper_type_var)
        
        # Display Calculated Spine
        self.spine_label = ctk.CTkLabel(ctrl, text="Spine Width: 0.00 inches", text_color="green")
        self.spine_label.pack(pady=5)
        
        # Tools
        ctk.CTkLabel(ctrl, text="Tools", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 5))
        
        btn_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10)
        
        ctk.CTkButton(btn_frame, text="Add Text", command=self.add_text, width=120).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(btn_frame, text="Add Image", command=self.add_image, width=120).pack(side="right", padx=5, pady=5)
        
        ctk.CTkButton(ctrl, text="Change Background", command=self.change_bg).pack(pady=5, fill="x", padx=10)
        
        # Guides toggle
        self.show_guides_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(ctrl, text="Show Guides", variable=self.show_guides_var, command=self.draw_guides).pack(pady=10)
        
        # Save / Export
        ctk.CTkLabel(ctrl, text="Project", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 5))
        
        ctk.CTkButton(ctrl, text="Save Project", command=self.save_project).pack(pady=5, fill="x", padx=10)
        ctk.CTkButton(ctrl, text="Export PDF", command=self.export_pdf, fg_color="green", hover_color="darkgreen").pack(pady=5, fill="x", padx=10)
        
    def _create_dropdown(self, parent, label, values, var):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(frame, text=label).pack(side="left")
        menu = ctk.CTkOptionMenu(frame, values=values, variable=var, command=lambda v: self._recalculate_dims())
        menu.pack(side="right")

    def _build_canvas(self):
        canvas_container = ctk.CTkFrame(self)
        canvas_container.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)
        
        # tkinter Canvas wrapped in a scrollable view (for future enhancement)
        self.canvas = tk.Canvas(canvas_container, bg="gray20", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        # Bind events for interaction
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        # Delete item
        self.canvas.bind("<Delete>", self.on_delete)
        
    def _recalculate_dims(self):
        try:
            pages = int(self.page_count.get())
            if pages < 1: pages = 1
        except ValueError as e:
            logger.debug(f"Ignoring ValueError during dimension calculation: {e}")
            return
            
        size_str = self.size_var.get()
        if "x" in size_str:
            w, h = map(float, size_str.split("x"))
        else:
            w, h = 8.5, 11 # Default for A4/A5 simplifications
            
        self.dims = self.generator.calculate_dimensions(
            trim_width=w, 
            trim_height=h, 
            pages=pages, 
            paper_type=self.paper_type_var.get()
        )
        
        self.spine_label.configure(text=f"Spine Width: {self.dims['spine_inches']:.4f} inches")
        
        self._refresh_canvas()

    def _refresh_canvas(self):
        self.canvas.delete("all")
        
        # Draw background base based on dims
        w = self.dims['full_width_px'] * self.zoom_factor
        h = self.dims['full_height_px'] * self.zoom_factor
        
        # Center the canvas rect
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        if cx <= 10: cx = 400 # Default if not rendered yet
        if cy <= 10: cy = 400
        
        ox = cx - (w/2)
        oy = cy - (h/2)
        
        self.canvas_offset_x = ox
        self.canvas_offset_y = oy
        
        # Draw base white background for the book
        self.canvas.create_rectangle(ox, oy, ox+w, oy+h, fill=self.bg_color, outline="black", tags="base")
        
        if self.show_guides_var.get():
            self.draw_guides()
            
        self._draw_objects()

    def draw_guides(self):
        self.canvas.delete("guide")
        if not self.show_guides_var.get():
            return
            
        ox = self.canvas_offset_x
        oy = self.canvas_offset_y
        z = self.zoom_factor
        
        bleed = self.dims['bleed_px'] * z
        tw = self.dims['trim_width_px'] * z
        th = self.dims['trim_height_px'] * z
        spine = self.dims['spine_px'] * z
        safe = self.dims['safe_zone_px'] * z
        
        full_w = self.dims['full_width_px'] * z
        full_h = self.dims['full_height_px'] * z
        
        # Bleed Zone (Red outer)
        self.canvas.create_rectangle(ox+bleed, oy+bleed, ox+full_w-bleed, oy+full_h-bleed, outline="red", dash=(4,4), tags="guide")
        
        # Spine Zone (Blue)
        spine_x = ox + bleed + tw
        self.canvas.create_rectangle(spine_x, oy, spine_x+spine, oy+full_h, outline="blue", tags="guide")
        
        # Safe Zones (Green)
        # Back Cover Safe Zone
        self.canvas.create_rectangle(ox+bleed+safe, oy+bleed+safe, ox+bleed+tw-safe, oy+bleed+th-safe, outline="green", dash=(2,2), tags="guide")
        
        # Front Cover Safe Zone
        self.canvas.create_rectangle(spine_x+spine+safe, oy+bleed+safe, spine_x+spine+tw-safe, oy+bleed+th-safe, outline="green", dash=(2,2), tags="guide")

    def _draw_objects(self):
        # We need a reference list to keep images from being garbage collected
        self.tk_images = []
        
        ox = self.canvas_offset_x
        oy = self.canvas_offset_y
        z = self.zoom_factor
        
        for i, obj in enumerate(self.canvas_objects):
            x = ox + (obj['x'] * z)
            y = oy + (obj['y'] * z)
            
            if obj['type'] == 'text':
                item = self.canvas.create_text(
                    x, y, 
                    text=obj['text'], 
                    fill=obj['color'], 
                    font=(obj['font'], int(obj['size']*z)),
                    tags=("draggable", f"obj_{i}"),
                    anchor="nw"
                )
            elif obj['type'] == 'image':
                if os.path.exists(obj['image_path']):
                    img = Image.open(obj['image_path'])
                    # Resize
                    img = img.resize((int(obj['width']*z), int(obj['height']*z)), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self.tk_images.append(photo) # Keep reference
                    item = self.canvas.create_image(
                        x, y, 
                        image=photo, 
                        tags=("draggable", f"obj_{i}"),
                        anchor="nw"
                    )

    # --- Interactions ---
    def on_press(self, event):
        self.canvas.focus_set()
        item = self.canvas.find_withtag("current")
        if item and "draggable" in self.canvas.gettags(item[0]):
            self.selected_item = item[0]
            self.drag_data["item"] = item[0]
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
        else:
            self.selected_item = None
            
    def on_drag(self, event):
        if self.drag_data["item"]:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            self.canvas.move(self.drag_data["item"], dx, dy)
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            
            # Update internal model
            tags = self.canvas.gettags(self.drag_data["item"])
            for tag in tags:
                if tag.startswith("obj_"):
                    idx = int(tag.split("_")[1])
                    self.canvas_objects[idx]['x'] += (dx / self.zoom_factor)
                    self.canvas_objects[idx]['y'] += (dy / self.zoom_factor)
                    break

    def on_release(self, event):
        self.drag_data["item"] = None
        
    def on_delete(self, event):
        if self.selected_item:
            tags = self.canvas.gettags(self.selected_item)
            for tag in tags:
                if tag.startswith("obj_"):
                    idx = int(tag.split("_")[1])
                    del self.canvas_objects[idx]
                    self._refresh_canvas()
                    self.selected_item = None
                    break
                    
    # --- Toolbar Actions ---
    def add_text(self):
        # Adding a default text object at center
        self.canvas_objects.append({
            "type": "text",
            "text": "Double Click to Edit",
            "x": self.dims['full_width_px'] / 2 - 200,
            "y": self.dims['full_height_px'] / 2,
            "color": "#000000",
            "font": "Arial",
            "size": 150
        })
        self._refresh_canvas()
        
    def add_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if path:
            img = Image.open(path)
            self.canvas_objects.append({
                "type": "image",
                "image_path": path,
                "x": 100,
                "y": 100,
                "width": img.width,
                "height": img.height
            })
            self._refresh_canvas()
            
    def change_bg(self):
        color_code = colorchooser.askcolor(title="Choose background color")
        if color_code[1]:
            self.bg_color = color_code[1]
            self._refresh_canvas()

    def export_pdf(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if path:
            # We also pass the objects so generator can render
            success = self.generator.export(self.canvas_objects, self.dims, self.bg_color, path, format="pdf")
            if success:
                messagebox.showinfo("Success", f"Cover PDF generated:\n{path}")
            else:
                messagebox.showerror("Error", "Failed to generate cover PDF.")
                
    def refresh_data(self):
        """Auto-loads cover design from active book project if present."""
        from book_builder.container import Container
        from book_builder.interfaces.core import IBookBuilder
        try:
            engine = Container().resolve(IBookBuilder)
            active_proj = engine.get_active_project()
        except Exception:
            active_proj = None
            
        if active_proj and "cover_design" in active_proj.custom_settings:
            cover_data = active_proj.custom_settings["cover_design"]
            logger.info(f"CoverDesignerView: loading cover design from active book project '{active_proj.name}'")
            self.cover_type_var.set(cover_data.get("cover_type", "Paperback"))
            self.size_var.set(cover_data.get("size", "8.5 x 11"))
            self.page_count.delete(0, 'end')
            self.page_count.insert(0, str(cover_data.get("pages", "100")))
            self.paper_type_var.set(cover_data.get("paper_type", "White"))
            self.bg_color = cover_data.get("bg_color", "#FFFFFF")
            self.canvas_objects = cover_data.get("objects", [])
            self._recalculate_dims()

    def save_project(self):
        # Gather state
        state = {
            "type": "cover_designer_pro",
            "cover_type": self.cover_type_var.get(),
            "size": self.size_var.get(),
            "pages": self.page_count.get(),
            "paper_type": self.paper_type_var.get(),
            "bg_color": self.bg_color,
            "objects": self.canvas_objects
        }
        
        # Save to active book project if present
        from book_builder.container import Container
        from book_builder.interfaces.core import IBookBuilder
        from book_builder.repository import ProjectRepository
        active_proj = None
        try:
            engine = Container().resolve(IBookBuilder)
            active_proj = engine.get_active_project()
        except Exception:
            pass
            
        if active_proj:
            active_proj.custom_settings["cover_design"] = state
            ProjectRepository.save(active_proj)
            logger.info(f"CoverDesignerView: saved cover design to active project '{active_proj.name}'")
            
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.current_project_id is None:
                # create new
                cursor.execute("""
                    INSERT INTO projects (name, project_type, data) 
                    VALUES (?, ?, ?)
                """, ("My Cover Design", "cover", json.dumps(state)))
                self.current_project_id = cursor.lastrowid
            else:
                # update
                cursor.execute("""
                    UPDATE projects SET data = ?, last_modified = CURRENT_TIMESTAMP WHERE id = ?
                """, (json.dumps(state), self.current_project_id))
            conn.commit()
            messagebox.showinfo("Saved", "Project saved successfully.")
        except Exception as e:
            logger.error(f"Error saving project: {e}")
            messagebox.showerror("Error", "Failed to save project.")

    def load_project(self, project_id, project_name, state):
        try:
            self.current_project_id = project_id
            self.cover_type_var.set(state.get("cover_type", "Paperback"))
            self.size_var.set(state.get("size", "8.5 x 11"))
            
            self.page_count.delete(0, 'end')
            self.page_count.insert(0, str(state.get("pages", "100")))
            
            self.paper_type_var.set(state.get("paper_type", "White"))
            self.bg_color = state.get("bg_color", "#FFFFFF")
            
            self.canvas_objects = state.get("objects", [])
            
            self._recalculate_dims()
            messagebox.showinfo("Success", f"Project '{project_name}' loaded.")
        except Exception as e:
            logger.error(f"Error loading project {project_id}: {e}")
            messagebox.showerror("Error", "Failed to load project state.")
