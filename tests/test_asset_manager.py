import unittest
import os
import shutil
from core.asset_manager import AssetManager, ASSETS_BASE_DIR
from core.template_manager import TemplateManager, TEMPLATES_DIR
from database.db import db
from PIL import Image

class TestAssetManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a dummy image for testing
        cls.test_img_path = "test_image.png"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(cls.test_img_path)
        
        # Ensure tables are fresh if needed, but DB is persistent in test.
        # We will just rely on the test_image

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_img_path):
            os.remove(cls.test_img_path)
            
        # Clean up assets_library
        if os.path.exists(ASSETS_BASE_DIR):
            shutil.rmtree(ASSETS_BASE_DIR)

    def setUp(self):
        self.asset_manager = AssetManager()
        self.template_manager = TemplateManager()

    def test_import_and_delete_asset(self):
        # Import
        asset = self.asset_manager.import_asset(self.test_img_path, "Clipart", "test, red")
        self.assertIsNotNone(asset)
        self.assertEqual(asset.category, "Clipart")
        self.assertTrue(os.path.exists(asset.file_path))
        self.assertTrue(os.path.exists(asset.thumbnail_path))
        
        # Get
        retrieved = self.asset_manager.get_asset(asset.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "test_image.png")
        
        # Favorite
        self.asset_manager.toggle_favorite(asset.id, True)
        favs = self.asset_manager.get_all_assets(favorites_only=True)
        self.assertTrue(any(a.id == asset.id for a in favs))
        
        # Rename
        self.asset_manager.rename_asset(asset.id, "renamed.png")
        retrieved = self.asset_manager.get_asset(asset.id)
        self.assertEqual(retrieved.name, "renamed.png")
        
        # Delete
        file_path = asset.file_path
        self.asset_manager.delete_asset(asset.id)
        self.assertIsNone(self.asset_manager.get_asset(asset.id))
        self.assertFalse(os.path.exists(file_path))

    def test_duplicate_asset(self):
        asset = self.asset_manager.import_asset(self.test_img_path, "Backgrounds")
        self.assertIsNotNone(asset)
        
        dup = self.asset_manager.duplicate_asset(asset.id)
        self.assertIsNotNone(dup)
        self.assertNotEqual(asset.id, dup.id)
        self.assertNotEqual(asset.file_path, dup.file_path)
        
        self.asset_manager.delete_asset(asset.id)
        self.asset_manager.delete_asset(dup.id)

    def test_template_manager(self):
        tmpl = self.template_manager.save_template("My Template", "Notebook", self.test_img_path)
        self.assertIsNotNone(tmpl)
        self.assertEqual(tmpl.template_type, "Notebook")
        
        all_t = self.template_manager.get_all_templates()
        self.assertGreater(len(all_t), 0)
        
        self.template_manager.delete_template(tmpl.id)
        self.assertIsNone(self.template_manager.get_template(tmpl.id))

if __name__ == '__main__':
    unittest.main()
