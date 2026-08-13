"""
Coloring Book Generator Frame - Core generation module.
Handles book metadata, image import, automatic image processing,
page numbering, print-ready PDF generation, PDF preview, progress bar,
and project save/load.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
import uuid
import json
import os
import tempfile
import threading

# PDF and image processing imports
try:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Core modules
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from core.pdf_engine import PDFEngine, TRIM_SIZES, BLEED_SIZE
    from core.project_io import ProjectIO
    from core.logger import get_logger
    PDF_ENGINE_AVAILABLE = True
except ImportError:
    PDF_ENGINE_AVAILABLE = False
    TRIM_SIZES = {
        "5 x 8 inches": (5 * 72, 8 * 72),
        "5.5 x 8.5 inches": (5.5 * 72, 8.5 * 72),
        "6 x 9 inches": (6 * 72, 9 * 72),
        "7 x 10 inches": (7 * 72, 10 * 72),
        "8 x 10 inches": (8 * 72, 10 * 72),
        "8.5 x 8.5 inches (Square)": (8.5 * 72, 8.5 * 72),
        "8.5 x 11 inches (Letter)": (8.5 * 72, 11 * 72),
    }
    BLEED_SIZE = 0.125 * 72

# Get logger
try:
    logger = get_logger("generator")
except Exception:
    import logging
    logger = logging.getLogger("generator")


class GeneratorFrame(ctk.CTkFrame):
    """Coloring Book Generator view with metadata, image import, and PDF generation."""

    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.app = app
        self.imported_images = []  # List of image file paths
        self.preview_refs = []  # Keep references to prevent garbage collection
        self.current_project_id = None  # Track loaded project for updates

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_header()
        self._create_content()

    def _create_header(self):
        """Create the page header."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=32, pady=(28, 12), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="Coloring Book Generator",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="Create print-ready coloring book PDFs",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray60"),
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        # Button frame (right side)
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, rowspan=2, sticky="e")

        # Preview PDF button
        self.preview_btn = ctk.CTkButton(
            btn_frame,
            text="👁  Preview",
            font=ctk.CTkFont(size=13),
            height=40,
            width=110,
            corner_radius=8,
            fg_color=("#7c3aed", "#7c3aed"),
            hover_color=("#6d28d9", "#6d28d9"),
            command=self._preview_pdf,
        )
        self.preview_btn.grid(row=0, column=0, padx=(0, 8))

        # Generate PDF button
        self.generate_btn = ctk.CTkButton(
            btn_frame,
            text="📄  Generate PDF",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            width=160,
            corner_radius=8,
            fg_color="#10b981",
            hover_color="#059669",
            command=self._generate_pdf,
        )
        self.generate_btn.grid(row=0, column=1, padx=(0, 8))

        # Save project button
        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="💾  Save",
            font=ctk.CTkFont(size=13),
            height=40,
            width=100,
            corner_radius=8,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._save_project,
        )
        self.save_btn.grid(row=0, column=2)

    def _create_content(self):
        """Create the main content area with two columns."""
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, padx=24, pady=(0, 24), sticky="nsew")
        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=3)
        content.grid_rowconfigure(0, weight=1)

        # Left column: Book details form
        self._create_form_panel(content)

        # Right column: Image import and preview
        self._create_image_panel(content)

    # ─── Form Panel (Left Column) ──────────────────────────────────────────────

    def _create_form_panel(self, parent):
        """Create the book details form panel."""
        form_scroll = ctk.CTkScrollableFrame(
            parent, corner_radius=12, label_text="  Book Details  ",
            label_font=ctk.CTkFont(size=14, weight="bold"),
        )
        form_scroll.grid(row=0, column=0, padx=(8, 8), pady=4, sticky="nsew")
        form_scroll.grid_columnconfigure(0, weight=1)

        settings = self.app.get_settings()

        # Book Title
        self._create_field_label(form_scroll, "Book Title *", 0)
        self.title_entry = ctk.CTkEntry(
            form_scroll, placeholder_text="My Coloring Book", height=36
        )
        self.title_entry.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="ew")

        # Subtitle
        self._create_field_label(form_scroll, "Subtitle", 2)
        self.subtitle_entry = ctk.CTkEntry(
            form_scroll, placeholder_text="A Fun Activity Book for Kids", height=36
        )
        self.subtitle_entry.grid(row=3, column=0, padx=16, pady=(0, 12), sticky="ew")

        # Author
        self._create_field_label(form_scroll, "Author", 4)
        self.author_entry = ctk.CTkEntry(
            form_scroll, placeholder_text="Author Name", height=36
        )
        self.author_entry.grid(row=5, column=0, padx=16, pady=(0, 12), sticky="ew")
        # Pre-fill from settings
        author = settings.get("author_name", "")
        if author:
            self.author_entry.insert(0, author)

        # Theme
        self._create_field_label(form_scroll, "Theme", 6)
        self.theme_entry = ctk.CTkEntry(
            form_scroll, placeholder_text="Animals, Nature, Fantasy...", height=36
        )
        self.theme_entry.grid(row=7, column=0, padx=16, pady=(0, 12), sticky="ew")

        # Age Group
        self._create_field_label(form_scroll, "Age Group", 8)
        self.age_group_menu = ctk.CTkOptionMenu(
            form_scroll,
            values=[
                "Toddlers (2-4)",
                "Kids (4-8)",
                "Tweens (8-12)",
                "Teens (12+)",
                "Adults",
                "All Ages",
            ],
            width=200,
            height=34,
        )
        self.age_group_menu.set("Kids (4-8)")
        self.age_group_menu.grid(row=9, column=0, padx=16, pady=(0, 12), sticky="w")

        # Number of Pages
        self._create_field_label(form_scroll, "Number of Pages", 10)
        self.pages_entry = ctk.CTkEntry(
            form_scroll, placeholder_text="30", height=36, width=120
        )
        self.pages_entry.grid(row=11, column=0, padx=16, pady=(0, 12), sticky="w")

        # Trim Size
        self._create_field_label(form_scroll, "Trim Size", 12)
        self.trim_size_menu = ctk.CTkOptionMenu(
            form_scroll,
            values=list(TRIM_SIZES.keys()),
            width=240,
            height=34,
        )
        default_size = settings.get("default_page_size", "8.5 x 11 inches (Letter)")
        if default_size in TRIM_SIZES:
            self.trim_size_menu.set(default_size)
        else:
            self.trim_size_menu.set("8.5 x 11 inches (Letter)")
        self.trim_size_menu.grid(row=13, column=0, padx=16, pady=(0, 12), sticky="w")

        # Bleed
        self._create_field_label(form_scroll, "Bleed (0.125\" added to each edge)", 14)
        self.bleed_var = ctk.StringVar(value="Yes")
        bleed_frame = ctk.CTkFrame(form_scroll, fg_color="transparent")
        bleed_frame.grid(row=15, column=0, padx=16, pady=(0, 12), sticky="w")

        self.bleed_yes = ctk.CTkRadioButton(
            bleed_frame, text="Yes", variable=self.bleed_var, value="Yes"
        )
        self.bleed_yes.grid(row=0, column=0, padx=(0, 20))

        self.bleed_no = ctk.CTkRadioButton(
            bleed_frame, text="No", variable=self.bleed_var, value="No"
        )
        self.bleed_no.grid(row=0, column=1)

        # Separator
        sep = ctk.CTkFrame(form_scroll, height=1, fg_color=("gray80", "gray25"))
        sep.grid(row=16, column=0, padx=16, pady=16, sticky="ew")

        # Progress bar section (hidden by default)
        self.progress_frame = ctk.CTkFrame(form_scroll, fg_color="transparent")
        self.progress_frame.grid(row=17, column=0, padx=16, pady=(0, 8), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
        )
        self.progress_label.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame, height=16, corner_radius=8
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        self.progress_bar.set(0)

        self.progress_percent = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#10b981", "#10b981"),
        )
        self.progress_percent.grid(row=2, column=0, sticky="w")

        # Hide progress initially
        self.progress_frame.grid_remove()

        # Status / info area
        self.status_label = ctk.CTkLabel(
            form_scroll,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray45", "gray55"),
            wraplength=280,
        )
        self.status_label.grid(row=18, column=0, padx=16, pady=(0, 8), sticky="w")

        self._update_status()

    # ─── Image Panel (Right Column) ────────────────────────────────────────────

    def _create_image_panel(self, parent):
        """Create the image import and preview panel."""
        image_frame = ctk.CTkFrame(parent, corner_radius=12)
        image_frame.grid(row=0, column=1, padx=(8, 8), pady=4, sticky="nsew")
        image_frame.grid_columnconfigure(0, weight=1)
        image_frame.grid_rowconfigure(2, weight=1)

        # Section header
        header_frame = ctk.CTkFrame(image_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header_frame,
            text="Image Import",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        self.image_count_label = ctk.CTkLabel(
            header_frame,
            text="0 images",
            font=ctk.CTkFont(size=12),
            text_color=("gray45", "gray55"),
        )
        self.image_count_label.grid(row=0, column=1, sticky="e")

        # Import buttons row
        btn_frame = ctk.CTkFrame(image_frame, fg_color="transparent")
        btn_frame.grid(row=1, column=0, padx=16, pady=(4, 8), sticky="ew")

        import_buttons = [
            ("📷 Import PNG", self._import_png),
            ("🖼️ Import JPG", self._import_jpg),
            ("🎨 Import SVG", self._import_svg),
            ("📂 Import All", self._import_all),
            ("🗑️ Clear All", self._clear_images),
        ]

        for i, (text, cmd) in enumerate(import_buttons):
            btn = ctk.CTkButton(
                btn_frame,
                text=text,
                font=ctk.CTkFont(size=11),
                height=32,
                width=100,
                corner_radius=6,
                fg_color=("gray78", "gray28") if "Clear" not in text else "#dc2626",
                hover_color=("gray68", "gray35") if "Clear" not in text else "#b91c1c",
                text_color=("gray10", "gray90") if "Clear" not in text else "white",
                command=cmd,
            )
            btn.grid(row=0, column=i, padx=3, pady=2)

        # Drop zone / Image preview area
        self.preview_frame = ctk.CTkFrame(
            image_frame,
            corner_radius=10,
            fg_color=("gray92", "gray17"),
            border_width=2,
            border_color=("gray75", "gray30"),
        )
        self.preview_frame.grid(row=2, column=0, padx=16, pady=(4, 16), sticky="nsew")
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(0, weight=1)

        # Drop zone placeholder
        self.drop_label = ctk.CTkLabel(
            self.preview_frame,
            text="🖼️\n\nDrag & Drop images here\nor use the import buttons above\n\nSupported: PNG, JPG, SVG",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray50"),
            justify="center",
        )
        self.drop_label.grid(row=0, column=0, pady=60)

        # Scrollable image preview (hidden initially)
        self.image_scroll = ctk.CTkScrollableFrame(
            self.preview_frame, fg_color="transparent", corner_radius=0
        )

        # Bind drag and drop events
        self._setup_drag_drop()

    def _setup_drag_drop(self):
        """Setup drag and drop functionality."""
        try:
            self.preview_frame.drop_target_register('DND_Files')
            self.preview_frame.dnd_bind('<<Drop>>', self._on_drop)
        except (AttributeError, Exception):
            pass

    def _on_drop(self, event):
        """Handle file drop event."""
        files = self._parse_drop_data(event.data)
        valid_extensions = {'.png', '.jpg', '.jpeg', '.svg'}
        added = 0
        for f in files:
            if Path(f).suffix.lower() in valid_extensions:
                self._add_image(f)
                added += 1
        if added > 0:
            self._refresh_preview()
            self._update_status()

    @staticmethod
    def _parse_drop_data(data: str) -> list:
        """Parse drag and drop data string into file paths."""
        if '{' in data:
            import re
            return re.findall(r'\{([^}]+)\}', data)
        return data.split()

    # ─── Image Import Methods ──────────────────────────────────────────────────

    def _import_png(self):
        """Import PNG files."""
        self._import_files([("PNG Files", "*.png")])

    def _import_jpg(self):
        """Import JPG/JPEG files."""
        self._import_files([("JPEG Files", "*.jpg *.jpeg")])

    def _import_svg(self):
        """Import SVG files."""
        self._import_files([("SVG Files", "*.svg")])

    def _import_all(self):
        """Import all supported image formats."""
        self._import_files([
            ("All Images", "*.png *.jpg *.jpeg *.svg"),
            ("PNG Files", "*.png"),
            ("JPEG Files", "*.jpg *.jpeg"),
            ("SVG Files", "*.svg"),
        ])

    def _import_files(self, filetypes: list):
        """Open file dialog and import selected images."""
        files = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=filetypes + [("All Files", "*.*")],
        )
        if files:
            for f in files:
                self._add_image(f)
            self._refresh_preview()
            self._update_status()

    def _add_image(self, filepath: str):
        """Add an image to the import list."""
        filepath = str(filepath)
        if filepath not in self.imported_images:
            self.imported_images.append(filepath)

    def _clear_images(self):
        """Clear all imported images."""
        if not self.imported_images:
            return
        self.imported_images.clear()
        self.preview_refs.clear()
        self._refresh_preview()
        self._update_status()

    def _refresh_preview(self):
        """Refresh the image preview area."""
        count = len(self.imported_images)
        self.image_count_label.configure(text=f"{count} image{'s' if count != 1 else ''}")

        if count == 0:
            self.image_scroll.grid_forget()
            self.drop_label.grid(row=0, column=0, pady=60)
            return

        self.drop_label.grid_forget()
        self.image_scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        for widget in self.image_scroll.winfo_children():
            widget.destroy()
        self.preview_refs.clear()

        self.image_scroll.grid_columnconfigure((0, 1, 2), weight=1)

        for i, img_path in enumerate(self.imported_images):
            self._create_thumbnail(i, img_path)

    def _create_thumbnail(self, index: int, img_path: str):
        """Create a thumbnail preview card for an image."""
        row = index // 3
        col = index % 3

        card = ctk.CTkFrame(
            self.image_scroll,
            corner_radius=8,
            width=140,
            height=160,
            fg_color=("gray85", "gray22"),
        )
        card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)

        if PIL_AVAILABLE and Path(img_path).suffix.lower() in ('.png', '.jpg', '.jpeg'):
            try:
                img = Image.open(img_path)
                img.thumbnail((120, 100), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.preview_refs.append(photo)

                img_label = ctk.CTkLabel(card, image=photo, text="")
                img_label.grid(row=0, column=0, padx=8, pady=(8, 4))
            except Exception:
                self._create_placeholder_thumb(card)
        else:
            self._create_placeholder_thumb(card)

        filename = Path(img_path).name
        if len(filename) > 18:
            filename = filename[:15] + "..."

        name_label = ctk.CTkLabel(
            card,
            text=filename,
            font=ctk.CTkFont(size=10),
            text_color=("gray40", "gray60"),
        )
        name_label.grid(row=1, column=0, padx=4, pady=(0, 4))

        page_label = ctk.CTkLabel(
            card,
            text=f"Page {index + 1}",
            font=ctk.CTkFont(size=9),
            text_color=("gray50", "gray50"),
        )
        page_label.grid(row=2, column=0, padx=4, pady=(0, 6))

        remove_btn = ctk.CTkButton(
            card,
            text="✕",
            width=24,
            height=24,
            corner_radius=12,
            fg_color=("#dc2626", "#dc2626"),
            hover_color=("#b91c1c", "#b91c1c"),
            font=ctk.CTkFont(size=11),
            command=lambda idx=index: self._remove_image(idx),
        )
        remove_btn.place(relx=0.88, rely=0.05, anchor="ne")

    def _create_placeholder_thumb(self, card):
        """Create a placeholder for images that can't be previewed."""
        placeholder = ctk.CTkLabel(
            card,
            text="🖼️",
            font=ctk.CTkFont(size=36),
        )
        placeholder.grid(row=0, column=0, padx=8, pady=(12, 4))

    def _remove_image(self, index: int):
        """Remove an image from the list by index."""
        if 0 <= index < len(self.imported_images):
            self.imported_images.pop(index)
            self._refresh_preview()
            self._update_status()

    # ─── Status Update ─────────────────────────────────────────────────────────

    def _update_status(self):
        """Update the status label with current state info."""
        count = len(self.imported_images)
        pages_text = self.pages_entry.get().strip()

        lines = []
        if count > 0:
            lines.append(f"✓ {count} image(s) imported")
        else:
            lines.append("⚠ No images imported yet")

        if pages_text and pages_text.isdigit():
            target = int(pages_text)
            if count < target:
                lines.append(f"ℹ Need {target - count} more images for {target} pages")
            elif count > target:
                lines.append(f"ℹ Only first {target} images will be used")

        if not REPORTLAB_AVAILABLE:
            lines.append("⚠ ReportLab not installed (pip install reportlab)")
        if not PIL_AVAILABLE:
            lines.append("⚠ Pillow not installed (pip install Pillow)")

        # Show project status
        if self.current_project_id:
            lines.append(f"📁 Project loaded (will update on save)")

        self.status_label.configure(text="\n".join(lines))

    # ─── Progress Bar ──────────────────────────────────────────────────────────

    def _show_progress(self):
        """Show the progress bar."""
        self.progress_frame.grid()
        self.progress_bar.set(0)
        self.progress_label.configure(text="Preparing...")
        self.progress_percent.configure(text="0%")

    def _hide_progress(self):
        """Hide the progress bar."""
        self.progress_frame.grid_remove()

    def _update_progress(self, current: int, total: int, message: str):
        """Update progress bar from the generation thread (thread-safe)."""
        self.after(0, lambda: self._set_progress(current, total, message))

    def _set_progress(self, current: int, total: int, message: str):
        """Set progress bar values (must be called from main thread)."""
        if total > 0:
            progress = current / total
            self.progress_bar.set(progress)
            percent = int(progress * 100)
            self.progress_percent.configure(text=f"{percent}%")
        self.progress_label.configure(text=message)

    # ─── PDF Generation ────────────────────────────────────────────────────────

    def _validate_for_generation(self) -> bool:
        """Validate inputs before PDF generation. Returns True if valid."""
        book_title = self.title_entry.get().strip()
        if not book_title:
            messagebox.showwarning("Missing Title", "Please enter a book title.")
            return False

        if not self.imported_images:
            messagebox.showwarning("No Images", "Please import at least one image.")
            return False

        if not REPORTLAB_AVAILABLE:
            messagebox.showerror(
                "Missing Dependency",
                "ReportLab is required for PDF generation.\n\n"
                "Install it with: pip install reportlab"
            )
            return False

        if not PIL_AVAILABLE:
            messagebox.showerror(
                "Missing Dependency",
                "Pillow is required for image processing.\n\n"
                "Install it with: pip install Pillow"
            )
            return False

        return True

    def _generate_pdf(self):
        """Generate a print-ready PDF and save to user-selected location."""
        if not self._validate_for_generation():
            return

        # Get export path
        settings = self.app.get_settings()
        default_path = settings.get("default_export_path", str(Path.home() / "Documents"))
        book_title = self.title_entry.get().strip()

        output_path = filedialog.asksaveasfilename(
            title="Export Print-Ready PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            initialdir=default_path,
            initialfile=f"{book_title.replace(' ', '_')}_KDP.pdf",
        )

        if not output_path:
            return

        logger.info(f"Generating PDF: {output_path}")
        self._start_generation(output_path, is_preview=False)

    def _preview_pdf(self):
        """Generate a temporary PDF for preview."""
        if not self._validate_for_generation():
            return

        # Create temp file for preview
        temp_dir = tempfile.gettempdir()
        book_title = self.title_entry.get().strip()
        output_path = os.path.join(temp_dir, f"{book_title.replace(' ', '_')}_preview.pdf")

        logger.info(f"Generating preview PDF: {output_path}")
        self._start_generation(output_path, is_preview=True)

    def _start_generation(self, output_path: str, is_preview: bool = False):
        """Start PDF generation in a background thread."""
        # Disable buttons
        self.generate_btn.configure(state="disabled", text="⏳ Generating...")
        self.preview_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")

        # Show progress
        self._show_progress()

        # Run in thread
        thread = threading.Thread(
            target=self._run_generation,
            args=(output_path, is_preview),
            daemon=True,
        )
        thread.start()

    def _run_generation(self, output_path: str, is_preview: bool):
        """Run PDF generation in background thread."""
        try:
            if PDF_ENGINE_AVAILABLE:
                # Use the full PDF engine
                pages_text = self.pages_entry.get().strip()
                num_pages = int(pages_text) if pages_text and pages_text.isdigit() else None

                engine = PDFEngine(
                    output_path=output_path,
                    title=self.title_entry.get().strip(),
                    subtitle=self.subtitle_entry.get().strip(),
                    author=self.author_entry.get().strip(),
                    trim_size=self.trim_size_menu.get(),
                    use_bleed=self.bleed_var.get() == "Yes",
                    images=self.imported_images,
                    num_pages=num_pages,
                    progress_callback=self._update_progress,
                )
                engine.generate()
            else:
                # Fallback: basic generation
                self._build_pdf_fallback(output_path)

            # Success
            self.after(0, lambda: self._on_generation_complete(output_path, is_preview))

        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            self.after(0, lambda: self._on_generation_error(str(e)))

    def _build_pdf_fallback(self, output_path: str):
        """Fallback PDF generation if core engine is not available."""
        trim_size_name = self.trim_size_menu.get()
        trim_w, trim_h = TRIM_SIZES.get(trim_size_name, (8.5 * 72, 11 * 72))
        use_bleed = self.bleed_var.get() == "Yes"
        bleed = BLEED_SIZE if use_bleed else 0
        page_w = trim_w + (2 * bleed)
        page_h = trim_h + (2 * bleed)

        pages_text = self.pages_entry.get().strip()
        if pages_text and pages_text.isdigit():
            num_pages = min(int(pages_text), len(self.imported_images))
        else:
            num_pages = len(self.imported_images)

        c = canvas.Canvas(output_path, pagesize=(page_w, page_h))
        c.setTitle(self.title_entry.get().strip())
        c.setAuthor(self.author_entry.get().strip())

        margin = 0.5 * 72
        img_area_w = trim_w - (2 * margin)
        img_area_h = trim_h - (2 * margin) - (0.4 * 72)

        total = num_pages + 4
        step = 0

        # Title page
        step += 1
        self._update_progress(step, total, "Title page...")
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(page_w / 2, page_h / 2 + 40, self.title_entry.get().strip())
        if self.subtitle_entry.get().strip():
            c.setFont("Helvetica", 18)
            c.drawCentredString(page_w / 2, page_h / 2 - 10, self.subtitle_entry.get().strip())
        c.showPage()

        # Copyright page
        step += 1
        self._update_progress(step, total, "Copyright page...")
        c.setFont("Helvetica", 11)
        year = datetime.now().year
        c.drawCentredString(page_w / 2, page_h / 2, f"\u00A9 {year} {self.author_entry.get().strip()}")
        c.drawCentredString(page_w / 2, page_h / 2 - 20, "All rights reserved.")
        c.showPage()

        # Belongs to page
        step += 1
        self._update_progress(step, total, "Belongs to page...")
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(page_w / 2, page_h / 2 + 40, "This Book Belongs To:")
        c.setLineWidth(1.5)
        c.line(page_w / 2 - 100, page_h / 2 - 20, page_w / 2 + 100, page_h / 2 - 20)
        c.showPage()

        # Coloring pages
        for i in range(num_pages):
            step += 1
            self._update_progress(step, total, f"Image {i + 1}/{num_pages}...")
            img_path = self.imported_images[i]
            try:
                img = Image.open(img_path)
                if img.mode == 'RGBA':
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                img_w, img_h = img.size
                scale = min(img_area_w / img_w, img_area_h / img_h)
                new_w = img_w * scale
                new_h = img_h * scale
                x = bleed + margin + (img_area_w - new_w) / 2
                y = bleed + margin + (img_area_h - new_h) / 2 + (0.4 * 72)

                img_reader = ImageReader(img)
                c.drawImage(img_reader, x, y, width=new_w, height=new_h)
            except Exception:
                c.setFont("Helvetica", 12)
                c.drawCentredString(page_w / 2, page_h / 2, f"[Image error: {Path(img_path).name}]")

            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawCentredString(page_w / 2, bleed + (0.35 * 72), str(i + 1))
            c.setFillColorRGB(0, 0, 0)
            c.showPage()

        # Thank you page
        step += 1
        self._update_progress(step, total, "Thank you page...")
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(page_w / 2, page_h / 2 + 30, "Thank You!")
        c.setFont("Helvetica", 16)
        c.drawCentredString(page_w / 2, page_h / 2 - 20, "We hope you enjoyed this coloring book.")
        c.showPage()

        c.save()
        self._update_progress(total, total, "Complete!")

    def _on_generation_complete(self, output_path: str, is_preview: bool):
        """Handle successful PDF generation."""
        # Re-enable buttons
        self.generate_btn.configure(state="normal", text="📄  Generate PDF")
        self.preview_btn.configure(state="normal")
        self.save_btn.configure(state="normal")

        # Hide progress after a short delay
        self.after(1500, self._hide_progress)

        logger.info(f"PDF generated: {output_path}")

        if is_preview:
            # Open preview directly
            self._show_pdf_preview(output_path)
        else:
            # Ask to preview
            result = messagebox.askyesno(
                "PDF Generated",
                f"PDF saved successfully!\n\n{output_path}\n\nWould you like to preview it?",
            )
            if result:
                self._show_pdf_preview(output_path)

    def _on_generation_error(self, error_msg: str):
        """Handle PDF generation error."""
        self.generate_btn.configure(state="normal", text="📄  Generate PDF")
        self.preview_btn.configure(state="normal")
        self.save_btn.configure(state="normal")
        self._hide_progress()

        logger.error(f"Generation error: {error_msg}")
        messagebox.showerror("Generation Error", f"Failed to generate PDF:\n\n{error_msg}")

    # ─── PDF Preview ───────────────────────────────────────────────────────────

    def _show_pdf_preview(self, pdf_path: str):
        """Open a PDF preview window."""
        PDFPreviewWindow(self, pdf_path)

    # ─── Save Project ──────────────────────────────────────────────────────────

    def _save_project(self):
        """Save the current generator state as a project (create or update)."""
        book_title = self.title_entry.get().strip()
        if not book_title:
            messagebox.showwarning("Missing Title", "Please enter a book title to save.")
            return

        now = datetime.now().isoformat()

        generator_data = {
            "title": book_title,
            "subtitle": self.subtitle_entry.get().strip(),
            "author": self.author_entry.get().strip(),
            "theme": self.theme_entry.get().strip(),
            "age_group": self.age_group_menu.get(),
            "num_pages": self.pages_entry.get().strip(),
            "trim_size": self.trim_size_menu.get(),
            "bleed": self.bleed_var.get(),
            "images": self.imported_images.copy(),
        }

        if self.current_project_id:
            # Update existing project
            project_data = {
                "id": self.current_project_id,
                "name": book_title,
                "description": f"{self.theme_entry.get().strip()} coloring book for {self.age_group_menu.get()}",
                "page_size": self.trim_size_menu.get(),
                "author": self.author_entry.get().strip(),
                "page_count": len(self.imported_images),
                "status": "in_progress" if self.imported_images else "draft",
                "modified_at": now,
                "generator_data": generator_data,
                "pages": [],
            }
            # Find and update in app's projects list
            self.app.update_project(self.current_project_id, project_data)
            logger.info(f"Updated project: {book_title} ({self.current_project_id})")
            messagebox.showinfo("Saved", f"Project '{book_title}' updated successfully!")
        else:
            # Create new project
            project_data = {
                "id": str(uuid.uuid4()),
                "name": book_title,
                "description": f"{self.theme_entry.get().strip()} coloring book for {self.age_group_menu.get()}",
                "page_size": self.trim_size_menu.get(),
                "author": self.author_entry.get().strip(),
                "page_count": len(self.imported_images),
                "status": "in_progress" if self.imported_images else "draft",
                "created_at": now,
                "modified_at": now,
                "generator_data": generator_data,
                "pages": [],
            }
            self.current_project_id = project_data["id"]
            self.app.add_project(project_data)
            logger.info(f"Created project: {book_title} ({self.current_project_id})")
            messagebox.showinfo("Saved", f"Project '{book_title}' saved successfully!")

        self._update_status()

    # ─── Load Project ──────────────────────────────────────────────────────────

    def load_project(self, project: dict):
        """Load a project's generator data into the form."""
        gen_data = project.get("generator_data", {})
        if not gen_data:
            return

        # Set project ID for future updates
        self.current_project_id = project.get("id")

        # Clear and fill fields
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, gen_data.get("title", ""))

        self.subtitle_entry.delete(0, "end")
        self.subtitle_entry.insert(0, gen_data.get("subtitle", ""))

        self.author_entry.delete(0, "end")
        self.author_entry.insert(0, gen_data.get("author", ""))

        self.theme_entry.delete(0, "end")
        self.theme_entry.insert(0, gen_data.get("theme", ""))

        age_group = gen_data.get("age_group", "Kids (4-8)")
        self.age_group_menu.set(age_group)

        self.pages_entry.delete(0, "end")
        self.pages_entry.insert(0, gen_data.get("num_pages", ""))

        trim_size = gen_data.get("trim_size", "8.5 x 11 inches (Letter)")
        self.trim_size_menu.set(trim_size)

        self.bleed_var.set(gen_data.get("bleed", "Yes"))

        # Load images (filter out non-existent ones)
        self.imported_images = gen_data.get("images", [])
        self.imported_images = [p for p in self.imported_images if Path(p).exists()]

        self._refresh_preview()
        self._update_status()

        logger.info(f"Loaded project: {gen_data.get('title')} ({self.current_project_id})")

    def refresh(self):
        """Refresh the generator frame."""
        self._update_status()

    @staticmethod
    def _create_field_label(parent, text: str, row: int):
        """Create a form field label."""
        label = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray30", "gray70"),
        )
        label.grid(row=row, column=0, padx=16, pady=(8, 4), sticky="w")


