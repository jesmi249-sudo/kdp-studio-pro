from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID, uuid4

@dataclass
class Asset:
    """Domain model representing a file dependency like an image, pattern, font, or template."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    asset_type: str = "Image" # Image, SVG, PNG, JPG, Font, Pattern, Background, Brush, Icon
    storage_type: str = "Linked" # Linked, Embedded
    file_path: str = ""
    file_size_bytes: int = 0
    dpi: int = 300
    width_px: int = 0
    height_px: int = 0
    is_favorite: bool = False
    tags: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
