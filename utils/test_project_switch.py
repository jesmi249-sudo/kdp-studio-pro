import os
import sys
import unittest
import customtkinter as ctk

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from book_builder.engine import BookBuilderEngine
from core.book_scene_planner import Scene, BookScenePlanner
from core.production_pipeline import ProductionWorkflow
from ui.views.book_scene_planner_view import BookScenePlannerView
from ui.views.production_dashboard import ProductionDashboardView
from book_builder.container import Container
from book_builder.interfaces.core import IBookBuilder

class TestProjectSwitching(unittest.TestCase):
    def setUp(self):
        # We need a root for customtkinter views
        self.root = ctk.CTk()
        self.engine = BookBuilderEngine()
        Container().register(IBookBuilder, self.engine)
        
        # Create Project A
        self.proj_a = self.engine.create_project("Project A", "Coloring Book", {})
        self.engine.save_project()
        
        # Create Project B
        self.proj_b = self.engine.create_project("Project B", "Coloring Book", {})
        self.engine.save_project()

    def tearDown(self):
        self.root.destroy()
        
    def test_view_synchronization(self):
        try:
            # Mock master hierarchy needed by views
            class MockMaster:
                def __init__(self, engine):
                    self.engine = engine
                    self.master = self
                    
                def select_frame(self, name):
                    pass
                    
            mock_master = MockMaster(self.engine)
            
            planner_view = BookScenePlannerView(self.root)
            planner_view.master = mock_master
            dashboard_view = ProductionDashboardView(self.root)
            dashboard_view.master = mock_master
            
            # Mock UI updates to prevent CTK from hanging without mainloop
            planner_view._refresh_scene_list = lambda: None
            planner_view._set_editor_state = lambda state: None
            dashboard_view.refresh = lambda: None
            
            print("1. Switch to Project A", flush=True)
            self.engine.load_project(self.proj_a.id)
            # Add a scene in Project A via the Engine directly (simulating work done elsewhere)
            planner = self.engine.get_scene_planner()
            scene_a = Scene(page_number=1)
            scene_a.main_prompt = "Prompt A"
            planner.add_scene(scene_a)
            self.engine.save_scene_planner(planner)
            self.engine.save_project()
            
            print("Refreshing planner view", flush=True)
            planner_view.refresh_data()
            
            print("Verifying planner view", flush=True)
            self.assertEqual(len(planner_view.planner.scenes), 1)
            self.assertEqual(planner_view.planner.scenes[0].main_prompt, "Prompt A")
            
            # 2. Switch to Project B
            self.engine.load_project(self.proj_b.id)
            
            # User clicks on "Book Scene Planner" in the UI sidebar
            planner_view.refresh_data()
            
            # Verify planner view loaded Project B's data (should have 0 scenes, not 1)
            self.assertEqual(len(planner_view.planner.scenes), 0, "CRITICAL: BookScenePlannerView leaked state from Project A into Project B!")
            
            # Add a scene in Project B
            scene_b = Scene(page_number=1)
            scene_b.main_prompt = "Prompt B"
            planner_view.planner.add_scene(scene_b)
            planner_view._persist_state() # User makes change in UI
            self.engine.save_project()
            
            # 3. Switch back to Project A
            self.engine.load_project(self.proj_a.id)
            
            # User clicks on "Production Dashboard" in UI sidebar
            dashboard_view.refresh_data()
            
            # Dashboard should only see Project A's scene
            self.assertEqual(len(dashboard_view.planner.scenes), 1)
            self.assertEqual(dashboard_view.planner.scenes[0].main_prompt, "Prompt A")
            print("TEST PASSED SUCCESSFULLY", flush=True)
            import os
            os._exit(0)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            import os
            os._exit(1)

if __name__ == '__main__':
    unittest.main()
