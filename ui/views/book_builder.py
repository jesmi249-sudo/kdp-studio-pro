import os
from typing import Any, List, Optional, Tuple, Dict
from uuid import UUID, uuid4
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image

from book_builder.interfaces.core import IBookBuilder
from book_builder.container import Container
from book_builder.engine import BookBuilderEngine
from book_builder.models.book import BookProject, BookMetadata
from book_builder.models.page import Page
from book_builder.models.asset import Asset
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from book_builder.rendering.service import PreviewService
from book_builder.rendering.queue import RenderQueue
from book_builder.rendering.thumbnail import PageThumbnailGenerator
from core.icon_manager import IconManager
from core.logger import get_logger
from ui.theme.colors import Colors
from ui.theme.fonts import Fonts
from ui.theme.spacing import Spacing

logger = get_logger(__name__)


class WorkspaceController:
    """
    Controller in the MVC pattern that coordinates actions between the BookBuilderView
    and the backend BookBuilderEngine, PreviewService, and RenderQueue.
    """
    def __init__(self, view: "BookBuilderView") -> None:
        self.view = view
        self.event_bus = EventBus()
        self.icon_mgr = IconManager()
        
        # Resolve BookBuilderEngine from Container
        container = Container()
        try:
            self.engine: BookBuilderEngine = container.resolve(IBookBuilder)
        except Exception:
            self.engine = BookBuilderEngine()
            container.register(IBookBuilder, self.engine)

        # Pre-instantiate rendering services
        self.preview_service = PreviewService()
        self.render_queue = RenderQueue(preview_service=self.preview_service)
        self.thumbnail_generator = PageThumbnailGenerator()
        
        # Keep track of the active zoom level (1.0 = 100% / 72 DPI)
        self.zoom_level = 1.0
        self.view_mode = "Single"
        
        # Subscribe to EventBus notifications
        self._subscribe_to_events()

    def _safe_view_after(self, delay_ms: int, callback: Callable) -> None:
        """Schedules callback on view event loop, validating widget presence."""
        if hasattr(self, "view") and self.view and hasattr(self.view, "winfo_exists"):
            try:
                if self.view.winfo_exists():
                    self.view.after(delay_ms, callback)
            except Exception:
                pass

    def _subscribe_to_events(self) -> None:
        """Subscribes controller event handlers to the EventBus."""
        self.event_bus.subscribe("PROJECT_CREATED", self._on_project_changed)
        self.event_bus.subscribe("PROJECT_OPENED", self._on_project_changed)
        self.event_bus.subscribe("PROJECT_SAVED", self._on_project_saved)
        self.event_bus.subscribe("PROJECT_CLOSED", self._on_project_closed)
        self.event_bus.subscribe("PageAdded", self._on_page_structure_changed)
        self.event_bus.subscribe("PageDeleted", self._on_page_structure_changed)
        self.event_bus.subscribe("PageMoved", self._on_page_structure_changed)
        self.event_bus.subscribe("ProjectModified", self._on_page_structure_changed)
        self.event_bus.subscribe("MetadataUpdated", self._on_metadata_changed)
        self.event_bus.subscribe("UndoExecuted", self._on_page_structure_changed)
        self.event_bus.subscribe("RedoExecuted", self._on_page_structure_changed)
        
        # Render queue events
        self.event_bus.subscribe("PAGE_RENDER_STARTED", self._on_render_started)
        self.event_bus.subscribe("PAGE_RENDER_COMPLETED", self._on_render_completed)
        self.event_bus.subscribe("PAGE_RENDER_FAILED", self._on_render_failed)
        self.event_bus.subscribe("PAGE_RENDER_CANCELLED", self._on_render_cancelled)
        
        # State manager events
        self.event_bus.subscribe("PAGE_SELECTION_CHANGED", self._on_page_selection_changed)
        self.event_bus.subscribe("DIRTY_STATE_CHANGED", self._on_dirty_state_changed)

    # --- Event Handlers ---

    def _on_project_changed(self, event: Event) -> None:
        """Triggered when a project is created or opened."""
        logger.info(f"WorkspaceController: Project changed event: {event.event_type}")
        self._safe_view_after(0, self._refresh_entire_workspace)

    def _on_project_saved(self, event: Event) -> None:
        """Triggered when a project is saved."""
        self._safe_view_after(0, lambda: self.view.status_bar.update_status(dirty=False) if hasattr(self.view, "status_bar") and self.view.status_bar else None)

    def _on_project_closed(self, event: Event) -> None:
        """Triggered when a project is closed."""
        self._safe_view_after(0, lambda: self.view.reset_to_empty() if hasattr(self.view, "reset_to_empty") else None)

    def _on_page_structure_changed(self, event: Event) -> None:
        """Triggered when pages are added, deleted, moved, or modified."""
        logger.info(f"WorkspaceController: Page structure changed: {event.event_type}")
        self._safe_view_after(0, self._refresh_page_layout_elements)

    def _on_metadata_changed(self, event: Event) -> None:
        """Triggered when project metadata is updated."""
        self._safe_view_after(0, lambda: self.view.properties_panel.refresh() if hasattr(self.view, "properties_panel") and self.view.properties_panel else None)
        self._safe_view_after(0, self._update_status_bar)

    def _on_page_selection_changed(self, event: Event) -> None:
        """Triggered when page focus shifts."""
        idx = event.payload.get("active_page_index", 0)
        self._safe_view_after(0, lambda: self.view.thumbnail_panel.set_active_page_index(idx) if hasattr(self.view, "thumbnail_panel") and self.view.thumbnail_panel else None)
        self._safe_view_after(0, self._trigger_canvas_refresh)
        self._safe_view_after(0, lambda: self.view.properties_panel.refresh() if hasattr(self.view, "properties_panel") and self.view.properties_panel else None)
        self._safe_view_after(0, self._update_status_bar)

    def _on_dirty_state_changed(self, event: Event) -> None:
        is_dirty = event.payload.get("is_dirty", False)
        self._safe_view_after(0, lambda: self.view.status_bar.update_status(dirty=is_dirty) if hasattr(self.view, "status_bar") and self.view.status_bar else None)

    def _on_render_started(self, event: Event) -> None:
        page_num = event.payload.get("page_number", 1)
        self._safe_view_after(0, lambda: self.view.status_bar.update_status(render_status=f"Rendering page {page_num}...") if hasattr(self.view, "status_bar") and self.view.status_bar else None)

    def _on_render_completed(self, event: Event) -> None:
        page_id = event.payload.get("page_id")
        active_page = self.engine.state_manager.get_active_page()
        if not active_page:
            return
            
        # Check if the page_id belongs to the spread
        is_part_of_spread = False
        if str(active_page.id) == page_id:
            is_part_of_spread = True
        elif getattr(self, "view_mode", "Single") == "Facing":
            project = self.engine.get_active_project()
            if project:
                active_idx = self.engine.state_manager.project_state.active_page_index if self.engine.state_manager.project_state else 0
                if active_idx > 0:
                    facing_idx = active_idx + 1 if active_idx % 2 == 1 else active_idx - 1
                    if 0 <= facing_idx < len(project.pages):
                        if str(project.pages[facing_idx].id) == page_id:
                            is_part_of_spread = True
                            
        if is_part_of_spread:
            try:
                if getattr(self, "view_mode", "Single") == "Facing":
                    img = self.get_facing_pages_image()
                else:
                    img = self.preview_service.generate_preview(active_page, self.zoom_level)
                if img:
                    self._safe_view_after(0, lambda: self.view.canvas_panel.set_preview_image(img) if hasattr(self.view, "canvas_panel") and self.view.canvas_panel else None)
            except Exception as e:
                logger.error(f"Failed to fetch rendered image: {e}")
                
        # Always refresh the thumbnail panel to show updated page previews
        self._safe_view_after(0, lambda: self.view.thumbnail_panel.refresh() if hasattr(self.view, "thumbnail_panel") and self.view.thumbnail_panel else None)
        self._safe_view_after(0, lambda: self.view.status_bar.update_status(render_status="Ready") if hasattr(self.view, "status_bar") and self.view.status_bar else None)

    def _on_render_failed(self, event: Event) -> None:
        err = event.payload.get("error", "Unknown error")
        self._safe_view_after(0, lambda: self.view.status_bar.update_status(render_status="Render Failed") if hasattr(self.view, "status_bar") and self.view.status_bar else None)
        self._safe_view_after(0, lambda: messagebox.showerror("Render Error", f"Failed to render page: {err}") if self.view.winfo_exists() else None)

    def _on_render_cancelled(self, event: Event) -> None:
        self._safe_view_after(0, lambda: self.view.status_bar.update_status(render_status="Ready") if hasattr(self.view, "status_bar") and self.view.status_bar else None)

    # --- UI Refresh Routines ---

    def _refresh_entire_workspace(self) -> None:
        """Completely rebuilds the UI views for the current active project state."""
        project = self.engine.get_active_project()
        if not project:
            self.view.reset_to_empty()
            return
            
        self.view.toolbar.enable_buttons(True)
        self.view.thumbnail_panel.refresh()
        self.view.properties_panel.refresh()
        self.view.asset_panel.refresh()
        
        # Load the active page selection
        active_idx = self.engine.state_manager.project_state.active_page_index if self.engine.state_manager.project_state else 0
        self.view.thumbnail_panel.set_active_page_index(active_idx)
        
        self._trigger_canvas_refresh()
        self._update_status_bar()

    def _refresh_page_layout_elements(self) -> None:
        """Refreshes workspace parts concerned with page lists and counts."""
        project = self.engine.get_active_project()
        if not project:
            return
        self.view.thumbnail_panel.refresh()
        self.view.properties_panel.refresh()
        self._trigger_canvas_refresh()
        self._update_status_bar()

    def _trigger_canvas_refresh(self) -> None:
        """Enqueues a background render job for the active selected page canvas."""
        active_page = self.engine.state_manager.get_active_page()
        if not active_page:
            self.view.canvas_panel.clear_canvas()
            return
            
        # Submit task to the background RenderQueue
        self.render_queue.submit(active_page, self.zoom_level, priority=5)
        
        # In facing pages mode, also pre-render facing page
        if getattr(self, "view_mode", "Single") == "Facing":
            project = self.engine.get_active_project()
            if project:
                active_idx = self.engine.state_manager.project_state.active_page_index if self.engine.state_manager.project_state else 0
                if active_idx > 0:
                    facing_idx = active_idx + 1 if active_idx % 2 == 1 else active_idx - 1
                    if 0 <= facing_idx < len(project.pages):
                        self.render_queue.submit(project.pages[facing_idx], self.zoom_level, priority=4)

    def _update_status_bar(self) -> None:
        """Refreshes status indicators in the footer bar."""
        project = self.engine.get_active_project()
        if not project:
            self.view.status_bar.update_status()
            return
            
        active_idx = self.engine.state_manager.project_state.active_page_index if self.engine.state_manager.project_state else 0
        page_num_str = f"Page {active_idx + 1} of {len(project.pages)}" if project.pages else "No Pages"
        
        self.view.status_bar.update_status(
            project_name=project.name,
            dirty=self.engine.state_manager.is_dirty(),
            selected_page=page_num_str,
            zoom_level=f"{int(self.zoom_level * 100)}%",
            autosave_status="Autosave: Active"
        )

    # --- Public View API Actions (Delegating to Engine) ---

    def create_project(self, name: str, book_type: str, settings: dict) -> None:
        self.engine.create_project(name, book_type, settings)

    def select_page(self, index: int) -> None:
        project = self.engine.get_active_project()
        if project and 0 <= index < len(project.pages):
            self.engine.state_manager.set_active_page(index)

    def add_page(self) -> None:
        project = self.engine.get_active_project()
        if not project:
            return
            
        # Determine index after currently selected page
        active_idx = self.engine.state_manager.project_state.active_page_index if self.engine.state_manager.project_state else 0
        new_page_number = active_idx + 2 if project.pages else 1
        
        new_page = Page(
            page_number=new_page_number,
            width_pt=project.trim_width_in * 72.0,
            height_pt=project.trim_height_in * 72.0,
            has_bleed=project.has_bleed
        )
        # Call facade method
        self.engine.add_page(new_page)
        
        # Automatically shift selection focus to the new page
        self.select_page(new_page_number - 1)

    def delete_page(self) -> None:
        project = self.engine.get_active_project()
        if not project or not project.pages:
            return
            
        active_idx = self.engine.state_manager.project_state.active_page_index if self.engine.state_manager.project_state else 0
        page_to_delete = project.pages[active_idx]
        
        # Enforce minimum page count check if needed
        confirm = messagebox.askyesno("Delete Page", f"Are you sure you want to delete Page {page_to_delete.page_number}?")
        if not confirm:
            return
            
        # Call facade method
        self.engine.delete_page(page_to_delete.page_number)
        
        # Adjust focus selection index safely
        new_idx = max(0, active_idx - 1)
        self.select_page(new_idx)

    def duplicate_page(self) -> None:
        project = self.engine.get_active_project()
        if not project or not project.pages:
            return
            
        active_idx = self.engine.state_manager.project_state.active_page_index if self.engine.state_manager.project_state else 0
        page_to_dup = project.pages[active_idx]
        
        # Call facade method
        self.engine.duplicate_page(page_to_dup.page_number)
        
        # Shift selection to duplicate (which is inserted immediately after)
        self.select_page(active_idx + 1)

    def move_page_up(self) -> None:
        project = self.engine.get_active_project()
        if not project or len(project.pages) <= 1:
            return
            
        active_idx = self.engine.state_manager.project_state.active_page_index if self.engine.state_manager.project_state else 0
        if active_idx == 0:
            return # Already top page
            
        self.engine.move_page(active_idx, active_idx - 1)
        self.select_page(active_idx - 1)

    def move_page_down(self) -> None:
        project = self.engine.get_active_project()
        if not project or len(project.pages) <= 1:
            return
            
        active_idx = self.engine.state_manager.project_state.active_page_index if self.engine.state_manager.project_state else 0
        if active_idx == len(project.pages) - 1:
            return # Already bottom page
            
        self.engine.move_page(active_idx, active_idx + 1)
        self.select_page(active_idx + 1)

    def undo(self) -> None:
        self.engine.undo()

    def redo(self) -> None:
        self.engine.redo()

    def save_project(self) -> None:
        success = self.engine.save_project()
        if success:
            messagebox.showinfo("Save Project", "Project saved successfully.")
        else:
            messagebox.showerror("Error", "Failed to save project. Ensure a project is currently open.")

    def load_project(self, project_id: Any) -> None:
        """Loads a project from database into the engine."""
        self.engine.load_project(project_id)

    def set_project(self, project: BookProject) -> None:
        """Sets the active project in the engine's state manager."""
        self.engine.state_manager.set_project(project)

    def set_zoom(self, zoom: float) -> None:
        self.zoom_level = max(0.1, min(8.0, zoom))
        self._update_status_bar()
        self._trigger_canvas_refresh()

    def update_metadata(self, title: str, subtitle: str, author: str, publisher: str, description: str) -> None:
        project = self.engine.get_active_project()
        if not project:
            return
            
        new_meta = BookMetadata(
            title=title,
            subtitle=subtitle,
            author=author,
            publisher=publisher,
            description=description,
            language=project.metadata.language,
            keywords=project.metadata.keywords,
            categories=project.metadata.categories,
            isbn=project.metadata.isbn
        )
        self.engine.update_metadata(new_meta)

    def get_facing_pages_image(self) -> Optional[Image.Image]:
        """Loads and stitches facing pages together side-by-side."""
        active_page = self.engine.state_manager.get_active_page()
        if not active_page:
            return None
        project = self.engine.get_active_project()
        if not project:
            return None
            
        active_idx = self.engine.state_manager.project_state.active_page_index if self.engine.state_manager.project_state else 0
        
        # Page 1 (index 0) is standard right-side standalone
        if active_idx == 0:
            return self.preview_service.generate_preview(active_page, self.zoom_level)
            
        # Determine left and right pages
        if active_idx % 2 == 1:
            left_idx = active_idx
            right_idx = active_idx + 1
        else:
            left_idx = active_idx - 1
            right_idx = active_idx
            
        left_page = project.pages[left_idx]
        img1 = self.preview_service.generate_preview(left_page, self.zoom_level)
        
        if right_idx < len(project.pages):
            right_page = project.pages[right_idx]
            img2 = self.preview_service.generate_preview(right_page, self.zoom_level)
        else:
            # Empty right page for final spread
            img2 = Image.new("RGBA", img1.size, (255, 255, 255, 255))
            
        w1, h1 = img1.size
        w2, h2 = img2.size
        
        # Stitch side-by-side
        stitched = Image.new("RGBA", (w1 + w2, max(h1, h2)), (240, 240, 240, 255))
        stitched.paste(img1, (0, 0))
        stitched.paste(img2, (w1, 0))
        return stitched

    def set_view_mode(self, mode: str) -> None:
        """Sets preview mode ('Single' or 'Facing') and triggers a refresh."""
        if mode in ("Single", "Facing"):
            self.view_mode = mode
            self._trigger_canvas_refresh()

    def fit_width(self) -> None:
        """Calculates and sets zoom level to fit the page width in the canvas view."""
        active_page = self.engine.state_manager.get_active_page()
        if not active_page: return
        canvas_w = self.view.canvas_panel.winfo_width()
        if canvas_w <= 1: canvas_w = 600
        page_w = active_page.width_pt
        if getattr(self, "view_mode", "Single") == "Facing":
            page_w *= 2
        zoom = (canvas_w - 40) / page_w
        self.set_zoom(zoom)

    def fit_height(self) -> None:
        """Calculates and sets zoom level to fit the page height in the canvas view."""
        active_page = self.engine.state_manager.get_active_page()
        if not active_page: return
        canvas_h = self.view.canvas_panel.winfo_height()
        if canvas_h <= 1: canvas_h = 700
        zoom = (canvas_h - 40) / active_page.height_pt
        self.set_zoom(zoom)

    def book_flip_forward(self) -> None:
        """Advances to the next page or spread."""
        project = self.engine.get_active_project()
        if not project: return
        active_idx = self.engine.state_manager.project_state.active_page_index if self.engine.state_manager.project_state else 0
        step = 2 if getattr(self, "view_mode", "Single") == "Facing" else 1
        new_idx = min(len(project.pages) - 1, active_idx + step)
        self.select_page(new_idx)

    def book_flip_backward(self) -> None:
        """Goes back to the previous page or spread."""
        project = self.engine.get_active_project()
        if not project: return
        active_idx = self.engine.state_manager.project_state.active_page_index if self.engine.state_manager.project_state else 0
        step = 2 if getattr(self, "view_mode", "Single") == "Facing" else 1
        new_idx = max(0, active_idx - step)
        self.select_page(new_idx)

    def search_page(self, query: str) -> Optional[int]:
        """Finds and selects the first page index matching query text or metadata."""
        project = self.engine.get_active_project()
        if not project or not query: return None
        query_lower = query.lower()
        for idx, page in enumerate(project.pages):
            for tb in page.text_blocks:
                if query_lower in tb.get("text", "").lower():
                    self.select_page(idx)
                    return idx
            if query_lower in str(page.page_number) or query_lower in page.page_type.lower():
                self.select_page(idx)
                return idx
        return None

    def generate_notebook(self, page_count: int, trim_width_in: float, trim_height_in: float,
                          margin_top_in: float, margin_bottom_in: float, margin_inside_in: float, margin_outside_in: float,
                          has_bleed: bool, template_type: str, settings: Optional[Dict[str, Any]] = None) -> None:
        """Executes GenerateNotebookPagesCommand via the command pipeline."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.notebook_commands import GenerateNotebookPagesCommand
        cmd = GenerateNotebookPagesCommand(
            project=project,
            page_count=page_count,
            trim_width_in=trim_width_in,
            trim_height_in=trim_height_in,
            margin_top_in=margin_top_in,
            margin_bottom_in=margin_bottom_in,
            margin_inside_in=margin_inside_in,
            margin_outside_in=margin_outside_in,
            has_bleed=has_bleed,
            template_type=template_type,
            settings=settings
        )
        self.engine.execute_command(cmd)

    def generate_coloring(self, page_count: int, trim_width_in: float, trim_height_in: float,
                          margin_top_in: float, margin_bottom_in: float, margin_inside_in: float, margin_outside_in: float,
                          has_bleed: bool, settings: Optional[Dict[str, Any]] = None) -> None:
        """Executes GenerateColoringPagesCommand to generate coloring page slots."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.coloring_commands import GenerateColoringPagesCommand
        cmd = GenerateColoringPagesCommand(
            project=project,
            page_count=page_count,
            trim_width_in=trim_width_in,
            trim_height_in=trim_height_in,
            margin_top_in=margin_top_in,
            margin_bottom_in=margin_bottom_in,
            margin_inside_in=margin_inside_in,
            margin_outside_in=margin_outside_in,
            has_bleed=has_bleed,
            settings=settings
        )
        self.engine.execute_command(cmd)

    def replace_artwork(self, page_index: int, artwork_path: str, settings: Dict[str, Any]) -> None:
        """Replaces the artwork image on a specific page index."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.coloring_commands import ReplaceArtworkCommand
        cmd = ReplaceArtworkCommand(
            project=project,
            page_index=page_index,
            new_artwork_path=artwork_path,
            settings=settings
        )
        self.engine.execute_command(cmd)

    def batch_import_artwork(self, artwork_paths: List[str], settings: Dict[str, Any]) -> None:
        """Batch imports multiple illustration images into coloring pages."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.coloring_commands import BatchImportArtworkCommand
        cmd = BatchImportArtworkCommand(
            project=project,
            artwork_paths=artwork_paths,
            settings=settings
        )
        self.engine.execute_command(cmd)

    def shuffle_artwork(self, settings: Dict[str, Any]) -> None:
        """Shuffles the placed illustrations order across print pages."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.coloring_commands import ShuffleArtworkCommand
        cmd = ShuffleArtworkCommand(project=project, settings=settings)
        self.engine.execute_command(cmd)

    def generate_planner(self, page_count: int, trim_width_in: float, trim_height_in: float,
                         margin_top_in: float, margin_bottom_in: float, margin_inside_in: float, margin_outside_in: float,
                         has_bleed: bool, planner_type: str, settings: Optional[Dict[str, Any]] = None) -> None:
        """Executes GeneratePlannerPagesCommand via the command pipeline."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.planner_commands import GeneratePlannerPagesCommand
        cmd = GeneratePlannerPagesCommand(
            project=project,
            page_count=page_count,
            trim_width_in=trim_width_in,
            trim_height_in=trim_height_in,
            margin_top_in=margin_top_in,
            margin_bottom_in=margin_bottom_in,
            margin_inside_in=margin_inside_in,
            margin_outside_in=margin_outside_in,
            has_bleed=has_bleed,
            planner_type=planner_type,
            settings=settings
        )
        self.engine.execute_command(cmd)

    def update_planner_settings(self, settings: Dict[str, Any]) -> None:
        """Updates the active planner layout settings."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.planner_commands import UpdatePlannerSettingsCommand
        cmd = UpdatePlannerSettingsCommand(project=project, settings=settings)
        self.engine.execute_command(cmd)

    def insert_planner_section(self, start_page_number: int, page_count: int, planner_type: str, settings: Dict[str, Any]) -> None:
        """Inserts a section of planner pages."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.planner_commands import InsertPlannerSectionCommand
        cmd = InsertPlannerSectionCommand(
            project=project,
            start_page_number=start_page_number,
            page_count=page_count,
            planner_type=planner_type,
            settings=settings
        )
        self.engine.execute_command(cmd)

    def duplicate_planner_page(self, page_index: int) -> None:
        """Duplicates a specific planner page."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.planner_commands import DuplicatePlannerPageCommand
        cmd = DuplicatePlannerPageCommand(project=project, page_index=page_index)
        self.engine.execute_command(cmd)

    def delete_planner_section(self, start_page_number: int, end_page_number: int) -> None:
        """Deletes a range of planner pages."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.planner_commands import DeletePlannerSectionCommand
        cmd = DeletePlannerSectionCommand(project=project, start_page_number=start_page_number, end_page_number=end_page_number)
        self.engine.execute_command(cmd)

    def generate_activity(self, page_count: int, trim_width_in: float, trim_height_in: float,
                          margin_top_in: float, margin_bottom_in: float, margin_inside_in: float, margin_outside_in: float,
                          has_bleed: bool, activity_type: str, settings: Optional[Dict[str, Any]] = None) -> None:
        """Executes GenerateActivityPagesCommand via command pipeline."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.activity_commands import GenerateActivityPagesCommand
        cmd = GenerateActivityPagesCommand(
            project=project,
            page_count=page_count,
            trim_width_in=trim_width_in,
            trim_height_in=trim_height_in,
            margin_top_in=margin_top_in,
            margin_bottom_in=margin_bottom_in,
            margin_inside_in=margin_inside_in,
            margin_outside_in=margin_outside_in,
            has_bleed=has_bleed,
            activity_type=activity_type,
            settings=settings
        )
        self.engine.execute_command(cmd)

    def regenerate_puzzle(self, page_index: int, settings: Dict[str, Any]) -> None:
        """Executes RegenerateActivityCommand."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.activity_commands import RegenerateActivityCommand
        cmd = RegenerateActivityCommand(project=project, page_index=page_index, settings=settings)
        self.engine.execute_command(cmd)

    def shuffle_puzzle(self, page_index: int, settings: Dict[str, Any]) -> None:
        """Executes ShuffleActivityCommand."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.activity_commands import ShuffleActivityCommand
        cmd = ShuffleActivityCommand(project=project, page_index=page_index, settings=settings)
        self.engine.execute_command(cmd)

    def replace_activity_artwork(self, page_index: int, new_activity_type: str, settings: Dict[str, Any]) -> None:
        """Executes ReplaceArtworkCommand."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.activity_commands import ReplaceArtworkCommand
        cmd = ReplaceArtworkCommand(project=project, page_index=page_index, new_activity_type=new_activity_type, settings=settings)
        self.engine.execute_command(cmd)

    def duplicate_activity_page(self, page_index: int) -> None:
        """Executes DuplicateActivityPageCommand."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.activity_commands import DuplicateActivityPageCommand
        cmd = DuplicateActivityPageCommand(project=project, page_index=page_index)
        self.engine.execute_command(cmd)

    def delete_activity_page(self, page_index: int) -> None:
        """Executes DeleteActivityPageCommand."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.activity_commands import DeleteActivityPageCommand
        cmd = DeleteActivityPageCommand(project=project, page_index=page_index)
        self.engine.execute_command(cmd)

    def add_decorative_asset(self, page_index: int, asset_path: str, geometry: Dict[str, Any]) -> None:
        """Executes AddDecorativeAssetCommand to overlay illustration or border onto a page."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.activity_commands import AddDecorativeAssetCommand
        cmd = AddDecorativeAssetCommand(
            project=project,
            page_index=page_index,
            asset_path=asset_path,
            geometry=geometry
        )
        self.engine.execute_command(cmd)

    def insert_asset_to_active_page(self, asset_path: str) -> None:
        """Inserts an asset at the center of the active page."""
        project = self.engine.get_active_project()
        if not project:
            return
        active_idx = self.engine.state_manager.project_state.active_page_index if self.engine.state_manager.project_state else 0
        if active_idx < 0 or active_idx >= len(project.pages):
            return
        page = project.pages[active_idx]
        w = page.width_pt
        h = page.height_pt
        
        # Center the asset (width=120, height=120)
        geom = {
            "x": (w - 120) / 2.0,
            "y": (h - 120) / 2.0,
            "width": 120.0,
            "height": 120.0
        }
        self.add_decorative_asset(active_idx, asset_path, geom)

    def batch_generate_activities(self, page_count: int, trim_width_in: float, trim_height_in: float,
                                  margin_top_in: float, margin_bottom_in: float, margin_inside_in: float, margin_outside_in: float,
                                  has_bleed: bool, activity_types: List[str], settings: Optional[Dict[str, Any]] = None) -> None:
        """Executes BatchGenerateActivitiesCommand."""
        project = self.engine.get_active_project()
        if not project:
            return
            
        from book_builder.commands.activity_commands import BatchGenerateActivitiesCommand
        cmd = BatchGenerateActivitiesCommand(
            project=project,
            page_count=page_count,
            trim_width_in=trim_width_in,
            trim_height_in=trim_height_in,
            margin_top_in=margin_top_in,
            margin_bottom_in=margin_bottom_in,
            margin_inside_in=margin_inside_in,
            margin_outside_in=margin_outside_in,
            has_bleed=has_bleed,
            activity_types=activity_types,
            settings=settings
        )
        self.engine.execute_command(cmd)

    def import_asset(self) -> None:
        project = self.engine.get_active_project()
        if not project:
            return
            
        file_path = filedialog.askopenfilename(
            title="Import Asset",
            filetypes=[
                ("Image/Vector Files", "*.png;*.jpg;*.jpeg;*.svg;*.pdf"),
                ("All Files", "*.*")
            ]
        )
        if not file_path:
            return
            
        name = os.path.basename(file_path)
        ext = os.path.splitext(name)[1].lower()
        asset_type = "Background" if ext == ".pdf" else "Image"
        
        asset = Asset(
            id=uuid4(),
            name=name,
            file_path=file_path,
            asset_type=asset_type,
            file_size_bytes=os.path.getsize(file_path) if os.path.exists(file_path) else 0
        )
        self.engine.import_asset(asset)

    def remove_asset(self, asset_id: UUID) -> None:
        self.engine.remove_asset(asset_id)


class Toolbar(ctk.CTkFrame):
    """Top toolbar displaying action buttons for page operations, undo, redo, and save."""
    def __init__(self, master: "BookBuilderView", controller: WorkspaceController, **kwargs) -> None:
        super().__init__(master, height=50, corner_radius=0, **kwargs)
        self.controller = controller
        self.icon_mgr = IconManager()
        
        self._build_ui()

    def _build_ui(self) -> None:
        # Group 1: Project operations
        self.save_btn = self._add_button("Save", "save.png", self.controller.save_project)
        self._add_separator()
        
        # Group 2: Edit history
        self.undo_btn = self._add_button("Undo", "undo.png", self.controller.undo)
        self.redo_btn = self._add_button("Redo", "redo.png", self.controller.redo)
        self._add_separator()
        
        # Group 3: Page management
        self.add_page_btn = self._add_button("+ Page", "new.png", self.controller.add_page)
        self.dup_page_btn = self._add_button("Duplicate", "open.png", self.controller.duplicate_page)
        self.del_page_btn = self._add_button("Delete", "help.png", self.controller.delete_page)
        self._add_separator()
        
        # Group 4: Page Reordering
        self.move_up_btn = self._add_button("Move Up", "undo.png", self.controller.move_page_up)
        self.move_down_btn = self._add_button("Move Down", "redo.png", self.controller.move_page_down)
        self._add_separator()
        
        # Group 5: Zoom Controls
        zoom_lbl = ctk.CTkLabel(self, text="Zoom:", font=Fonts.body_bold())
        zoom_lbl.pack(side="left", padx=(10, 2))
        
        self.zoom_val = ctk.CTkEntry(self, width=60, font=Fonts.body())
        self.zoom_val.insert(0, "100%")
        self.zoom_val.pack(side="left", padx=2, pady=5)
        self.zoom_val.bind("<Return>", self._on_zoom_enter)
        
        self.zoom_in_btn = ctk.CTkButton(self, text="+", width=30, font=Fonts.body_bold(), command=self._zoom_in)
        self.zoom_in_btn.pack(side="left", padx=2, pady=5)
        
        self.zoom_out_btn = ctk.CTkButton(self, text="-", width=30, font=Fonts.body_bold(), command=self._zoom_out)
        self.zoom_out_btn.pack(side="left", padx=2, pady=5)
        self._add_separator()

        # Group 6: Professional Preview Modes & Layout navigation
        ctk.CTkLabel(self, text="Mode:", font=Fonts.body_bold()).pack(side="left", padx=2)
        self.mode_var = ctk.StringVar(value="Single")
        self.mode_menu = ctk.CTkOptionMenu(
            self, variable=self.mode_var, values=["Single", "Facing"], width=80,
            command=self._on_mode_changed
        )
        self.mode_menu.pack(side="left", padx=2, pady=5)
        
        self.fit_w_btn = ctk.CTkButton(self, text="Fit Width", width=70, font=Fonts.body(), command=self.controller.fit_width)
        self.fit_w_btn.pack(side="left", padx=2, pady=5)
        
        self.fit_h_btn = ctk.CTkButton(self, text="Fit Height", width=70, font=Fonts.body(), command=self.controller.fit_height)
        self.fit_h_btn.pack(side="left", padx=2, pady=5)
        
        # Book Flip buttons
        self.flip_prev_btn = ctk.CTkButton(self, text="◀", width=30, font=Fonts.body_bold(), command=self.controller.book_flip_backward)
        self.flip_prev_btn.pack(side="left", padx=2, pady=5)
        self.flip_next_btn = ctk.CTkButton(self, text="▶", width=30, font=Fonts.body_bold(), command=self.controller.book_flip_forward)
        self.flip_next_btn.pack(side="left", padx=2, pady=5)
        self._add_separator()

        # Go To Page & Search Page entries
        ctk.CTkLabel(self, text="Go To:", font=Fonts.body_bold()).pack(side="left", padx=2)
        self.goto_val = ctk.CTkEntry(self, width=45, font=Fonts.body())
        self.goto_val.pack(side="left", padx=2, pady=5)
        self.goto_val.bind("<Return>", self._on_goto_enter)

        ctk.CTkLabel(self, text="Search:", font=Fonts.body_bold()).pack(side="left", padx=(10, 2))
        self.search_val = ctk.CTkEntry(self, width=80, font=Fonts.body())
        self.search_val.pack(side="left", padx=2, pady=5)
        self.search_val.bind("<Return>", self._on_search_enter)

    def _on_mode_changed(self, val: str) -> None:
        self.controller.set_view_mode(val)

    def _on_goto_enter(self, event) -> None:
        val = self.goto_val.get().strip()
        if val.isdigit():
            self.controller.select_page(int(val) - 1)
            self.goto_val.delete(0, "end")

    def _on_search_enter(self, event) -> None:
        query = self.search_val.get().strip()
        if query:
            self.controller.search_page(query)

    def _add_button(self, text: str, icon_name: str, command: Any) -> ctk.CTkButton:
        img = self.icon_mgr.get_icon(icon_name)
        btn = ctk.CTkButton(
            self, text=text, image=img, width=60, fg_color="transparent",
            text_color=("black", "white"), font=Fonts.body(), command=command
        )
        btn.pack(side="left", padx=2, pady=5)
        return btn

    def _add_separator(self) -> None:
        sep = ctk.CTkFrame(self, width=2, height=30, fg_color=("gray75", "gray30"))
        sep.pack(side="left", padx=8, pady=10)

    def enable_buttons(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.save_btn.configure(state=state)
        self.undo_btn.configure(state=state)
        self.redo_btn.configure(state=state)
        self.add_page_btn.configure(state=state)
        self.dup_page_btn.configure(state=state)
        self.del_page_btn.configure(state=state)
        self.move_up_btn.configure(state=state)
        self.move_down_btn.configure(state=state)
        self.zoom_in_btn.configure(state=state)
        self.zoom_out_btn.configure(state=state)

    def _on_zoom_enter(self, event) -> None:
        val = self.zoom_val.get().replace("%", "").strip()
        try:
            factor = float(val) / 100.0
            self.controller.set_zoom(factor)
        except ValueError:
            self.zoom_val.delete(0, "end")
            self.zoom_val.insert(0, f"{int(self.controller.zoom_level * 100)}%")

    def _zoom_in(self) -> None:
        self.controller.set_zoom(self.controller.zoom_level + 0.2)
        self.zoom_val.delete(0, "end")
        self.zoom_val.insert(0, f"{int(self.controller.zoom_level * 100)}%")

    def _zoom_out(self) -> None:
        self.controller.set_zoom(self.controller.zoom_level - 0.2)
        self.zoom_val.delete(0, "end")
        self.zoom_val.insert(0, f"{int(self.controller.zoom_level * 100)}%")


class StatusBar(ctk.CTkFrame):
    """Status bar displaying project state, active page, rendering status, and zoom level."""
    def __init__(self, master: "BookBuilderView", **kwargs) -> None:
        super().__init__(master, height=30, corner_radius=0, **kwargs)
        
        self.project_lbl = ctk.CTkLabel(self, text="No Project Active", font=Fonts.small())
        self.project_lbl.pack(side="left", padx=15, pady=2)
        
        self.render_lbl = ctk.CTkLabel(self, text="Status: Idle", font=Fonts.small(), text_color=Colors.TEXT_MUTED[1])
        self.render_lbl.pack(side="left", padx=30, pady=2)
        
        self.autosave_lbl = ctk.CTkLabel(self, text="Autosave: Idle", font=Fonts.small(), text_color=Colors.TEXT_MUTED[1])
        self.autosave_lbl.pack(side="right", padx=15, pady=2)
        
        self.zoom_lbl = ctk.CTkLabel(self, text="Zoom: 100%", font=Fonts.small())
        self.zoom_lbl.pack(side="right", padx=20, pady=2)
        
        self.selection_lbl = ctk.CTkLabel(self, text="Page 0 of 0", font=Fonts.small())
        self.selection_lbl.pack(side="right", padx=20, pady=2)

    def update_status(self, project_name: str = "", dirty: bool = False, selected_page: str = "Page 0 of 0", 
                      zoom_level: str = "100%", render_status: str = "Ready", autosave_status: str = "Autosave: Active") -> None:
        """Updates text values on status label fields."""
        if not project_name:
            self.project_lbl.configure(text="No Project Active", text_color=Colors.TEXT_MUTED[1])
            self.selection_lbl.configure(text="Page 0 of 0")
            self.zoom_lbl.configure(text="Zoom: 100%")
            self.render_lbl.configure(text="Status: Idle")
            return
            
        dirty_indicator = " *" if dirty else ""
        self.project_lbl.configure(text=f"Project: {project_name}{dirty_indicator}", text_color=Colors.TEXT_MAIN[1])
        self.selection_lbl.configure(text=selected_page)
        self.zoom_lbl.configure(text=f"Zoom: {zoom_level}")
        self.render_lbl.configure(text=f"Status: {render_status}")
        self.autosave_lbl.configure(text=autosave_status)


class PageThumbnailPanel(ctk.CTkFrame):
    """Left sidebar scrollable thumbnail list of book pages with virtual pagination."""
    def __init__(self, master: "BookBuilderView", controller: WorkspaceController, **kwargs) -> None:
        super().__init__(master, width=200, **kwargs)
        self.controller = controller
        self.cards: List[ctk.CTkFrame] = []
        self.active_idx = 0
        
        # Pagination variables
        self.page_size = 20
        self.current_page = 0
        
        self._build_ui()
        
    def _build_ui(self) -> None:
        self.grid_rowconfigure(0, weight=0) # Pagination control
        self.grid_rowconfigure(1, weight=1) # Scrollable frame
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Pagination header
        self.nav_frame = ctk.CTkFrame(self, height=35, fg_color="transparent")
        self.nav_frame.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        
        self.prev_btn = ctk.CTkButton(self.nav_frame, text="◀", width=25, font=Fonts.small(), command=self.prev_page)
        self.prev_btn.pack(side="left", padx=2)
        
        self.page_lbl = ctk.CTkLabel(self.nav_frame, text="Page 1-20", font=Fonts.small())
        self.page_lbl.pack(side="left", expand=True)
        
        self.next_btn = ctk.CTkButton(self.nav_frame, text="▶", width=25, font=Fonts.small(), command=self.next_page)
        self.next_btn.pack(side="left", padx=2)
        
        # 2. Scrollable frame for page list
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

    def prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh()

    def next_page(self) -> None:
        project = self.controller.engine.get_active_project()
        if project:
            max_pages = (len(project.pages) - 1) // self.page_size
            if self.current_page < max_pages:
                self.current_page += 1
                self.refresh()

    def refresh(self) -> None:
        """Re-populates the scrollable frame with page thumbnail cards."""
        # Clean existing widgets
        for card in self.cards:
            card.destroy()
        self.cards.clear()

        project = self.controller.engine.get_active_project()
        if not project or not project.pages:
            placeholder = ctk.CTkLabel(self.scroll_frame, text="No Pages", font=Fonts.body(), text_color=Colors.TEXT_MUTED[1])
            placeholder.pack(pady=Spacing.L)
            self.cards.append(placeholder)
            self.page_lbl.configure(text="0 of 0")
            return

        # Calculate paginated window indices
        total_pages = len(project.pages)
        start_idx = self.current_page * self.page_size
        end_idx = min(total_pages, start_idx + self.page_size)
        
        # Update label
        self.page_lbl.configure(text=f"{start_idx + 1}-{end_idx} of {total_pages}")
        
        # Populate visible cards
        for idx in range(start_idx, end_idx):
            page = project.pages[idx]
            card = ctk.CTkFrame(self.scroll_frame, height=130, corner_radius=6, border_width=1, fg_color=Colors.BG_CARD)
            card.pack(fill="x", padx=5, pady=6)
            
            # Label
            lbl = ctk.CTkLabel(card, text=f"Page {page.page_number}", font=Fonts.small())
            lbl.pack(pady=(4, 2))
            
            # Fetch Cached/Disk Thumbnail Path
            thumb_path = self.controller.thumbnail_generator.get_thumbnail_path(page, size=(80, 80))
            if thumb_path and os.path.exists(thumb_path):
                try:
                    pil_img = Image.open(thumb_path)
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(80, 80))
                    img_lbl = ctk.CTkLabel(card, image=ctk_img, text="")
                    img_lbl.pack(pady=2)
                except Exception as e:
                    logger.error(f"Thumbnail panel: failed to load thumbnail image file: {e}")
            else:
                # Fallback gray box
                box = ctk.CTkFrame(card, width=80, height=80, fg_color="gray75" if idx != self.active_idx else Colors.PRIMARY[1])
                box.pack(pady=2)
            
            # Click command to select
            card.bind("<Button-1>", lambda event, i=idx: self.controller.select_page(i))
            for widget in card.winfo_children():
                widget.bind("<Button-1>", lambda event, i=idx: self.controller.select_page(i))
                
            self.cards.append(card)
            
        self.set_active_page_index(self.active_idx)

    def set_active_page_index(self, index: int) -> None:
        """Updates border color styling for the selected page card."""
        self.active_idx = index
        
        # Automatically shift pagination page if active index is out of bounds
        if index < self.current_page * self.page_size or index >= (self.current_page + 1) * self.page_size:
            self.current_page = index // self.page_size
            self.refresh()
            return
            
        # Highlight card in active subset
        start_idx = self.current_page * self.page_size
        for i, card in enumerate(self.cards):
            actual_idx = start_idx + i
            if isinstance(card, ctk.CTkFrame):
                if actual_idx == index:
                    card.configure(border_color=Colors.PRIMARY[0], border_width=2)
                else:
                    card.configure(border_color=Colors.BORDER[1], border_width=1)


class PageCanvas(ctk.CTkFrame):
    """Central workspace canvas for displaying selected page preview raster graphics."""
    def __init__(self, master: "BookBuilderView", controller: WorkspaceController, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.controller = controller
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(self, bg="#444444", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=Spacing.S, pady=Spacing.S)
        
        self.canvas_image_id = None
        self.current_pil_img = None
        self.tk_image = None
        self.drag_rect_id = None
        
        # Display empty message on start
        self.canvas.bind("<Configure>", self._on_configure)

    def show_drag_indicator(self, rx: float, ry: float, w_pt: float = 120.0, h_pt: float = 120.0) -> None:
        """Draws a dotted rectangle on the canvas representing drag placement location."""
        self.clear_drag_indicator()
        if self.current_pil_img is None:
            return
            
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        img_w, img_h = self.current_pil_img.size
        ratio = min(canvas_w / img_w, canvas_h / img_h) * 0.95
        fit_w = img_w * ratio
        
        project = self.controller.engine.get_active_project()
        if not project or not project.pages:
            return
        active_idx = self.controller.engine.state_manager.project_state.active_page_index if self.controller.engine.state_manager.project_state else 0
        if active_idx < 0 or active_idx >= len(project.pages):
            return
        page = project.pages[active_idx]
        pt_ratio = fit_w / page.width_pt
        
        w_px = w_pt * pt_ratio
        h_px = h_pt * pt_ratio
        
        x0 = rx - w_px / 2.0
        y0 = ry - h_px / 2.0
        x1 = rx + w_px / 2.0
        y1 = ry + h_px / 2.0
        
        self.drag_rect_id = self.canvas.create_rectangle(
            x0, y0, x1, y1,
            outline=Colors.PRIMARY[0], width=2, dash=(4, 4)
        )

    def clear_drag_indicator(self) -> None:
        """Clears any active drag placement rectangle overlay."""
        if self.drag_rect_id is not None:
            self.canvas.delete(self.drag_rect_id)
            self.drag_rect_id = None

    def set_preview_image(self, img: Image.Image) -> None:
        """Sets the raster image to render on the canvas."""
        self.current_pil_img = img
        self._redraw_image()

    def clear_canvas(self) -> None:
        """Clears the canvas content."""
        self.current_pil_img = None
        self.canvas.delete("all")
        
        # Draw placeholder text
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.canvas.create_text(
            w // 2, h // 2, text="No Project Active\n\nCreate a new project or select an existing project from the sidebar.",
            fill="white", justify="center", font=("Roboto", 14, "bold")
        )

    def _on_configure(self, event) -> None:
        self._redraw_image()

    def _redraw_image(self) -> None:
        if self.current_pil_img is None:
            self.clear_canvas()
            return
            
        self.canvas.delete("all")
        
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        # Resize image to fit canvas bounds maintaining ratio
        img_w, img_h = self.current_pil_img.size
        ratio = min(canvas_w / img_w, canvas_h / img_h) * 0.95
        
        fit_w = int(img_w * ratio)
        fit_h = int(img_h * ratio)
        
        # Prevent zero dimension resize exceptions
        fit_w = max(10, fit_w)
        fit_h = max(10, fit_h)
        
        try:
            resized_img = self.current_pil_img.resize((fit_w, fit_h), Image.Resampling.LANCZOS)
            from PIL import ImageTk
            self.tk_image = ImageTk.PhotoImage(resized_img)
            
            # Render centered
            x = canvas_w // 2
            y = canvas_h // 2
            self.canvas_image_id = self.canvas.create_image(x, y, image=self.tk_image, anchor="center")
        except Exception as e:
            logger.error(f"PageCanvas: failed to render preview image to canvas widget: {e}")
            self.clear_canvas()


class PropertiesPanel(ctk.CTkScrollableFrame):
    """Right sidebar panel displaying and allowing editing of project/page parameters."""
    def __init__(self, master: "BookBuilderView", controller: WorkspaceController, **kwargs) -> None:
        super().__init__(master, width=250, **kwargs)
        self.controller = controller
        self.plugin_panel: Optional[ctk.CTkFrame] = None
        self.active_project_type: Optional[str] = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.container_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.container_frame.pack(fill="both", expand=True)
        
        # Title Label
        ctk.CTkLabel(self.container_frame, text="Document Info", font=Fonts.heading3()).pack(anchor="w", pady=(Spacing.M, Spacing.S))
        
        # Project metadata
        ctk.CTkLabel(self.container_frame, text="Project Title:", font=Fonts.body_bold()).pack(anchor="w", pady=(10, 0))
        self.title_entry = ctk.CTkEntry(self.container_frame)
        self.title_entry.pack(fill="x", pady=2)
        
        ctk.CTkLabel(self.container_frame, text="Author:", font=Fonts.body_bold()).pack(anchor="w", pady=(10, 0))
        self.author_entry = ctk.CTkEntry(self.container_frame)
        self.author_entry.pack(fill="x", pady=2)
        
        ctk.CTkLabel(self.container_frame, text="Publisher:", font=Fonts.body_bold()).pack(anchor="w", pady=(10, 0))
        self.pub_entry = ctk.CTkEntry(self.container_frame)
        self.pub_entry.pack(fill="x", pady=2)
        
        ctk.CTkLabel(self.container_frame, text="Description:", font=Fonts.body_bold()).pack(anchor="w", pady=(10, 0))
        self.desc_entry = ctk.CTkTextbox(self.container_frame, height=80)
        self.desc_entry.pack(fill="x", pady=2)
        
        # Page statistics
        self.stats_lbl = ctk.CTkLabel(self.container_frame, text="Page dimensions: 0x0 pt", font=Fonts.small(), text_color=Colors.TEXT_MUTED[1])
        self.stats_lbl.pack(anchor="w", pady=(Spacing.M, 0))
        
        # Apply button
        self.apply_btn = ctk.CTkButton(
            self.container_frame, text="Apply Changes", fg_color=Colors.PRIMARY[0], command=self._on_apply_changes
        )
        self.apply_btn.pack(fill="x", pady=Spacing.L)

    def _show_standard_panel(self) -> None:
        if self.plugin_panel:
            self.plugin_panel.pack_forget()
            self.plugin_panel.destroy()
            self.plugin_panel = None
        self.container_frame.pack(fill="both", expand=True)
        self.active_project_type = None

    def _show_plugin_panel(self, p_type: str) -> None:
        if self.active_project_type == p_type:
            return
            
        self.container_frame.pack_forget()
        if self.plugin_panel:
            self.plugin_panel.pack_forget()
            self.plugin_panel.destroy()
            
        from book_builder.studio_registry import StudioRegistry
        self.plugin_panel = StudioRegistry().get_settings_panel(p_type, self, self.controller)
        if self.plugin_panel:
            self.plugin_panel.pack(fill="both", expand=True, padx=Spacing.XS, pady=Spacing.XS)
            self.active_project_type = p_type
        else:
            self._show_standard_panel()

    def refresh(self) -> None:
        """Populates form elements with active metadata or displays dynamic plugin panels."""
        project = self.controller.engine.get_active_project()
        if not project:
            self._show_standard_panel()
            self.title_entry.delete(0, "end")
            self.author_entry.delete(0, "end")
            self.pub_entry.delete(0, "end")
            self.desc_entry.delete("1.0", "end")
            self.stats_lbl.configure(text="Page dimensions: 0x0 pt")
            self.apply_btn.configure(state="disabled")
            return
            
        p_type = project.book_type
        from book_builder.studio_registry import StudioRegistry
        meta = StudioRegistry().get_studio_metadata(p_type)
        
        if meta:
            self._show_plugin_panel(p_type)
        else:
            self._show_standard_panel()
            self.apply_btn.configure(state="normal")
            
            # Populate values
            self.title_entry.delete(0, "end")
            self.title_entry.insert(0, project.metadata.title or project.name)
            
            self.author_entry.delete(0, "end")
            self.author_entry.insert(0, project.metadata.author)
            
            self.pub_entry.delete(0, "end")
            self.pub_entry.insert(0, project.metadata.publisher)
            
            self.desc_entry.delete("1.0", "end")
            self.desc_entry.insert("1.0", project.metadata.description)
            
            # Page dimensions info
            active_page = self.controller.engine.state_manager.get_active_page()
            if active_page:
                self.stats_lbl.configure(
                    text=f"Active Page: {active_page.page_number}\nWidth: {active_page.width_pt} pt\nHeight: {active_page.height_pt} pt\nBleed: {'Yes' if active_page.has_bleed else 'No'}"
                )
            else:
                self.stats_lbl.configure(text="No active page selection")

    def _on_apply_changes(self) -> None:
        self.controller.update_metadata(
            title=self.title_entry.get(),
            subtitle="",
            author=self.author_entry.get(),
            publisher=self.pub_entry.get(),
            description=self.desc_entry.get("1.0", "end-1c")
        )
        messagebox.showinfo("Properties", "Metadata properties updated successfully.")


class AssetPanel(ctk.CTkFrame):
    """Bottom drawer compartment managing imported assets and reusable asset libraries."""
    def __init__(self, master: "BookBuilderView", controller: WorkspaceController, **kwargs) -> None:
        super().__init__(master, height=160, corner_radius=0, **kwargs)
        self.controller = controller
        self.asset_items: List[ctk.CTkFrame] = []
        self.img_cache: Dict[str, Any] = {}
        self.tab_var = ctk.StringVar(value="library")
        self.dragged_asset_path: Optional[str] = None
        
        # Grid layout configure
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Filter panel
        self.grid_rowconfigure(1, weight=1) # Scroll area
        
        # 1. Filter panel
        self.filter_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.filter_panel.grid(row=0, column=0, sticky="ew", padx=Spacing.S, pady=(Spacing.S, 0))
        
        # Tab buttons
        self.tab_btn_lib = ctk.CTkButton(
            self.filter_panel, text="Library Assets", width=100, height=26,
            fg_color=Colors.PRIMARY[0], text_color="white",
            command=lambda: self._set_tab("library")
        )
        self.tab_btn_lib.pack(side="left", padx=5)
        
        self.tab_btn_proj = ctk.CTkButton(
            self.filter_panel, text="Project Assets", width=100, height=26,
            fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0],
            border_width=1, border_color=Colors.BORDER[1],
            command=lambda: self._set_tab("project")
        )
        self.tab_btn_proj.pack(side="left", padx=5)
        
        # Category Dropdown
        self.cat_var = ctk.StringVar(value="All")
        self.cat_menu = ctk.CTkOptionMenu(
            self.filter_panel, variable=self.cat_var, width=120, height=26,
            values=["All", "Characters", "Animals", "Vehicles", "Nature", "Food", "Fantasy", "Borders", "Icons", "Goals", "Decorations"],
            command=lambda v: self.refresh()
        )
        self.cat_menu.pack(side="left", padx=10)
        
        # Search bar
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.filter_panel, placeholder_text="Search assets...", textvariable=self.search_var,
            width=150, height=26
        )
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh())
        
        # 2. Scrollable container
        self.scroll_container = ctk.CTkScrollableFrame(self, orientation="horizontal")
        self.scroll_container.grid(row=1, column=0, sticky="nsew", padx=Spacing.S, pady=Spacing.S)

    def _set_tab(self, tab: str) -> None:
        self.tab_var.set(tab)
        if tab == "library":
            self.tab_btn_lib.configure(fg_color=Colors.PRIMARY[0], text_color="white")
            self.tab_btn_proj.configure(fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0])
        else:
            self.tab_btn_proj.configure(fg_color=Colors.PRIMARY[0], text_color="white")
            self.tab_btn_lib.configure(fg_color=Colors.BG_CARD, text_color=Colors.TEXT_MAIN[0])
        self.refresh()

    def _get_library_assets(self) -> List[Dict[str, str]]:
        library_dir = "assets_library"
        assets_list = []
        if not os.path.exists(library_dir):
            return assets_list
        for cat in os.listdir(library_dir):
            cat_path = os.path.join(library_dir, cat)
            if os.path.isdir(cat_path):
                for f in os.listdir(cat_path):
                    if f.lower().endswith((".png", ".jpg", ".jpeg", ".svg")):
                        assets_list.append({
                            "name": os.path.splitext(f)[0].replace("_", " ").title(),
                            "file_path": os.path.abspath(os.path.join(cat_path, f)),
                            "category": cat
                        })
        return assets_list

    def _get_thumbnail(self, path: str) -> Any:
        if path in self.img_cache:
            return self.img_cache[path]
        try:
            pil_img = Image.open(path).convert("RGBA")
            pil_img.thumbnail((60, 60))
            ctk_img = ctk.CTkImage(light_image=pil_img, size=(60, 60))
            self.img_cache[path] = ctk_img
            return ctk_img
        except Exception as e:
            logger.error(f"AssetPanel: failed to load thumbnail '{path}': {e}")
            return None

    def refresh(self) -> None:
        """Re-renders imported asset items list."""
        for item in self.asset_items:
            item.destroy()
        self.asset_items.clear()
        
        project = self.controller.engine.get_active_project()
        if not project:
            return
            
        current_tab = self.tab_var.get()
        search_term = self.search_var.get().strip().lower()
        selected_cat = self.cat_var.get()
        
        # Add "Import Asset" button card only if on project assets tab
        if current_tab == "project":
            import_card = ctk.CTkFrame(self.scroll_container, width=120, height=80, corner_radius=6, border_width=1, border_color=Colors.BORDER[1])
            import_card.pack(side="left", padx=5)
            self.asset_items.append(import_card)
            
            ctk.CTkButton(
                import_card, text="+ Import Asset", font=Fonts.body_bold(),
                fg_color="transparent", hover_color=Colors.BG_MAIN, text_color=Colors.PRIMARY[0],
                command=self.controller.import_asset
            ).pack(expand=True, fill="both")
            
            # Show project assets
            for asset in project.assets:
                # Apply filter
                if search_term and search_term not in asset.name.lower():
                    continue
                # Note: imported assets don't have categories by default unless matching category filter
                
                card = ctk.CTkFrame(self.scroll_container, width=150, height=100, corner_radius=6, border_width=1, fg_color=Colors.BG_CARD)
                card.pack(side="left", padx=5)
                self.asset_items.append(card)
                
                # Check if asset has a physical file path on disk to load preview
                thumb_img = None
                if asset.file_path and os.path.exists(asset.file_path):
                    thumb_img = self._get_thumbnail(asset.file_path)
                    
                if thumb_img:
                    lbl = ctk.CTkLabel(card, image=thumb_img, text="")
                    lbl.pack(pady=(4, 2))
                else:
                    lbl = ctk.CTkLabel(card, text=asset.name, font=Fonts.small(), wraplength=120)
                    lbl.pack(pady=(10, 2))
                    
                # Drag and drop binds
                card.bind("<ButtonPress-1>", lambda event, path=asset.file_path: self._on_drag_start(event, path))
                card.bind("<B1-Motion>", self._on_drag_motion)
                card.bind("<ButtonRelease-1>", lambda event, path=asset.file_path: self._on_drag_release(event, path))
                lbl.bind("<ButtonPress-1>", lambda event, path=asset.file_path: self._on_drag_start(event, path))
                lbl.bind("<B1-Motion>", self._on_drag_motion)
                lbl.bind("<ButtonRelease-1>", lambda event, path=asset.file_path: self._on_drag_release(event, path))
                
                # Double click to insert center
                card.bind("<Double-1>", lambda event, path=asset.file_path: self.controller.insert_asset_to_active_page(path))
                lbl.bind("<Double-1>", lambda event, path=asset.file_path: self.controller.insert_asset_to_active_page(path))
                
                # Remove button
                remove_btn = ctk.CTkButton(
                    card, text="Remove", width=40, height=20, font=Fonts.small(), fg_color=Colors.ERROR[0],
                    command=lambda a_id=asset.id: self._confirm_remove(a_id, asset.name)
                )
                remove_btn.pack(pady=(2, 4))
        else:
            # Show library assets scanned from disk
            library_assets = self._get_library_assets()
            for asset in library_assets:
                # Apply search filter
                if search_term and search_term not in asset["name"].lower():
                    continue
                # Apply category filter
                if selected_cat != "All" and asset["category"].lower() != selected_cat.lower():
                    continue
                    
                card = ctk.CTkFrame(self.scroll_container, width=120, height=110, corner_radius=6, border_width=1, fg_color=Colors.BG_CARD)
                card.pack(side="left", padx=5)
                self.asset_items.append(card)
                
                thumb_img = self._get_thumbnail(asset["file_path"])
                if thumb_img:
                    lbl = ctk.CTkLabel(card, image=thumb_img, text="")
                    lbl.pack(pady=(6, 2))
                else:
                    lbl = ctk.CTkLabel(card, text=asset["name"], font=Fonts.small(), wraplength=100)
                    lbl.pack(pady=(12, 2))
                    
                name_lbl = ctk.CTkLabel(card, text=asset["name"], font=Fonts.small(), wraplength=100)
                name_lbl.pack(pady=(2, 4))
                
                # Drag and drop binds
                card.bind("<ButtonPress-1>", lambda event, path=asset["file_path"]: self._on_drag_start(event, path))
                card.bind("<B1-Motion>", self._on_drag_motion)
                card.bind("<ButtonRelease-1>", lambda event, path=asset["file_path"]: self._on_drag_release(event, path))
                lbl.bind("<ButtonPress-1>", lambda event, path=asset["file_path"]: self._on_drag_start(event, path))
                lbl.bind("<B1-Motion>", self._on_drag_motion)
                lbl.bind("<ButtonRelease-1>", lambda event, path=asset["file_path"]: self._on_drag_release(event, path))
                name_lbl.bind("<ButtonPress-1>", lambda event, path=asset["file_path"]: self._on_drag_start(event, path))
                name_lbl.bind("<B1-Motion>", self._on_drag_motion)
                name_lbl.bind("<ButtonRelease-1>", lambda event, path=asset["file_path"]: self._on_drag_release(event, path))
                
                # Double click to insert center
                card.bind("<Double-1>", lambda event, path=asset["file_path"]: self.controller.insert_asset_to_active_page(path))
                lbl.bind("<Double-1>", lambda event, path=asset["file_path"]: self.controller.insert_asset_to_active_page(path))
                name_lbl.bind("<Double-1>", lambda event, path=asset["file_path"]: self.controller.insert_asset_to_active_page(path))

    def _on_drag_start(self, event, asset_path: str) -> None:
        self.dragged_asset_path = asset_path
        self.controller.view.status_bar.update_status(f"Dragging asset: {os.path.basename(asset_path)}...")

    def _on_drag_motion(self, event) -> None:
        if not hasattr(self, "dragged_asset_path") or not self.dragged_asset_path:
            return
            
        canvas_panel = self.controller.view.canvas_panel
        canvas_widget = canvas_panel.canvas
        
        # Relative coordinates to canvas widget
        cx = event.x_root - canvas_widget.winfo_rootx()
        cy = event.y_root - canvas_widget.winfo_rooty()
        
        if 0 <= cx <= canvas_widget.winfo_width() and 0 <= cy <= canvas_widget.winfo_height():
            canvas_panel.show_drag_indicator(cx, cy)
        else:
            canvas_panel.clear_drag_indicator()

    def _on_drag_release(self, event, asset_path: str) -> None:
        if not hasattr(self, "dragged_asset_path") or not self.dragged_asset_path:
            return
            
        canvas_panel = self.controller.view.canvas_panel
        canvas_widget = canvas_panel.canvas
        canvas_panel.clear_drag_indicator()
        
        cx = event.x_root - canvas_widget.winfo_rootx()
        cy = event.y_root - canvas_widget.winfo_rooty()
        
        self.dragged_asset_path = None
        self.controller.view.status_bar.update_status()
        
        # If dropped inside canvas boundaries
        if 0 <= cx <= canvas_widget.winfo_width() and 0 <= cy <= canvas_widget.winfo_height():
            project = self.controller.engine.get_active_project()
            if not project or not project.pages:
                return
            active_idx = self.controller.engine.state_manager.project_state.active_page_index if self.controller.engine.state_manager.project_state else 0
            if active_idx < 0 or active_idx >= len(project.pages):
                return
            page = project.pages[active_idx]
            
            canvas_w = canvas_widget.winfo_width()
            canvas_h = canvas_widget.winfo_height()
            
            img_w, img_h = canvas_panel.current_pil_img.size
            ratio = min(canvas_w / img_w, canvas_h / img_h) * 0.95
            fit_w = img_w * ratio
            fit_h = img_h * ratio
            
            page_img_x0 = (canvas_w - fit_w) / 2
            page_img_y0 = (canvas_h - fit_h) / 2
            
            ix = cx - page_img_x0
            iy = cy - page_img_y0
            
            pt_ratio = fit_w / page.width_pt
            px = ix / pt_ratio
            py = page.height_pt - (iy / pt_ratio)
            
            # Clamp inside boundaries
            w_geom = 120.0
            h_geom = 120.0
            px_clamped = max(0.0, min(page.width_pt - w_geom, px - w_geom / 2.0))
            py_clamped = max(0.0, min(page.height_pt - h_geom, py - h_geom / 2.0))
            
            geom = {
                "x": px_clamped,
                "y": py_clamped,
                "width": w_geom,
                "height": h_geom
            }
            self.controller.add_decorative_asset(active_idx, asset_path, geom)

    def _confirm_remove(self, asset_id: UUID, name: str) -> None:
        confirm = messagebox.askyesno("Remove Asset", f"Are you sure you want to remove '{name}'?")
        if confirm:
            self.controller.remove_asset(asset_id)


class BookBuilderView(ctk.CTkFrame):
    """
    Unified central workspace view that brings all the visual sub-panels together
    under the coordination of the WorkspaceController.
    """
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        
        # Grid configure
        self.grid_rowconfigure(0, weight=0) # Toolbar
        self.grid_rowconfigure(1, weight=1) # Main Split Workspace
        self.grid_rowconfigure(2, weight=0) # Bottom drawer (Assets)
        self.grid_rowconfigure(3, weight=0) # Statusbar
        self.grid_columnconfigure(0, weight=1)
        
        self.controller = WorkspaceController(self)
        
        self._build_ui()
        self.reset_to_empty()

    def _build_ui(self) -> None:
        # 1. Toolbar
        self.toolbar = Toolbar(self, self.controller)
        self.toolbar.grid(row=0, column=0, sticky="ew")
        
        # 2. Main Workspace Split Layout
        self.main_split = ctk.CTkFrame(self, fg_color="transparent")
        self.main_split.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        
        self.main_split.grid_columnconfigure(0, weight=0, minsize=200) # Left thumbnails
        self.main_split.grid_columnconfigure(1, weight=1)             # Center Canvas
        self.main_split.grid_columnconfigure(2, weight=0, minsize=250) # Right properties
        self.main_split.grid_rowconfigure(0, weight=1)
        
        # Sub-panels
        self.thumbnail_panel = PageThumbnailPanel(self.main_split, self.controller)
        self.thumbnail_panel.grid(row=0, column=0, sticky="nsew", padx=Spacing.XS, pady=Spacing.XS)
        
        self.canvas_panel = PageCanvas(self.main_split, self.controller)
        self.canvas_panel.grid(row=0, column=1, sticky="nsew", padx=Spacing.XS, pady=Spacing.XS)
        
        self.properties_panel = PropertiesPanel(self.main_split, self.controller)
        self.properties_panel.grid(row=0, column=2, sticky="nsew", padx=Spacing.XS, pady=Spacing.XS)
        
        # 3. Asset bottom drawer
        self.asset_panel = AssetPanel(self, self.controller)
        self.asset_panel.grid(row=2, column=0, sticky="ew", padx=2, pady=2)
        
        # 4. Status Bar
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=3, column=0, sticky="ew")

    def refresh_data(self) -> None:
        """Invoked dynamically when view focus returns to update components."""
        self.controller._refresh_entire_workspace()

    def reset_to_empty(self) -> None:
        """Resets the UI widgets when no book project is loaded."""
        self.toolbar.enable_buttons(False)
        self.thumbnail_panel.refresh()
        self.canvas_panel.clear_canvas()
        self.properties_panel.refresh()
        self.asset_panel.refresh()
        self.status_bar.update_status()

    # --- Router Command Dispatch Handles ---
    def cmd_save(self) -> None:
        self.controller.save_project()
        
    def cmd_undo(self) -> None:
        self.controller.undo()
        
    def cmd_redo(self) -> None:
        self.controller.redo()

    def load_project(self, project_id: Any, project_name: str = "", state: Dict[str, Any] = None) -> None:
        """Loads a project into the workspace via the controller."""
        logger.info(f"BookBuilderView: routing load project call for ID: {project_id}")
        self.controller.load_project(project_id)
