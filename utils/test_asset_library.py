import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_phase_7a_asset_library():
    print("Testing Phase 7A Asset Library Migrations and Metadata...")
    
    # 1. Initialize Database (This triggers the ALTER TABLE migrations)
    from database.db import db
    db.initialize_db()
    print("PASS: Database migration initialization.")

    from core.asset_manager import AssetManager
    manager = AssetManager()

    # Create a dummy image file to import
    dummy_img = "test_lilly.png"
    from PIL import Image
    Image.new("RGB", (100, 100), "pink").save(dummy_img)

    try:
        # 2. Import Asset with new metadata
        asset = manager.import_asset(
            dummy_img, 
            category="Characters", 
            tags="main, test", 
            project_id=99,
            character="Lilly",
            pose="Standing",
            expression="Happy",
            outfit="Default",
            scene="Forest",
            status="Draft"
        )
        
        if not asset:
            print("FAILED: Asset import returned None")
            sys.exit(1)
            
        print("PASS: Asset imported successfully.")

        # 3. Verify Metadata Persistence
        if asset.character != "Lilly" or asset.project_id != 99 or asset.pose != "Standing":
            print(f"FAILED: Metadata mismatch. Got character={asset.character}, project_id={asset.project_id}")
            sys.exit(1)
            
        print("PASS: Metadata stored and retrieved successfully.")

        # 4. Search and Filter
        lilly_assets = manager.get_all_assets(character_filter="Lilly")
        if not lilly_assets or lilly_assets[0].id != asset.id:
            print("FAILED: Character filter failed.")
            sys.exit(1)
            
        project_assets = manager.get_all_assets(project_id=99)
        if not project_assets or project_assets[0].id != asset.id:
            print("FAILED: Project ID filter failed.")
            sys.exit(1)
            
        print("PASS: Search and filtering by Character and Project ID.")

        # 5. Update Metadata
        success = manager.update_metadata(asset.id, pose="Sitting", expression="Sad")
        if not success:
            print("FAILED: Metadata update returned False")
            sys.exit(1)
            
        updated_asset = manager.get_asset(asset.id)
        if updated_asset.pose != "Sitting" or updated_asset.expression != "Sad":
            print(f"FAILED: Metadata update did not persist. Got pose={updated_asset.pose}")
            sys.exit(1)
            
        print("PASS: Update metadata.")

        # 6. Duplicate Asset
        dup = manager.duplicate_asset(asset.id)
        if not dup or dup.character != "Lilly" or dup.pose != "Sitting":
            print("FAILED: Duplication did not copy metadata.")
            sys.exit(1)
            
        print("PASS: Duplicate asset.")

        # 7. Delete Assets
        manager.delete_asset(asset.id)
        manager.delete_asset(dup.id)
        
        if manager.get_asset(asset.id) is not None:
            print("FAILED: Asset deletion failed.")
            sys.exit(1)
            
        print("PASS: Delete asset.")

    finally:
        # Cleanup
        if os.path.exists(dummy_img):
            os.remove(dummy_img)

    print("\nALL PHASE 7A TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_phase_7a_asset_library()
