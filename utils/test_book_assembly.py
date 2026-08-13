import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_phase_7g_book_assembly():
    print("Testing Phase 7G Book Assembly Workflow...")
    
    from database.db import db
    db.initialize_db()

    from core.asset_manager import AssetManager
    from core.book_scene_planner import BookScenePlanner, Scene
    from core.prompt_batch_service import PromptBatchService
    from core.production_pipeline import ProductionWorkflow
    from book_builder.engine import BookBuilderEngine
    from core.book_assembly_service import BookAssemblyService
    
    asset_manager = AssetManager()
    planner = BookScenePlanner()
    batch_service = PromptBatchService(planner)
    pipeline = ProductionWorkflow(planner, asset_manager)
    engine = BookBuilderEngine()
    assembly_service = BookAssemblyService(engine)

    # Create dummy images
    dummy_char_img = "test_lilly.png"
    dummy_artwork = "test_artwork.png"
    
    from PIL import Image
    Image.new("RGB", (100, 100), "pink").save(dummy_char_img)
    # Simulate an 8.5x11 300DPI image
    Image.new("RGB", (2550, 3300), "white").save(dummy_artwork)

    try:
        # Import Assets
        char_asset = asset_manager.import_asset(dummy_char_img, category="Characters", character="Lilly")
        art_asset = asset_manager.import_asset(dummy_artwork, category="Scenes", name="Lilly Garden Scene")

        if not char_asset or not art_asset:
            print("FAILED: Asset imports failed.")
            sys.exit(1)

        # 1. Setup two scenes
        scene1 = Scene(page_number=1, character_id=char_asset.id)
        scene1.config["location"] = "Garden"
        planner.add_scene(scene1)
        
        scene2 = Scene(page_number=2, character_id=char_asset.id)
        scene2.config["location"] = "Classroom"
        planner.add_scene(scene2)

        batch_service.generate_all_prompts()
        pipeline.validate_all() # Sync the newly added scenes to pipeline pages
        
        # 2. Assign artwork to Scene 1 only
        pipeline.assign_asset(scene1.id, art_asset.id)
        pipeline.validate_all()
        
        stats = pipeline.get_progress_summary()
        if stats["pages_validated"] != 1:
            print(f"FAILED: Validated page count incorrect. Status: {pipeline.pages[scene1.id].status}. Errors: {pipeline.pages[scene1.id].validation_errors}")
            sys.exit(1)
            
        print("PASS: Scene and Production Pipeline prepared.")

        # 3. Build KDP Book
        project = assembly_service.build_project(pipeline)
        
        if not project:
            print("FAILED: BookAssemblyService returned None.")
            sys.exit(1)
            
        # 4. Verify Engine & Page Properties
        if len(project.pages) != 1:
            print(f"FAILED: Expected 1 validated page to be assembled, got {len(project.pages)}")
            sys.exit(1)
            
        page = project.pages[0]
        if page.page_number != 1:
            print("FAILED: Page number mapping incorrect.")
            sys.exit(1)
            
        if len(page.images) != 1:
            print("FAILED: Image object not appended to Page.")
            sys.exit(1)
            
        img_obj = page.images[0]
        if img_obj["file_path"] != art_asset.file_path:
            print("FAILED: Image file path mapping incorrect.")
            sys.exit(1)
            
        geom = img_obj["geometry"]
        # Safe zone check:
        # Image is 2550x3300 (aspect ratio 8.5/11 = 0.7727)
        # Safe zone is 7.5x10 (aspect ratio 7.5/10 = 0.75)
        # Scale is constrained by width: final_w = 540.0, final_h = 3300 * (540/2550) = 698.82
        expected_w = 540.0
        expected_h = 698.8235
        expected_x = 36.0
        expected_y = 36.0 + (720.0 - expected_h) / 2
        
        if abs(geom["width"] - expected_w) > 0.1 or abs(geom["height"] - expected_h) > 0.1:
            print(f"FAILED: Image geometry mapping incorrect. Got width {geom['width']}, height {geom['height']}")
            sys.exit(1)
            
        if abs(geom["x"] - expected_x) > 0.1 or abs(geom["y"] - expected_y) > 0.1:
            print(f"FAILED: Image positioning incorrect. Got x {geom['x']}, y {geom['y']}")
            sys.exit(1)

        print("PASS: Book Assembly Engine built project successfully with proper geometry scaling.")

        # Cleanup
        asset_manager.delete_asset(char_asset.id)
        asset_manager.delete_asset(art_asset.id)

    finally:
        for f in [dummy_char_img, dummy_artwork]:
            if os.path.exists(f):
                os.remove(f)

    print("\nALL PHASE 7G TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_phase_7g_book_assembly()
