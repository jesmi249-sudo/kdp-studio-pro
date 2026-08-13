from typing import Callable, Any
from book_builder.jobs.base import Task, CancellationToken, ProgressEvent
from book_builder.models.page import Page
from book_builder.interfaces.services import IPreviewService
from book_builder.events.event import Event
from book_builder.events.bus import EventBus
from core.logger import get_logger

logger = get_logger(__name__)

class RenderJob(Task):
    """
    Asynchronous background Task that compiles page previews via PreviewService.
    Integrates with EventBus to publish status updates and manages CancellationToken check points.
    """
    def __init__(self, page: Page, zoom_level: float, preview_service: IPreviewService, priority: int = 10) -> None:
        # A priority value (default 10) - lower values represent higher priority
        super().__init__(priority)
        self.page = page
        self.zoom_level = zoom_level
        self.preview_service = preview_service
        self.event_bus = EventBus()

    def execute(self, progress_callback: Callable[[ProgressEvent], None], token: CancellationToken) -> Any:
        """
        Executes the background page rendering process.
        Publishes start, completion, failure, and cancellation events.
        """
        # Publish start event
        self.event_bus.publish(Event(
            event_type="PAGE_RENDER_STARTED",
            sender_id=self.id,
            payload={
                "page_id": str(self.page.id),
                "page_number": self.page.page_number,
                "zoom_level": self.zoom_level
            }
        ))
        
        try:
            logger.info(f"RenderJob {self.id}: starting background render for page {self.page.id} (zoom {self.zoom_level})")
            progress_callback(ProgressEvent(self.id, 0.1, "Initializing render context..."))

            # Audit cancellation
            if token.is_cancelled():
                self._handle_cancellation(progress_callback)
                return None

            progress_callback(ProgressEvent(self.id, 0.3, "Rendering page elements..."))
            
            # Audit cancellation before generating preview
            if token.is_cancelled():
                self._handle_cancellation(progress_callback)
                return None

            # Render low-resolution image
            preview_img = self.preview_service.generate_preview(self.page, self.zoom_level)

            # Audit cancellation after generating preview
            if token.is_cancelled():
                self._handle_cancellation(progress_callback)
                return None

            progress_callback(ProgressEvent(self.id, 1.0, "Render completed successfully"))
            logger.info(f"RenderJob {self.id}: completed render for page {self.page.id}")
            
            # Publish completion event
            self.event_bus.publish(Event(
                event_type="PAGE_RENDER_COMPLETED",
                sender_id=self.id,
                payload={
                    "page_id": str(self.page.id),
                    "page_number": self.page.page_number,
                    "zoom_level": self.zoom_level,
                    "image": preview_img
                }
            ))
            
            return preview_img

        except Exception as e:
            logger.error(f"RenderJob {self.id}: render failed for page {self.page.id}: {e}")
            progress_callback(ProgressEvent(self.id, 1.0, f"Error: {e}"))
            
            # Publish failure event
            self.event_bus.publish(Event(
                event_type="PAGE_RENDER_FAILED",
                sender_id=self.id,
                payload={
                    "page_id": str(self.page.id),
                    "page_number": self.page.page_number,
                    "zoom_level": self.zoom_level,
                    "error": str(e)
                }
            ))
            raise e

    def _handle_cancellation(self, progress_callback: Callable[[ProgressEvent], None]) -> None:
        """Helper to fire cancellation notifications and update progress."""
        logger.info(f"RenderJob {self.id}: render cancelled for page {self.page.id}")
        progress_callback(ProgressEvent(self.id, 1.0, "Cancelled"))
        self.event_bus.publish(Event(
            event_type="PAGE_RENDER_CANCELLED",
            sender_id=self.id,
            payload={
                "page_id": str(self.page.id),
                "page_number": self.page.page_number,
                "zoom_level": self.zoom_level
            }
        ))
