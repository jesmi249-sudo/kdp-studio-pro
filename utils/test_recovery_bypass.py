import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from book_builder.engine import BookBuilderEngine
from core.book_scene_planner import Scene, BookScenePlanner
from core.production_pipeline import ProductionWorkflow
from core.asset_manager import AssetManager
from book_builder.autosave import AutosaveManager
from database.db import db

class TestRecoveryBypass(unittest.TestCase):
    def setUp(self):
        self.engine = BookBuilderEngine()
        
    def test_crash_recovery(self):
        # 1. Create a new project and save to DB
        project = self.engine.create_project("Recovery Test Project", "Coloring Book", {})
        self.assertTrue(self.engine.save_project(), "Failed to save initial project to DB")
        project_id = project.id
        
        # 2. Modify project state (e.g. add a scene) but DO NOT save to DB
        planner = self.engine.get_scene_planner()
        scene = Scene(page_number=1)
        scene.main_prompt = "Initial DB Prompt"
        planner.add_scene(scene)
        self.engine.save_scene_planner(planner)
        self.engine.save_project() # Initial DB state has 1 scene with "Initial DB Prompt"
        
        # 3. Modify AGAIN (this represents unsaved work during a crash)
        planner = self.engine.get_scene_planner()
        planner.scenes[0].main_prompt = "Unsaved Recovery Prompt"
        self.engine.save_scene_planner(planner)
        
        # 4. Trigger manual autosave checkpoint (simulating background thread)
        AutosaveManager.create_checkpoint(self.engine.get_active_project())
        self.engine.clear_dirty()
        
        # 5. Simulate App Crash (Close without saving to SQLite, bypassing clean exit)
        self.engine.state_manager.autosave_manager.stop() # just stop the timer, don't clear checkpoint
        
        # Mock messagebox to prevent blocking
        from unittest.mock import patch
        with patch('tkinter.messagebox.askyesno', return_value=True):
            # 6. Simulate Restart - Load Project via NEW Engine instance
            new_engine = BookBuilderEngine()
            recovered_project = new_engine.load_project(project_id)
        
        # 7. Assert that the recovered project has the checkpoint data, not the DB data
        self.assertIsNotNone(recovered_project)
        
        recovered_planner = new_engine.get_scene_planner()
        self.assertEqual(len(recovered_planner.scenes), 1)
        self.assertEqual(
            recovered_planner.scenes[0].main_prompt, 
            "Unsaved Recovery Prompt", 
            "CRITICAL: Crash recovery bypassed! Loaded DB state instead of checkpoint state."
        )

if __name__ == '__main__':
    unittest.main()
