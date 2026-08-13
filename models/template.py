from dataclasses import dataclass
from typing import Optional

@dataclass
class Template:
    id: Optional[int]
    name: str
    template_type: str
    tags: str
    file_path: str
    thumbnail_path: str
    is_favorite: bool
    created_at: str
    last_used: str

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row['id'],
            name=row['name'],
            template_type=row['template_type'],
            tags=row['tags'] or "",
            file_path=row['file_path'],
            thumbnail_path=row['thumbnail_path'] or "",
            is_favorite=bool(row['is_favorite']),
            created_at=row['created_at'],
            last_used=row['last_used'] or ""
        )
