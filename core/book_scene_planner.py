import uuid
from typing import List, Dict, Optional, Any

class Scene:
    def __init__(self, page_number: int, character_id: Optional[int] = None, template_id: str = "custom"):
        self.id = str(uuid.uuid4())
        self.page_number = page_number
        self.character_id = character_id
        self.template_id = template_id
        self.config: Dict[str, str] = {}
        self.status = "Planned"
        self.main_prompt = ""
        self.negative_prompt = ""
        self.custom_notes = ""

    def copy(self):
        new_scene = Scene(self.page_number, self.character_id, self.template_id)
        new_scene.config = self.config.copy()
        new_scene.status = "Planned"
        new_scene.custom_notes = self.custom_notes
        return new_scene

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "page_number": self.page_number,
            "character_id": self.character_id,
            "template_id": self.template_id,
            "config": self.config,
            "status": self.status,
            "main_prompt": self.main_prompt,
            "negative_prompt": self.negative_prompt,
            "custom_notes": self.custom_notes
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scene":
        s = cls(
            page_number=data.get("page_number", 1),
            character_id=data.get("character_id"),
            template_id=data.get("template_id", "custom")
        )
        s.id = data.get("id", str(uuid.uuid4()))
        s.config = data.get("config", {})
        s.status = data.get("status", "Planned")
        s.main_prompt = data.get("main_prompt", "")
        s.negative_prompt = data.get("negative_prompt", "")
        s.custom_notes = data.get("custom_notes", "")
        return s

class BookScenePlanner:
    """Manages an ordered, lightweight in-memory collection of planned scenes."""
    
    def __init__(self):
        self.scenes: List[Scene] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenes": [s.to_dict() for s in self.scenes]
        }
        
    def load_from_dict(self, data: Dict[str, Any]):
        self.scenes = []
        for s_data in data.get("scenes", []):
            self.scenes.append(Scene.from_dict(s_data))

    def add_scene(self, scene: Scene):
        self.scenes.append(scene)
        self._reindex_pages()

    def get_scene(self, scene_id: str) -> Optional[Scene]:
        for s in self.scenes:
            if s.id == scene_id:
                return s
        return None
        
    def get_scene_by_page(self, page_number: int) -> Optional[Scene]:
        for s in self.scenes:
            if s.page_number == page_number:
                return s
        return None

    def duplicate_scene(self, scene_id: str):
        original = self.get_scene(scene_id)
        if not original:
            return
        
        idx = self.scenes.index(original)
        new_scene = original.copy()
        self.scenes.insert(idx + 1, new_scene)
        self._reindex_pages()

    def delete_scene(self, scene_id: str):
        self.scenes = [s for s in self.scenes if s.id != scene_id]
        self._reindex_pages()

    def move_scene_up(self, scene_id: str):
        original = self.get_scene(scene_id)
        if not original:
            return
        idx = self.scenes.index(original)
        if idx > 0:
            self.scenes.pop(idx)
            self.scenes.insert(idx - 1, original)
            self._reindex_pages()

    def move_scene_down(self, scene_id: str):
        original = self.get_scene(scene_id)
        if not original:
            return
        idx = self.scenes.index(original)
        if idx < len(self.scenes) - 1:
            self.scenes.pop(idx)
            self.scenes.insert(idx + 1, original)
            self._reindex_pages()

    def clear_scenes(self):
        self.scenes.clear()

    def _reindex_pages(self):
        """Ensures page numbers are sequential based on current list order."""
        for i, scene in enumerate(self.scenes, start=1):
            scene.page_number = i
