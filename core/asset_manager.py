import os
import shutil
from typing import List, Optional
from database.db import db
from models.asset import Asset
from core.thumbnail_generator import ThumbnailGenerator
from core.logger import get_logger

logger = get_logger(__name__)

ASSETS_BASE_DIR = "assets_library"
CATEGORIES = [
    "Characters", "Poses", "Expressions", "Outfits", 
    "Backgrounds", "Decorations", "Scenes", "Coloring Artwork", "Storybook Illustrations"
]

class AssetManager:
    def __init__(self):
        self._initialize_structure()

    def _initialize_structure(self):
        if not os.path.exists(ASSETS_BASE_DIR):
            os.makedirs(ASSETS_BASE_DIR, exist_ok=True)
            
        for category in CATEGORIES:
            path = os.path.join(ASSETS_BASE_DIR, category)
            os.makedirs(path, exist_ok=True)

    def import_asset(self, source_path: str, category: str, tags: str = "", **kwargs) -> Optional[Asset]:
        """Imports an asset into the library and database."""
        if not os.path.exists(source_path):
            logger.error(f"Cannot import, file not found: {source_path}")
            return None
            
        if category not in CATEGORIES:
            logger.error(f"Invalid category: {category}")
            return None

        file_name = os.path.basename(source_path)
        dest_path = os.path.join(ASSETS_BASE_DIR, category, file_name)
        
        # Handle duplicates by appending a number
        base, ext = os.path.splitext(file_name)
        counter = 1
        while os.path.exists(dest_path):
            new_name = f"{base}_{counter}{ext}"
            dest_path = os.path.join(ASSETS_BASE_DIR, category, new_name)
            counter += 1

        try:
            shutil.copy2(source_path, dest_path)
        except Exception as e:
            logger.error(f"File copy failed: {e}")
            return None

        # Extract metadata
        file_size = os.path.getsize(dest_path)
        ext = ext.lower()
        dimensions = ""
        dpi = 0
        
        # Try to get image metadata
        if ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            try:
                from PIL import Image
                with Image.open(dest_path) as img:
                    dimensions = f"{img.width}x{img.height}"
                    dpi_info = img.info.get("dpi", (0, 0))
                    dpi = int(dpi_info[0]) if dpi_info[0] > 0 else 72
            except Exception:
                pass

        # Generate thumbnail
        thumb_path = ThumbnailGenerator.generate(dest_path)

        # Insert DB
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO assets (name, category, tags, file_type, file_size, dimensions, dpi, file_path, thumbnail_path, project_id, character, pose, expression, outfit, scene, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (os.path.basename(dest_path), category, tags, ext, file_size, dimensions, dpi, dest_path, thumb_path,
                  kwargs.get('project_id'), kwargs.get('character'), kwargs.get('pose'), kwargs.get('expression'),
                  kwargs.get('outfit'), kwargs.get('scene'), kwargs.get('status')))
            asset_id = cursor.lastrowid
            conn.commit()
            return self.get_asset(asset_id)
        except Exception as e:
            logger.error(f"DB insert failed: {e}")
            return None

    def get_asset(self, asset_id: int) -> Optional[Asset]:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assets WHERE id = ?", (asset_id,))
        row = cursor.fetchone()
        return Asset.from_row(row) if row else None

    def get_all_assets(self, category: str = "All", search_query: str = "", favorites_only: bool = False, character_filter: str = "", project_id: Optional[int] = None) -> List[Asset]:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM assets WHERE 1=1"
        params = []
        
        if category and category != "All":
            query += " AND category = ?"
            params.append(category)
            
        if search_query:
            query += " AND (name LIKE ? OR tags LIKE ?)"
            params.append(f"%{search_query}%")
            params.append(f"%{search_query}%")
            
        if favorites_only:
            query += " AND is_favorite = 1"
            
        if character_filter:
            query += " AND character = ?"
            params.append(character_filter)
            
        if project_id is not None:
            query += " AND project_id = ?"
            params.append(project_id)
            
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        return [Asset.from_row(row) for row in cursor.fetchall()]

    def delete_asset(self, asset_id: int) -> bool:
        asset = self.get_asset(asset_id)
        if not asset: return False
        
        # Remove file
        if os.path.exists(asset.file_path):
            try:
                os.remove(asset.file_path)
            except OSError as e:
                logger.error(f"Failed to delete file {asset.file_path}: {e}")
                return False
                
        # Remove DB record
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        conn.commit()
        return True

    def toggle_favorite(self, asset_id: int, status: bool) -> bool:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE assets SET is_favorite = ? WHERE id = ?", (1 if status else 0, asset_id))
        conn.commit()
        return True

    def rename_asset(self, asset_id: int, new_name: str) -> bool:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE assets SET name = ? WHERE id = ?", (new_name, asset_id))
        conn.commit()
        return True

    def update_metadata(self, asset_id: int, **kwargs) -> bool:
        allowed_keys = ['name', 'category', 'tags', 'project_id', 'character', 'pose', 'expression', 'outfit', 'scene', 'status']
        updates = []
        params = []
        for k, v in kwargs.items():
            if k in allowed_keys:
                updates.append(f"{k} = ?")
                params.append(v)
        
        if not updates:
            return False
            
        params.append(asset_id)
        query = f"UPDATE assets SET {', '.join(updates)} WHERE id = ?"
        
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            return False

    def duplicate_asset(self, asset_id: int) -> Optional[Asset]:
        asset = self.get_asset(asset_id)
        if not asset: return None
        return self.import_asset(asset.file_path, asset.category, asset.tags,
                                 project_id=asset.project_id, character=asset.character,
                                 pose=asset.pose, expression=asset.expression,
                                 outfit=asset.outfit, scene=asset.scene, status=asset.status)
