import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_artwork_production_workflow():
    print("Testing Phase 8F: Lilly 24-Page Artwork Production Workflow...")
    
    from core.book_scene_planner import BookScenePlanner, Scene
    from core.asset_manager import AssetManager
    from core.production_pipeline import ProductionWorkflow
    from PIL import Image
    
    test_dir = os.path.join(os.path.dirname(__file__), "test_artwork_workflow")
    os.makedirs(test_dir, exist_ok=True)
    
    planner = BookScenePlanner()
    asset_manager = AssetManager()
    workflow = ProductionWorkflow(planner, asset_manager)
    
    # 1. Simulate 24 planned pages
    for i in range(1, 25):
        scene = Scene(page_number=i, character_id=999)
        scene.main_prompt = f"Prompt for page {i}"
        scene.status = "Prompt Ready"
        planner.add_scene(scene)
        
    workflow.sync_scenes()
    
    stats = workflow.get_progress_summary()
    assert stats["total_scenes"] == 24
    assert stats["artwork_missing"] == 24
    assert stats["export_ready"] is False
    print("PASS: 1. 24 pages created, all artwork missing, export is blocked.")
    
    # 2. Simulate importing valid artwork for Page 1
    valid_img = os.path.join(test_dir, "valid_art.png")
    Image.new("RGB", (2550, 3300), color="white").save(valid_img)
    
    scene1_id = planner.scenes[0].id
    workflow.import_artwork(scene1_id, valid_img)
    
    page1 = workflow.pages[scene1_id]
    assert page1.artwork_status == "ARTWORK IMPORTED"
    
    stats = workflow.get_progress_summary()
    assert stats["artwork_imported"] == 1
    print("PASS: 2. Valid artwork imported. Status updated to ARTWORK IMPORTED.")
    
    # 3. Simulate processing artwork for Page 1
    workflow.process_artwork(scene1_id)
    assert page1.artwork_status == "PROCESSED"
    
    stats = workflow.get_progress_summary()
    assert stats["artwork_processed"] == 1
    print("PASS: 3. Artwork processed successfully. Status updated to PROCESSED.")
    
    # 4. Simulate importing invalid artwork (wrong extension) for Page 2
    invalid_img = os.path.join(test_dir, "bad_art.txt")
    with open(invalid_img, "w") as f:
        f.write("not an image")
        
    scene2_id = planner.scenes[1].id
    workflow.import_artwork(scene2_id, invalid_img)
    
    page2 = workflow.pages[scene2_id]
    assert page2.artwork_status == "ERROR"
    print("PASS: 4. Invalid artwork file extension gracefully rejected.")
    
    # 5. Simulate validation workflow
    workflow.batch_validate_all()
    
    # Page 1 should be VALIDATED
    assert page1.artwork_status == "VALIDATED"
    
    stats = workflow.get_progress_summary()
    assert stats["artwork_validated"] == 1
    assert stats["artwork_missing"] == 23 # 24 - 1
    assert stats["export_ready"] is False
    
    print("PASS: 5. Batch validation accurately identifies validated, missing, and blocking errors.")
    
    print("\nALL PHASE 8F PRODUCTION WORKFLOW TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_artwork_production_workflow()
