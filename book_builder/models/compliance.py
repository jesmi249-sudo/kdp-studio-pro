from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID

@dataclass
class ComplianceIssue:
    """Value object representing a single KDP layout warning or validation failure."""
    rule_name: str
    severity: str # CRITICAL, ERROR, WARNING, INFO
    message: str
    page_number: Optional[int] = None
    element_id: Optional[UUID] = None


@dataclass
class ComplianceResult:
    """Value object compiling the compliance audit status for a book project."""
    is_compliant: bool = True
    health_score: int = 100
    issues: List[ComplianceIssue] = field(default_factory=list)
    audited_at: datetime = field(default_factory=datetime.utcnow)
