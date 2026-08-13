from typing import Dict, Any
from core.logger import get_logger

logger = get_logger(__name__)

class ProjectMigrationManager:
    """Manages project data schema translations for legacy project structures."""

    @staticmethod
    def migrate(data: Dict[str, Any]) -> Dict[str, Any]:
        """Maps and translates older project structures to the v8.0.0 schema."""
        schema_version = data.get("schema_version", "1.0.0")
        logger.info(f"ProjectMigrationManager: checking schema version '{schema_version}'")
        
        # Simple migration chain rules
        if schema_version < "8.0.0":
            logger.info("ProjectMigrationManager: upgrading legacy project structure to v8.0.0")
            
            # Map legacy planner fields or fill empty defaults
            if "pages" not in data:
                data["pages"] = []
            if "assets" not in data:
                data["assets"] = []
            if "metadata" not in data:
                data["metadata"] = {}
                
            # Set target schema version token
            data["schema_version"] = "8.0.0"
            logger.info("ProjectMigrationManager: upgrade completed successfully.")
            
        return data
