from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from models.planner_object import PlannerObject
import uuid

@dataclass
class MasterPage:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Master"
    type: str = "cover" # cover, left, right, chapter, notes
    objects: List[PlannerObject] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "objects": [obj.to_dict() for obj in self.objects]
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MasterPage':
        objs = [PlannerObject.from_dict(obj_data) for obj_data in data.get("objects", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Master"),
            type=data.get("type", "cover"),
            objects=objs
        )

@dataclass
class PlannerPage:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    page_number: int = 1
    master_page_id: Optional[str] = None
    objects: List[PlannerObject] = field(default_factory=list)
    date_context: Optional[str] = None # ISO format date string for variable resolution
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "page_number": self.page_number,
            "master_page_id": self.master_page_id,
            "objects": [obj.to_dict() for obj in self.objects],
            "date_context": self.date_context
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlannerPage':
        objs = [PlannerObject.from_dict(obj_data) for obj_data in data.get("objects", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            page_number=data.get("page_number", 1),
            master_page_id=data.get("master_page_id"),
            objects=objs,
            date_context=data.get("date_context")
        )

@dataclass
class PlannerProject:
    id: Optional[int] = None
    name: str = "Untitled Planner"
    trim_width: float = 8.5
    trim_height: float = 11.0
    pages: List[PlannerPage] = field(default_factory=list)
    master_pages: List[MasterPage] = field(default_factory=list)
    
    # Calendar properties
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "trim_width": self.trim_width,
            "trim_height": self.trim_height,
            "pages": [p.to_dict() for p in self.pages],
            "master_pages": [mp.to_dict() for mp in self.master_pages],
            "start_date": self.start_date,
            "end_date": self.end_date
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any], project_id: int = None) -> 'PlannerProject':
        pages = [PlannerPage.from_dict(p) for p in data.get("pages", [])]
        masters = [MasterPage.from_dict(mp) for mp in data.get("master_pages", [])]
        return cls(
            id=project_id,
            name=data.get("name", "Untitled Planner"),
            trim_width=data.get("trim_width", 8.5),
            trim_height=data.get("trim_height", 11.0),
            pages=pages,
            master_pages=masters,
            start_date=data.get("start_date"),
            end_date=data.get("end_date")
        )