class PDFPreviewWindow(ctk.CTkToplevel):
    """Window for previewing generated PDFs."""

    def __init__(self, parent, pdf_path: str):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.current_page = 0
        self.page_images = []
        self.photo_refs = []

        self.title(f"PDF Preview - {Path(pdf_path).name}")
        self.geometry("700x900")
        self.minsize(500, 600)
        self.transient(parent)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_toolbar()
        self._create_preview_area()
        self._create_footer()

        # Load PDF pages
        self._load_pdf()

    def _create_toolbar(self):
        """Create the preview toolbar."""
        toolbar = ctk.CTkFrame(self, height=50, corner_radius=0)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_columnconfigure(2, weight=1)

        # Navigation buttons
        self.prev_btn = ctk.CTkButton(
            toolbar, text="◀ Previous", width=100, height=32,
            command=self._prev_page,
        )
        self.prev_btn.grid(row=0, column=0, padx=(16, 4), pady=8)

        self.next_btn = ctk.CTkButton(
            toolbar, text="Next ▶", width=100, height=32,
            command=self._next_page,
        )
        self.next_btn.grid(row=0, column=1, padx=4, pady=8)

        # Page indicator
        self.page_indicator = ctk.CTkLabel(
            toolbar, text="Page 0 / 0", font=ctk.CTkFont(size=13)
        )
        self.page_indicator.grid(row=0, column=2, padx=16, pady=8)

        # Open file location button
        open_btn = ctk.CTkButton(
            toolbar, text="📂 Open Location", width=130, height=32,
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray38"),
            text_color=("gray10", "gray90"),
            command=self._open_file_location,
        )
        open_btn.grid(row=0, column=3, padx=(4, 16), pady=8)

    def _create_preview_area(self):
        """Create the scrollable preview area."""
        self.preview_scroll = ctk.CTkScrollableFrame(
            self, fg_color=("gray95", "gray12"), corner_radius=0
        )
        self.preview_scroll.grid(row=1, column=0, sticky="nsew")
        self.preview_scroll.grid_columnconfigure(0, weight=1)
        self.preview_scroll.grid_rowconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(
            self.preview_scroll,
            text="Loading preview...",
            font=ctk.CTkFont(size=14),
        )
        self.preview_label.grid(row=0, column=0, pady=40)

    def _create_footer(self):
        """Create the footer with file info."""
        footer = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color=("gray90", "gray16"))
        footer.grid(row=2, column=0, sticky="ew")

        self.file_info_label = ctk.CTkLabel(
            footer,
            text=f"  {self.pdf_path}",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray55"),
        )
        self.file_info_label.grid(row=0, column=0, padx=8, pady=4, sticky="w")

    def _load_pdf(self):
        """Load PDF pages for preview using pdf2image or fallback."""
        if not PIL_AVAILABLE:
            self.preview_label.configure(text="Pillow not available for preview.")
            return

        try:
            from pdf2image import convert_from_path
            self.page_images = convert_from_path(self.pdf_path, dpi=150)
            self._display_page(0)
        except ImportError:
            self.preview_label.configure(
                text=f"📄 PDF Generated Successfully\n\n"
                     f"File: {Path(self.pdf_path).name}\n"
                     f"Size: {self._get_file_size()}\n\n"
                     f"Install pdf2image for visual preview:\n"
                     f"pip install pdf2image\n\n"
                     f"The PDF file is ready for printing."
            )
            self.page_indicator.configure(text="Preview unavailable")
        except Exception as e:
            self.preview_label.configure(
                text=f"📄 PDF Generated Successfully\n\n"
                     f"File: {Path(self.pdf_path).name}\n"
                     f"Size: {self._get_file_size()}\n\n"
                     f"Could not render preview: {str(e)}\n\n"
                     f"The PDF file is ready for printing."
            )

    def _display_page(self, page_num: int):
        """Display a specific page."""
        if not self.page_images or page_num < 0 or page_num >= len(self.page_images):
            return

        self.current_page = page_num
        img = self.page_images[page_num]

        # Resize to fit preview area
        max_width = 600
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img_resized = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        photo = ImageTk.PhotoImage(img_resized)
        self.photo_refs = [photo]

        self.preview_label.configure(image=photo, text="")
        self.page_indicator.configure(
            text=f"Page {page_num + 1} / {len(self.page_images)}"
        )

        # Update button states
        self.prev_btn.configure(state="normal" if page_num > 0 else "disabled")
        self.next_btn.configure(
            state="normal" if page_num < len(self.page_images) - 1 else "disabled"
        )

    def _prev_page(self):
        """Go to previous page."""
        self._display_page(self.current_page - 1)

    def _next_page(self):
        """Go to next page."""
        self._display_page(self.current_page + 1)

    def _open_file_location(self):
        """Open the folder containing the PDF."""
        folder = str(Path(self.pdf_path).parent)
        try:
            os.startfile(folder)  # Windows
        except AttributeError:
            import subprocess
            subprocess.Popen(["xdg-open", folder])  # Linux

    def _get_file_size(self) -> str:
        """Get human-readable file size."""
        try:
            size = Path(self.pdf_path).stat().st_size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"
        except OSError:
            return "Unknown"
