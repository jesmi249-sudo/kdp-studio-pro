from typing import List, Dict
from models.planner import PlannerProject, PlannerPage, MasterPage
from models.planner_object import PlannerObject

class MasterPageEngine:
    """Merges Master Page background objects with Page foreground objects."""
    
    @staticmethod
    def get_merged_objects(page: PlannerPage, project: PlannerProject) -> List[PlannerObject]:
        """
        Returns a flattened list of PlannerObjects for rendering.
        Objects from the Master Page are placed behind (rendered first).
        """
        merged = []
        
        # 1. Add Master Page objects if linked
        if page.master_page_id:
            # Find the master page
            master = next((mp for mp in project.master_pages if mp.id == page.master_page_id), None)
            if master:
                # Deep copy to avoid mutating the master
                for obj in master.objects:
                    obj_dict = obj.to_dict()
                    copied_obj = PlannerObject.from_dict(obj_dict)
                    copied_obj.locked = True # Inherited objects cannot be moved on the page canvas directly
                    merged.append(copied_obj)
                    
        # 2. Add specific page objects
        merged.extend(page.objects)
        
        # Sort by layer to ensure Z-index drawing order
        merged.sort(key=lambda o: o.layer)
        
        return merged
