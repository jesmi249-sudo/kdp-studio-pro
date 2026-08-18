import sqlite3
import os
from core.logger import get_logger

logger = get_logger(__name__)

DB_DIR = "database"
import sys
is_test = os.environ.get("KDP_TEST_MODE") == "1"
if not is_test and any('pytest' in arg or 'unittest' in arg or arg.endswith('test.py') or 'test_' in arg for arg in sys.argv):
    is_test = True

if is_test:
    DB_FILE = ":memory:"
else:
    DB_FILE = os.path.join(DB_DIR, "kdp_studio.db")

class Database:
    def __init__(self):
        self.conn = None
        self.initialize_db()

    def get_connection(self):
        if not self.conn:
            if not os.path.exists(DB_DIR):
                os.makedirs(DB_DIR)
            self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def initialize_db(self):
        logger.info("Initializing SQLite database")
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create Projects table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    project_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data TEXT
                )
            ''')
            
            # Create Assets table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    dimensions TEXT,
                    dpi INTEGER,
                    file_path TEXT NOT NULL,
                    thumbnail_path TEXT,
                    is_favorite BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                )
            ''')

            # Phase 7A Schema Migrations
            new_columns = [
                ("project_id", "INTEGER"),
                ("character", "TEXT"),
                ("pose", "TEXT"),
                ("expression", "TEXT"),
                ("outfit", "TEXT"),
                ("scene", "TEXT"),
                ("status", "TEXT")
            ]
            
            # Check existing columns to avoid duplicate column errors on multiple runs
            cursor.execute("PRAGMA table_info(assets)")
            existing_columns = [row['name'] for row in cursor.fetchall()]
            
            for col_name, col_type in new_columns:
                if col_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE assets ADD COLUMN {col_name} {col_type}")
                        logger.info(f"Added column {col_name} to assets table")
                    except Exception as e:
                        logger.error(f"Failed to add column {col_name}: {e}")

            # Create Templates table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    template_type TEXT NOT NULL,
                    tags TEXT,
                    file_path TEXT NOT NULL,
                    thumbnail_path TEXT,
                    is_favorite BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

    def get_all_projects(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY last_modified DESC")
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to fetch projects: {e}")
            return []
            
    def delete_project(self, project_id):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}")
            return False
            
    def rename_project(self, project_id, new_name):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE projects SET name = ?, last_modified = CURRENT_TIMESTAMP WHERE id = ?", (new_name, project_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to rename project {project_id}: {e}")
            return False

    # --- Planner Studio Integration ---
    def save_planner_project(self, project):
        import json
        state = project.to_dict()
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if project.id is None:
                cursor.execute("""
                    INSERT INTO projects (name, project_type, data) 
                    VALUES (?, ?, ?)
                """, (project.name, "planner", json.dumps(state)))
                project.id = cursor.lastrowid
            else:
                cursor.execute("""
                    UPDATE projects SET data = ?, last_modified = CURRENT_TIMESTAMP WHERE id = ?
                """, (json.dumps(state), project.id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving planner project: {e}")
            return False

    def load_planner_project(self, project_id):
        import json
        from models.planner import PlannerProject
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ? AND project_type = 'planner'", (project_id,))
            row = cursor.fetchone()
            if row and row['data']:
                data = json.loads(row['data'])
                return PlannerProject.from_dict(data, project_id=row['id'])
            return None
        except Exception as e:
            logger.error(f"Error loading planner project {project_id}: {e}")
            return None

db = Database()
