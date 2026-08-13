from typing import Dict, Any, List, Optional
from core.book_scene_planner import BookScenePlanner
from core.asset_manager import AssetManager
from core.image_processing_service import ImageProcessingService

class ProductionPage:
    """Represents the union of a planned scene and its assigned output asset."""
    def __init__(self, scene_id: str):
        self.scene_id = scene_id
        self.asset_id: Optional[int] = None # Legacy support, maps to processed_asset_id if available
        self.original_asset_id: Optional[int] = None
        self.processed_asset_id: Optional[int] = None
        self.validation_errors: List[str] = []
        self.status = "Planned"
        self.artwork_status = "ARTWORK MISSING"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "asset_id": self.asset_id,
            "original_asset_id": self.original_asset_id,
            "processed_asset_id": self.processed_asset_id,
            "validation_errors": self.validation_errors,
            "status": self.status,
            "artwork_status": self.artwork_status
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductionPage":
        p = cls(scene_id=data.get("scene_id", ""))
        p.asset_id = data.get("asset_id")
        p.original_asset_id = data.get("original_asset_id")
        p.processed_asset_id = data.get("processed_asset_id")
        p.validation_errors = data.get("validation_errors", [])
        p.status = data.get("status", "Planned")
        p.artwork_status = data.get("artwork_status", "ARTWORK MISSING")
        return p

