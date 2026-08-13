import customtkinter as ctk
import os
from tkinter import filedialog, messagebox
from generators.metadata_generator import MetadataGenerator
from core.logger import get_logger

logger = get_logger(__name__)

class MetadataView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.generator = MetadataGenerator()
        
        self.grid_columnconfigure(1, weight=1)
        
        self.title_label = ctk.CTkLabel(self, text="Metadata Generator", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 20), sticky="w")
        
        # Form fields
        self.fields = {}
        row = 1
        
        form_items = [
            ("title", "Title:"),
            ("subtitle", "Subtitle:"),
            ("author", "Author:"),
            ("series", "Series:"),
            ("language", "Language:"),
            ("publisher", "Publisher:")
        ]
        
        for key, label in form_items:
            lbl = ctk.CTkLabel(self, text=label)
            lbl.grid(row=row, column=0, padx=20, pady=5, sticky="e")
            
            entry = ctk.CTkEntry(self, width=400)
            entry.grid(row=row, column=1, padx=20, pady=5, sticky="w")
            if key == "language":
                entry.insert(0, "English")
                
            self.fields[key] = entry
            row += 1
            
        # Description (Textbox)
        desc_lbl = ctk.CTkLabel(self, text="Description:")
        desc_lbl.grid(row=row, column=0, padx=20, pady=5, sticky="ne")
        self.desc_box = ctk.CTkTextbox(self, width=400, height=100)
        self.desc_box.grid(row=row, column=1, padx=20, pady=5, sticky="w")
        row += 1
        
        # Keywords (Entry)
        kw_lbl = ctk.CTkLabel(self, text="Keywords (comma separated):")
        kw_lbl.grid(row=row, column=0, padx=20, pady=5, sticky="e")
        self.kw_entry = ctk.CTkEntry(self, width=400)
        self.kw_entry.grid(row=row, column=1, padx=20, pady=5, sticky="w")
        row += 1
        
        # Categories (Entry)
        cat_lbl = ctk.CTkLabel(self, text="Categories (comma separated):")
        cat_lbl.grid(row=row, column=0, padx=20, pady=5, sticky="e")
        self.cat_entry = ctk.CTkEntry(self, width=400)
        self.cat_entry.grid(row=row, column=1, padx=20, pady=5, sticky="w")
        row += 1
        
        # Export Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)
        
        self.export_json_btn = ctk.CTkButton(btn_frame, text="Export JSON", command=self.export_json)
        self.export_json_btn.pack(side="left", padx=10)
        
        self.export_csv_btn = ctk.CTkButton(btn_frame, text="Export CSV", command=self.export_csv)
        self.export_csv_btn.pack(side="left", padx=10)
        
    def _update_generator_data(self):
        """Syncs UI fields to the generator."""
        for key, entry in self.fields.items():
            self.generator.set_field(key, entry.get())
            
        self.generator.set_field("description", self.desc_box.get("1.0", "end-1c"))
        
        keywords = [k.strip() for k in self.kw_entry.get().split(",") if k.strip()]
        self.generator.set_field("keywords", keywords)
        
        categories = [c.strip() for c in self.cat_entry.get().split(",") if c.strip()]
        self.generator.set_field("categories", categories)

    def export_json(self):
        self._update_generator_data()
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if path:
            if self.generator.export_json(path):
                messagebox.showinfo("Success", f"Metadata exported to {os.path.basename(path)}")
            else:
                messagebox.showerror("Error", "Failed to export JSON.")
                
    def export_csv(self):
        self._update_generator_data()
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if path:
            if self.generator.export_csv(path):
                messagebox.showinfo("Success", f"Metadata exported to {os.path.basename(path)}")
            else:
                messagebox.showerror("Error", "Failed to export CSV.")

    def prefill_data(self, title="", subtitle="", author="", language=""):
        if title:
            self.fields["title"].delete(0, "end")
            self.fields["title"].insert(0, title)
        if subtitle:
            self.fields["subtitle"].delete(0, "end")
            self.fields["subtitle"].insert(0, subtitle)
        if author:
            self.fields["author"].delete(0, "end")
            self.fields["author"].insert(0, author)
        if language:
            self.fields["language"].delete(0, "end")
            self.fields["language"].insert(0, language)
