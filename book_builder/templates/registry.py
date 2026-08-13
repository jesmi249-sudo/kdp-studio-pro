from typing import Dict, Type
from book_builder.interfaces.template import IActivityLayoutGenerator
from core.logger import get_logger

logger = get_logger(__name__)

class ActivityTemplateRegistry:
    """
    Registry pattern for managing Activity Layout Generators.
    Allows registering new activity types without modifying central routing logic.
    """
    _generators: Dict[str, Type[IActivityLayoutGenerator]] = {}
    
    @classmethod
    def register(cls, layout_name: str, generator_class: Type[IActivityLayoutGenerator]) -> None:
        """
        Registers a layout generator for a specific layout name.
        """
        cls._generators[layout_name.lower()] = generator_class
        logger.debug(f"Registered activity layout generator for: {layout_name}")
        
    @classmethod
    def get_generator(cls, layout_name: str) -> Type[IActivityLayoutGenerator]:
        """
        Retrieves the layout generator for a given layout name.
        If an exact match isn't found, checks if the layout_name *contains* a registered key.
        Falls back to 'default' if no match is found.
        """
        layout_name = layout_name.lower()
        
        # Exact match
        if layout_name in cls._generators:
            return cls._generators[layout_name]
            
        # Substring match (e.g., 'maze_easy' matches 'maze')
        for key, generator_class in cls._generators.items():
            if key in layout_name:
                return generator_class
                
        # Fallback
        logger.warning(f"No specific generator found for '{layout_name}', using default.")
        return cls._generators.get("default")

