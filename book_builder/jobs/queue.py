import queue
import threading
from typing import Dict, Callable, Any, List, Optional
from book_builder.jobs.base import Task, CancellationToken, ProgressEvent
from core.logger import get_logger

logger = get_logger(__name__)

class TaskQueue:
    """Thread-safe background task priority queue and worker thread pool."""
    def __init__(self, num_workers: int = 2) -> None:
        self._queue = queue.PriorityQueue()
        self._tokens: Dict[str, CancellationToken] = {}
        self._tokens_lock = threading.Lock()
        self._workers: List[threading.Thread] = []
        self._shutdown = threading.Event()
        self._num_workers = num_workers
        self._start_workers()

    def _start_workers(self) -> None:
        for i in range(self._num_workers):
            t = threading.Thread(target=self._worker_loop, name=f"BB_Worker_{i}", daemon=True)
            t.start()
            self._workers.append(t)
            logger.debug(f"Started background worker thread: {t.name}")

    def enqueue(self, task: Task, progress_callback: Callable[[ProgressEvent], None]) -> CancellationToken:
        """Enqueues a task and returns its cancellation token."""
        token = CancellationToken()
        with self._tokens_lock:
            self._tokens[task.id] = token
        
        # PriorityQueue sorts by priority, task_id tie-breaker prevents task object comparison errors
        self._queue.put((task.priority, task.id, task, progress_callback))
        logger.info(f"Enqueued background task '{task.id}' (Priority: {task.priority})")
        return token

    def cancel(self, task_id: str) -> bool:
        """Requests cancellation for an active or queued task by ID."""
        with self._tokens_lock:
            if task_id in self._tokens:
                self._tokens[task_id].cancel()
                logger.info(f"Requested cancellation for task '{task_id}'")
                return True
        return False

    def _worker_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                # Wait for task with timeout to check for shutdown periodically
                item = self._queue.get(timeout=1.0)
                _, task_id, task, progress_callback = item
                
                # Fetch token safely
                token: Optional[CancellationToken] = None
                with self._tokens_lock:
                    token = self._tokens.get(task_id)

                if token and token.is_cancelled():
                    logger.info(f"Task '{task_id}' was cancelled before starting execution.")
                    self._queue.task_done()
                    self._cleanup_token(task_id)
                    continue

                logger.info(f"Worker starting execution of task '{task_id}'")
                try:
                    task.execute(progress_callback, token)
                    logger.info(f"Completed task '{task_id}' successfully")
                except Exception as e:
                    logger.error(f"Error executing background task '{task_id}': {e}")
                    # Notify UI of failure
                    try:
                        progress_callback(ProgressEvent(task_id, 1.0, f"Error: {str(e)}"))
                    except Exception:
                        pass
                finally:
                    self._queue.task_done()
                    self._cleanup_token(task_id)

            except queue.Empty:
                continue

    def _cleanup_token(self, task_id: str) -> None:
        with self._tokens_lock:
            if task_id in self._tokens:
                del self._tokens[task_id]

    def shutdown(self) -> None:
        """Terminates worker threads and cancels active tasks."""
        logger.info("Shutting down background task queue...")
        self._shutdown.set()
        
        with self._tokens_lock:
            for t_id, token in self._tokens.items():
                token.cancel()
        
        for worker in self._workers:
            worker.join(timeout=2.0)
        self._workers.clear()
        logger.info("Background task queue shut down complete")
