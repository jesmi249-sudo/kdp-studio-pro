import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_phase_7c_prompt_workflow():
    print("Testing Phase 7C Character Prompt Workflow...")
    
    # 1. Initialize Database
    from database.db import db
    db.initialize_db()

    from core.asset_manager import AssetManager
    from core.character_prompt_service import CharacterPromptService
    
    manager = AssetManager()
    service = CharacterPromptService()

    # Create dummy image
    dummy_img = "test_prompt_lilly.png"
    from PIL import Image
    Image.new("RGB", (100, 100), "pink").save(dummy_img)

    try:
        # Import test character
        asset = manager.import_asset(
            dummy_img, 
            category="Characters", 
            character="Lilly",
            tags="10 year old girl, brown hair",
            outfit="Blue overalls",
            expression="Smiling",
            pose="Standing tall",
            status="Must wear yellow boots"
        )
        
        if not asset:
            print("FAILED: Asset import failed.")
            sys.exit(1)

        print("PASS: Test character imported.")

        # Test 1: Basic Prompt Generation (No Scene Overrides)
        prompt, neg = service.generate_prompt(asset.id, {})
        
        if "Lilly" not in prompt or "brown hair" not in prompt or "Smiling" not in prompt:
            print("FAILED: Basic prompt generation failed to include base traits.")
            print(f"Generated: {prompt}")
            sys.exit(1)
            
        if "1girl" in prompt:
            print("PASS: Dynamic '1girl' subject insertion successful.")
            
        if "grayscale" not in neg:
            print("FAILED: Negative prompt not generated correctly.")
            sys.exit(1)
            
        print("PASS: Basic deterministic prompt generated.")

        # Test 2: Overrides & Scene Configuration
        scene_config = {
            "scene_description": "walking through a magical forest",
            "pose": "running",
            "expression": "surprised",
            "style": "clean line art, coloring book page"
        }
        
        override_prompt, _ = service.generate_prompt(asset.id, scene_config)
        
        if "running" not in override_prompt or "surprised" not in override_prompt:
            print("FAILED: Pose/Expression overrides not applied.")
            print(f"Generated: {override_prompt}")
            sys.exit(1)
            
        if "magical forest" not in override_prompt or "coloring book page" not in override_prompt:
            print("FAILED: Scene description / style not appended.")
            print(f"Generated: {override_prompt}")
            sys.exit(1)
            
        # Ensure base traits are still there
        if "Blue overalls" not in override_prompt or "yellow boots" not in override_prompt:
            print("FAILED: Un-overridden base traits missing.")
            print(f"Generated: {override_prompt}")
            sys.exit(1)
            
        print("PASS: Scene configuration and overrides applied successfully.")

        # Test 3: Empty Metadata Handling
        # Import an empty character
        empty_asset = manager.import_asset(dummy_img, category="Characters")
        empty_prompt, empty_neg = service.generate_prompt(empty_asset.id, {"scene_description": "dark room"})
        
        expected_name = empty_asset.character or empty_asset.name
        if expected_name not in empty_prompt or "dark room" not in empty_prompt:
            print("FAILED: Empty metadata handling failed.")
            print(f"Generated: {empty_prompt}")
            sys.exit(1)
            
        print("PASS: Empty/missing metadata handled gracefully.")

        # Cleanup
        manager.delete_asset(asset.id)
        manager.delete_asset(empty_asset.id)

    finally:
        if os.path.exists(dummy_img):
            os.remove(dummy_img)

    print("\nALL PHASE 7C TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_phase_7c_prompt_workflow()
