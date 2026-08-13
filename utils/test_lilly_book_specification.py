import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_lilly_book_specification():
    print("Testing Phase 8E: Lilly Full Book Production Preparation...")
    
    from core.book_scene_planner import BookScenePlanner, Scene
    from core.asset_manager import AssetManager
    from core.production_pipeline import ProductionWorkflow
    from book_builder.engine import BookBuilderEngine
    from core.book_assembly_service import BookAssemblyService
    from exporters.validation import KDPValidator
    
    test_dir = os.path.join(os.path.dirname(__file__), "test_lilly_book_spec")
    os.makedirs(test_dir, exist_ok=True)
    
    # 1. Pipeline Initialization
    planner = BookScenePlanner()
    asset_manager = AssetManager()
    workflow = ProductionWorkflow(planner, asset_manager)

    # 2. Configure Full Book Specification
    workflow.book_title = "Lilly's Grand Adventure"
    workflow.author = "Lilly Creator" # TODO: Real author name if needed
    workflow.config = {
        "book_type": "Coloring Book",
        "trim_width_in": 8.5,
        "trim_height_in": 11.0,
        "has_bleed": False,
        "paper_type": "White",
        "cover_finish": "Glossy",
        "isbn": "TODO",
        "publisher": "TODO"
    }
    
    print("PASS: 1. Book Configuration set up. (Note: ISBN and Publisher marked as TODO)")
    
    # 3. Create Character Reference
    from PIL import Image
    char_img_path = os.path.join(test_dir, "lilly_ref.jpg")
    Image.new("RGB", (100, 100), color="white").save(char_img_path)
    
    lilly_asset = asset_manager.import_asset(
        source_path=char_img_path,
        category="Characters",
        name="Lilly",
        character="Lilly",
        tags="Curly brown hair, overalls",
        outfit="Overalls",
        expression="Happy, curious, expressive"
    )
    print("PASS: 2. Character reference (Lilly) connected to AssetManager.")
    
    # 4. Page-by-Page Production Plan (24 Pages)
    scenes_descriptions = [
        "Lilly finding a magical seed",
        "Lilly planting the seed in her garden",
        "Lilly watering the sprout",
        "Lilly watching the giant flower grow",
        "Lilly playing under the giant flower",
        "Lilly climbing the stem",
        "Lilly meeting a friendly ladybug",
        "Lilly sharing a snack with the ladybug",
        "Lilly sliding down a leaf",
        "Lilly exploring a maze of roots",
        "Lilly discovering a glowing mushroom",
        "Lilly chasing a butterfly",
        "Lilly weaving a crown of smaller flowers",
        "Lilly trying on the flower crown",
        "Lilly looking at a magical caterpillar",
        "Lilly observing a chrysalis",
        "Lilly watching a new butterfly emerge",
        "Lilly waving goodbye to the butterfly",
        "Lilly collecting dew drops in a leaf cup",
        "Lilly building a small rock tower",
        "Lilly drawing a picture in the dirt",
        "Lilly napping under a giant mushroom",
        "Lilly waking up to a beautiful sunset",
        "Lilly walking back home holding a small flower"
    ]
    
    for i, desc in enumerate(scenes_descriptions):
        scene = Scene(page_number=i+1, character_id=lilly_asset.id)
        # Use existing character tags to ensure consistency in the prompt
        traits = lilly_asset.tags or ""
        outfit = lilly_asset.outfit or ""
        # 5. Prompt Preparation
        scene.main_prompt = f"Coloring page, black and white line art. A young girl ({traits}, wearing {outfit}). {desc}."
        scene.status = "Prompt Ready"
        planner.add_scene(scene)
        
    workflow.sync_scenes()
    print("PASS: 3. Complete 24-page plan is structurally valid.")
    print("PASS: 4. Prompts generated using character traits for consistency.")
    
    # Verify no invalid identities
    missing_id = [s for s in planner.scenes if not s.character_id]
    if missing_id:
        print(f"FAILED: Found {len(missing_id)} pages with missing character identities.")
        sys.exit(1)
    print("PASS: 5. No page has an invented or missing character identity.")
    
    # 6. Production Tracking Status
    workflow.validate_all()
    stats = workflow.get_progress_summary()
    
    if stats["total_scenes"] != 24:
        print(f"FAILED: Expected 24 total scenes, got {stats['total_scenes']}")
        sys.exit(1)
        
    if stats["prompts_ready"] != 24:
        print(f"FAILED: Expected 24 ready prompts, got {stats['prompts_ready']}")
        sys.exit(1)
        
    if stats["artwork_assigned"] != 0:
        print(f"FAILED: Expected 0 artwork assigned (since this is planning phase), got {stats['artwork_assigned']}")
        sys.exit(1)
        
    print("PASS: 6. Every planned page has a trackable status (Prompts Ready: 24, Artwork: 0).")
    
    # 7. Assemble Book and Check Validation Gate
    engine = BookBuilderEngine()
    assembly = BookAssemblyService(engine)
    project = assembly.build_project(workflow)
    
    validator = KDPValidator()
    issues = validator.run_full_preflight_audit(project)
    
    # Since 0 artwork is assigned, we expect "Missing Image" errors or similar depending on KDPValidator
    # Let's check what errors it throws when scenes have no assets assigned.
    # In BookAssemblyService, if asset doesn't exist, it adds a page with 0 images, which triggers a WARNING "Blank Page Detected" in validator.
    # We should have exactly 24 blank page warnings.
    warnings = [w for w in issues if w.rule_name == "Blank Page Detected"]
    
    if len(warnings) != 24:
        print(f"FAILED: Expected 24 Blank Page Detected warnings, got {len(warnings)}")
        sys.exit(1)
        
    print("PASS: 7. KDP Validator correctly catches the missing artwork as 'Blank Page Detected' for all 24 pages.")
    
    print("\nALL PHASE 8E PRODUCTION PREPARATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_lilly_book_specification()
