import os
import sys
import shutil
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_lilly_production_sample():
    print("Testing Phase 8D: Lilly Production Sample (5 pages)...")
    
    from core.character_service import CharacterService
    from core.book_scene_planner import BookScenePlanner, Scene
    from core.asset_manager import AssetManager
    from core.production_pipeline import ProductionWorkflow
    from core.image_processing_service import ImageProcessingService
    from book_builder.engine import BookBuilderEngine
    from core.book_assembly_service import BookAssemblyService
    from exporters.validation import KDPValidator
    from core.publishing_package_service import PublishingPackageService
    from book_builder.models.export import ExportProfile
    from exporters.export_engine import ExportEngine
    
    test_dir = os.path.join(os.path.dirname(__file__), "test_lilly_production")
    os.makedirs(test_dir, exist_ok=True)
    
    # 2. Pipeline Initialization
    planner = BookScenePlanner()
    asset_manager = AssetManager()
    workflow = ProductionWorkflow(planner, asset_manager)

    # 1. Initialize character and metadata
    char_service = CharacterService()
    
    char_img_path = os.path.join(test_dir, "lilly_character.jpg")
    Image.new("RGB", (500, 500), color="white").save(char_img_path)
    
    lilly_asset = asset_manager.import_asset(
        source_path=char_img_path,
        category="Characters",
        name="Lilly",
        character="Lilly",
        tags="Curly brown hair, overalls",
        outfit="Overalls",
        expression="Happy"
    )
    
    print("PASS: 1. Character metadata configured.")
    
    # 3. Configure Book Project
    workflow.book_title = "Lilly's Adventures in the Garden"
    workflow.author = "Creator"
    workflow.config = {
        "book_type": "Coloring Book",
        "trim_width_in": 8.5,
        "trim_height_in": 11.0,
        "has_bleed": False,
        "paper_type": "White",
        "cover_finish": "Glossy"
    }
    print("PASS: 2. Pipeline and book configuration initialized.")
    
    # 4. Plan 5 Scenes
    scenes_data = [
        "Lilly finding a magical seed",
        "Lilly planting the seed",
        "Lilly watering the sprout",
        "Lilly watching the giant flower grow",
        "Lilly playing under the giant flower"
    ]
    for i, desc in enumerate(scenes_data):
        scene = Scene(page_number=i+1, character_id=lilly_asset.id)
        scene.main_prompt = f"Coloring page, black and white line art. {desc}"
        scene.status = "Prompt Ready"
        planner.add_scene(scene)
    workflow.sync_scenes()
    print("PASS: 3. Five scenes planned and prompts generated.")
    
    # 5. Artwork Assignment and Processing
    for scene in planner.scenes:
        # Generate a mock high-res original artwork
        img_path = os.path.join(test_dir, f"original_scene_{scene.page_number}.jpg")
        img = Image.new("RGB", (2550, 3300), color="white")
        draw = ImageDraw.Draw(img)
        # Draw some lines to pass line-art checks
        draw.rectangle((500, 500, 2000, 2800), outline="black", width=20)
        draw.line((500, 500, 2000, 2800), fill="black", width=20)
        img.save(img_path, dpi=(300, 300))
        
        # Import original
        original_asset = asset_manager.import_asset(img_path, category="Coloring Artwork")
        
        # Process into line-art derivative
        processed_asset = ImageProcessingService.prepare_line_art(original_asset, asset_manager)
        
        # Assign to pipeline
        workflow.assign_asset(scene.id, processed_asset.id)
        
    workflow.validate_all()
    stats = workflow.get_progress_summary()
    if stats["pages_validated"] != 5:
        print(f"FAILED: Expected 5 validated pages, got {stats['pages_validated']}.")
        sys.exit(1)
    print("PASS: 4. Artwork assigned, non-destructively processed, and pages validated.")
    
    # 6. Book Assembly
    engine = BookBuilderEngine()
    assembly = BookAssemblyService(engine)
    project = assembly.build_project(workflow)
    
    if len(project.pages) != 5:
        print(f"FAILED: Assembled project has {len(project.pages)} pages instead of 5.")
        sys.exit(1)
    print("PASS: 5. Book assembled properly with 5 pages.")
    
    # 7. KDP Validation (Bypass 24-page minimum for the 5-page pilot)
    validator = KDPValidator()
    issues = validator.run_full_preflight_audit(project)
    
    # Filter out Insufficient Pages error
    errors = [e for e in issues if e.severity == "ERROR" and e.rule_name != "Insufficient Pages"]
    if errors:
        print(f"FAILED: Unexpected KDP Validation errors: {[e.rule_name for e in errors]}")
        sys.exit(1)
        
    print("PASS: 6. KDP Validation passed (Insufficient Pages bypassed for pilot).")
    
    # 8. Publishing Package Export
    # Monkey-patch validator so the ExportEngine doesn't block on "Insufficient Pages"
    def mock_audit(p):
        return [i for i in issues if i.rule_name != "Insufficient Pages"]
    validator.run_full_preflight_audit = mock_audit
    
    export_engine = ExportEngine()
    package_service = PublishingPackageService(validator=validator, export_engine=export_engine)
    
    profile = ExportProfile(
        profile_name="Lilly Production Pilot",
        export_format="KDP_PDF",
        color_space="CMYK",
        dpi=300,
        custom_options={"naming_template": "{project_name}_interior"}
    )
    
    output_base = os.path.join(test_dir, "export_pkg")
    try:
        package_dir = package_service.build_publishing_package(project, profile, output_base)
    except Exception as e:
        print(f"FAILED: Export failed: {e}")
        sys.exit(1)
        
    import glob
    interior_dir = os.path.join(package_dir, "Interior")
    pdf_files = glob.glob(os.path.join(interior_dir, "*.pdf"))
    if not pdf_files or os.path.getsize(pdf_files[0]) == 0:
        print("FAILED: Interior PDF was not created or is empty.")
        sys.exit(1)
        
    manifest_path = os.path.join(package_dir, "Metadata", "manifest.json")
    if not os.path.exists(manifest_path):
        print("FAILED: Publishing manifest was not created.")
        sys.exit(1)
        
    print("PASS: 7. Publishing Package and PDF Interior successfully generated.")
    
    print("\nALL PHASE 8D PRODUCTION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_lilly_production_sample()
