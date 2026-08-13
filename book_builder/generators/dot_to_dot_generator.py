from typing import List, Tuple

class DotToDotGenerator:
    """Provides point sequence coordinates representing trace puzzles (house, star, diamond)."""
    def __init__(self) -> None:
        pass
        
    def generate(self, shape_type: str = "house") -> List[Tuple[float, float]]:
        """
        Returns normalized 0.0 - 1.0 coordinate points sequence.
        """
        shape_type = shape_type.lower()
        if shape_type == "star":
            return [
                (0.50, 0.90),
                (0.62, 0.62),
                (0.92, 0.62),
                (0.68, 0.44),
                (0.77, 0.12),
                (0.50, 0.32),
                (0.23, 0.12),
                (0.32, 0.44),
                (0.08, 0.62),
                (0.38, 0.62)
            ]
        elif shape_type == "diamond":
            return [
                (0.50, 0.85),
                (0.85, 0.50),
                (0.50, 0.15),
                (0.15, 0.50)
            ]
        else: # "house"
            return [
                (0.20, 0.20),
                (0.80, 0.20),
                (0.80, 0.60),
                (0.50, 0.85),
                (0.20, 0.60)
            ]
