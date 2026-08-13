import os
import json
from typing import List, Dict, Any, Tuple
from database.db import db
from core.config import config
from core.logger import get_logger

logger = get_logger(__name__)

class DashboardService:
    """Stateless business service for the Dashboard, separating UI from databases and diagnostic checks."""
    
    @staticmethod
    def get_statistics() -> Tuple[int, int, int]:
        """
        Retrieves project, book, and export counts from the database and configuration.
        
        Returns:
            Tuple[int, int, int]: (project_count, book_count, export_count)
        """
        try:
            projects = db.get_all_projects()
            proj_count: int = len(projects)
            
            # Count projects created by Book Wizard or Planner Studio
            book_count: int = sum(
                1 for p in projects 
                if p['project_type'] in ['wizard', 'planner']
            )
            
            export_count: int = config.get("export_count", 0)
            return proj_count, book_count, export_count
        except Exception as e:
            logger.error(f"Failed to fetch statistics in DashboardService: {e}")
            return 0, 0, 0

    @staticmethod
    def get_recent_projects(limit: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves and formats a list of recently modified projects.
        
        Args:
            limit: Maximum number of projects to return.
            
        Returns:
            List[Dict[str, Any]]: List of project data dictionaries formatted for UI presentation.
        """
        formatted_projects: List[Dict[str, Any]] = []
        try:
            projects = db.get_all_projects()
            for p in projects[:limit]:
                p_id: int = p['id']
                p_name: str = p['name']
                p_type: str = p['project_type']
                p_date: str = p['last_modified']
                
                # Derive display book type and status
                book_type: str = p_type.capitalize()
                status: str = "Active"
                
                p_data = p['data']
                if p_data:
                    try:
                        state: Dict[str, Any] = json.loads(p_data)
                        if p_type == 'wizard':
                            book_type = state.get('type', 'Coloring Book')
                        status = state.get('status', 'Active')
                    except Exception as parse_err:
                        logger.warning(f"Failed to parse project data for id {p_id}: {parse_err}")
                
                formatted_projects.append({
                    "id": p_id,
                    "name": p_name,
                    "project_type": p_type,
                    "book_type": book_type,
                    "last_modified": p_date,
                    "status": status,
                    "raw_data": p
                })
        except Exception as e:
            logger.error(f"Failed to fetch recent projects in DashboardService: {e}")
        return formatted_projects

    @staticmethod
    def check_system_health() -> List[Tuple[str, str, str]]:
        """
        Runs real-time diagnostic checks on crucial application systems.
        
        Returns:
            List[Tuple[str, str, str]]: A list of (system_name, status_text, status_color) tuples.
        """
        health: List[Tuple[str, str, str]] = []
        
        # 1. Database Connection Check
        db_ok: bool = False
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            db_ok = True
        except Exception as db_err:
            logger.error(f"Database health check failed: {db_err}")
            
        health.append(("Database", "Connected" if db_ok else "Disconnected", "green" if db_ok else "red"))
        
        # 2. Asset Library Path Check
        assets_ok: bool = os.path.exists("assets_library")
        health.append(("Asset Library", "Loaded" if assets_ok else "Missing", "green" if assets_ok else "red"))
        
        # 3. Templates Path Check
        templates_ok: bool = os.path.exists(os.path.join("assets_library", "Templates"))
        health.append(("Templates", "Loaded" if templates_ok else "Missing", "green" if templates_ok else "red"))
        
        # 4. Export Engine Integrity Check
        export_ok: bool = False
        try:
            from core.export_manager import ExportManager
            export_ok = True
        except Exception as export_err:
            logger.error(f"Export Engine class validation failed: {export_err}")
        health.append(("Export Engine", "Ready" if export_ok else "Failed", "green" if export_ok else "red"))
        
        # 5. Compliance Engine Integrity Check
        compliance_ok: bool = False
        try:
            from core.compliance_checker import ComplianceChecker
            compliance_ok = True
        except Exception as compliance_err:
            logger.error(f"Compliance Engine class validation failed: {compliance_err}")
        health.append(("Compliance Engine", "Ready" if compliance_ok else "Failed", "green" if compliance_ok else "red"))
        
        return health
