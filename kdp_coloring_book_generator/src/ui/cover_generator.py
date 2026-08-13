"""
Cover Generator Frame - Professional full-wrap cover designer.
Lets the user design a front cover, back cover, and spine with draggable
image and text layers, auto-calculated spine width, bleed support, a
barcode placeholder, and offline export to PNG / vector PDF / 300 DPI PDF.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
from pathlib import Path
from datetime import datetime
import uuid
import tempfile
import threading
import os

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from core.cover_engine import (
        CoverLayout, CoverEngine, TRIM_SIZES, PAPER_TYPES, COVER_FONTS,
        DEFAULT_TRIM_SIZE, calculate_spine_width_points, spine_text_is_safe,
    )
    from core.logger import get_logger
    COVER_ENGINE_AVAILABLE = True
except ImportError:
    COVER_ENGINE_AVAILABLE = False
    TRIM_SIZES = {"8.5 x 11 inches (Letter)": (8.5 * 72, 11 * 72)}
    PAPER_TYPES = {"White (60lb / 90gsm)": 0.002252}
    COVER_FONTS = ["Helvetica", "Helvetica-Bold", "Times-Roman", "Courier"]
    DEFAULT_TRIM_SIZE = "8.5 x 11 inches (Letter)"

try:
    from core.logger import get_logger
    logger = get_logger("cover_generator")
except Exception:
    import logging
    logger = logging.getLogger("cover_generator")

# Optional SVG support (fully offline if the package happens to be installed;
# gracefully degrades to a placeholder otherwise -- no network calls either way).
try:
    import cairosvg
    SVG_AVAILABLE = True
except ImportError:
    SVG_AVAILABLE = False

VALID_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".svg"}
HANDLE_SIZE = 8
MIN_LAYER_SIZE = 12  # points, minimum width/height when resizing

# Font family mapping for the on-screen tkinter preview (approximate).
_TK_FONT_FAMILY = {
    "Helvetica": "Helvetica", "Helvetica-Bold": "Helvetica", "Helvetica-Oblique": "Helvetica",
    "Helvetica-BoldOblique": "Helvetica", "Times-Roman": "Times", "Times-Bold": "Times",
    "Times-Italic": "Times", "Times-BoldItalic": "Times", "Courier": "Courier", "Courier-Bold": "Courier",
}


class CoverGeneratorFrame(ctk.CTkFrame):
    """Cover Generator view: form + drag/resize live preview + layer manager + export."""

    def __init__(self, parent, app):
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self.app = app

        # ── Design state ────────────────────────────────────────────────
        self.layers = []            # list of layer dicts (see cover_engine docstring)
        self.next_z = 1
        self.selected_id = None
        self.view_mode = "full"     # "full" | "front" | "back" | "spine"
        self.current_project_id = None

        # Canvas render bookkeeping (recomputed every draw)
        self.scale = 1.0
        self.view_x0 = 0.0
        self.view_y1 = 0.0
        self._image_cache = {}      # layer_id -> PhotoImage (prevents GC)
        self._drag_state = None     # dict describing an in-progress move/resize

        self.layout_model = None    # CoverLayout, rebuilt on relevant field changes

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_header()
        self._create_content()
        self._rebuild_layout()

    # ─── Header ─────────────────────────────────────────────────────────────

    def _create_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=32, pady=(28, 12), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(
            header_frame, text="Cover Generator",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ctk.CTkLabel(
            header_frame, text="Design a print-ready full-wrap cover — front, spine, and back",
            font=ctk.CTkFont(size=13), text_color=("gray40", "gray60"),
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, rowspan=2, sticky="e")

        self.export_png_btn = ctk.CTkButton(
            btn_frame, text="🖼  Front PNG", font=ctk.CTkFont(size=13),
            height=40, width=120, corner_radius=8,
            fg_color=("#7c3aed", "#7c3aed"), hover_color=("#6d28d9", "#6d28d9"),
            command=self._export_front_png,
        )
        self.export_png_btn.grid(row=0, column=0, padx=(0, 8))

        self.export_wrap_btn = ctk.CTkButton(
            btn_frame, text="📖  Full Wrap PDF", font=ctk.CTkFont(size=13),
            height=40, width=140, corner_radius=8,
            fg_color=("#2563eb", "#2563eb"), hover_color=("#1d4ed8", "#1d4ed8"),
            command=self._export_full_wrap_pdf,
        )
        self.export_wrap_btn.grid(row=0, column=1, padx=(0, 8))

        self.export_print_btn = ctk.CTkButton(
            btn_frame, text="🖨  Print PDF (300 DPI)", font=ctk.CTkFont(size=13, weight="bold"),
            height=40, width=170, corner_radius=8,
            fg_color="#10b981", hover_color="#059669",
            command=self._export_print_pdf,
        )
        self.export_print_btn.grid(row=0, column=2, padx=(0, 8))

        self.save_btn = ctk.CTkButton(
            btn_frame, text="💾  Save", font=ctk.CTkFont(size=13),
            height=40, width=100, corner_radius=8,
            fg_color="#2563eb", hover_color="#1d4ed8",
            command=self._save_project,
        )
        self.save_btn.grid(row=0, column=3)

    # ─── Content Layout ─────────────────────────────────────────────────────

    def _create_content(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, padx=24, pady=(0, 24), sticky="nsew")
        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=4)
        content.grid_columnconfigure(2, weight=2)
        content.grid_rowconfigure(0, weight=1)

        self._create_form_panel(content)
        self._create_canvas_panel(content)
        self._create_layers_panel(content)

    # ─── Form Panel (Left) ──────────────────────────────────────────────────

    def _create_form_panel(self, parent):
        form = ctk.CTkScrollableFrame(
            parent, corner_radius=12, label_text="  Book Details  ",
            label_font=ctk.CTkFont(size=14, weight="bold"),
        )
        form.grid(row=0, column=0, padx=(0, 8), pady=4, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)
        settings = self.app.get_settings()

        row = 0
        self._field_label(form, "Book Title *", row); row += 1
        self.title_entry = ctk.CTkEntry(form, placeholder_text="My Coloring Book", height=36)
        self.title_entry.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1

        self._field_label(form, "Subtitle", row); row += 1
        self.subtitle_entry = ctk.CTkEntry(form, placeholder_text="A Fun Activity Book", height=36)
        self.subtitle_entry.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1

        self._field_label(form, "Author Name", row); row += 1
        self.author_entry = ctk.CTkEntry(form, placeholder_text="Author Name", height=36)
        self.author_entry.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1
        author = settings.get("author_name", "")
        if author:
            self.author_entry.insert(0, author)

        self._field_label(form, "Pen Name (optional)", row); row += 1
        self.pen_name_entry = ctk.CTkEntry(form, placeholder_text="Published under...", height=36)
        self.pen_name_entry.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1

        self._field_label(form, "Trim Size", row); row += 1
        self.trim_size_menu = ctk.CTkOptionMenu(
            form, values=list(TRIM_SIZES.keys()), width=240, height=34,
            command=lambda _v: self._rebuild_layout(),
        )
        default_size = settings.get("default_page_size", DEFAULT_TRIM_SIZE)
        self.trim_size_menu.set(default_size if default_size in TRIM_SIZES else DEFAULT_TRIM_SIZE)
        self.trim_size_menu.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="w"); row += 1

        self._field_label(form, "Page Count (interior pages)", row); row += 1
        self.page_count_entry = ctk.CTkEntry(form, placeholder_text="30", height=36, width=120)
        self.page_count_entry.insert(0, "30")
        self.page_count_entry.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="w"); row += 1
        self.page_count_entry.bind("<KeyRelease>", lambda _e: self._rebuild_layout())

        self._field_label(form, "Paper Type (spine calc)", row); row += 1
        self.paper_type_menu = ctk.CTkOptionMenu(
            form, values=list(PAPER_TYPES.keys()), width=240, height=34,
            command=lambda _v: self._rebuild_layout(),
        )
        self.paper_type_menu.set(list(PAPER_TYPES.keys())[0])
        self.paper_type_menu.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="w"); row += 1

        self._field_label(form, "Bleed (0.125\" per edge)", row); row += 1
        self.bleed_var = ctk.StringVar(value="Yes")
        bleed_frame = ctk.CTkFrame(form, fg_color="transparent")
        bleed_frame.grid(row=row, column=0, padx=16, pady=(0, 8), sticky="w"); row += 1
        ctk.CTkRadioButton(bleed_frame, text="Yes", variable=self.bleed_var, value="Yes",
                            command=self._rebuild_layout).grid(row=0, column=0, padx=(0, 20))
        ctk.CTkRadioButton(bleed_frame, text="No", variable=self.bleed_var, value="No",
                            command=self._rebuild_layout).grid(row=0, column=1)

        # Spine width readout
        self.spine_label = ctk.CTkLabel(
            form, text="Spine width: —", font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#2563eb", "#60a5fa"), wraplength=260, justify="left",
        )
        self.spine_label.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="w"); row += 1

        sep = ctk.CTkFrame(form, height=1, fg_color=("gray80", "gray25"))
        sep.grid(row=row, column=0, padx=16, pady=8, sticky="ew"); row += 1

        self._field_label(form, "Background Color", row); row += 1
        bg_frame = ctk.CTkFrame(form, fg_color="transparent")
        bg_frame.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew"); row += 1
        self.bg_color = "#FFFFFF"
        self.bg_swatch = ctk.CTkButton(
            bg_frame, text="", width=36, height=28, corner_radius=6,
            fg_color=self.bg_color, hover_color=self.bg_color, border_width=1,
            border_color=("gray60", "gray40"), command=self._pick_background_color,
        )
        self.bg_swatch.grid(row=0, column=0, padx=(0, 8))
        self.bg_color_label = ctk.CTkLabel(bg_frame, text=self.bg_color, font=ctk.CTkFont(size=12))
        self.bg_color_label.grid(row=0, column=1)

        self._field_label(form, "Default Font (for new text)", row); row += 1
        self.default_font_menu = ctk.CTkOptionMenu(form, values=COVER_FONTS, width=200, height=34)
        self.default_font_menu.set(COVER_FONTS[1] if len(COVER_FONTS) > 1 else COVER_FONTS[0])
        self.default_font_menu.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="w"); row += 1

        self.status_label = ctk.CTkLabel(
            form, text="", font=ctk.CTkFont(size=12),
            text_color=("gray45", "gray55"), wraplength=260, justify="left",
        )
        self.status_label.grid(row=row, column=0, padx=16, pady=(4, 8), sticky="w"); row += 1

    @staticmethod
    def _field_label(parent, text, row):
        ctk.CTkLabel(
            parent, text=text, font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray30", "gray70"),
        ).grid(row=row, column=0, padx=16, pady=(8, 4), sticky="w")

    def _pick_background_color(self):
        color = colorchooser.askcolor(color=self.bg_color, title="Choose Background Color")
        if color and color[1]:
            self.bg_color = color[1]
            self.bg_swatch.configure(fg_color=self.bg_color, hover_color=self.bg_color)
            self.bg_color_label.configure(text=self.bg_color)
            self._redraw_canvas()

    # ─── Canvas Panel (Center) ──────────────────────────────────────────────

    def _create_canvas_panel(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=12)
        panel.grid(row=0, column=1, padx=8, pady=4, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(panel, fg_color="transparent")
        top_bar.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        top_bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top_bar, text="Live Preview", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )

        self.view_mode_menu = ctk.CTkSegmentedButton(
            top_bar, values=["Full Wrap", "Front", "Spine", "Back"],
            command=self._on_view_mode_change,
        )
        self.view_mode_menu.set("Full Wrap")
        self.view_mode_menu.grid(row=0, column=2, sticky="e")

        canvas_holder = ctk.CTkFrame(panel, corner_radius=10, fg_color=("gray92", "gray17"))
        canvas_holder.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
        canvas_holder.grid_columnconfigure(0, weight=1)
        canvas_holder.grid_rowconfigure(0, weight=1)

        self.canvas_w = 760
        self.canvas_h = 440
        self.canvas = tk.Canvas(
            canvas_holder, width=self.canvas_w, height=self.canvas_h,
            highlightthickness=0, bg="#d9d9d9",
        )
        self.canvas.grid(row=0, column=0, padx=10, pady=10)
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Configure>", lambda _e: self._redraw_canvas())

        hint = ctk.CTkLabel(
            panel, text="Drag a layer to move it. Drag a corner handle to resize.",
            font=ctk.CTkFont(size=11), text_color=("gray45", "gray55"),
        )
        hint.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="w")

    def _on_view_mode_change(self, label):
        mapping = {"Full Wrap": "full", "Front": "front", "Spine": "spine", "Back": "back"}
        self.view_mode = mapping.get(label, "full")
        self._redraw_canvas()

    # ─── Layers Panel (Right) ───────────────────────────────────────────────

    def _create_layers_panel(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=12)
        panel.grid(row=0, column=2, padx=(8, 0), pady=4, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(panel, text="Layers", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(16, 8), sticky="w"
        )

        img_btn_frame = ctk.CTkFrame(panel, fg_color="transparent")
        img_btn_frame.grid(row=1, column=0, padx=16, pady=(0, 4), sticky="ew")
        img_btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            img_btn_frame, text="🖼  Add Image", height=32, corner_radius=6,
            font=ctk.CTkFont(size=12), command=self._import_image,
        ).grid(row=0, column=0, padx=(0, 4), pady=2, sticky="ew")

        ctk.CTkButton(
            img_btn_frame, text="🔤  Add Text", height=32, corner_radius=6,
            font=ctk.CTkFont(size=12), command=self._add_text_layer,
        ).grid(row=0, column=1, padx=(4, 0), pady=2, sticky="ew")

        drop_hint = ctk.CTkLabel(
            panel, text="Drag & drop PNG / JPG / SVG files onto the canvas",
            font=ctk.CTkFont(size=10), text_color=("gray50", "gray50"), wraplength=200,
        )
        drop_hint.grid(row=2, column=0, padx=16, pady=(0, 8), sticky="w")

        self.layer_list = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.layer_list.grid(row=3, column=0, padx=8, pady=(0, 8), sticky="nsew")
        self.layer_list.grid_columnconfigure(0, weight=1)

        # Property editor (shown when a layer is selected)
        self.prop_container = ctk.CTkFrame(panel, corner_radius=10, fg_color=("gray90", "gray16"))
        self.prop_container.grid(row=4, column=0, padx=8, pady=(0, 12), sticky="ew")
        self.prop_container.grid_columnconfigure(0, weight=1)
        self._render_property_editor()

        self._setup_drag_drop()

    def _setup_drag_drop(self):
        try:
            self.canvas.drop_target_register('DND_Files')
            self.canvas.dnd_bind('<<Drop>>', self._on_canvas_drop)
        except (AttributeError, Exception):
            pass

    def _on_canvas_drop(self, event):
        for f in self._parse_drop_data(event.data):
            if Path(f).suffix.lower() in VALID_IMAGE_EXT:
                self._add_image_layer(f)
        self._redraw_canvas()

    @staticmethod
    def _parse_drop_data(data: str) -> list:
        if '{' in data:
            import re
            return re.findall(r'\{([^}]+)\}', data)
        return data.split()

    # ─── Layout / Spine Calculation ─────────────────────────────────────────

    def _rebuild_layout(self):
        """Recompute the CoverLayout from current form values and redraw."""
        trim = self.trim_size_menu.get()
        pages_text = self.page_count_entry.get().strip()
        pages = int(pages_text) if pages_text.isdigit() else 0
        paper = self.paper_type_menu.get()
        use_bleed = self.bleed_var.get() == "Yes"

        self.layout_model = CoverLayout(trim, pages, paper, use_bleed)

        spine_pt = self.layout_model.spine_w
        spine_in = spine_pt / 72.0
        safe = spine_text_is_safe(pages)
        warn = "" if safe else "  ⚠ Below recommended page count for readable spine text."
        self.spine_label.configure(
            text=f"Spine width: {spine_in:.3f}\" ({spine_pt:.1f} pt){warn}"
        )
        self._update_status()
        self._redraw_canvas()

    def _update_status(self):
        lines = []
        img_count = sum(1 for l in self.layers if l.get("type") == "image")
        txt_count = sum(1 for l in self.layers if l.get("type") == "text")
        lines.append(f"{img_count} image layer(s), {txt_count} text layer(s)")
        if not PIL_AVAILABLE:
            lines.append("⚠ Pillow not installed (pip install Pillow)")
        if not SVG_AVAILABLE:
            lines.append("ℹ SVG import shown as placeholder (optional: pip install cairosvg)")
        if self.current_project_id:
            lines.append("📁 Project loaded (will update on save)")
        self.status_label.configure(text="\n".join(lines))

    # ─── Image Import ───────────────────────────────────────────────────────

    def _import_image(self):
        files = filedialog.askopenfilenames(
            title="Select Cover Images",
            filetypes=[
                ("All Images", "*.png *.jpg *.jpeg *.svg"),
                ("PNG Files", "*.png"), ("JPEG Files", "*.jpg *.jpeg"),
                ("SVG Files", "*.svg"), ("All Files", "*.*"),
            ],
        )
        for f in files:
            self._add_image_layer(f)
        self._redraw_canvas()

    def _rasterize_svg(self, path: str) -> str:
        """Convert an SVG to a temp PNG for preview/embedding. Returns a PNG path."""
        out_path = os.path.join(tempfile.gettempdir(), f"cover_svg_{uuid.uuid4().hex}.png")
        cairosvg.svg2png(url=path, write_to=out_path, output_width=1200)
        return out_path

    def _add_image_layer(self, path: str):
        display_path = path
        if Path(path).suffix.lower() == ".svg":
            if SVG_AVAILABLE:
                try:
                    display_path = self._rasterize_svg(path)
                except Exception as e:
                    logger.warning(f"SVG rasterization failed for {path}: {e}")
                    messagebox.showwarning(
                        "SVG Import",
                        f"Could not rasterize SVG:\n{Path(path).name}\n\n{e}",
                    )
                    return
            else:
                messagebox.showinfo(
                    "SVG Support",
                    "SVG rasterization library not found. The file will be referenced "
                    "as a placeholder. Install 'cairosvg' for full offline SVG support.",
                )

        panel = self.view_mode if self.view_mode != "full" else "front"
        default_w, default_h = 150.0, 150.0
        if PIL_AVAILABLE and Path(display_path).suffix.lower() != ".svg":
            try:
                with Image.open(display_path) as im:
                    iw, ih = im.size
                    ratio = iw / ih if ih else 1
                    default_h = 200.0
                    default_w = default_h * ratio
            except Exception:
                pass

        x, y, w, h = self.layout_model.default_layer_rect(panel, default_w, default_h)
        layer = {
            "id": str(uuid.uuid4()), "type": "image", "name": Path(path).name,
            "path": display_path, "source_path": path,
            "x": x, "y": y, "width": w, "height": h, "z": self.next_z,
        }
        self.next_z += 1
        self.layers.append(layer)
        self.selected_id = layer["id"]
        self._refresh_layer_list()
        self._render_property_editor()

    # ─── Text Layer ─────────────────────────────────────────────────────────

    def _add_text_layer(self):
        panel = self.view_mode if self.view_mode != "full" else "front"
        default_w, default_h = 220.0, 44.0
        x, y, w, h = self.layout_model.default_layer_rect(panel, default_w, default_h)
        layer = {
            "id": str(uuid.uuid4()), "type": "text", "name": "Text Layer",
            "text": "Your Title Here", "font": self.default_font_menu.get(),
            "font_size": 28, "color": "#000000", "align": "center",
            "bold": False, "italic": False, "underline": False, "effect": "none",
            "x": x, "y": y, "width": w, "height": h, "z": self.next_z,
        }
        self.next_z += 1
        self.layers.append(layer)
        self.selected_id = layer["id"]
        self._refresh_layer_list()
        self._render_property_editor()
        self._redraw_canvas()

    # ─── Layer List UI ──────────────────────────────────────────────────────

    def _refresh_layer_list(self):
        for w in self.layer_list.winfo_children():
            w.destroy()

        ordered = sorted(self.layers, key=lambda l: -l.get("z", 0))
        for layer in ordered:
            self._create_layer_row(layer)

    def _create_layer_row(self, layer):
        is_selected = layer["id"] == self.selected_id
        row = ctk.CTkFrame(
            self.layer_list, corner_radius=6,
            fg_color=("gray80", "gray28") if is_selected else ("gray88", "gray20"),
        )
        row.grid(sticky="ew", pady=2)
        row.grid_columnconfigure(1, weight=1)

        icon = "🖼" if layer["type"] == "image" else "🔤"
        label_text = layer["name"] if layer["type"] == "image" else (layer.get("text") or "Text")
        if len(label_text) > 16:
            label_text = label_text[:14] + "…"

        btn = ctk.CTkButton(
            row, text=f"{icon}  {label_text}", anchor="w", height=30,
            fg_color="transparent", hover_color=("gray70", "gray32"),
            font=ctk.CTkFont(size=12),
            command=lambda lid=layer["id"]: self._select_layer(lid),
        )
        btn.grid(row=0, column=0, columnspan=2, sticky="ew", padx=2, pady=2)

        ctrl_frame = ctk.CTkFrame(row, fg_color="transparent")
        ctrl_frame.grid(row=1, column=0, columnspan=2, sticky="e", padx=4, pady=(0, 4))

        ctk.CTkButton(
            ctrl_frame, text="▲", width=24, height=22, font=ctk.CTkFont(size=10),
            command=lambda lid=layer["id"]: self._nudge_z(lid, 1),
        ).grid(row=0, column=0, padx=1)
        ctk.CTkButton(
            ctrl_frame, text="▼", width=24, height=22, font=ctk.CTkFont(size=10),
            command=lambda lid=layer["id"]: self._nudge_z(lid, -1),
        ).grid(row=0, column=1, padx=1)
        ctk.CTkButton(
            ctrl_frame, text="✕", width=24, height=22, font=ctk.CTkFont(size=10),
            fg_color="#dc2626", hover_color="#b91c1c",
            command=lambda lid=layer["id"]: self._delete_layer(lid),
        ).grid(row=0, column=2, padx=1)

    def _select_layer(self, layer_id):
        self.selected_id = layer_id
        self._refresh_layer_list()
        self._render_property_editor()
        self._redraw_canvas()

    def _get_layer(self, layer_id):
        for l in self.layers:
            if l["id"] == layer_id:
                return l
        return None

    def _nudge_z(self, layer_id, direction):
        layer = self._get_layer(layer_id)
        if layer:
            layer["z"] = layer.get("z", 0) + direction
            self._refresh_layer_list()
            self._redraw_canvas()

    def _delete_layer(self, layer_id):
        self.layers = [l for l in self.layers if l["id"] != layer_id]
        if self.selected_id == layer_id:
            self.selected_id = None
        self._image_cache.pop(layer_id, None)
        self._refresh_layer_list()
        self._render_property_editor()
        self._redraw_canvas()
        self._update_status()

    # ─── Property Editor ────────────────────────────────────────────────────

    def _render_property_editor(self):
        for w in self.prop_container.winfo_children():
            w.destroy()

        layer = self._get_layer(self.selected_id) if self.selected_id else None
        if layer is None:
            ctk.CTkLabel(
                self.prop_container, text="Select a layer to edit its properties.",
                font=ctk.CTkFont(size=11), text_color=("gray45", "gray55"), wraplength=200,
            ).grid(row=0, column=0, padx=12, pady=12)
            return

        ctk.CTkLabel(
            self.prop_container, text="Properties",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        if layer["type"] == "text":
            self._render_text_properties(layer)
        else:
            self._render_image_properties(layer)

    def _render_text_properties(self, layer):
        r = 1
        text_var = ctk.StringVar(value=layer.get("text", ""))
        entry = ctk.CTkEntry(self.prop_container, textvariable=text_var, height=32)
        entry.grid(row=r, column=0, padx=12, pady=4, sticky="ew"); r += 1

        def _apply_text(*_a):
            layer["text"] = text_var.get()
            self._refresh_layer_list()
            self._redraw_canvas()
        text_var.trace_add("write", _apply_text)

        font_menu = ctk.CTkOptionMenu(
            self.prop_container, values=COVER_FONTS, width=200,
            command=lambda v: (layer.__setitem__("font", v), self._redraw_canvas()),
        )
        font_menu.set(layer.get("font", COVER_FONTS[0]))
        font_menu.grid(row=r, column=0, padx=12, pady=4, sticky="ew"); r += 1

        size_frame = ctk.CTkFrame(self.prop_container, fg_color="transparent")
        size_frame.grid(row=r, column=0, padx=12, pady=4, sticky="ew"); r += 1
        ctk.CTkLabel(size_frame, text="Size:", font=ctk.CTkFont(size=11)).grid(row=0, column=0)
        size_entry = ctk.CTkEntry(size_frame, width=60, height=28)
        size_entry.insert(0, str(int(layer.get("font_size", 24))))
        size_entry.grid(row=0, column=1, padx=6)

        def _apply_size(_e=None):
            try:
                layer["font_size"] = max(int(size_entry.get()), 4)
            except ValueError:
                pass
            self._redraw_canvas()
        size_entry.bind("<KeyRelease>", _apply_size)

        color_btn = ctk.CTkButton(
            size_frame, text="Color", width=60, height=28,
            fg_color=layer.get("color", "#000000"), hover_color=layer.get("color", "#000000"),
            command=lambda: self._pick_text_color(layer),
        )
        color_btn.grid(row=0, column=2, padx=6)
        layer["_color_btn_ref"] = color_btn  # keep ref for live swatch update

        align_frame = ctk.CTkFrame(self.prop_container, fg_color="transparent")
        align_frame.grid(row=r, column=0, padx=12, pady=4, sticky="ew"); r += 1
        align_var = ctk.StringVar(value=layer.get("align", "center"))

        def _apply_align(val):
            layer["align"] = val
            self._redraw_canvas()
        for i, opt in enumerate(["left", "center", "right"]):
            ctk.CTkRadioButton(
                align_frame, text=opt.title(), variable=align_var, value=opt,
                command=lambda v=opt: _apply_align(v),
            ).grid(row=0, column=i, padx=4)

        effects_frame = ctk.CTkFrame(self.prop_container, fg_color="transparent")
        effects_frame.grid(row=r, column=0, padx=12, pady=4, sticky="ew"); r += 1

        bold_var = ctk.BooleanVar(value=layer.get("bold", False))
        italic_var = ctk.BooleanVar(value=layer.get("italic", False))
        underline_var = ctk.BooleanVar(value=layer.get("underline", False))

        def _apply_style(*_a):
            layer["bold"] = bold_var.get()
            layer["italic"] = italic_var.get()
            layer["underline"] = underline_var.get()
            layer["font"] = self._resolve_style_font(layer.get("font", "Helvetica"), bold_var.get(), italic_var.get())
            self._redraw_canvas()

        ctk.CTkCheckBox(effects_frame, text="Bold", variable=bold_var, width=60,
                        command=_apply_style).grid(row=0, column=0, padx=2)
        ctk.CTkCheckBox(effects_frame, text="Italic", variable=italic_var, width=60,
                        command=_apply_style).grid(row=0, column=1, padx=2)
        ctk.CTkCheckBox(effects_frame, text="Underline", variable=underline_var, width=80,
                        command=_apply_style).grid(row=0, column=2, padx=2)

        effect_menu = ctk.CTkOptionMenu(
            self.prop_container, values=["none", "shadow", "outline"], width=200,
            command=lambda v: (layer.__setitem__("effect", v), self._redraw_canvas()),
        )
        effect_menu.set(layer.get("effect", "none"))
        effect_menu.grid(row=r, column=0, padx=12, pady=(4, 12), sticky="ew"); r += 1

    @staticmethod
    def _resolve_style_font(base_font, bold, italic):
        """Map bold/italic toggles onto the closest ReportLab base-14 font name."""
        family = "Helvetica"
        for fam in ("Helvetica", "Times", "Courier"):
            if base_font.startswith(fam):
                family = fam
                break
        if family == "Times":
            if bold and italic:
                return "Times-BoldItalic"
            if bold:
                return "Times-Bold"
            if italic:
                return "Times-Italic"
            return "Times-Roman"
        if family == "Courier":
            return "Courier-Bold" if bold else "Courier"
        # Helvetica
        if bold and italic:
            return "Helvetica-BoldOblique"
        if bold:
            return "Helvetica-Bold"
        if italic:
            return "Helvetica-Oblique"
        return "Helvetica"

    def _pick_text_color(self, layer):
        color = colorchooser.askcolor(color=layer.get("color", "#000000"), title="Text Color")
        if color and color[1]:
            layer["color"] = color[1]
            btn = layer.get("_color_btn_ref")
            if btn is not None:
                try:
                    btn.configure(fg_color=color[1], hover_color=color[1])
                except Exception:
                    pass
            self._redraw_canvas()

    def _render_image_properties(self, layer):
        ctk.CTkLabel(
            self.prop_container, text=layer.get("name", "Image"),
            font=ctk.CTkFont(size=12), wraplength=200,
        ).grid(row=1, column=0, padx=12, pady=4, sticky="w")

        btn_frame = ctk.CTkFrame(self.prop_container, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=12, pady=(4, 12), sticky="ew")

        ctk.CTkButton(
            btn_frame, text="Center on Panel", height=28, font=ctk.CTkFont(size=11),
            command=lambda: self._center_layer(layer),
        ).grid(row=0, column=0, padx=2, sticky="ew")

        ctk.CTkButton(
            btn_frame, text="Fit to Panel", height=28, font=ctk.CTkFont(size=11),
            command=lambda: self._fit_layer_to_panel(layer),
        ).grid(row=1, column=0, padx=2, pady=(4, 0), sticky="ew")

    def _center_layer(self, layer):
        panel = self._panel_for_layer(layer)
        x0, y0, x1, y1 = self.layout_model.panel_rect(panel)
        layer["x"] = (x0 + x1) / 2 - layer["width"] / 2
        layer["y"] = (y0 + y1) / 2 - layer["height"] / 2
        self._redraw_canvas()

    def _fit_layer_to_panel(self, layer):
        panel = self._panel_for_layer(layer)
        x0, y0, x1, y1 = self.layout_model.panel_rect(panel)
        margin = 18
        layer["x"], layer["y"] = x0 + margin, y0 + margin
        layer["width"], layer["height"] = (x1 - x0) - 2 * margin, (y1 - y0) - 2 * margin
        self._redraw_canvas()

    def _panel_for_layer(self, layer):
        """Best-guess which panel a layer's center currently sits on."""
        cx = layer["x"] + layer["width"] / 2
        lo = self.layout_model
        if cx < lo.spine_x0:
            return "back"
        if cx < lo.spine_x1:
            return "spine"
        return "front"

    # ─── Canvas Rendering ───────────────────────────────────────────────────

    def _view_bounds(self):
        lo = self.layout_model
        if self.view_mode == "full":
            return 0.0, 0.0, lo.total_w, lo.total_h
        x0, y0, x1, y1 = lo.panel_rect(self.view_mode)
        return x0, y0, x1, y1

    def _redraw_canvas(self):
        if self.layout_model is None:
            return
        self.canvas.delete("all")
        vx0, vy0, vx1, vy1 = self._view_bounds()
        vw, vh = max(vx1 - vx0, 1), max(vy1 - vy0, 1)
        self.scale = min(self.canvas_w / vw, self.canvas_h / vh)
        self.view_x0, self.view_y1 = vx0, vy1

        # Background
        bg_x0, bg_y0 = self._to_canvas(vx0, vy1)
        bg_x1, bg_y1 = self._to_canvas(vx1, vy0)
        self.canvas.create_rectangle(bg_x0, bg_y0, bg_x1, bg_y1, fill=self.bg_color, outline="")

        # Panel boundary guides (only meaningful in full-wrap view)
        if self.view_mode == "full":
            lo = self.layout_model
            for x in (lo.spine_x0, lo.spine_x1):
                cx, cy0 = self._to_canvas(x, lo.total_h)
                _, cy1 = self._to_canvas(x, 0)
                self.canvas.create_line(cx, cy0, cx, cy1, fill="#999999", dash=(4, 2))
            if lo.use_bleed:
                bx0, by0 = self._to_canvas(lo.bleed, lo.total_h - lo.bleed)
                bx1, by1 = self._to_canvas(lo.total_w - lo.bleed, lo.bleed)
                self.canvas.create_rectangle(bx0, by0, bx1, by1, outline="#cc4444", dash=(2, 2))

        for layer in sorted(self.layers, key=lambda l: l.get("z", 0)):
            self._draw_layer_on_canvas(layer)

        if self.selected_id:
            layer = self._get_layer(self.selected_id)
            if layer:
                self._draw_selection(layer)

    def _to_canvas(self, dx, dy):
        cx = (dx - self.view_x0) * self.scale
        cy = (self.view_y1 - dy) * self.scale
        return cx, cy

    def _from_canvas(self, cx, cy):
        dx = cx / self.scale + self.view_x0
        dy = self.view_y1 - cy / self.scale
        return dx, dy

    def _layer_screen_bbox(self, layer):
        x0c, y1c = self._to_canvas(layer["x"], layer["y"])
        x1c, y0c = self._to_canvas(layer["x"] + layer["width"], layer["y"] + layer["height"])
        return min(x0c, x1c), min(y0c, y1c), max(x0c, x1c), max(y0c, y1c)

    def _draw_layer_on_canvas(self, layer):
        x0, y0, x1, y1 = self._layer_screen_bbox(layer)
        if x1 <= 0 or y1 <= 0 or x0 >= self.canvas_w or y0 >= self.canvas_h:
            return  # fully off the current view

        if layer["type"] == "image":
            self._draw_image_preview(layer, x0, y0, x1, y1)
        else:
            self._draw_text_preview(layer, x0, y0, x1, y1)

    def _draw_image_preview(self, layer, x0, y0, x1, y1):
        w, h = max(int(x1 - x0), 1), max(int(y1 - y0), 1)
        photo = None
        path = layer.get("path", "")
        if PIL_AVAILABLE and path and Path(path).exists():
            try:
                img = Image.open(path)
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                img = img.resize((w, h), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
            except Exception:
                photo = None

        if photo is not None:
            self._image_cache[layer["id"]] = photo
            self.canvas.create_image(x0, y0, image=photo, anchor="nw", tags=("layer", layer["id"]))
        else:
            self.canvas.create_rectangle(x0, y0, x1, y1, fill="#cccccc", outline="#888888",
                                          tags=("layer", layer["id"]))
            self.canvas.create_text(
                (x0 + x1) / 2, (y0 + y1) / 2, text=layer.get("name", "Image"),
                fill="#555555", font=("Helvetica", 9), tags=("layer", layer["id"]),
            )

    def _draw_text_preview(self, layer, x0, y0, x1, y1):
        text = layer.get("text", "")
        family = _TK_FONT_FAMILY.get(layer.get("font", "Helvetica"), "Helvetica")
        size_px = max(int(layer.get("font_size", 24) * self.scale), 6)
        weight = "bold" if "Bold" in layer.get("font", "") else "normal"
        slant = "italic" if ("Italic" in layer.get("font", "") or "Oblique" in layer.get("font", "")) else "roman"
        tk_font = (family, size_px, weight, slant)

        align = layer.get("align", "center")
        anchor_x = {"left": x0, "center": (x0 + x1) / 2, "right": x1}.get(align, (x0 + x1) / 2)
        anchor = {"left": "w", "center": "center", "right": "e"}.get(align, "center")
        cy = (y0 + y1) / 2

        effect = layer.get("effect", "none")
        color = layer.get("color", "#000000")
        if effect == "shadow":
            self.canvas.create_text(anchor_x + 2, cy + 2, text=text, font=tk_font,
                                     fill="#00000055", anchor=anchor, tags=("layer", layer["id"]))
        elif effect == "outline":
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                self.canvas.create_text(anchor_x + dx, cy + dy, text=text, font=tk_font,
                                         fill="#000000", anchor=anchor, tags=("layer", layer["id"]))

        item = self.canvas.create_text(
            anchor_x, cy, text=text, font=tk_font, fill=color, anchor=anchor,
            tags=("layer", layer["id"]),
        )
        if layer.get("underline"):
            bbox = self.canvas.bbox(item)
            if bbox:
                uy = bbox[3] + 1
                self.canvas.create_line(bbox[0], uy, bbox[2], uy, fill=color, tags=("layer", layer["id"]))

        # Faint outline box so empty/near-invisible text is still selectable & visible
        self.canvas.create_rectangle(x0, y0, x1, y1, outline="#bbbbbb", dash=(2, 2),
                                      tags=("layer", layer["id"]))

    def _draw_selection(self, layer):
        x0, y0, x1, y1 = self._layer_screen_bbox(layer)
        self.canvas.create_rectangle(x0, y0, x1, y1, outline="#2563eb", width=2, tags="selection")
        for hx, hy in self._handle_positions(x0, y0, x1, y1):
            self.canvas.create_rectangle(
                hx - HANDLE_SIZE / 2, hy - HANDLE_SIZE / 2, hx + HANDLE_SIZE / 2, hy + HANDLE_SIZE / 2,
                fill="#2563eb", outline="white", tags="selection",
            )

    @staticmethod
    def _handle_positions(x0, y0, x1, y1):
        return [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]

    # ─── Mouse Interaction (Move / Resize) ─────────────────────────────────

    def _handle_at_point(self, x, y, layer):
        bx0, by0, bx1, by1 = self._layer_screen_bbox(layer)
        names = ["nw", "ne", "sw", "se"]
        for name, (hx, hy) in zip(names, self._handle_positions(bx0, by0, bx1, by1)):
            if abs(x - hx) <= HANDLE_SIZE and abs(y - hy) <= HANDLE_SIZE:
                return name
        return None

    def _on_canvas_press(self, event):
        x, y = event.x, event.y

        selected = self._get_layer(self.selected_id) if self.selected_id else None
        if selected:
            handle = self._handle_at_point(x, y, selected)
            if handle:
                self._drag_state = {
                    "mode": "resize", "handle": handle, "layer_id": selected["id"],
                    "start_x": x, "start_y": y,
                    "orig": (selected["x"], selected["y"], selected["width"], selected["height"]),
                }
                return

        hit_layer = None
        for layer in sorted(self.layers, key=lambda l: -l.get("z", 0)):
            bx0, by0, bx1, by1 = self._layer_screen_bbox(layer)
            if bx0 <= x <= bx1 and by0 <= y <= by1:
                hit_layer = layer
                break

        if hit_layer:
            self.selected_id = hit_layer["id"]
            self._drag_state = {
                "mode": "move", "layer_id": hit_layer["id"],
                "start_x": x, "start_y": y,
                "orig": (hit_layer["x"], hit_layer["y"]),
            }
            self._refresh_layer_list()
            self._render_property_editor()
        else:
            self.selected_id = None
            self._drag_state = None
            self._refresh_layer_list()
            self._render_property_editor()

        self._redraw_canvas()

    def _on_canvas_drag(self, event):
        if not self._drag_state:
            return
        layer = self._get_layer(self._drag_state["layer_id"])
        if not layer:
            return

        dx_screen = event.x - self._drag_state["start_x"]
        dy_screen = event.y - self._drag_state["start_y"]
        dx = dx_screen / self.scale
        dy = -dy_screen / self.scale  # screen y-down vs design y-up

        if self._drag_state["mode"] == "move":
            ox, oy = self._drag_state["orig"]
            layer["x"] = ox + dx
            layer["y"] = oy + dy
        else:
            ox, oy, ow, oh = self._drag_state["orig"]
            handle = self._drag_state["handle"]
            new_x, new_y, new_w, new_h = ox, oy, ow, oh

            if "e" in handle:
                new_w = max(ow + dx, MIN_LAYER_SIZE)
            if "w" in handle:
                new_w = max(ow - dx, MIN_LAYER_SIZE)
                new_x = ox + (ow - new_w)
            if "n" in handle:
                new_h = max(oh + dy, MIN_LAYER_SIZE)
            if "s" in handle:
                new_h = max(oh - dy, MIN_LAYER_SIZE)
                new_y = oy + (oh - new_h)

            layer["x"], layer["y"], layer["width"], layer["height"] = new_x, new_y, new_w, new_h

        self._redraw_canvas()

    def _on_canvas_release(self, _event):
        self._drag_state = None

    # ─── Export ─────────────────────────────────────────────────────────────

    def _build_engine(self):
        return CoverEngine(
            layout=self.layout_model,
            layers=self.layers,
            background_color=self.bg_color,
            title=self.title_entry.get().strip(),
            author=self.author_entry.get().strip() or self.pen_name_entry.get().strip(),
        )

    def _validate_export(self) -> bool:
        if not self.title_entry.get().strip():
            messagebox.showwarning("Missing Title", "Please enter a book title.")
            return False
        if not COVER_ENGINE_AVAILABLE:
            messagebox.showerror("Missing Module", "The cover engine could not be loaded.")
            return False
        return True

    def _export_front_png(self):
        if not self._validate_export():
            return
        settings = self.app.get_settings()
        default_path = settings.get("default_export_path", str(Path.home() / "Documents"))
        title = self.title_entry.get().strip()
        output_path = filedialog.asksaveasfilename(
            title="Export Front Cover PNG", defaultextension=".png",
            filetypes=[("PNG Files", "*.png")], initialdir=default_path,
            initialfile=f"{title.replace(' ', '_')}_front_cover.png",
        )
        if not output_path:
            return
        self._run_export(lambda: self._build_engine().build_front_cover_png(output_path), output_path)

    def _export_full_wrap_pdf(self):
        if not self._validate_export():
            return
        settings = self.app.get_settings()
        default_path = settings.get("default_export_path", str(Path.home() / "Documents"))
        title = self.title_entry.get().strip()
        output_path = filedialog.asksaveasfilename(
            title="Export Full Wrap PDF", defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")], initialdir=default_path,
            initialfile=f"{title.replace(' ', '_')}_full_wrap.pdf",
        )
        if not output_path:
            return
        self._run_export(lambda: self._build_engine().build_full_wrap_pdf(output_path), output_path)

    def _export_print_pdf(self):
        if not self._validate_export():
            return
        settings = self.app.get_settings()
        default_path = settings.get("default_export_path", str(Path.home() / "Documents"))
        title = self.title_entry.get().strip()
        output_path = filedialog.asksaveasfilename(
            title="Export 300 DPI Print-Ready PDF", defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")], initialdir=default_path,
            initialfile=f"{title.replace(' ', '_')}_print_300dpi.pdf",
        )
        if not output_path:
            return
        self._run_export(lambda: self._build_engine().build_print_ready_pdf(output_path), output_path)

    def _run_export(self, export_fn, output_path):
        self._set_export_buttons_state("disabled")
        thread = threading.Thread(target=self._run_export_thread, args=(export_fn, output_path), daemon=True)
        thread.start()

    def _run_export_thread(self, export_fn, output_path):
        try:
            export_fn()
            self.after(0, lambda: self._on_export_complete(output_path))
        except Exception as e:
            logger.error(f"Cover export failed: {e}", exc_info=True)
            self.after(0, lambda: self._on_export_error(str(e)))

    def _set_export_buttons_state(self, state):
        for btn in (self.export_png_btn, self.export_wrap_btn, self.export_print_btn, self.save_btn):
            btn.configure(state=state)

    def _on_export_complete(self, output_path):
        self._set_export_buttons_state("normal")
        messagebox.showinfo("Export Complete", f"Cover exported successfully!\n\n{output_path}")

    def _on_export_error(self, error_msg):
        self._set_export_buttons_state("normal")
        messagebox.showerror("Export Error", f"Failed to export cover:\n\n{error_msg}")

    # ─── Save / Load Project ────────────────────────────────────────────────

    def _serialize_layers(self):
        clean = []
        for l in self.layers:
            d = {k: v for k, v in l.items() if not k.startswith("_")}
            clean.append(d)
        return clean

    def _save_project(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Missing Title", "Please enter a book title to save.")
            return

        now = datetime.now().isoformat()
        cover_data = {
            "title": title,
            "subtitle": self.subtitle_entry.get().strip(),
            "author": self.author_entry.get().strip(),
            "pen_name": self.pen_name_entry.get().strip(),
            "trim_size": self.trim_size_menu.get(),
            "page_count": self.page_count_entry.get().strip(),
            "paper_type": self.paper_type_menu.get(),
            "bleed": self.bleed_var.get(),
            "background_color": self.bg_color,
            "default_font": self.default_font_menu.get(),
            "layers": self._serialize_layers(),
        }

        if self.current_project_id:
            project_data = {
                "name": title,
                "description": "Cover design project",
                "page_size": self.trim_size_menu.get(),
                "author": self.author_entry.get().strip(),
                "page_count": int(self.page_count_entry.get().strip() or 0),
                "status": "in_progress",
                "modified_at": now,
                "cover_data": cover_data,
            }
            self.app.update_project(self.current_project_id, project_data)
            messagebox.showinfo("Saved", f"Cover project '{title}' updated successfully!")
        else:
            project_data = {
                "id": str(uuid.uuid4()),
                "name": title,
                "description": "Cover design project",
                "page_size": self.trim_size_menu.get(),
                "author": self.author_entry.get().strip(),
                "page_count": int(self.page_count_entry.get().strip() or 0),
                "status": "in_progress",
                "created_at": now,
                "modified_at": now,
                "cover_data": cover_data,
                "pages": [],
            }
            self.current_project_id = project_data["id"]
            self.app.add_project(project_data)
            messagebox.showinfo("Saved", f"Cover project '{title}' saved successfully!")

        self._update_status()
        logger.info(f"Saved cover project: {title} ({self.current_project_id})")

    def load_project(self, project: dict):
        """Load a saved cover project's data into the editor."""
        cover_data = project.get("cover_data")
        if not cover_data:
            return

        self.current_project_id = project.get("id")

        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, cover_data.get("title", ""))
        self.subtitle_entry.delete(0, "end")
        self.subtitle_entry.insert(0, cover_data.get("subtitle", ""))
        self.author_entry.delete(0, "end")
        self.author_entry.insert(0, cover_data.get("author", ""))
        self.pen_name_entry.delete(0, "end")
        self.pen_name_entry.insert(0, cover_data.get("pen_name", ""))

        trim_size = cover_data.get("trim_size", DEFAULT_TRIM_SIZE)
        if trim_size in TRIM_SIZES:
            self.trim_size_menu.set(trim_size)

        self.page_count_entry.delete(0, "end")
        self.page_count_entry.insert(0, str(cover_data.get("page_count", "30")))

        paper_type = cover_data.get("paper_type")
        if paper_type in PAPER_TYPES:
            self.paper_type_menu.set(paper_type)

        self.bleed_var.set(cover_data.get("bleed", "Yes"))
        self.bg_color = cover_data.get("background_color", "#FFFFFF")
        self.bg_swatch.configure(fg_color=self.bg_color, hover_color=self.bg_color)
        self.bg_color_label.configure(text=self.bg_color)

        default_font = cover_data.get("default_font")
        if default_font in COVER_FONTS:
            self.default_font_menu.set(default_font)

        self.layers = [dict(l) for l in cover_data.get("layers", [])]
        self.next_z = max([l.get("z", 0) for l in self.layers], default=0) + 1
        self.selected_id = None

        self._rebuild_layout()
        self._refresh_layer_list()
        self._render_property_editor()
        logger.info(f"Loaded cover project: {cover_data.get('title')} ({self.current_project_id})")

    def refresh(self):
        """Called when this frame is shown; nothing heavy needed here."""
        pass
