import os
import shutil
from typing import List, Optional
from database.db import db
from models.template import Template
from core.thumbnail_generator import ThumbnailGenerator
from core.logger import get_logger

logger = get_logger(__name__)

TEMPLATES_DIR = os.path.join("assets_library", "Templates")

class TemplateManager:
    def __init__(self):
        os.makedirs(TEMPLATES_DIR, exist_ok=True)

    def save_template(self, name: str, template_type: str, source_file: str, tags: str = "") -> Optional[Template]:
        if not os.path.exists(source_file):
            return None
            
        file_name = os.path.basename(source_file)
        dest_path = os.path.join(TEMPLATES_DIR, file_name)
        
        base, ext = os.path.splitext(file_name)
        counter = 1
        while os.path.exists(dest_path):
            new_name = f"{base}_{counter}{ext}"
            dest_path = os.path.join(TEMPLATES_DIR, new_name)
            counter += 1

        try:
            shutil.copy2(source_file, dest_path)
        except Exception as e:
            logger.error(f"Template copy failed: {e}")
            return None

        thumb_path = ThumbnailGenerator.generate(dest_path)

        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO templates (name, template_type, tags, file_path, thumbnail_path)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, template_type, tags, dest_path, thumb_path))
            t_id = cursor.lastrowid
            conn.commit()
            return self.get_template(t_id)
        except Exception as e:
            logger.error(f"DB insert failed: {e}")
            return None

    def get_template(self, template_id: int) -> Optional[Template]:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
        row = cursor.fetchone()
        return Template.from_row(row) if row else None

    def get_all_templates(self, template_type: str = "All") -> List[Template]:
        conn = db.get_connection()
        cursor = conn.cursor()
        if template_type == "All":
            cursor.execute("SELECT * FROM templates ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM templates WHERE template_type = ? ORDER BY created_at DESC", (template_type,))
        return [Template.from_row(row) for row in cursor.fetchall()]

    def delete_template(self, template_id: int) -> bool:
        tmpl = self.get_template(template_id)
        if not tmpl: return False
        
        if os.path.exists(tmpl.file_path):
            os.remove(tmpl.file_path)
                
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        conn.commit()
        return True
