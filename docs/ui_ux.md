# KDP Studio Pro UI/UX Architecture

## Overview
Phase 5.5 overhauled the user interface to bring commercial-grade polish, responsiveness, and architecture to KDP Studio Pro.

## Theme System
All styling is strictly centralized inside the `ui/theme/` directory.
- `colors.py`: Single source of truth for semantic palettes (Primary, Success, Text, etc.).
- `fonts.py`: Typographical hierarchy (Heading1, Body, Small).
- `spacing.py`: Grid alignment paddings/margins.
- `theme_manager.py`: Controls light/dark toggles globally.

## Icon System
Icons are 24x24 transparent PNGs loaded via the `IconManager` (`core/icon_manager.py`). 
The manager caches loaded images into `CTkImage` objects to ensure instantaneous, memory-efficient rendering across the application.

## Command Dispatcher
A globally available Singleton (`CommandDispatcher`) in `core/command_dispatcher.py` handles Top Toolbar button clicks. 
It dynamically interrogates the currently active view (e.g. `InteriorView`, `DashboardView`) and triggers the corresponding `cmd_[action]()` method if it exists. 

## App Layout (`ui/app.py`)
- **Row 0**: Global Toolbar
- **Row 1**: Main Workspace (Column 0: Sidebar, Column 1: Main Content)
- **Row 2**: Global Status Bar

### Lazy Loading
Views are no longer instantiated at startup. `_lazy_load_view(name)` ensures that RAM and CPU cycles are only consumed when a user actually clicks a sidebar button, achieving near-instant application boot times.

## Splash Screen
A borderless `CTkToplevel` window intercepts the boot cycle to show a progress bar. It prevents the user from seeing partial UI flashes while heavy assets load.
