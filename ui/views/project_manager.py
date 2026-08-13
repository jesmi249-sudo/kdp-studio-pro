import customtkinter as ctk
from tkinter import messagebox
from database.db import db
import json

class ProjectManagerView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        
        # Header Frame
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Project Manager", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, sticky="w")
        
        self.new_book_btn = ctk.CTkButton(self.header_frame, text="+ New Book", font=ctk.CTkFont(weight="bold"), command=self.open_new_book_dialog)
        self.new_book_btn.grid(row=0, column=1, sticky="e")
        
        self.info_label = ctk.CTkLabel(self, text="Manage your KDP projects here.", font=ctk.CTkFont(size=16))
        self.info_label.grid(row=1, column=0, padx=20, pady=10, sticky="nw")
        
        # Project List Frame
        self.project_list_frame = ctk.CTkScrollableFrame(self, label_text="Recent Projects")
        self.project_list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.grid_rowconfigure(2, weight=1)
        
        self.load_projects()

    def load_projects(self):
        # Clear existing
        for widget in self.project_list_frame.winfo_children():
            widget.destroy()
            
        projects = db.get_all_projects()
        
        if not projects:
            ctk.CTkLabel(self.project_list_frame, text="No recent projects. Click '+ New Book' to start.", text_color="gray").pack(pady=20)
            return
            
        for p in projects:
            self._create_project_card(p)
            
    def _create_project_card(self, project):
        p_id = project['id']
        p_name = project['name']
        p_type = project['project_type']
        p_date = project['last_modified']
        
        card = ctk.CTkFrame(self.project_list_frame)
        card.pack(fill="x", pady=5, padx=5)
        
        info = f"{p_name} ({p_type}) - Last Modified: {p_date}"
        ctk.CTkLabel(card, text=info, font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=10, pady=10)
        
        # Actions
        ctk.CTkButton(card, text="Delete", fg_color="red", hover_color="darkred", width=60, 
                      command=lambda id=p_id: self.delete_project(id)).pack(side="right", padx=5, pady=10)
        
        ctk.CTkButton(card, text="Rename", width=60, 
                      command=lambda id=p_id, n=p_name: self.rename_project(id, n)).pack(side="right", padx=5, pady=10)
                      
        ctk.CTkButton(card, text="Open", fg_color="green", hover_color="darkgreen", width=60, 
                      command=lambda p=project: self.open_project(p)).pack(side="right", padx=5, pady=10)

    def open_new_book_dialog(self):
        from ui.views.book_wizard import BookWizardController
        wizard = BookWizardController(self.winfo_toplevel())
        wizard.start()

    def delete_project(self, project_id):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this project?"):
            if db.delete_project(project_id):
                self.load_projects()

    def rename_project(self, project_id, current_name):
        dialog = ctk.CTkInputDialog(text="Enter new project name:", title="Rename Project")
        new_name = dialog.get_input()
        if new_name and new_name.strip() != "":
            if db.rename_project(project_id, new_name.strip()):
                self.load_projects()

    def open_project(self, project):
        app = self.winfo_toplevel()
        if hasattr(app, 'open_project'):
            app.open_project(project)
        else:
            messagebox.showerror("Error", "Main application open_project handler not found.")
