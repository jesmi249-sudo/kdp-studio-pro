from dataclasses import dataclass
from typing import Optional

@dataclass
class Asset:
    id: Optional[int]
    name: str
    category: str
    tags: str
    file_type: str
    file_size: int
    dimensions: str
    dpi: int
    file_path: str
    thumbnail_path: str
    is_favorite: bool
    created_at: str
    last_used: str
    project_id: Optional[int] = None
    character: Optional[str] = None
    pose: Optional[str] = None
    expression: Optional[str] = None
    outfit: Optional[str] = None
    scene: Optional[str] = None
    status: Optional[str] = None

    @classmethod
    def from_row(cls, row):
        # Gracefully handle missing columns for backward compatibility if migration hasn't run yet
        keys = row.keys()
        return cls(
            id=row['id'],
            name=row['name'],
            category=row['category'],
            tags=row['tags'] or "",
            file_type=row['file_type'] or "",
            file_size=row['file_size'] or 0,
            dimensions=row['dimensions'] or "",
            dpi=row['dpi'] or 0,
            file_path=row['file_path'],
            thumbnail_path=row['thumbnail_path'] or "",
            is_favorite=bool(row['is_favorite']),
            created_at=row['created_at'],
            last_used=row['last_used'] or "",
            project_id=row['project_id'] if 'project_id' in keys else None,
            character=row['character'] if 'character' in keys else None,
            pose=row['pose'] if 'pose' in keys else None,
            expression=row['expression'] if 'expression' in keys else None,
            outfit=row['outfit'] if 'outfit' in keys else None,
            scene=row['scene'] if 'scene' in keys else None,
            status=row['status'] if 'status' in keys else None
        )
