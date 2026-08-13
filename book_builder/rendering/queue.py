import threading
from typing import Callable, Optional, Dict, Tuple
from book_builder.jobs.queue import TaskQueue
from book_builder.jobs.base import CancellationToken, ProgressEvent
from book_builder.models.page import Page
from book_builder.interfaces.services import IPreviewService
from book_builder.rendering.job import RenderJob
from book_builder.rendering.service import PreviewService
from core.logger import get_logger

logger = get_logger(__name__)

class RenderQueue:
    """
    Thread-safe Singleton wrapper that routes background page rendering requests
    through the existing TaskQueue engine.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> "RenderQueue":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RenderQueue, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    @classmethod
    def _reset_singleton(cls) -> None:
        with cls._lock:
            cls._instance = None

    def __init__(self, task_queue: Optional[TaskQueue] = None, preview_service: Optional[IPreviewService] = None) -> None:
        with self._lock:
            if self._initialized:
                return
            self._task_queue = task_queue or TaskQueue(num_workers=2)
            self._preview_service = preview_service or PreviewService()
            self._active_tokens: Dict[str, CancellationToken] = {}
            self._tokens_lock = threading.Lock()
            self._initialized = True
            logger.info("RenderQueue: initialized with TaskQueue and PreviewService")

    def submit(self, page: Page, zoom_level: float, priority: int = 10, progress_callback: Optional[Callable[[ProgressEvent], None]] = None) -> Tuple[str, CancellationToken]:
        """
        Submits a page for background preview rendering.
        Returns a tuple of (task_id, CancellationToken).
        """
        # Create a background rendering task
        job = RenderJob(page, zoom_level, self._preview_service, priority)
        
        # Define a wrapper callback to clean up the token registration upon completion/failure
        def progress_wrapper(event: ProgressEvent) -> None:
            if progress_callback:
                try:
                    progress_callback(event)
                except Exception as cb_err:
                    logger.error(f"RenderQueue: progress callback exception: {cb_err}")
            
            # If task is done (indicated by progress == 1.0 or custom state check)
            if event.progress >= 1.0 or "Error" in event.message or "Cancelled" in event.message:
                self._cleanup_token(event.task_id)

        # Enqueue the job on the task queue
        token = self._task_queue.enqueue(job, progress_wrapper)
        
        with self._tokens_lock:
            self._active_tokens[job.id] = token
            
        logger.debug(f"RenderQueue: submitted page {page.id} (task {job.id})")
        return job.id, token

    def cancel(self, task_id: str) -> bool:
        """
        Cancels a pending or running rendering task.
        """
        # First request cancellation on the token
        cancelled = False
        with self._tokens_lock:
            if task_id in self._active_tokens:
                self._active_tokens[task_id].cancel()
                cancelled = True
                
        # Forward cancellation to underlying TaskQueue
        queue_cancelled = self._task_queue.cancel(task_id)
        
        if cancelled or queue_cancelled:
            logger.info(f"RenderQueue: cancelled task {task_id}")
            self._cleanup_token(task_id)
            return True
            
        return False

    def shutdown(self) -> None:
        """
        Cleans up and shuts down the underlying worker thread pool.
        """
        self._task_queue.shutdown()
        with self._tokens_lock:
            self._active_tokens.clear()
        logger.info("RenderQueue: shut down complete")

    def _cleanup_token(self, task_id: str) -> None:
        with self._tokens_lock:
            if task_id in self._active_tokens:
                del self._active_tokens[task_id]
