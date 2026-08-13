from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

@dataclass
class Page:
    """Domain model representing a single layout page inside a book project."""
    id: UUID = field(default_factory=uuid4)
    page_number: int = 1
    page_type: str = "Body" # Cover, Front Matter, Body, Back Matter
    width_pt: float = 612.0 # Standard 8.5" * 72pt
    height_pt: float = 792.0 # Standard 11" * 72pt
    margin_top_pt: float = 36.0 # 0.5" margin default
    margin_bottom_pt: float = 36.0
    margin_inside_pt: float = 36.0
    margin_outside_pt: float = 36.0
    has_bleed: bool = False
    rotation_deg: float = 0.0
    background_asset_id: Optional[UUID] = None
    layers: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    text_blocks: List[Dict[str, Any]] = field(default_factory=list)
    vector_objects: List[Dict[str, Any]] = field(default_factory=list)
    guides: List[Dict[str, Any]] = field(default_factory=list)
    bookmarks: List[Dict[str, Any]] = field(default_factory=list)
    template_id: Optional[UUID] = None
    rendering_state: Dict[str, Any] = field(default_factory=dict)
    validation_state: Dict[str, Any] = field(default_factory=dict)
