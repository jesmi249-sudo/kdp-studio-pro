import customtkinter as ctk
from tkinter import messagebox
from database.db import db
import json

class Step1_BookType(ctk.CTkFrame):
    def __init__(self, master, controller, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        
        ctk.CTkLabel(self, text="Step 1: Choose Book Type", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(40, 20))
        
        self.book_type_var = ctk.StringVar(value=self.controller.state.get("type", "Coloring Book"))
        
        types = ["Coloring Book", "Notebook", "Journal", "Planner", "Activity Book", "Story Book"]
        for t in types:
            rb = ctk.CTkRadioButton(self, text=t, variable=self.book_type_var, value=t)
            rb.pack(pady=10)
            
    def save_state(self):
        self.controller.state["type"] = self.book_type_var.get()

class Step2_BookDetails(ctk.CTkFrame):
    def __init__(self, master, controller, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        
        ctk.CTkLabel(self, text="Step 2: Book Details", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(40, 20))
        
        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.pack(pady=10, padx=40, fill="x")
        
        self.entries = {}
        fields = ["Project Name", "Trim Size", "Page Count", "Paper Type", "Bleed"]
        
        for i, field in enumerate(fields):
            ctk.CTkLabel(form_frame, text=field).grid(row=i, column=0, padx=10, pady=10, sticky="e")
            entry = ctk.CTkEntry(form_frame, width=300)
            entry.grid(row=i, column=1, padx=10, pady=10, sticky="w")
            
            state_key = field.lower().replace(" ", "_")
            if state_key in self.controller.state:
                entry.insert(0, str(self.controller.state[state_key]))
            self.entries[state_key] = entry
            
    def save_state(self):
        for k, entry in self.entries.items():
            self.controller.state[k] = entry.get()

class BookWizardController:
    def __init__(self, app, initial_state=None):
        self.app = app
        if initial_state:
            self.state = initial_state
        else:
            self.state = {
                "type": "Coloring Book",
                "project_name": "New Project",
                "trim_size": "8.5 x 11",
                "page_count": "100",
                "paper_type": "White",
                "bleed": "No Bleed"
            }
        
        self.current_step = 1
        self.total_steps = 2
        
        self.step_frames = {
            1: Step1_BookType(self.app.main_content_frame, self, fg_color="transparent"),
            2: Step2_BookDetails(self.app.main_content_frame, self, fg_color="transparent"),
        }
        
        self.bar = self.app.wizard_bar_frame
        
        for widget in self.bar.winfo_children():
            widget.destroy()
            
        self.step_label = ctk.CTkLabel(self.bar, text="", font=ctk.CTkFont(weight="bold"))
        self.step_label.grid(row=0, column=1, pady=15)
        
        self.btn_cancel = ctk.CTkButton(self.bar, text="Cancel", fg_color="red", hover_color="darkred", width=80, command=self.cancel)
        self.btn_cancel.grid(row=0, column=0, padx=20, sticky="w")
        
        nav_btns = ctk.CTkFrame(self.bar, fg_color="transparent")
        nav_btns.grid(row=0, column=2, padx=20, sticky="e")
        
        self.btn_back = ctk.CTkButton(nav_btns, text="Back", width=80, command=self.prev_step)
        self.btn_back.pack(side="left", padx=5)
        
        self.btn_next = ctk.CTkButton(nav_btns, text="Next", width=80, command=self.next_step)
        self.btn_next.pack(side="left", padx=5)
        
    def start(self):
        self.bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.show_step()
        
    def show_step(self):
        for f in self.step_frames.values():
            f.grid_forget()
            
        self.step_label.configure(text=f"Step {self.current_step} of {self.total_steps}")
        
        if self.current_step == 1:
            self.btn_back.configure(state="disabled")
        else:
            self.btn_back.configure(state="normal")
            
        if self.current_step == self.total_steps:
            self.btn_next.configure(text="Create")
        else:
            self.btn_next.configure(text="Next")

        self.step_frames[self.current_step].grid(row=0, column=0, sticky="nsew")
        if self.app.current_frame:
            self.app.current_frame.grid_forget()

    def next_step(self):
        if self.current_step in self.step_frames:
            self.step_frames[self.current_step].save_state()
            
        if self.current_step == self.total_steps:
            self.finish()
        else:
            self.current_step += 1
            self.show_step()
            
    def prev_step(self):
        if self.current_step in self.step_frames:
            self.step_frames[self.current_step].save_state()
            
        if self.current_step > 1:
            self.current_step -= 1
            self.show_step()
            
    def cancel(self):
        self.end_wizard("Dashboard")
        
    def finish(self):
        book_type = self.state.get("type", "Coloring Book")
        
        # Fallback for Story Book and Journal studios which use separate data models
        if book_type in ["Story Book", "Journal"]:
            self.save_project()
            messagebox.showinfo("Success", "Project created successfully!")
            
            p_id = self.state.get("project_id")
            project_row = {
                "id": p_id,
                "name": self.state.get("project_name", "Untitled"),
                "project_type": "wizard",
                "data": json.dumps(self.state)
            }
            
            self.bar.grid_forget()
            for f in self.step_frames.values():
                f.grid_forget()
                
            self.app.open_project(project_row)
            return

        # 1. Resolve BookBuilderEngine from Container
        from book_builder.container import Container
        from book_builder.interfaces.core import IBookBuilder
        try:
            engine = Container().resolve(IBookBuilder)
        except Exception:
            from book_builder.engine import BookBuilderEngine
            engine = BookBuilderEngine()
            Container().register(IBookBuilder, engine)
            
        # 2. Parse trim size
        trim_str = self.state.get("trim_size", "8.5 x 11")
        try:
            w_str, h_str = trim_str.split("x")
            trim_w = float(w_str.strip())
            trim_h = float(h_str.strip())
        except Exception:
            trim_w, trim_h = 8.5, 11.0
            
        # 3. Parse bleed
        bleed = "No" not in self.state.get("bleed", "No Bleed")
        
        # 4. Parse page count
        try:
            page_count = int(self.state.get("page_count", "40").strip())
        except Exception:
            page_count = 40
            
        # 5. Create settings dictionary
        settings = {
            "trim_width_in": trim_w,
            "trim_height_in": trim_h,
            "has_bleed": bleed,
            "paper_type": self.state.get("paper_type", "White")
        }
        
        # 6. Create project in engine
        project = engine.create_project(
            name=self.state.get("project_name", "Untitled"),
            book_type=book_type,
            settings=settings
        )
        
        # 7. Generate pages depending on studio type
        try:
            if book_type == "Coloring Book":
                from book_builder.commands.coloring_commands import GenerateColoringPagesCommand
                cmd = GenerateColoringPagesCommand(
                    project=project,
                    page_count=page_count,
                    trim_width_in=trim_w,
                    trim_height_in=trim_h,
                    margin_top_in=0.5,
                    margin_bottom_in=0.5,
                    margin_inside_in=0.5,
                    margin_outside_in=0.5,
                    has_bleed=bleed,
                    settings={"scale_style": "Fit", "border_style": "Bold"}
                )
                engine.execute_command(cmd)
            elif book_type == "Notebook":
                from book_builder.commands.notebook_commands import GenerateNotebookPagesCommand
                cmd = GenerateNotebookPagesCommand(
                    project=project,
                    page_count=page_count,
                    trim_width_in=trim_w,
                    trim_height_in=trim_h,
                    margin_top_in=0.5,
                    margin_bottom_in=0.5,
                    margin_inside_in=0.5,
                    margin_outside_in=0.5,
                    has_bleed=bleed,
                    template_type="Lined College Ruled"
                )
                engine.execute_command(cmd)
            elif book_type == "Planner":
                from book_builder.commands.planner_commands import GeneratePlannerPagesCommand
                cmd = GeneratePlannerPagesCommand(
                    project=project,
                    page_count=page_count,
                    trim_width_in=trim_w,
                    trim_height_in=trim_h,
                    margin_top_in=0.5,
                    margin_bottom_in=0.5,
                    margin_inside_in=0.5,
                    margin_outside_in=0.5,
                    has_bleed=bleed,
                    template_type="Monthly Planner"
                )
                engine.execute_command(cmd)
            elif book_type == "Activity Book":
                from book_builder.commands.activity_commands import GenerateActivityPagesCommand
                cmd = GenerateActivityPagesCommand(
                    project=project,
                    page_count=page_count,
                    trim_width_in=trim_w,
                    trim_height_in=trim_h,
                    margin_top_in=0.5,
                    margin_bottom_in=0.5,
                    margin_inside_in=0.5,
                    margin_outside_in=0.5,
                    has_bleed=bleed,
                    template_type="Mixed Activities"
                )
                engine.execute_command(cmd)
        except Exception as gen_err:
            import logging
            logging.getLogger(__name__).error(f"BookWizard: Failed to auto-generate default template pages: {gen_err}")

        # 8. Save the project to generate pages and insert it in the database
        success = engine.save_project()
        if not success:
            messagebox.showerror("Error", "Failed to save the newly created project.")
            return
            
        p_id = project.id
        self.state["project_id"] = p_id
        
        # 9. Formulate project row for routing
        from book_builder.serializer import ProjectSerializer
        project_row = {
            "id": p_id,
            "name": project.name,
            "project_type": project.book_type,
            "data": json.dumps(ProjectSerializer.serialize_project(project))
        }
        
        messagebox.showinfo("Success", "Project created successfully!")
        
        self.bar.grid_forget()
        for f in self.step_frames.values():
            f.grid_forget()
            
        self.app.open_project(project_row)
        
    def save_project(self):
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO projects (name, project_type, data) 
                VALUES (?, ?, ?)
            """, (self.state.get("project_name", "Untitled"), "wizard", json.dumps(self.state)))
            conn.commit()
            self.state["project_id"] = cursor.lastrowid
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project: {e}")
            
    def end_wizard(self, target_studio):
        self.bar.grid_forget()
        for f in self.step_frames.values():
            f.grid_forget()
        self.app.select_frame(target_studio)
