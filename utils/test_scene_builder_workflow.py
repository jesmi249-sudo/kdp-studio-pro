import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_phase_7d_scene_builder_workflow():
    print("Testing Phase 7D Scene Builder & Templates Workflow...")
    
    # 1. Initialize Database
    from database.db import db
    db.initialize_db()

    from core.asset_manager import AssetManager
    from core.character_prompt_service import CharacterPromptService
    from core.prompt_template_service import PromptTemplateService
    
    manager = AssetManager()
    prompt_service = CharacterPromptService()
    template_service = PromptTemplateService()

    # Create dummy image
    dummy_img = "test_scene_lilly.png"
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
            expression="Smiling",
            pose="Standing tall",
            status="Must wear yellow boots"
        )
        
        if not asset:
            print("FAILED: Asset import failed.")
            sys.exit(1)

        print("PASS: Lilly character created successfully.")

        # Test 1: Template Loading
        templates = template_service.get_all_templates()
        if not templates or len(templates) < 6:
            print("FAILED: Template service did not load minimum templates.")
            sys.exit(1)
            
        print("PASS: Generic prompt templates loaded successfully.")

        # Test 2: Character Action Scene Template + Custom Fields
        # Workflow: 
        # Select "Character Action Scene"
        action_template = template_service.get_template("character_action")
        scene_config = action_template["defaults"].copy()
        
        # Override with custom user choices
        scene_config["location"] = "Garden"
        scene_config["props"] = "Flowers and butterflies"
        scene_config["action"] = "Holding a flower"
        scene_config["expression"] = "Happy"
        scene_config["pose"] = "Standing"
        scene_config["view"] = "front"
        scene_config["composition"] = "full body, centered"
        
        # Generate final prompt
        prompt, neg = prompt_service.generate_prompt(asset.id, scene_config)
        
        # Verify deterministic output
        expected_elements = [
            "Lilly", "10 year old girl", "brown hair", "Blue overalls", "Must wear yellow boots",
            "front", "Holding a flower", "Standing", "Happy", 
            "Flowers and butterflies", "Garden", "minimal background", 
            "full body, centered", "clean line art", "black and white coloring page style"
        ]
        
        for elem in expected_elements:
            if elem not in prompt:
                print(f"FAILED: Expected element '{elem}' not found in prompt.")
                print(f"Generated: {prompt}")
                sys.exit(1)
                
        print("PASS: Lilly Action Scene successfully mapped all generic and overridden metadata.")
        
        # Test 3: Negative prompt strictness
        if "grayscale" not in neg or "shading" not in neg:
            print("FAILED: Strict KDP negative prompt rules not enforced.")
            sys.exit(1)
            
        print("PASS: Strict KDP coloring-book negative prompt verified.")
        
        # Cleanup
        manager.delete_asset(asset.id)

    finally:
        if os.path.exists(dummy_img):
            os.remove(dummy_img)

    print("\nALL PHASE 7D TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_phase_7d_scene_builder_workflow()
