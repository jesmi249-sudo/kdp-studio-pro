import random
from typing import List, Tuple, Dict, Any
from book_builder.generators.activity_utils import get_rng

class MatchingGenerator:
    """Generates left/right matching item pairs and computes correct solution lines."""
    def __init__(self, pairs: List[Tuple[str, str]] = None, seed: int = None) -> None:
        self.rng = get_rng(seed)
        self.pairs = pairs or [
            ("Apple", "Fruit"),
            ("Carrot", "Vegetable"),
            ("Dog", "Animal"),
            ("Eagle", "Bird"),
            ("Salmon", "Fish")
        ]

    def generate(self) -> Tuple[List[str], List[str], List[Tuple[int, int]]]:
        """
        Returns:
            left: List of items (in initial order).
            right: Shuffled list of matches.
            solutions: List of (left_idx, right_idx) matching indices.
        """
        left = [p[0] for p in self.pairs]
        right = [p[1] for p in self.pairs]
        
        # Shuffle right column
        right_shuffled = list(right)
        self.rng.shuffle(right_shuffled)
        
        solutions = []
        for l_idx, l_item in enumerate(left):
            r_item = self.pairs[l_idx][1]
            r_idx = right_shuffled.index(r_item)
            solutions.append((l_idx, r_idx))
            
        return left, right_shuffled, solutions
