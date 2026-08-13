from typing import List, Dict, Any
from core.book_scene_planner import BookScenePlanner, Scene
from core.character_prompt_service import CharacterPromptService

class PromptBatchService:
    def __init__(self, scene_planner: BookScenePlanner):
        self.scene_planner = scene_planner
        self.prompt_service = CharacterPromptService()

    def generate_all_prompts(self) -> List[Dict[str, Any]]:
        """
        Iterates over all planned scenes and generates the prompts using the
        central CharacterPromptService. 
        Updates the scene objects in memory.
        Returns a summary list of results.
        """
        results = []
        for scene in self.scene_planner.scenes:
            if not scene.character_id:
                scene.status = "Needs Revision"
                scene.main_prompt = ""
                scene.negative_prompt = ""
                results.append({
                    "page": scene.page_number,
                    "status": "Failed: No character selected"
                })
                continue

            try:
                main_p, neg_p = self.prompt_service.generate_prompt(scene.character_id, scene.config)
                scene.main_prompt = main_p or ""
                scene.negative_prompt = neg_p or ""
                scene.status = "Prompt Ready"
                results.append({
                    "page": scene.page_number,
                    "status": "Success"
                })
            except Exception as e:
                scene.status = "Needs Revision"
                results.append({
                    "page": scene.page_number,
                    "status": f"Failed: {str(e)}"
                })
                
        return results

    def generate_single_prompt(self, scene_id: str) -> bool:
        """Generates the prompt for a single scene."""
        scene = self.scene_planner.get_scene(scene_id)
        if not scene or not scene.character_id:
            if scene:
                scene.status = "Needs Revision"
            return False
            
        try:
            main_p, neg_p = self.prompt_service.generate_prompt(scene.character_id, scene.config)
            scene.main_prompt = main_p or ""
            scene.negative_prompt = neg_p or ""
            scene.status = "Prompt Ready"
            return True
        except Exception:
            scene.status = "Needs Revision"
            return False
