# KDP Coloring Book Generator

A professional Windows desktop application for generating KDP (Kindle Direct Publishing) coloring books. Built with Python and CustomTkinter, designed to work **completely offline** — no API keys or internet connection required.

## Features (Current Build)

- **Modern Dark UI** — Professional CustomTkinter interface with sidebar navigation
- **Dashboard** — Overview of project statistics, recent projects, and quick actions
- **Coloring Book Generator** — Metadata form, image import, and print-ready interior PDF generation
- **Cover Generator** — Full-wrap cover designer (front, spine, back) with:
  - Draggable/resizable image and text layers on a live preview canvas
  - Automatic spine width calculation from page count + paper type
  - Bleed support and a KDP barcode placeholder on the back cover
  - PNG import (drag & drop or file dialog), plus optional offline SVG import
  - Export to Front Cover PNG, vector Full Wrap PDF, and a flattened 300 DPI print-ready PDF
- **Project Manager** — Create, search, select, and delete unlimited projects with full metadata
- **Settings** — Configure theme, UI scaling, author name, export path, and page defaults
- **Local Persistence** — All data saved as JSON files locally (unlimited projects)
- **Modular Architecture** — Clean separation of concerns for easy extension

## Project Structure

```
kdp_coloring_book_generator/
├── src/
│   ├── app.py                  # Main application entry point
│   └── ui/
│       ├── __init__.py         # UI package exports
│       ├── dashboard.py        # Dashboard frame
│       ├── project_manager.py  # Project CRUD and list view
│       └── settings.py         # Application settings
├── assets/                     # Icons, images, media (future)
├── data/                       # Local JSON data storage
│   ├── projects.json           # Project data (auto-created)
│   └── settings.json           # User settings (auto-created)
├── docs/                       # Documentation
├── requirements.txt            # Python dependencies
├── build.spec                  # PyInstaller spec for .exe packaging
└── README.md
```

## Installation & Running

### Prerequisites

- Python 3.9 or higher

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the Application

```bash
cd kdp_coloring_book_generator/src
python app.py
```

## Building Windows .exe

To package as a standalone Windows executable:

```bash
pip install pyinstaller
pyinstaller build.spec
```

The executable will be created in the `dist/` folder.

## Planned Features (Not Yet Implemented)

- Page editor with per-page image adjustments
- Batch page processing
- KDP-compliant output validation
- Cover template presets/gallery

## Tech Stack

- **Python 3.9+**
- **CustomTkinter** — Modern UI toolkit
- **JSON** — Local data persistence
- **PyInstaller** — Windows .exe packaging

## License

Private project — All rights reserved.
