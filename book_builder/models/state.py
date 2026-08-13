from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

@dataclass
class ValidationError:
    """Value object holding model-level parsing or schema mismatch error details."""
    field_name: str
    message: str


@dataclass
class ValidationResult:
    """Value object compiling schema validation checks on project state JSON models."""
    is_valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ProjectState:
    """Represents the transient, in-memory state of an active project session."""
    project_id: UUID
    is_dirty: bool = False
    active_page_index: int = 0
    selected_element_uuids: List[UUID] = field(default_factory=list)
    clipboard_content: Optional[Dict[str, Any]] = None
    last_saved_at: datetime = field(default_factory=datetime.utcnow)
    active_jobs_count: int = 0
    undo_count: int = 0
    redo_count: int = 0
