from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

@dataclass
class BookMetadata:
    """Value object holding Amazon KDP catalog details."""
    title: str = ""
    subtitle: str = ""
    author: str = ""
    publisher: str = ""
    description: str = ""
    language: str = "en"
    keywords: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    isbn: Optional[str] = None
    imprint: Optional[str] = None
    series_name: Optional[str] = None
    series_number: Optional[int] = None
    age_range_min: Optional[int] = None
    age_range_max: Optional[int] = None


@dataclass
class BookProject:
    """Aggregate Root representing a KDP coloring/low-content book project."""
    id: UUID = field(default_factory=uuid4)
    name: str = "New Project"
    book_type: str = "Coloring Book"
    metadata: BookMetadata = field(default_factory=BookMetadata)
    trim_width_in: float = 8.5
    trim_height_in: float = 11.0
    has_bleed: bool = False
    paper_type: str = "White"
    cover_finish: str = "Matte"
    pages: List[Any] = field(default_factory=list)
    assets: List[Any] = field(default_factory=list)
    templates: List[Any] = field(default_factory=list)
    themes: List[Any] = field(default_factory=list)
    export_profiles: List[Any] = field(default_factory=list)
    compliance_state: Optional[Any] = None
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    schema_version: str = "8.0.0"
