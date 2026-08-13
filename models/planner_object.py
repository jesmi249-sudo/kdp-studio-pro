from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import uuid

@dataclass
class PlannerObject:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "text"  # text, image, rect, line, table, calendar_grid
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 50.0
    rotation: float = 0.0
    opacity: float = 1.0
    
    # Styling
    fill_color: str = "#000000"
    stroke_color: str = "#000000"
    stroke_width: float = 1.0
    corner_radius: float = 0.0
    
    # Text properties
    text: str = ""
    font_family: str = "Helvetica"
    font_size: float = 12.0
    alignment: str = "left" # left, center, right
    
    # Image properties
    image_path: Optional[str] = None
    
    # Complex Object properties (Tables/Calendars)
    rows: int = 1
    columns: int = 1
    padding: float = 5.0
    spacing: float = 0.0
    
    # State
    layer: int = 0
    locked: bool = False
    visible: bool = True
    
    # Master Page Association
    master_page_link: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "opacity": self.opacity,
            "fill_color": self.fill_color,
            "stroke_color": self.stroke_color,
            "stroke_width": self.stroke_width,
            "corner_radius": self.corner_radius,
            "text": self.text,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "alignment": self.alignment,
            "image_path": self.image_path,
            "rows": self.rows,
            "columns": self.columns,
            "padding": self.padding,
            "spacing": self.spacing,
            "layer": self.layer,
            "locked": self.locked,
            "visible": self.visible,
            "master_page_link": self.master_page_link
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlannerObject':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
