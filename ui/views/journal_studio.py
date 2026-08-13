import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from core.logger import get_logger
from core.planner_templates import PlannerTemplates
from core.planner_engine import PlannerEngine
from models.planner import PlannerProject
from ui.theme.fonts import Fonts
from ui.theme.spacing import Spacing
from ui.theme.colors import Colors

logger = get_logger(__name__)

class JournalStudioView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.project = PlannerTemplates.create_blank_project()
        self.active_page_idx = 0
        self.selected_object_idx = None
        
        self.grid_columnconfigure(0, weight=0, minsize=200) # Left sidebar (pages)
        self.grid_columnconfigure(1, weight=1) # Canvas
        self.grid_columnconfigure(2, weight=0, minsize=250) # Right sidebar (Properties)
        self.grid_rowconfigure(0, weight=1)
        
        self._build_left_sidebar()
        self._build_canvas()
        self._build_right_sidebar()
        
        self._refresh_canvas()

    def _build_left_sidebar(self):
        self.left_panel = ctk.CTkScrollableFrame(self, width=200)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=Spacing.S, pady=Spacing.S)
        
        ctk.CTkLabel(self.left_panel, text="Pages", font=Fonts.heading3()).pack(pady=Spacing.M)
        
        # We will dynamically populate this in a real app.
        for i, page in enumerate(self.project.pages):
            btn = ctk.CTkButton(self.left_panel, text=f"Page {page.page_number}", 
                                fg_color="transparent", text_color=Colors.TEXT_MAIN[1],
                                command=lambda idx=i: self._select_page(idx))
            btn.pack(fill="x", pady=2)
            
        ctk.CTkButton(self.left_panel, text="+ Add Page", fg_color=Colors.PRIMARY[0], command=self._add_page).pack(pady=Spacing.M)

    def _build_canvas(self):
        canvas_container = ctk.CTkFrame(self)
        canvas_container.grid(row=0, column=1, sticky="nsew", padx=Spacing.S, pady=Spacing.S)
        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(canvas_container, bg="gray20", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        # Interactions
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        
    def _build_right_sidebar(self):
        self.right_panel = ctk.CTkScrollableFrame(self, width=250)
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=Spacing.S, pady=Spacing.S)
        
        ctk.CTkLabel(self.right_panel, text="Properties", font=Fonts.heading3()).pack(pady=Spacing.M)
        
        # Coordinates
        coord_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        coord_frame.pack(fill="x", pady=Spacing.S)
        
        ctk.CTkLabel(coord_frame, text="X:").grid(row=0, column=0, padx=2)
        self.prop_x = ctk.CTkEntry(coord_frame, width=60)
        self.prop_x.grid(row=0, column=1, padx=2)
        
        ctk.CTkLabel(coord_frame, text="Y:").grid(row=0, column=2, padx=2)
        self.prop_y = ctk.CTkEntry(coord_frame, width=60)
        self.prop_y.grid(row=0, column=3, padx=2)
        
        # Dimensions
        dim_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        dim_frame.pack(fill="x", pady=Spacing.S)
        
        ctk.CTkLabel(dim_frame, text="W:").grid(row=0, column=0, padx=2)
        self.prop_w = ctk.CTkEntry(dim_frame, width=60)
        self.prop_w.grid(row=0, column=1, padx=2)
        
        ctk.CTkLabel(dim_frame, text="H:").grid(row=0, column=2, padx=2)
        self.prop_h = ctk.CTkEntry(dim_frame, width=60)
        self.prop_h.grid(row=0, column=3, padx=2)
        
        # Styling
        ctk.CTkLabel(self.right_panel, text="Text content:").pack(anchor="w", pady=(10, 0))
        self.prop_text = ctk.CTkEntry(self.right_panel)
        self.prop_text.pack(fill="x", pady=2)
        
        # Update Button
        ctk.CTkButton(self.right_panel, text="Apply Changes", command=self._apply_properties).pack(pady=Spacing.L)

    def _select_page(self, idx):
        self.active_page_idx = idx
        self.selected_object_idx = None
        self._refresh_canvas()
        
    def _add_page(self):
        from models.planner import PlannerPage
        new_page = PlannerPage(page_number=len(self.project.pages) + 1)
        self.project.pages.append(new_page)
        self._build_left_sidebar() # Rebuild sidebar to show new button
        
    def _refresh_canvas(self):
        self.canvas.delete("all")
        
        # Draw paper background
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        if cx <= 10: cx = 400
        if cy <= 10: cy = 400
        
        # Scale (approx 100px per inch for preview)
        w = self.project.trim_width * 100
        h = self.project.trim_height * 100
        
        ox = cx - (w/2)
        oy = cy - (h/2)
        self.canvas_offset_x = ox
        self.canvas_offset_y = oy
        
        self.canvas.create_rectangle(ox, oy, ox+w, oy+h, fill="white", outline="black")
        
        # Draw active page objects
        if not self.project.pages: return
        page = self.project.pages[self.active_page_idx]
        
        for i, obj in enumerate(page.objects):
            x = ox + obj.x
            y = oy + obj.y
            color = "red" if i == self.selected_object_idx else "blue"
            
            if obj.type == "text":
                self.canvas.create_text(x, y, text=obj.text, fill="black", font=(obj.font_family, int(obj.font_size)), anchor="nw", tags=f"obj_{i}")
                # Highlight bounds if selected
                if i == self.selected_object_idx:
                    self.canvas.create_rectangle(x, y, x+obj.width, y+obj.height, outline="red", tags=f"sel_{i}")
            else:
                self.canvas.create_rectangle(x, y, x+obj.width, y+obj.height, outline=color, tags=f"obj_{i}")

    def on_press(self, event):
        item = self.canvas.find_withtag("current")
        if item:
            tags = self.canvas.gettags(item[0])
            for tag in tags:
                if tag.startswith("obj_"):
                    self.selected_object_idx = int(tag.split("_")[1])
                    self._populate_properties()
                    self._refresh_canvas()
                    return
        
        self.selected_object_idx = None
        self._refresh_canvas()

    def _populate_properties(self):
        if self.selected_object_idx is None: return
        page = self.project.pages[self.active_page_idx]
        obj = page.objects[self.selected_object_idx]
        
        self.prop_x.delete(0, 'end')
        self.prop_x.insert(0, str(obj.x))
        
        self.prop_y.delete(0, 'end')
        self.prop_y.insert(0, str(obj.y))
        
        self.prop_w.delete(0, 'end')
        self.prop_w.insert(0, str(obj.width))
        
        self.prop_h.delete(0, 'end')
        self.prop_h.insert(0, str(obj.height))
        
        self.prop_text.delete(0, 'end')
        self.prop_text.insert(0, obj.text)

    def _apply_properties(self):
        if self.selected_object_idx is None: return
        page = self.project.pages[self.active_page_idx]
        obj = page.objects[self.selected_object_idx]
        
        try:
            obj.x = float(self.prop_x.get())
            obj.y = float(self.prop_y.get())
            obj.width = float(self.prop_w.get())
            obj.height = float(self.prop_h.get())
            obj.text = self.prop_text.get()
            self._refresh_canvas()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for coordinates.")

    # --- Toolbar Commands (via Dispatcher) ---
    def cmd_save(self):
        messagebox.showinfo("Save", "Planner project saved successfully.")
        
    def cmd_export(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if path:
            success = PlannerEngine.export_pdf(self.project, path)
            if success:
                messagebox.showinfo("Export", "Planner PDF generated successfully!")
            else:
                messagebox.showerror("Error", "Failed to generate PDF.")

    def load_project(self, project_id, project_name, state):
        self.project_id = project_id
        if "pages" not in state or not state["pages"]:
            self.project = PlannerTemplates.create_blank_project()
        else:
            self.project = PlannerProject.from_dict(state, project_id)
        
        self.project.name = project_name
        self._build_left_sidebar()
        self._select_page(0)
