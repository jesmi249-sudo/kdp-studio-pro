from datetime import datetime, timezone
from typing import Dict, Any, Callable
from uuid import UUID, uuid4

class Event:
    """Base class for all system events inside KDP Studio Pro."""
    def __init__(self, event_type: str, sender_id: str, payload: Dict[str, Any] = None) -> None:
        self.event_id: UUID = uuid4()
        self.event_type: str = event_type
        self.sender_id: str = sender_id
        self.timestamp: datetime = datetime.now(timezone.utc)
        self.payload: Dict[str, Any] = payload if payload is not None else {}

    def to_dict(self) -> Dict[str, Any]:
        """Serializes event metadata for logging or subprocess channels."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "sender_id": self.sender_id,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload
        }


# Type alias for event callbacks
EventHandler = Callable[[Event], None]
