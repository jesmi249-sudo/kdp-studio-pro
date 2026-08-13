# Planner & Journal Studio Architecture

## Overview
The Planner & Journal Studio allows users to create professional, KDP-ready planners via a modular component-based system. It supports parameter-driven layouts, variable date-resolution, and Master Pages.

## Core Engines

### 1. Planner Engine (`core/planner_engine.py`)
Responsible for executing the final build to PDF using `ReportLab`. It iterates through all pages, merges Master Page overlays, resolves variables via the `VariableEngine`, and plots `PlannerObject` primitives onto the canvas.

### 2. Variable Engine (`core/variable_engine.py`)
Parses text for contextual tags.
Supported tags (V1 Static):
- `{DATE}`, `{DAY}`, `{DAY_NAME}`, `{MONTH}`, `{MONTH_NAME}`, `{YEAR}`
- `{PAGE_NUMBER}`, `{TOTAL_PAGES}`
- `{BOOK_TITLE}`, `{AUTHOR}`

### 3. Calendar Engine (`core/calendar_engine.py`)
Provides the mathematical backbone for planner generation. Safely generates `ISO 8601` formatted date arrays spanning days, weeks, and months.

### 4. Layout Engine (`core/layout_engine.py`)
Creates complex composite tracker grids (e.g. `create_habit_tracker`, `create_dot_grid`) and standard shapes.

### 5. Master Page System (`core/master_page.py`)
`MasterPageEngine.get_merged_objects()` combines background elements (locked Master items) with foreground elements (Page-specific items) prior to PDF generation.

### 6. Database Integration (`database/db.py`)
The Planner Studio seamlessly serializes the nested object hierarchy (Projects -> Pages -> Objects -> Variables) into the main `projects` table using the `data` TEXT field as JSON.
- `save_planner_project(project)`
- `load_planner_project(project_id)`
This approach avoids complex relational query bottlenecks when loading 300+ page planners and ensures total backward compatibility with the v2.0 KDP Studio Pro architecture.

## Models
Data integrity is enforced using strictly-typed Python Dataclasses:
- `PlannerObject`: A primitive visual component.
- `PlannerPage`: A specific page holding local objects and a `date_context`.
- `MasterPage`: A background layer holding inheritable objects.
- `PlannerProject`: The root container.

## Workflow
1. User creates a `PlannerProject`.
2. User designs a `MasterPage` using parameter-based properties in the right sidebar.
3. User adds text using Variables (e.g. `{DATE}`).
4. Upon clicking **Export**, the `PlannerEngine` computes 365 days of layouts on the fly, yielding a PDF.
