from dataclasses import dataclass, field
from typing import List

@dataclass
class Issue:
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    category: str  # Project, Metadata, Interior, Cover, Images, Files
    rule_name: str
    explanation: str
    suggested_fix: str

class ComplianceResult:
    def __init__(self):
        self.issues: List[Issue] = []
        self.score_deductions = {
            "INFO": 0,
            "WARNING": 5,
            "ERROR": 15,
            "CRITICAL": 30
        }

    def add_issue(self, issue: Issue):
        self.issues.append(issue)

    @property
    def health_score(self) -> int:
        score = 100
        for issue in self.issues:
            score -= self.score_deductions.get(issue.severity, 0)
        return max(0, score)

    @property
    def status_message(self) -> str:
        score = self.health_score
        if score >= 90:
            return "Ready for Amazon KDP"
        elif score >= 70:
            return "Needs Attention"
        else:
            return "Not Ready (Critical Errors)"
