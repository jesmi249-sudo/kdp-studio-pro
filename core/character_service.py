from typing import List, Optional
from models.asset import Asset
from core.asset_manager import AssetManager

class CharacterService:
    """Service to manage character references and consistency without adding new database tables."""
    
    def __init__(self):
        self.asset_manager = AssetManager()
        
    def get_primary_characters(self) -> List[Asset]:
        """Returns all assets stored under the 'Characters' category."""
        return self.asset_manager.get_all_assets(category="Characters")
        
    def format_character_reference(self, asset_id: int) -> Optional[str]:
        """
        Builds a structured character reference description from the saved metadata.
        Maps Phase 7A fields to Character Bible traits.
        """
        asset = self.asset_manager.get_asset(asset_id)
        if not asset or asset.category != "Characters":
            return None
            
        # Map fields
        name = asset.character or asset.name
        visual_identity = asset.tags or "Not specified"
        clothing = asset.outfit or "Not specified"
        expression = asset.expression or "Not specified"
        pose = asset.pose or "Not specified"
        consistency = asset.status or "Not specified"
        
        # Build formatted output
        reference = f"Character:\n{name}\n\n"
        reference += f"Visual identity:\n{visual_identity}\n\n"
        reference += f"Clothing:\n{clothing}\n\n"
        reference += f"Expression / Personality:\n{expression}\n\n"
        reference += f"Pose / Posture:\n{pose}\n\n"
        reference += f"Consistency requirements:\n{consistency}"
        
        return reference
