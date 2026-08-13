# Template & Asset Management System

The Template & Asset Management System serves as the central library for all reusable elements across KDP Studio Pro. It provides robust tools to import, categorize, index, and cache assets like Images, SVG files, PDFs, Fonts, and project layouts.

## Architecture Overview

The system is built on a modular, Service-Oriented Architecture (SOA):

- **Database (`database/db.py`)**: Stores all asset and template metadata (`assets` and `templates` tables).
- **Models (`models/asset.py`, `models/template.py`)**: Dataclasses representing database records, enabling type-safe object manipulation.
- **Thumbnail Service (`core/thumbnail_generator.py`)**: A fallback-based generation engine. 
  - Attempts to use Pillow for raster images.
  - Falls back to `cairosvg` and `PyMuPDF` if available for vector and PDF formats.
  - Safely falls back to auto-generated placeholder icons to guarantee zero-crash execution.
- **Asset Service (`core/asset_manager.py`)**: Handles the physical copying of files into the localized `assets_library/` folder and keeps the SQLite database synced.
- **Template Service (`core/template_manager.py`)**: Specialized CRUD for larger project layout saves.
- **User Interface (`ui/views/asset_manager_view.py`)**: Implements a highly responsive interface with Grid/List toggles, live search, and categorized sidebars.

## Folder Structure

The application automatically provisions the following directory tree upon initialization:

```text
kdp_studio/
├── .cache/
│   └── thumbnails/           # Auto-generated PNG thumbnails
├── assets_library/
│   ├── Backgrounds/
│   ├── Borders/
│   ├── Clipart/
│   ├── Fonts/
│   ├── Frames/
│   ├── Icons/
│   ├── SVG/
│   ├── Templates/
│   └── Textures/
```

## Caching Workflow

1. An asset is imported.
2. The `ThumbnailGenerator` hashes the source file path and modification time.
3. It checks `.cache/thumbnails/` for an existing hit.
4. If a miss, the appropriate library renders a PNG thumbnail (max 150x150).
5. The `AssetManagerView` lazy loads this thumbnail into the UI grid.

## Database Schema

**`assets` table:**
- `id` (PK)
- `name` (TEXT)
- `category` (TEXT)
- `tags` (TEXT)
- `file_type` (TEXT)
- `file_size` (INTEGER)
- `dimensions` (TEXT)
- `dpi` (INTEGER)
- `file_path` (TEXT)
- `thumbnail_path` (TEXT)
- `is_favorite` (BOOLEAN)
- `created_at` (TIMESTAMP)

## Future Integration Points

The system exposes clean APIs (e.g., `AssetManager().get_all_assets(category="Clipart")`) designed for upcoming features:
- Drag-and-drop into the **Cover Designer**.
- Batch importing into the **Coloring Book Generator**.
- Applying Layout Templates to the **Interior Designer**.

## Testing Guide

To validate functionality:
1. Run `python -m unittest tests/test_asset_manager.py`.
2. This suite tests DB CRUD, physical file copying, duplication logic, renaming, and the fallback thumbnail generation mechanisms.
