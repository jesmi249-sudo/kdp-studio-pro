from typing import List, Dict, Any

class PromptTemplateService:
    """Service to provide predefined structured prompt templates for the Scene Builder."""
    
    def __init__(self):
        self._templates = self._load_default_templates()
        
    def _load_default_templates(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "character_portrait",
                "name": "Character Portrait",
                "defaults": {
                    "composition": "close-up portrait, centered",
                    "background": "simple white background",
                    "action": "looking at viewer",
                    "pose": "standing",
                    "view": "front",
                    "style": "clean line art, black and white coloring page style, bold outlines, no shading, no filled colors"
                }
            },
            {
                "id": "character_action",
                "name": "Character Action Scene",
                "defaults": {
                    "composition": "full body, dynamic composition",
                    "background": "minimal background",
                    "action": "running and jumping",
                    "pose": "dynamic action pose",
                    "view": "3/4 view",
                    "style": "clean line art, black and white coloring page style, bold outlines, no shading, no filled colors"
                }
            },
            {
                "id": "character_simple_bg",
                "name": "Character with Simple Background",
                "defaults": {
                    "composition": "medium shot, centered character",
                    "background": "simple background with a few basic elements, uncluttered",
                    "action": "standing peacefully",
                    "pose": "relaxed pose",
                    "view": "front",
                    "style": "clean line art, black and white coloring page style, bold outlines, no shading, no filled colors"
                }
            },
            {
                "id": "character_story",
                "name": "Character in Story Scene",
                "defaults": {
                    "composition": "full scene, rule of thirds, character interacting with environment",
                    "background": "detailed storybook background",
                    "action": "exploring the surroundings",
                    "pose": "active pose",
                    "view": "side",
                    "style": "clean line art, black and white coloring page style, bold outlines, no shading, no filled colors"
                }
            },
            {
                "id": "character_activity",
                "name": "Character Activity Page",
                "defaults": {
                    "composition": "full body, centered character surrounded by related props",
                    "background": "white background with floating coloring items",
                    "action": "engaging in a fun activity",
                    "pose": "sitting or kneeling",
                    "view": "front",
                    "style": "clean line art, black and white coloring page style, bold outlines, no shading, no filled colors"
                }
            },
            {
                "id": "custom",
                "name": "Custom Scene",
                "defaults": {
                    "composition": "centered",
                    "background": "white background",
                    "action": "",
                    "pose": "",
                    "view": "front",
                    "style": "clean line art, black and white coloring page style, bold outlines, no shading, no filled colors"
                }
            }
        ]
        
    def get_all_templates(self) -> List[Dict[str, Any]]:
        return self._templates
        
    def get_template(self, template_id: str) -> Dict[str, Any]:
        for t in self._templates:
            if t["id"] == template_id:
                return t
        return self._templates[-1] # fallback to custom
