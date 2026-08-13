from typing import Optional
import os
from core.production_pipeline import ProductionWorkflow
from book_builder.engine import BookBuilderEngine
from book_builder.models.page import Page
from book_builder.models.book import BookProject
from core.logger import get_logger

logger = get_logger(__name__)

class BookAssemblyService:
    """
    Safely connects the lightweight Production Pipeline into the BookBuilderEngine.
    Mathematical page generation occurs here to map Phase 7 assets to Page images.
    """
    
    def __init__(self, engine: BookBuilderEngine):
        self.engine = engine

    def build_project(self, workflow: ProductionWorkflow) -> Optional[BookProject]:
        """
        Takes a validated ProductionWorkflow and maps it into a BookProject.
        Does not perform image resampling. Only calculates layout coordinates.
        """
        # Ensure validation is up-to-date
        workflow.validate_all()
        
        # Create a new project
        title = workflow.book_title or "KDP Production Build"
        
        config = getattr(workflow, "config", {})
        book_type = config.get("book_type", "Coloring Book")
        trim_width_in = config.get("trim_width_in", 8.5)
        trim_height_in = config.get("trim_height_in", 11.0)
        has_bleed = config.get("has_bleed", False)
        paper_type = config.get("paper_type", "White")
        cover_finish = config.get("cover_finish", "Matte")
        
        project = self.engine.create_project(
            name=title,
            book_type=book_type,
            settings={
                "trim_width_in": trim_width_in,
                "trim_height_in": trim_height_in,
                "has_bleed": has_bleed,
                "paper_type": paper_type,
                "cover_finish": cover_finish
            }
        )
        
        # Prepare layout dimensions
        dpi = 300
        w_pt = project.trim_width_in * 72.0
        h_pt = project.trim_height_in * 72.0
        
        # Standard KDP Safe Zone for 8.5x11 (0.5 inch margins)
        margin_pt = 36.0 
        safe_x = margin_pt
        safe_y = margin_pt
        safe_w = w_pt - (margin_pt * 2)
        safe_h = h_pt - (margin_pt * 2)
        
        # Iterate over scenes in sequence, respecting the order planner dictates
        for scene in workflow.scene_planner.scenes:
            page_info = workflow.pages.get(scene.id)
            
            # Missing scene/page mapping gracefully skipped
            if not page_info:
                logger.warning(f"Skipping Scene {scene.id}: No mapping found in production pipeline.")
                continue
                
            # We assemble all planned scenes into pages so that the KDP Validator can correctly audit them.
            asset = workflow.asset_manager.get_asset(page_info.asset_id) if page_info.asset_id else None
            
            # Missing artwork detection
            if not asset or not os.path.exists(asset.file_path):
                logger.warning(f"Page {scene.page_number} is missing artwork. Assembling as blank page.")
                # We will just append the blank page below without images
            else:
                pass # Proceed normally with the asset
                
            # Create Page Model
            new_page = Page(
                page_number=scene.page_number,
                width_pt=w_pt,
                height_pt=h_pt,
                margin_top_pt=margin_pt,
                margin_bottom_pt=margin_pt,
                margin_inside_pt=margin_pt,
                margin_outside_pt=margin_pt,
                has_bleed=project.has_bleed
            )
            
            # Map imported image into BookBuilder rendering format
            if asset and os.path.exists(asset.file_path):
                img_w_px, img_h_px = 2550, 3300 # fallback 8.5x300
                if asset.dimensions and 'x' in asset.dimensions:
                    try:
                        parts = asset.dimensions.split('x')
                        img_w_px = int(parts[0])
                        img_h_px = int(parts[1])
                    except ValueError:
                        pass
                
                img_w_pt = (img_w_px / asset.dpi) * 72.0 if asset.dpi > 0 else (img_w_px / 300.0) * 72.0
                img_h_pt = (img_h_px / asset.dpi) * 72.0 if asset.dpi > 0 else (img_h_px / 300.0) * 72.0
                
                scale = min(safe_w / img_w_pt, safe_h / img_h_pt)
                final_w = img_w_pt * scale
                final_h = img_h_pt * scale
                
                final_x = safe_x + (safe_w - final_w) / 2
                final_y = safe_y + (safe_h - final_h) / 2

                new_page.images.append({
                    "type": "image",
                    "file_path": asset.file_path,
                    "geometry": {
                        "x": final_x,
                        "y": final_y,
                        "width": final_w,
                        "height": final_h
                    },
                    "asset_id": str(asset.id)
                })
            
            self.engine.add_page(new_page)
            
        # Commit the transaction safely via BookBuilder engine
        self.engine.save_project()
        
        return self.engine.active_project
