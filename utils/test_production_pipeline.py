import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_phase_7f_production_pipeline():
    print("Testing Phase 7F Production Pipeline Workflow...")
    
    from database.db import db
    db.initialize_db()

    from core.asset_manager import AssetManager
    from core.book_scene_planner import BookScenePlanner, Scene
    from core.prompt_batch_service import PromptBatchService
    from core.production_pipeline import ProductionWorkflow
    
    asset_manager = AssetManager()
    planner = BookScenePlanner()
    batch_service = PromptBatchService(planner)
    pipeline = ProductionWorkflow(planner, asset_manager)

    # Create dummy images
    dummy_char_img = "test_lilly.png"
    dummy_artwork = "test_artwork.png"
    
    from PIL import Image
    Image.new("RGB", (100, 100), "pink").save(dummy_char_img)
    Image.new("RGB", (800, 1000), "white").save(dummy_artwork)

    try:
        # Import Character Asset
        char_asset = asset_manager.import_asset(
            dummy_char_img, 
            category="Characters", 
            character="Lilly"
        )
        
        # Import Generated Artwork Asset
        art_asset = asset_manager.import_asset(
            dummy_artwork, 
            category="Scenes",
            name="Lilly Garden Scene"
        )

        if not char_asset or not art_asset:
            print("FAILED: Asset imports failed.")
            sys.exit(1)

        # 1. Create a planned scene
        scene = Scene(page_number=1, character_id=char_asset.id)
        scene.config["location"] = "Garden"
        planner.add_scene(scene)

        # Test initial pipeline sync and missing prompt/artwork
        pipeline.validate_all()
        stats = pipeline.get_progress_summary()
        
        if stats["total_scenes"] != 1 or stats["prompts_ready"] != 0 or stats["pages_validated"] != 0:
            print("FAILED: Initial pipeline stats are incorrect.")
            sys.exit(1)
            
        page = pipeline.pages[scene.id]
        if "Incomplete or Missing Prompt" not in page.validation_errors:
            print("FAILED: Missing prompt validation not triggered.")
            sys.exit(1)
            
        if "Missing Assigned Artwork" not in page.validation_errors:
            print("FAILED: Missing artwork validation not triggered.")
            sys.exit(1)
            
        print("PASS: Missing prompt & artwork detection successful.")

        # 2. Generate Prompt
        batch_service.generate_all_prompts()
        pipeline.validate_all()
        
        if pipeline.pages[scene.id].status != "Prompt Ready - Awaiting Artwork":
            print(f"FAILED: Status didn't update to Prompt Ready. It is: {pipeline.pages[scene.id].status}")
            sys.exit(1)
            
        print("PASS: Prompt generation correctly tracked by pipeline.")

        # 3. Assign Artwork
        pipeline.assign_asset(scene.id, art_asset.id)
        
        stats = pipeline.get_progress_summary()
        if stats["artwork_assigned"] != 1 or stats["pages_validated"] != 1:
            print("FAILED: Artwork assignment did not validate the page.")
            sys.exit(1)
            
        if pipeline.pages[scene.id].status != "Validated & Ready":
            print("FAILED: Page status did not transition to 'Validated & Ready'.")
            sys.exit(1)
            
        print("PASS: Artwork assignment and full page validation successful.")

        # 4. Remove Artwork
        pipeline.remove_asset(scene.id)
        stats = pipeline.get_progress_summary()
        if stats["pages_validated"] != 0:
            print("FAILED: Artwork removal did not invalidate the page.")
            sys.exit(1)
            
        print("PASS: Artwork removal correctly tracked by pipeline.")

        # Cleanup
        asset_manager.delete_asset(char_asset.id)
        asset_manager.delete_asset(art_asset.id)

    finally:
        for f in [dummy_char_img, dummy_artwork]:
            if os.path.exists(f):
                os.remove(f)

    print("\nALL PHASE 7F TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_phase_7f_production_pipeline()
