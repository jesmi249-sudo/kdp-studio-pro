from abc import ABC, abstractmethod
from typing import Dict, Any, List

class IActivityLayoutGenerator(ABC):
    """
    Interface for specific activity layout generators (e.g. Maze, Sudoku, Tracing).
    Generates vector objects to be placed within the calculated safe content bounds.
    """
    @abstractmethod
    def generate_layout(self, context: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates vector objects for the puzzle layout.
        
        Args:
            context (Dict[str, Any]): Layout context containing coordinates, sizes, and colors:
                - x_start, y_start, printable_w, content_h, theme_color, text_color, line_color, etc.
                - is_answer_key, seed, difficulty, etc.
            settings (Dict[str, Any]): Raw template settings dictionary for custom overrides.
            
        Returns:
            List[Dict[str, Any]]: A list of vector objects to render.
        """
        pass