class ProductionWorkflow:
    """Orchestrates the KDP Book Production Pipeline."""
    
    def __init__(self, scene_planner: BookScenePlanner, asset_manager: AssetManager):
        self.scene_planner = scene_planner
        self.asset_manager = asset_manager
        self.pages: Dict[str, ProductionPage] = {} # scene_id -> ProductionPage
        self.book_title = "Untitled Production"
        self.author = ""
        self.config = {
            "book_type": "Coloring Book",
            "trim_width_in": 8.5,
            "trim_height_in": 11.0,
            "has_bleed": False,
            "paper_type": "White",
            "cover_finish": "Matte"
        }
        
        # Initialize pages for existing scenes
        self.sync_scenes()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pages": {sid: p.to_dict() for sid, p in self.pages.items()},
            "book_title": self.book_title,
            "author": self.author,
            "config": self.config
        }
        
    def load_from_dict(self, data: Dict[str, Any]):
        self.book_title = data.get("book_title", "Untitled Production")
        self.author = data.get("author", "")
        self.config = data.get("config", self.config)
        self.pages = {}
        for sid, p_data in data.get("pages", {}).items():
            self.pages[sid] = ProductionPage.from_dict(p_data)
        self.sync_scenes()

    def sync_scenes(self):
        """Ensures every planned scene has a corresponding production page."""
        current_scene_ids = {s.id for s in self.scene_planner.scenes}
        # Remove deleted scenes
        for sid in list(self.pages.keys()):
            if sid not in current_scene_ids:
                del self.pages[sid]
                
        # Add new scenes
        for scene in self.scene_planner.scenes:
            if scene.id not in self.pages:
                self.pages[scene.id] = ProductionPage(scene.id)
                if scene.status == "Prompt Ready":
                    self.pages[scene.id].artwork_status = "PROMPT READY"

    def import_artwork(self, scene_id: str, file_path: str):
        """Safely imports an original artwork file for a scene."""
        import os
        if scene_id not in self.pages:
            return
            
        scene = self.scene_planner.get_scene(scene_id)
        page = self.pages[scene_id]
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ['.png', '.jpg', '.jpeg']:
            page.artwork_status = "ERROR"
            page.validation_errors = [f"Unsupported format '{ext}'. Must be PNG or JPG."]
            return
            
        asset = self.asset_manager.import_asset(
            source_path=file_path, 
            category="Coloring Artwork",
            name=f"Artwork - Page {scene.page_number}" if scene else "Artwork"
        )
        
        page.original_asset_id = asset.id
        page.asset_id = asset.id
        page.artwork_status = "ARTWORK IMPORTED"
        page.validation_errors = []

    def process_artwork(self, scene_id: str):
        """Processes the original artwork into a line-art derivative."""
        page = self.pages.get(scene_id)
        if not page or not page.original_asset_id:
            return
            
        original_asset = self.asset_manager.get_asset(page.original_asset_id)
        if not original_asset:
            page.artwork_status = "ERROR"
            page.validation_errors = ["Original asset not found."]
            return
            
        try:
            processed_asset = ImageProcessingService.prepare_line_art(original_asset, self.asset_manager)
            page.processed_asset_id = processed_asset.id
            page.asset_id = processed_asset.id # Update primary asset pointer
            page.artwork_status = "PROCESSED"
            page.validation_errors = []
        except Exception as e:
            page.artwork_status = "ERROR"
            page.validation_errors = [f"Processing failed: {e}"]

    def assign_asset(self, scene_id: str, asset_id: int):
        # Legacy support
        if scene_id in self.pages:
            self.pages[scene_id].asset_id = asset_id
            self.pages[scene_id].processed_asset_id = asset_id
            self.pages[scene_id].artwork_status = "PROCESSED"
            self.validate_page(scene_id)

    def remove_asset(self, scene_id: str):
        if scene_id in self.pages:
            self.pages[scene_id].asset_id = None
            self.pages[scene_id].original_asset_id = None
            self.pages[scene_id].processed_asset_id = None
            self.pages[scene_id].artwork_status = "ARTWORK MISSING"
            self.validate_page(scene_id)

    def validate_page(self, scene_id: str):
        """Performs lightweight pre-export validation for a single page."""
        page = self.pages.get(scene_id)
        scene = self.scene_planner.get_scene(scene_id)
        if not page or not scene:
            return
            
        errors = []
        
        if not scene.character_id and self.config.get("book_type") == "Coloring Book":
            errors.append("Missing Character Selection")
            
        if (not scene.main_prompt or scene.status == "Needs Revision") and self.config.get("book_type") == "Coloring Book":
            errors.append("Incomplete or Missing Prompt")
            
        if not page.asset_id:
            errors.append("Missing Assigned Artwork")
            if page.artwork_status not in ["ARTWORK IMPORTED", "ERROR"]:
                page.artwork_status = "ARTWORK MISSING"
        else:
            # Check if asset exists
            asset = self.asset_manager.get_asset(page.asset_id)
            if not asset:
                errors.append("Assigned Artwork Not Found in Library")
                page.artwork_status = "ERROR"
            else:
                # Perform deep quality check
                quality = ImageProcessingService.check_quality(asset)
                if quality["status"] == "ERROR":
                    for msg in quality["messages"]:
                        errors.append(f"Image Error: {msg}")
                    page.artwork_status = "ERROR"
                elif quality["status"] == "WARNING":
                    for msg in quality["messages"]:
                        errors.append(f"Quality Warning: {msg}")
                    if page.artwork_status != "ERROR":
                        page.artwork_status = "VALIDATED"
                else:
                    if page.artwork_status != "ERROR":
                        page.artwork_status = "VALIDATED"
                        
        page.validation_errors = errors
        
        if not scene.character_id or (not scene.main_prompt and scene.status == "Needs Revision"):
            page.status = "Needs Revision"
        elif not scene.main_prompt:
            page.status = "Planned"
        elif not page.asset_id:
            page.status = "Prompt Ready - Awaiting Artwork"
        elif any(e.startswith("Image Error") or e.startswith("Assigned Artwork") for e in errors):
            page.status = "Needs Revision"
        elif any(e.startswith("Quality Warning") for e in errors):
            page.status = "Validated with Warnings"
        else:
            page.status = "Validated & Ready"

    def validate_all(self):
        self.sync_scenes()
        for sid in self.pages:
            self.validate_page(sid)
            
    def batch_validate_all(self):
        self.validate_all()

    def get_progress_summary(self) -> Dict[str, Any]:
        """Calculates lightweight, deterministic progress stats."""
        self.sync_scenes() # Do not run deep validate_all automatically for UI speed
        
        total_scenes = len(self.scene_planner.scenes)
        prompts_ready = sum(1 for s in self.scene_planner.scenes if s.status == "Prompt Ready")
        
        imported = sum(1 for p in self.pages.values() if p.artwork_status in ["ARTWORK IMPORTED", "PROCESSED", "VALIDATED", "ERROR"] and p.original_asset_id)
        processed = sum(1 for p in self.pages.values() if p.artwork_status in ["PROCESSED", "VALIDATED"] and p.processed_asset_id)
        validated = sum(1 for p in self.pages.values() if p.artwork_status == "VALIDATED" and p.status in ["Validated & Ready", "Validated with Warnings"])
        missing = sum(1 for p in self.pages.values() if not p.asset_id)
        errors = sum(1 for p in self.pages.values() if p.artwork_status == "ERROR" or (p.status == "Needs Revision" and p.asset_id))
        
        pages_validated = sum(1 for p in self.pages.values() if p.status == "Validated & Ready")
        
        return {
            "total_scenes": total_scenes,
            "prompts_ready": prompts_ready,
            "artwork_imported": imported,
            "artwork_processed": processed,
            "artwork_validated": validated,
            "artwork_missing": missing,
            "artwork_errors": errors,
            "pages_validated": pages_validated,
            "export_ready": total_scenes > 0 and validated == total_scenes
        }
