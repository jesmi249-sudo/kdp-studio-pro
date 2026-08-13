from typing import Optional, Dict, Tuple
from core.character_service import CharacterService

class CharacterPromptService:
    def __init__(self):
        self.char_service = CharacterService()

    def generate_prompt(self, character_id: int, scene_config: Dict[str, str]) -> Tuple[Optional[str], str]:
        """
        Generates a structured prompt and a negative prompt for a character.
        Returns: (prompt_string, negative_prompt_string)
        """
        asset = self.char_service.asset_manager.get_asset(character_id)
        if not asset or asset.category != "Characters":
            return None, ""
            
        # Character Bible fields
        name = asset.character or asset.name
        visual_identity = asset.tags or ""
        base_clothing = asset.outfit or ""
        base_expression = asset.expression or ""
        base_pose = asset.pose or ""
        consistency = asset.status or ""
        
        # User Scene Config overrides/additions
        scene_desc = scene_config.get("scene_description", "").strip()
        background = scene_config.get("background", "").strip()
        action = scene_config.get("action", "").strip()
        mood = scene_config.get("mood", "").strip()
        camera = scene_config.get("camera", "").strip()
        composition = scene_config.get("composition", "").strip()
        
        # New Phase 7D Scene Builder fields
        view = scene_config.get("view", "").strip()
        location = scene_config.get("location", "").strip()
        props = scene_config.get("props", "").strip()
        
        # Priority to user overrides for pose and expression
        active_pose = scene_config.get("pose", "").strip() or base_pose
        active_expression = scene_config.get("expression", "").strip() or base_expression
        active_outfit = scene_config.get("outfit", "").strip() or base_clothing
        style = scene_config.get("style", "").strip()
        
        # Build deterministic prompt parts
        prompt_parts = []
        
        # 1. Subject & Core Identity
        subject = f"1girl, {name}" if "girl" in visual_identity.lower() or "female" in visual_identity.lower() else name
        prompt_parts.append(subject)
        
        if visual_identity:
            prompt_parts.append(visual_identity)
            
        # 2. Action, Pose, Expression, View
        if view:
            prompt_parts.append(view)
        if action:
            prompt_parts.append(action)
        if active_pose:
            prompt_parts.append(active_pose)
        if active_expression:
            prompt_parts.append(active_expression)
            
        # 3. Clothing & Accessories & Props
        if active_outfit:
            prompt_parts.append(active_outfit)
        if props:
            prompt_parts.append(props)
            
        # 4. Consistency Requirements
        if consistency:
            prompt_parts.append(consistency)
            
        # 5. Scene, Background, Location
        if scene_desc:
            prompt_parts.append(scene_desc)
        if location:
            prompt_parts.append(location)
        if background:
            prompt_parts.append(background)
            
        # 6. Camera & Mood & Composition
        if camera:
            prompt_parts.append(camera)
        if mood:
            prompt_parts.append(mood)
        if composition:
            prompt_parts.append(composition)
            
        # 7. Style Guidelines
        if style:
            prompt_parts.append(style)
            
        # Clean and join the prompt deterministically
        cleaned_parts = [p.strip().rstrip(',') for p in prompt_parts if p.strip()]
        final_prompt = ", ".join(cleaned_parts)
        
        # Negative Prompt for clean KDP coloring pages
        negative_prompt = (
            "color, shading, gradients, grayscale, greyscale, 3d, realistic, photorealistic, "
            "watermark, text, signature, bad anatomy, bad hands, missing fingers, extra digit, "
            "fewer digits, cropped, worst quality, low quality, messy lines, sketchy, dirty background"
        )
        
        return final_prompt, negative_prompt
