import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from book_builder.engine import BookBuilderEngine
from core.book_scene_planner import Scene, BookScenePlanner
from core.production_pipeline import ProductionWorkflow
from core.asset_manager import AssetManager

class TestPersistenceSync(unittest.TestCase):
    def setUp(self):
        self.engine = BookBuilderEngine()
        self.asset_manager = AssetManager()
        
    def test_workflow_persistence(self):
        # 1. Create a new project
        project = self.engine.create_project("Persistence Test Project", "Coloring Book", {})
        project_id = project.id
        
        # 2. Get scene planner and add a scene
        planner = self.engine.get_scene_planner()
        scene = Scene(page_number=1)
        scene.config["location"] = "library"
        scene.main_prompt = "A girl reading in a library"
        planner.add_scene(scene)
        
        # Save planner state to project
        self.engine.save_scene_planner(planner)
        
        # 3. Get production workflow and import artwork (mocked)
        workflow = self.engine.get_production_workflow(self.asset_manager)
        
        # We manually mock an asset import by modifying the page directly for testing logic
        # since we don't want to actually load an image file from disk.
        page = workflow.pages.get(scene.id)
        self.assertIsNotNone(page, "Production page was not automatically created for the new scene.")
        
        page.artwork_status = "ARTWORK IMPORTED"
        page.asset_id = 999 # mock asset ID
        self.engine.save_production_workflow(workflow)
        
        # 4. Save project to sqlite
        self.assertTrue(self.engine.save_project(), "Project failed to save to database.")
        project_id = project.id
        
        # Close project
        self.engine.close_project()
        self.assertIsNone(self.engine.get_active_project())
        
        # 5. Reload project from database
        loaded_project = self.engine.load_project(project_id)
        self.assertIsNotNone(loaded_project, "Failed to load project from database.")
        
        # 6. Verify restored scene planner
        restored_planner = self.engine.get_scene_planner()
        self.assertEqual(len(restored_planner.scenes), 1, "Scene planner did not restore the saved scenes.")
        restored_scene = restored_planner.scenes[0]
        self.assertEqual(restored_scene.id, scene.id)
        self.assertEqual(restored_scene.main_prompt, "A girl reading in a library")
        self.assertEqual(restored_scene.config["location"], "library")
        
        # 7. Verify restored production workflow
        restored_workflow = self.engine.get_production_workflow(self.asset_manager)
        restored_page = restored_workflow.pages.get(scene.id)
        self.assertIsNotNone(restored_page, "Production workflow lost the scene-page mapping.")
        self.assertEqual(restored_page.artwork_status, "ARTWORK IMPORTED", "Production workflow did not restore artwork status.")
        self.assertEqual(restored_page.asset_id, 999, "Production workflow lost the asset ID mapping.")
        
        print("\n[SUCCESS] Phase 9 Persistence Sync Verified: Scenes and Artwork mapping successfully survive project closing and reloading.")

if __name__ == '__main__':
    unittest.main()
