import threading
from typing import Dict, Set, List
from book_builder.events.event import Event, EventHandler
from core.logger import get_logger

logger = get_logger(__name__)

class EventBus:
    """Thread-safe, singleton publish-subscribe Event Bus."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> "EventBus":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventBus, cls).__new__(cls)
                cls._instance._subscribers = {}
                cls._instance._subscribers_lock = threading.Lock()
        return cls._instance

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Registers an event handler callback to listen for specific event types."""
        with self._subscribers_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = set()
            self._subscribers[event_type].add(handler)
            logger.debug(f"Subscribed handler {handler.__name__ if hasattr(handler, '__name__') else str(handler)} to '{event_type}'")

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Removes a registered callback handler from an event type list."""
        with self._subscribers_lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].discard(handler)
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]
                logger.debug(f"Unsubscribed handler from '{event_type}'")

    def publish(self, event: Event) -> None:
        """Publishes an event to all registered listener callbacks."""
        handlers_to_notify: List[EventHandler] = []
        with self._subscribers_lock:
            if event.event_type in self._subscribers:
                handlers_to_notify.extend(list(self._subscribers[event.event_type]))
            if "*" in self._subscribers:
                handlers_to_notify.extend(list(self._subscribers["*"]))

        for handler in handlers_to_notify:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error executing handler for event '{event.event_type}': {e}")
