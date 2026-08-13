import json
import sqlite3
from typing import List, Optional, Any
from uuid import UUID, uuid4
from book_builder.models.book import BookProject
from book_builder.serializer import ProjectSerializer
from database.db import db
from core.logger import get_logger

logger = get_logger(__name__)

class ProjectRepository:
    """Repository handling SQLite CRUD queries for BookProject aggregates."""

    @staticmethod
    def save(project: BookProject) -> bool:
        """Persists the project to the database, performing an insert or update."""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Serialize project structure to JSON text
            serialized = ProjectSerializer.serialize_project(project)
            serialized_json = json.dumps(serialized)
            
            is_new = True
            db_id = None
            
            # Determine if project exists by checking if ID is an integer
            if isinstance(project.id, int):
                is_new = False
                db_id = project.id
            elif isinstance(project.id, str) and project.id.isdigit():
                is_new = False
                db_id = int(project.id)
            else:
                # Check if this UUID/String exists in data or if there's a record with this name/type
                # We default to treating it as new unless a primary database index was assigned.
                pass

            if not is_new:
                cursor.execute("""
                    UPDATE projects 
                    SET name = ?, last_modified = CURRENT_TIMESTAMP, data = ?
                    WHERE id = ?
                """, (project.name, serialized_json, db_id))
            else:
                cursor.execute("""
                    INSERT INTO projects (name, project_type, data)
                    VALUES (?, ?, ?)
                """, (project.name, project.book_type, serialized_json))
                # Map the autoincremented key back to the model ID
                project.id = cursor.lastrowid
                
            conn.commit()
            logger.info(f"ProjectRepository: successfully saved '{project.name}' (ID: {project.id})")
            return True
        except Exception as e:
            logger.error(f"ProjectRepository: failed to save project: {e}")
            return False

    @staticmethod
    def get_by_id(project_id: Any) -> Optional[BookProject]:
        """Retrieves and deserializes a BookProject aggregate by primary key ID."""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            if row and row['data']:
                data = json.loads(row['data'])
                # Execute schema migration upgrades if required
                from book_builder.migration import ProjectMigrationManager
                data = ProjectMigrationManager.migrate(data)
                project = ProjectSerializer.deserialize_project(data)
                project.id = row['id'] # Enforce primary key ID consistency
                return project
        except Exception as e:
            logger.error(f"ProjectRepository: failed to fetch project {project_id}: {e}")
        return None

    @staticmethod
    def get_all() -> List[BookProject]:
        """Loads and returns all projects stored in the database."""
        projects = []
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY last_modified DESC")
            rows = cursor.fetchall()
            for row in rows:
                if row['data']:
                    try:
                        data = json.loads(row['data'])
                        project = ProjectSerializer.deserialize_project(data)
                        project.id = row['id']
                        projects.append(project)
                    except Exception as e:
                        # Gracefully skip parsing legacy formats or incompatible mock test rows
                        logger.warning(f"ProjectRepository: skipping invalid project row {row['id']}: {e}")
        except Exception as e:
            logger.error(f"ProjectRepository: failed to fetch all projects: {e}")
        return projects

    @staticmethod
    def delete(project_id: Any) -> bool:
        """Deletes a project row from database by ID."""
        return db.delete_project(project_id)
