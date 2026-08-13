from typing import List, Tuple, Dict
import math

class TracingGenerator:
    """Generates coordinate paths representing trace-ready alphabet, numbers, and basic shapes."""
    def __init__(self) -> None:
        pass
        
    def get_letter_paths(self, letter: str) -> List[List[Tuple[float, float]]]:
        """
        Returns normalized 0.0 - 1.0 coordinate lines for a letter.
        """
        letter = letter.upper()
        # Default simple stroke lines mapping
        if letter == 'A':
            return [
                [(0.5, 0.9), (0.1, 0.1)],  # Left stroke
                [(0.5, 0.9), (0.9, 0.1)],  # Right stroke
                [(0.25, 0.4), (0.75, 0.4)]  # Center bar
            ]
        elif letter == 'B':
            return [
                [(0.2, 0.1), (0.2, 0.9)],  # Stem
                [(0.2, 0.9), (0.6, 0.9), (0.7, 0.7), (0.6, 0.5), (0.2, 0.5)], # Top loop
                [(0.2, 0.5), (0.7, 0.5), (0.8, 0.3), (0.7, 0.1), (0.2, 0.1)]  # Bottom loop
            ]
        elif letter == 'C':
            # Circular arc
            path = []
            for i in range(13):
                angle = math.radians(45 + i * 22.5) # from 45 to 315 deg
                path.append((0.5 + 0.35 * math.cos(angle), 0.5 + 0.35 * math.sin(angle)))
            return [path]
        else:
            # Fallback simple vertical + horizontal line representing 'L' shape
            return [
                [(0.2, 0.9), (0.2, 0.1)],
                [(0.2, 0.1), (0.8, 0.1)]
            ]

    def get_number_paths(self, num_char: str) -> List[List[Tuple[float, float]]]:
        """Returns normalized 0.0 - 1.0 coordinate lines for a digit."""
        if num_char == '1':
            return [
                [(0.3, 0.75), (0.5, 0.9)],
                [(0.5, 0.9), (0.5, 0.1)],
                [(0.2, 0.1), (0.8, 0.1)]
            ]
        elif num_char == '2':
            return [
                [(0.2, 0.7), (0.2, 0.8), (0.5, 0.9), (0.8, 0.8), (0.8, 0.6), (0.2, 0.1), (0.8, 0.1)]
            ]
        else:
            # Fallback '0'
            path = []
            for i in range(17):
                angle = math.radians(i * 22.5)
                path.append((0.5 + 0.3 * math.cos(angle), 0.5 + 0.45 * math.sin(angle)))
            return [path]

    def get_shape_paths(self, shape_name: str) -> List[List[Tuple[float, float]]]:
        """Returns coordinate paths for geometric shapes (circle, square, triangle, star)."""
        shape_name = shape_name.lower()
        if shape_name == "circle":
            path = []
            for i in range(37):
                angle = math.radians(i * 10)
                path.append((0.5 + 0.4 * math.cos(angle), 0.5 + 0.4 * math.sin(angle)))
            return [path]
        elif shape_name == "square" or shape_name == "rectangle":
            return [[(0.1, 0.1), (0.1, 0.9), (0.9, 0.9), (0.9, 0.1), (0.1, 0.1)]]
        elif shape_name == "triangle":
            return [[(0.5, 0.9), (0.1, 0.1), (0.9, 0.1), (0.5, 0.9)]]
        elif shape_name == "star":
            # 5-pointed star path
            points = []
            for i in range(11):
                angle = math.radians(90 + i * 72)
                r = 0.4 if i % 2 == 0 else 0.16
                points.append((0.5 + r * math.cos(angle), 0.5 + r * math.sin(angle)))
            return [points]
        else:
            return [[(0.1, 0.1), (0.9, 0.9)]]
