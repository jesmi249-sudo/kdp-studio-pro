import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_phase_7b_character_workflow():
    print("Testing Phase 7B Character Consistency Workflow...")
    
    # 1. Initialize Database
    from database.db import db
    db.initialize_db()
    print("PASS: Database initialization.")

    from core.asset_manager import AssetManager
    from core.character_service import CharacterService
    
    manager = AssetManager()
    service = CharacterService()

    # Create a dummy image file to import
    dummy_img = "test_character_lilly.png"
    from PIL import Image
    Image.new("RGB", (100, 100), "pink").save(dummy_img)

    try:
        # 2. Import Character Asset mapping Phase 7A fields to Character Bible
        asset = manager.import_asset(
            dummy_img, 
            category="Characters", 
            character="Lilly",
            tags="Age 10, brown hair, bright green eyes.", # Visual identity
            outfit="Blue overalls over a white shirt.", # Clothing
            expression="Usually cheerful and curious.", # Expression
            pose="Dynamic and energetic.", # Pose
            status="Must always wear her signature yellow boots." # Consistency
        )
        
        if not asset:
            print("FAILED: Character Asset import failed")
            sys.exit(1)
            
        print("PASS: Character Asset imported using existing architecture.")

        # 3. Test Service - Primary Characters Selection
        chars = service.get_primary_characters()
        if not chars or not any(c.id == asset.id for c in chars):
            print("FAILED: Character selector failed to find the primary character.")
            sys.exit(1)
            
        print("PASS: Reusable character selector logic.")

        # 4. Test Service - Character Bible Formatting
        reference = service.format_character_reference(asset.id)
        if not reference:
            print("FAILED: Reference generation returned None.")
            sys.exit(1)
            
        if "Lilly" not in reference or "brown hair" not in reference or "yellow boots" not in reference:
            print("FAILED: Reference did not format traits correctly.")
            print(f"Got:\n{reference}")
            sys.exit(1)
            
        print("PASS: Character Bible formatting.")

        # 5. Test Backward Compatibility
        # Verify no new columns were added that break existing code
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(assets)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        unwanted_columns = ['age', 'hair', 'accessories', 'personality']
        for col in unwanted_columns:
            if col in columns:
                print(f"FAILED: Found unauthorized DB column '{col}'. Architecture rule broken!")
                sys.exit(1)
                
        print("PASS: Backward compatibility and strict schema adherence verified.")

        # Cleanup
        manager.delete_asset(asset.id)

    finally:
        # Cleanup
        if os.path.exists(dummy_img):
            os.remove(dummy_img)

    print("\nALL PHASE 7B TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_phase_7b_character_workflow()
