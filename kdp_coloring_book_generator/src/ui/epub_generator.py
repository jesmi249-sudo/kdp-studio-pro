"""
EPUB Generator Frame - Professional eBook creator.
Builds Kindle-compliant EPUB files in Text or Image modes.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
import uuid
import tempfile
import threading
import os

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from core.epub_engine import EpubEngine, EBOOKLIB_AVAILABLE
    from core.logger import get_logger
except ImportError:
    EBOOKLIB_AVAILABLE = False
    
try:
    from core.logger import get_logger
    logger = get_logger("epub_generator")
except Exception:
    import logging
    logger = logging.getLogger("epub_generator")

VALID_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".svg"}


class EpubGeneratorFrame(ctk.CTkFrame):
    """EPUB Generator view: metadata form, chapter/image list, and export."""

    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.app = app

        self.items = []            
        self.selected_item_id = None
        self.current_project_id = None
        self.mode = "text"

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_header()
        self._create_content()

    def _create_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=32, pady=(28, 12), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(
            header_frame, text="EPUB Generator",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ctk.CTkLabel(
            header_frame, text="Generate Kindle-compliant reflowable or fixed-layout eBooks",
            font=ctk.CTkFont(size=13), text_color=("gray40", "gray60"),
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, rowspan=2, sticky="e")

        self.preview_btn = ctk.CTkButton(
            btn_frame, text="👁  Preview EPUB", font=ctk.CTkFont(size=13),
            height=40, width=140, corner_radius=8,
            fg_color=("#7c3aed", "#7c3aed"), hover_color=("#6d28d9", "#6d28d9"),
            command=self._preview_epub,
        )
        self.preview_btn.grid(row=0, column=0, padx=(0, 8))

        self.export_btn = ctk.CTkButton(
            btn_frame, text="📖  Export EPUB", font=ctk.CTkFont(size=13, weight="bold"),
            height=40, width=140, corner_radius=8,
            fg_color="#10b981", hover_color="#059669",
            command=self._export_epub,
        )
        self.export_btn.grid(row=0, column=1, padx=(0, 8))

        self.save_btn = ctk.CTkButton(
            btn_frame, text="💾  Save", font=ctk.CTkFont(size=13),
            height=40, width=100, corner_radius=8,
            fg_color="#2563eb", hover_color="#1d4ed8",
            command=self._save_project,
        )
        self.save_btn.grid(row=0, column=2)

    def _create_content(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, padx=24, pady=(0, 24), sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self._create_form_panel(content)
        self._create_items_panel(content)

    def _create_form_panel(self, parent):
        form = ctk.CTkScrollableFrame(
            parent, corner_radius=12, label_text="  Book Metadata  ",
            label_font=ctk.CTkFont(size=14, weight="bold"),
        )
        form.grid(row=0, column=0, padx=(0, 8), pady=4, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)
        settings = self.app.get_settings()

        row = 0
        
        self._field_label(form, "Mode", row); row += 1
        self.mode_menu = ctk.CTkOptionMenu(
            form, values=["Text eBook (Story/Reflowable)", "Image eBook (Picture Book)"],
            width=240, height=34, command=self._on_mode_change
        )
        self.mode_menu.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="w"); row += 1

        self._field_label(form, "Book Title *", row); row += 1
        self.title_entry = ctk.CTkEntry(form, placeholder_text="My eBook", height=36)
        self.title_entry.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1

        self._field_label(form, "Subtitle", row); row += 1
        self.subtitle_entry = ctk.CTkEntry(form, placeholder_text="A Great Story", height=36)
        self.subtitle_entry.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1

        self._field_label(form, "Author", row); row += 1
        self.author_entry = ctk.CTkEntry(form, placeholder_text="Author Name", height=36)
        self.author_entry.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1
        if settings.get("author_name"):
            self.author_entry.insert(0, settings.get("author_name"))

        self._field_label(form, "Publisher", row); row += 1
        self.publisher_entry = ctk.CTkEntry(form, placeholder_text="Self Published", height=36)
        self.publisher_entry.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1

        self._field_label(form, "Copyright Year/Notice", row); row += 1
        self.copyright_entry = ctk.CTkEntry(form, placeholder_text="© 2026 Author Name", height=36)
        self.copyright_entry.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1

        self._field_label(form, "Language", row); row += 1
        self.lang_entry = ctk.CTkEntry(form, placeholder_text="en", height=36)
        self.lang_entry.insert(0, "en")
        self.lang_entry.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1

        self._field_label(form, "ISBN (Optional)", row); row += 1
        self.isbn_entry = ctk.CTkEntry(form, placeholder_text="978-...", height=36)
        self.isbn_entry.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1

        self._field_label(form, "Description", row); row += 1
        self.desc_textbox = ctk.CTkTextbox(form, height=80)
        self.desc_textbox.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1

        self._field_label(form, "About the Author (Auto-page)", row); row += 1
        self.about_textbox = ctk.CTkTextbox(form, height=80)
        self.about_textbox.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1

        self._field_label(form, "Thank You / Review Request (Auto-page)", row); row += 1
        self.thanks_textbox = ctk.CTkTextbox(form, height=80)
        self.thanks_textbox.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1

        self.status_label = ctk.CTkLabel(
            form, text="", font=ctk.CTkFont(size=12),
            text_color=("gray45", "gray55"), wraplength=260, justify="left",
        )
        self.status_label.grid(row=row, column=0, padx=16, pady=(4, 8), sticky="w"); row += 1
        self._update_status()

    @staticmethod
    def _field_label(parent, text, row):
        ctk.CTkLabel(
            parent, text=text, font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray30", "gray70"),
        ).grid(row=row, column=0, padx=16, pady=(8, 4), sticky="w")

    def _on_mode_change(self, val):
        self.mode = "text" if "Text" in val else "image"
        self._refresh_items_list()
        self._render_property_editor()

    def _create_items_panel(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=12)
        panel.grid(row=0, column=1, padx=(8, 0), pady=4, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(panel, text="Book Content", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(16, 8), sticky="w"
        )

        btn_frame = ctk.CTkFrame(panel, fg_color="transparent")
        btn_frame.grid(row=1, column=0, padx=16, pady=(0, 4), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_frame, text="🔤  Add Chapter (Text)", height=32, corner_radius=6,
            command=self._add_text_item
        ).grid(row=0, column=0, padx=(0, 4), pady=2, sticky="ew")

        ctk.CTkButton(
            btn_frame, text="🖼  Add Image (Page)", height=32, corner_radius=6,
            command=self._add_image_items
        ).grid(row=0, column=1, padx=(4, 0), pady=2, sticky="ew")

        drop_hint = ctk.CTkLabel(
            panel, text="Drag & drop PNG/JPG/SVG files here",
            font=ctk.CTkFont(size=10), text_color=("gray50", "gray50"),
        )
        drop_hint.grid(row=2, column=0, padx=16, pady=(0, 8), sticky="w")
        
        # Setup drag and drop for images
        try:
            panel.drop_target_register('DND_Files')
            panel.dnd_bind('<<Drop>>', self._on_drop)
        except Exception:
            pass

        self.items_list = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.items_list.grid(row=3, column=0, padx=8, pady=(0, 8), sticky="nsew")
        self.items_list.grid_columnconfigure(0, weight=1)

        self.prop_container = ctk.CTkFrame(panel, corner_radius=10, fg_color=("gray90", "gray16"))
        self.prop_container.grid(row=4, column=0, padx=8, pady=(0, 12), sticky="ew")
        self.prop_container.grid_columnconfigure(0, weight=1)
        self._render_property_editor()

    def _on_drop(self, event):
        data = event.data
        if '{' in data:
            import re
            files = re.findall(r'\{([^}]+)\}', data)
        else:
            files = data.split()
        for f in files:
            if Path(f).suffix.lower() in VALID_IMAGE_EXT:
                self._add_image_item(f)
        self._refresh_items_list()
        
    def _add_text_item(self):
        item = {
            "id": str(uuid.uuid4()),
            "type": "text",
            "title": f"Chapter {len(self.items) + 1}",
            "content": "Write your chapter content here..."
        }
        self.items.append(item)
        self.selected_item_id = item["id"]
        self._refresh_items_list()
        self._render_property_editor()

    def _add_image_items(self):
        files = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.svg")]
        )
        for f in files:
            self._add_image_item(f)
        self._refresh_items_list()
        self._render_property_editor()

    def _add_image_item(self, path):
        item = {
            "id": str(uuid.uuid4()),
            "type": "image",
            "title": "",
            "description": "",
            "image_path": path
        }
        self.items.append(item)
        self.selected_item_id = item["id"]

    def _refresh_items_list(self):
        for w in self.items_list.winfo_children():
            w.destroy()

        for idx, item in enumerate(self.items):
            is_selected = item["id"] == self.selected_item_id
            row = ctk.CTkFrame(
                self.items_list, corner_radius=6,
                fg_color=("gray80", "gray28") if is_selected else ("gray88", "gray20"),
            )
            row.grid(sticky="ew", pady=2)
            row.grid_columnconfigure(1, weight=1)

            icon = "🖼" if item["type"] == "image" else "🔤"
            label_text = item["title"] or Path(item.get("image_path", "Untitled")).name
            if len(label_text) > 20:
                label_text = label_text[:18] + "…"

            btn = ctk.CTkButton(
                row, text=f"{idx+1}. {icon} {label_text}", anchor="w", height=30,
                fg_color="transparent", hover_color=("gray70", "gray32"),
                font=ctk.CTkFont(size=12),
                command=lambda lid=item["id"]: self._select_item(lid),
            )
            btn.grid(row=0, column=0, columnspan=2, sticky="ew", padx=2, pady=2)

            ctrl_frame = ctk.CTkFrame(row, fg_color="transparent")
            ctrl_frame.grid(row=1, column=0, columnspan=2, sticky="e", padx=4, pady=(0, 4))

            ctk.CTkButton(
                ctrl_frame, text="▲", width=24, height=22,
                command=lambda lid=item["id"]: self._move_item(lid, -1)
            ).grid(row=0, column=0, padx=1)
            ctk.CTkButton(
                ctrl_frame, text="▼", width=24, height=22,
                command=lambda lid=item["id"]: self._move_item(lid, 1)
            ).grid(row=0, column=1, padx=1)
            ctk.CTkButton(
                ctrl_frame, text="✕", width=24, height=22, fg_color="#dc2626", hover_color="#b91c1c",
                command=lambda lid=item["id"]: self._delete_item(lid)
            ).grid(row=0, column=2, padx=1)

    def _select_item(self, lid):
        self.selected_item_id = lid
        self._refresh_items_list()
        self._render_property_editor()

    def _move_item(self, lid, direction):
        idx = next((i for i, x in enumerate(self.items) if x["id"] == lid), -1)
        if idx == -1: return
        new_idx = idx + direction
        if 0 <= new_idx < len(self.items):
            self.items.insert(new_idx, self.items.pop(idx))
            self._refresh_items_list()

    def _delete_item(self, lid):
        self.items = [i for i in self.items if i["id"] != lid]
        if self.selected_item_id == lid:
            self.selected_item_id = None
        self._refresh_items_list()
        self._render_property_editor()

    def _render_property_editor(self):
        for w in self.prop_container.winfo_children():
            w.destroy()

        item = next((i for i in self.items if i["id"] == self.selected_item_id), None)
        if item is None:
            ctk.CTkLabel(
                self.prop_container, text="Select a chapter or image to edit.",
                font=ctk.CTkFont(size=11), text_color=("gray45", "gray55")
            ).grid(row=0, column=0, padx=12, pady=12)
            return

        ctk.CTkLabel(
            self.prop_container, text="Edit Properties", font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        r = 1
        # Title
        ctk.CTkLabel(self.prop_container, text="Title / Headline:").grid(row=r, column=0, padx=12, sticky="w"); r += 1
        title_var = ctk.StringVar(value=item.get("title", ""))
        title_entry = ctk.CTkEntry(self.prop_container, textvariable=title_var, height=32)
        title_entry.grid(row=r, column=0, padx=12, pady=(0, 8), sticky="ew"); r += 1
        title_var.trace_add("write", lambda *a: self._update_item_field(item, "title", title_var.get()))

        if item["type"] == "text":
            ctk.CTkLabel(self.prop_container, text="Content (HTML or plain text):").grid(row=r, column=0, padx=12, sticky="w"); r += 1
            content_box = ctk.CTkTextbox(self.prop_container, height=150)
            content_box.grid(row=r, column=0, padx=12, pady=(0, 12), sticky="ew"); r += 1
            content_box.insert("0.0", item.get("content", ""))
            content_box.bind("<KeyRelease>", lambda e: self._update_item_field(item, "content", content_box.get("0.0", "end-1c")))

        elif item["type"] == "image":
            ctk.CTkLabel(self.prop_container, text="Image Description / Caption:").grid(row=r, column=0, padx=12, sticky="w"); r += 1
            desc_var = ctk.StringVar(value=item.get("description", ""))
            desc_entry = ctk.CTkEntry(self.prop_container, textvariable=desc_var, height=32)
            desc_entry.grid(row=r, column=0, padx=12, pady=(0, 12), sticky="ew"); r += 1
            desc_var.trace_add("write", lambda *a: self._update_item_field(item, "description", desc_var.get()))
            
            ctk.CTkLabel(self.prop_container, text=f"File: {Path(item.get('image_path', '')).name}", text_color="gray50").grid(row=r, column=0, padx=12, pady=4, sticky="w")

    def _update_item_field(self, item, field, value):
        item[field] = value
        if field == "title":
            self._refresh_items_list()

    def _update_status(self):
        if not EBOOKLIB_AVAILABLE:
            self.status_label.configure(text="⚠ EbookLib not installed. Run: pip install EbookLib")
        elif not PIL_AVAILABLE:
            self.status_label.configure(text="⚠ Pillow not installed. Images won't be optimized.")
        else:
            self.status_label.configure(text="Ready")

    def _get_metadata(self):
        return {
            "title": self.title_entry.get().strip(),
            "subtitle": self.subtitle_entry.get().strip(),
            "author": self.author_entry.get().strip(),
            "publisher": self.publisher_entry.get().strip(),
            "copyright": self.copyright_entry.get().strip(),
            "language": self.lang_entry.get().strip(),
            "isbn": self.isbn_entry.get().strip(),
            "description": self.desc_textbox.get("0.0", "end-1c").strip(),
            "about_author": self.about_textbox.get("0.0", "end-1c").strip(),
            "thank_you": self.thanks_textbox.get("0.0", "end-1c").strip(),
        }

    def _validate_export(self):
        if not self.title_entry.get().strip():
            messagebox.showwarning("Validation Error", "Title is required.")
            return False
        if not EBOOKLIB_AVAILABLE:
            messagebox.showerror("Dependency Error", "EbookLib is required to generate EPUBs.")
            return False
        return True

    def _export_epub(self):
        if not self._validate_export(): return
        default_path = self.app.get_settings().get("default_export_path", str(Path.home() / "Documents"))
        title = self.title_entry.get().strip().replace(' ', '_')
        output_path = filedialog.asksaveasfilename(
            title="Export EPUB", defaultextension=".epub",
            filetypes=[("EPUB Files", "*.epub")], initialdir=default_path,
            initialfile=f"{title}.epub",
        )
        if not output_path: return
        self._run_export(output_path, preview=False)

    def _preview_epub(self):
        if not self._validate_export(): return
        output_path = os.path.join(tempfile.gettempdir(), f"preview_{uuid.uuid4().hex}.epub")
        self._run_export(output_path, preview=True)

    def _run_export(self, output_path, preview=False):
        self.preview_btn.configure(state="disabled")
        self.export_btn.configure(state="disabled")
        meta = self._get_metadata()
        items = list(self.items)
        mode = self.mode

        def task():
            try:
                engine = EpubEngine(metadata=meta, items=items, output_path=output_path, mode=mode)
                engine.build()
                self.after(0, lambda: self._on_export_complete(output_path, preview))
            except Exception as e:
                self.after(0, lambda: self._on_export_error(str(e)))

        threading.Thread(target=task, daemon=True).start()

    def _on_export_complete(self, output_path, preview):
        self.preview_btn.configure(state="normal")
        self.export_btn.configure(state="normal")
        if preview:
            try:
                os.startfile(output_path)
            except Exception as e:
                messagebox.showwarning("Preview Error", f"Could not open EPUB viewer: {e}")
        else:
            messagebox.showinfo("Export Complete", f"EPUB saved successfully!\n\n{output_path}")

    def _on_export_error(self, err):
        self.preview_btn.configure(state="normal")
        self.export_btn.configure(state="normal")
        messagebox.showerror("Export Failed", f"An error occurred while generating the EPUB:\n\n{err}")

    def _save_project(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Missing Title", "Please enter a book title to save.")
            return

        epub_data = {
            "metadata": self._get_metadata(),
            "items": self.items,
            "mode": self.mode_menu.get(),
        }

        now = datetime.now().isoformat()

        if self.current_project_id:
            project_data = {
                "name": title,
                "description": "EPUB design project",
                "status": "in_progress",
                "modified_at": now,
                "epub_data": epub_data,
            }
            self.app.update_project(self.current_project_id, project_data)
            messagebox.showinfo("Saved", "EPUB project updated successfully!")
        else:
            project_data = {
                "id": str(uuid.uuid4()),
                "name": title,
                "description": "EPUB design project",
                "status": "in_progress",
                "created_at": now,
                "modified_at": now,
                "epub_data": epub_data,
            }
            self.current_project_id = project_data["id"]
            self.app.add_project(project_data)
            messagebox.showinfo("Saved", "EPUB project saved successfully!")

    def load_project(self, project: dict):
        epub_data = project.get("epub_data")
        if not epub_data: return

        self.current_project_id = project.get("id")
        meta = epub_data.get("metadata", {})
        
        self.title_entry.delete(0, "end"); self.title_entry.insert(0, meta.get("title", ""))
        self.subtitle_entry.delete(0, "end"); self.subtitle_entry.insert(0, meta.get("subtitle", ""))
        self.author_entry.delete(0, "end"); self.author_entry.insert(0, meta.get("author", ""))
        self.publisher_entry.delete(0, "end"); self.publisher_entry.insert(0, meta.get("publisher", ""))
        self.copyright_entry.delete(0, "end"); self.copyright_entry.insert(0, meta.get("copyright", ""))
        self.lang_entry.delete(0, "end"); self.lang_entry.insert(0, meta.get("language", "en"))
        self.isbn_entry.delete(0, "end"); self.isbn_entry.insert(0, meta.get("isbn", ""))
        
        self.desc_textbox.delete("0.0", "end"); self.desc_textbox.insert("0.0", meta.get("description", ""))
        self.about_textbox.delete("0.0", "end"); self.about_textbox.insert("0.0", meta.get("about_author", ""))
        self.thanks_textbox.delete("0.0", "end"); self.thanks_textbox.insert("0.0", meta.get("thank_you", ""))

        self.mode_menu.set(epub_data.get("mode", "Text eBook (Story/Reflowable)"))
        self.mode = "text" if "Text" in self.mode_menu.get() else "image"
        
        self.items = epub_data.get("items", [])
        self.selected_item_id = None
        self._refresh_items_list()
        self._render_property_editor()
