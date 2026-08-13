import os
import sys
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_lilly_real_artwork():
    print("Testing Phase 8B: Lilly Pilot Real Artwork & PDF Verification...")
    
    from core.character_service import CharacterService
    from core.book_scene_planner import BookScenePlanner, Scene
    from core.prompt_batch_service import PromptBatchService
    from core.asset_manager import AssetManager
    from core.production_pipeline import ProductionWorkflow
    from book_builder.engine import BookBuilderEngine
    from core.book_assembly_service import BookAssemblyService
    from core.publishing_package_service import PublishingPackageService
    from core.image_processing_service import ImageProcessingService
    from exporters.validation import KDPValidator
    from book_builder.models.export import ExportProfile
    from PIL import Image

    # --- Step 1: Character Metadata ---
    char_service = CharacterService()
    asset_manager = AssetManager()
    characters = char_service.get_primary_characters()
    lilly = next((c for c in characters if c.name == "Lilly"), None)
    
    if not lilly:
        print("Lilly not found. Creating mock Lilly metadata...")
        dummy_char_path = os.path.join(os.path.dirname(__file__), "dummy_lilly.jpg")
        img = Image.new("RGB", (100, 100), color="pink")
        img.save(dummy_char_path)
        lilly = asset_manager.import_asset(dummy_char_path, category="Characters")
        asset_manager.update_metadata(
            lilly.id,
            name="Lilly",
            tags="7 year old, pigtails",
            outfit="Overalls",
            expression="Happy",
            pose="Standing",
            status="Consistency Required"
        )
    print("PASS: 1. Character metadata ready.")

    # --- Step 2: Scene Planner (5 Scenes) ---
    planner = BookScenePlanner()
    poses = ["Standing", "Jumping", "Sitting", "Running", "Sleeping"]
    for i, pose in enumerate(poses):
        scene = Scene(page_number=i+1, character_id=lilly.id)
        scene.config = {
            "pose": pose,
            "expression": "Happy",
            "location": "Park",
            "props": "Teddy Bear"
        }
        planner.add_scene(scene)
    
    if len(planner.scenes) != 5:
        print("FAILED: Did not create 5 scenes.")
        sys.exit(1)
    print("PASS: 2. Five scenes created.")

    # --- Step 3: Prompt Batch Generation ---
    batch_service = PromptBatchService(planner)
    batch_service.generate_all_prompts()
    print("PASS: 3. Prompts generated.")

    # --- Step 4 & 5: Mock Real Artwork & Import ---
    test_dir = os.path.join(os.path.dirname(__file__), "test_artworks")
    os.makedirs(test_dir, exist_ok=True)
    
    pipeline = ProductionWorkflow(planner, asset_manager)
    imported_assets = []
    
    for i in range(5):
        art_path = os.path.join(test_dir, f"real_artwork_{i+1}.jpg")
        # 2550x3300 represents 8.5x11 inches at 300 DPI
        img = Image.new("RGB", (2550, 3300), color="white")
        img.save(art_path, dpi=(300, 300))
        
        # Import into Coloring Artwork
        asset = asset_manager.import_asset(art_path, category="Coloring Artwork")
        imported_assets.append(asset)
        
    print("PASS: 4-5. High-resolution artworks created and imported safely.")
    
    # --- Step 6-7: Process Line Art explicitly on one asset ---
    original_path = imported_assets[0].file_path
    processed_asset = ImageProcessingService.prepare_line_art(imported_assets[0], asset_manager)
    
    if original_path == processed_asset.file_path:
        print("FAILED: Processed artwork overwrote original artwork!")
        sys.exit(1)
        
    if not os.path.exists(original_path):
        print("FAILED: Original artwork was deleted during processing!")
        sys.exit(1)
        
    print("PASS: 6-8. Image processing successfully created a derived image without modifying the original.")
    
    # Assign processed asset to page 1, and original assets to the rest
    pipeline.assign_asset(planner.scenes[0].id, processed_asset.id)
    for i in range(1, 5):
        pipeline.assign_asset(planner.scenes[i].id, imported_assets[i].id)
        
    pipeline.validate_all()
    stats = pipeline.get_progress_summary()
    if stats["artwork_assigned"] != 5:
        print("FAILED: Not all artworks were assigned.")
        sys.exit(1)

    # --- Step 9: Assemble Project ---
    engine = BookBuilderEngine()
    assembly = BookAssemblyService(engine)
    
    project = assembly.build_project(pipeline)
    if len(project.pages) != 5:
        print(f"FAILED: Expected 5 assembled pages, got {len(project.pages)}.")
        sys.exit(1)
    print("PASS: 9. Five real-artwork pages assembled successfully.")

    # --- Step 10: KDP Validation ---
    validator = KDPValidator()
    issues = validator.run_full_preflight_audit(project)
    
    # Filter out Insufficient Pages since this is an intentional 5-page pilot test
    errors = [e for e in issues if e.severity == "ERROR" and e.rule_name != "Insufficient Pages"]
    if errors:
        print(f"FAILED: KDP Validation produced unexpected ERRORs: {[e.rule_name for e in errors]}")
        sys.exit(1)
        
    print("PASS: 10. KDP Validation passed (No unexpected ERRORs).")
    
    # Monkey-patch validator to hide Insufficient Pages from package_service
    original_audit = validator.run_full_preflight_audit
    def patched_audit(proj):
        issues = original_audit(proj)
        return [i for i in issues if i.rule_name != "Insufficient Pages"]
    validator.run_full_preflight_audit = patched_audit
    
    # --- Step 11-12: PDF Export ---
    # We will use actual ExportEngine this time
    from exporters.export_engine import ExportEngine
    from book_builder.models.export import ExportProfile
    
    export_engine = ExportEngine()
    package_service = PublishingPackageService(validator=validator, export_engine=export_engine)
    
    profile = ExportProfile(
        profile_name="Test Pilot",
        export_format="KDP_PDF",
        color_space="CMYK",
        dpi=300
    )
    
    output_base = os.path.join(test_dir, "export_pkg")
    try:
        package_path = package_service.build_publishing_package(project, profile, output_base)
    except Exception as e:
        print(f"FAILED: Publishing Package Export threw exception: {e}")
        sys.exit(1)
        
    import glob
    interior_dir = os.path.join(package_path, "Interior")
    pdf_files = glob.glob(os.path.join(interior_dir, "*.pdf"))
    
    if not pdf_files:
        print("FAILED: Interior PDF was not created.")
        sys.exit(1)
        
    pdf_path = pdf_files[0]
    
    if os.path.getsize(pdf_path) == 0:
        print("FAILED: Interior PDF has zero bytes.")
        sys.exit(1)
        
    manifest_path = os.path.join(package_path, "Metadata", "manifest.json")
    if not os.path.exists(manifest_path):
        print("FAILED: Publishing manifest was not created.")
        sys.exit(1)
        
    print("PASS: 11-12. Real 5-page PDF interior and manifest successfully generated with valid sizes.")
    
    # Clean up test directories safely
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        
    print("\nALL PHASE 8B PILOT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_lilly_real_artwork()
