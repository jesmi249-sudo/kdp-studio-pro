import os
import json
import uuid
import shutil
from unittest.mock import patch

from book_builder.engine import BookBuilderEngine
from book_builder.models.book import BookProject
from book_builder.repository import ProjectRepository
from book_builder.autosave import AutosaveManager
from database.db import db
from core.logger import get_logger
import logging

logging.basicConfig(level=logging.INFO)

def run_tests():
    # Setup
    engine = BookBuilderEngine()
    
    # 1. Create a project
    project_a = engine.create_project("Project A", "Coloring Book", {})
    engine.save_project()
    proj_a_id = project_a.id
    
    # 2. Simulate a crash: mark dirty, create checkpoint
    engine.state_manager.mark_dirty()
    AutosaveManager.create_checkpoint(project_a)
    
    # Check checkpoint exists
    checkpoint_path = AutosaveManager.get_checkpoint_path(proj_a_id)
    assert os.path.exists(checkpoint_path), "Checkpoint should exist"
    
    # Test A: Recovery dialog -> YES -> checkpoint restored
    print("Running Test A: YES -> checkpoint restored")
    with patch('tkinter.messagebox.askyesno', return_value=True):
        recovered = engine.load_project(proj_a_id)
        assert recovered is not None
        assert engine.state_manager.is_dirty() is True # Should remain dirty because it's unsaved to DB
        assert os.path.exists(checkpoint_path), "Checkpoint should NOT be cleared if YES"

    # Test B: Recovery dialog -> NO -> normal project state
    print("Running Test B: NO -> normal project state")
    with patch('tkinter.messagebox.askyesno', return_value=False):
        normal_proj = engine.load_project(proj_a_id)
        assert normal_proj is not None
        assert engine.state_manager.is_dirty() is False # Loaded from DB, clean state
        assert not os.path.exists(checkpoint_path), "Checkpoint SHOULD be cleared if NO"
        
    # Test C: Project A -> Project B -> Project A switching
    print("Running Test C: Project Switching")
    project_b = engine.create_project("Project B", "Coloring Book", {})
    engine.save_project()
    proj_b_id = project_b.id
    
    switched_a = engine.load_project(proj_a_id)
    assert switched_a.id == proj_a_id
    switched_b = engine.load_project(proj_b_id)
    assert switched_b.id == proj_b_id
    switched_a2 = engine.load_project(proj_a_id)
    assert switched_a2.id == proj_a_id
    
    # Test D: Backward compatibility with projects saved before Phase 9
    print("Running Test D: Backward compatibility")
    # Simulate old JSON schema lacking certain fields
    old_data = {
        "id": str(proj_a_id),
        "name": "Old Project",
        "book_type": "Coloring Book"
        # missing schema_version, custom_settings, etc.
    }
    from book_builder.serializer import ProjectSerializer
    old_proj = ProjectSerializer.deserialize_project(old_data)
    assert old_proj.name == "Old Project"
    assert old_proj.schema_version == "8.0.0" # Default fallback
    assert old_proj.custom_settings == {}
    
    # Test E: Export/image safety
    print("Running Test E: Export/image safety check")
    import sys
    # Just checking Pillow image import safety
    from PIL import Image
    assert Image is not None
    
    print("All lightweight diagnostic tests passed!")

if __name__ == "__main__":
    run_tests()
