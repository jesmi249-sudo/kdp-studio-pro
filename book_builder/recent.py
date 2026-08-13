from datetime import datetime, timezone
from typing import List, Dict, Any
from core.config import config
from core.logger import get_logger

logger = get_logger(__name__)

class RecentProjectsManager:
    """Manages the configuration-backed registry of recently opened projects."""
    
    KEY = "recent_projects"
    MAX_ITEMS = 10

    @classmethod
    def get_recent_projects(cls) -> List[Dict[str, Any]]:
        """Retrieves the list of recent projects from the global config."""
        return config.get(cls.KEY, [])

    @classmethod
    def add_recent_project(cls, project_id: Any, name: str, book_type: str) -> None:
        """Adds or moves a project to the top of the recents registry."""
        recents = cls.get_recent_projects()
        
        # Format the project ID as string for JSON config compatibility
        str_id = str(project_id)
        
        # Remove if already exists to reposition it at the top
        recents = [r for r in recents if r.get("id") != str_id]
        
        new_entry = {
            "id": str_id,
            "name": name,
            "book_type": book_type,
            "last_opened": datetime.now(timezone.utc).isoformat()
        }
        
        recents.insert(0, new_entry)
        
        # Cap the history list
        if len(recents) > cls.MAX_ITEMS:
            recents = recents[:cls.MAX_ITEMS]
            
        config.set(cls.KEY, recents)
        logger.info(f"RecentProjectsManager: registered project '{name}' ({str_id})")

    @classmethod
    def remove_recent_project(cls, project_id: Any) -> None:
        """Removes a project entry from the recents registry (e.g. on deletion)."""
        recents = cls.get_recent_projects()
        str_id = str(project_id)
        
        updated_recents = [r for r in recents if r.get("id") != str_id]
        if len(updated_recents) != len(recents):
            config.set(cls.KEY, updated_recents)
            logger.info(f"RecentProjectsManager: removed project '{str_id}' from recents")
