import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_phase_7e_book_scene_planner():
    print("Testing Phase 7E Book Scene Planner Workflow...")
    
    # 1. Initialize Database
    from database.db import db
    db.initialize_db()

    from core.asset_manager import AssetManager
    from core.book_scene_planner import BookScenePlanner, Scene
    from core.prompt_batch_service import PromptBatchService
    
    manager = AssetManager()
    planner = BookScenePlanner()
    batch_service = PromptBatchService(planner)

    # Create dummy image
    dummy_img = "test_planner_lilly.png"
    from PIL import Image
    Image.new("RGB", (100, 100), "pink").save(dummy_img)

    try:
        # Create Lilly Character Asset
        asset = manager.import_asset(
            dummy_img, 
            category="Characters", 
            character="Lilly",
            tags="10 year old girl, brown hair",
            outfit="Blue overalls",
            expression="Neutral",
            pose="Neutral",
            status="Must wear yellow boots"
        )
        
        if not asset:
            print("FAILED: Asset import failed.")
            sys.exit(1)

        print("PASS: Lilly character created successfully.")

        # Test 1: Scene Collection CRUD & Reordering
        s1 = Scene(page_number=1, character_id=asset.id)
        s1.config["location"] = "Garden"
        s1.config["action"] = "Holding a flower"
        
        s2 = Scene(page_number=2, character_id=asset.id)
        s2.config["location"] = "Classroom"
        
        planner.add_scene(s1)
        planner.add_scene(s2)
        
        if len(planner.scenes) != 2:
            print("FAILED: Scene addition failed.")
            sys.exit(1)
            
        planner.duplicate_scene(s1.id)
        if len(planner.scenes) != 3 or planner.scenes[1].config["location"] != "Garden":
            print("FAILED: Scene duplication failed or ordering is wrong.")
            sys.exit(1)
            
        # Current: 1: Garden, 2: Garden(copy), 3: Classroom
        # Delete copy
        planner.delete_scene(planner.scenes[1].id)
        
        # Move up Classroom
        planner.move_scene_up(planner.scenes[1].id)
        
        if planner.scenes[0].config["location"] != "Classroom" or planner.scenes[0].page_number != 1:
            print("FAILED: Move up / Reindexing failed.")
            sys.exit(1)
            
        print("PASS: Scene collection CRUD and dynamic reordering successful.")

        # Test 2: Empty Scene Handling
        s_empty = Scene(page_number=3) # No character ID
        planner.add_scene(s_empty)
        
        # Test 3: Batch Generation & Character Consistency
        results = batch_service.generate_all_prompts()
        
        if len(results) != 3:
            print("FAILED: Batch service did not return correct number of results.")
            sys.exit(1)
            
        # Verify empty scene failed gracefully
        if "Failed" not in results[2]["status"] or planner.scenes[2].status != "Needs Revision":
            print("FAILED: Empty scene handling failed.")
            sys.exit(1)
            
        # Verify valid scenes successfully generated and used character metadata
        s_class = planner.scenes[0]
        s_garden = planner.scenes[1]
        
        if s_class.status != "Prompt Ready" or s_garden.status != "Prompt Ready":
            print("FAILED: Valid scenes did not reach Prompt Ready status.")
            sys.exit(1)
            
        if "Lilly" not in s_class.main_prompt or "Lilly" not in s_garden.main_prompt:
            print("FAILED: Character consistency failure. Metadata not applied to both scenes.")
            sys.exit(1)
            
        if "Classroom" not in s_class.main_prompt or "Garden" not in s_garden.main_prompt:
            print("FAILED: Scene-specific overrides not applied.")
            sys.exit(1)

        print("PASS: Batch prompt generation and character consistency verified.")

        # Cleanup
        manager.delete_asset(asset.id)

    finally:
        if os.path.exists(dummy_img):
            os.remove(dummy_img)

    print("\nALL PHASE 7E TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_phase_7e_book_scene_planner()
