import string
from typing import List, Dict, Tuple, Optional
from book_builder.generators.activity_utils import get_rng

class WordSearchGenerator:
    """Generates Word Search letter grids and tracks placed word coordinate paths."""
    def __init__(self, size: int = 12, words: List[str] = None, seed: int = None) -> None:
        self.size = size
        self.rng = get_rng(seed)
        self.words = [w.strip().upper() for w in (words or ["PYTHON", "COFFEE", "GRID", "MAZE", "PUZZLE", "SUDOKU", "TRACING"])]
        
    def generate(self) -> Tuple[List[List[str]], List[str], Dict[str, List[Tuple[int, int]]]]:
        """
        Generates grid.
        Returns:
            grid: 2D list of letters.
            placed_words: list of words successfully placed.
            solutions: dict of word -> list of coordinate tuples.
        """
        grid = [["" for _ in range(self.size)] for _ in range(self.size)]
        solutions: Dict[str, List[Tuple[int, int]]] = {}
        placed_words: List[str] = []
        
        # Directions: (dr, dc)
        directions = [
            (0, 1),   # Right
            (1, 0),   # Down
            (1, 1),   # Down-Right
            (-1, 1),  # Up-Right
            (0, -1),  # Left
            (-1, 0),  # Up
            (-1, -1), # Up-Left
            (1, -1)   # Down-Left
        ]
        
        # Sort words by length descending to place larger ones first
        sorted_words = sorted(self.words, key=len, reverse=True)
        
        for word in sorted_words:
            placed = False
            # Limit placement attempts
            attempts = 0
            while not placed and attempts < 150:
                attempts += 1
                dr, dc = self.rng.choice(directions)
                start_r = self.rng.randint(0, self.size - 1)
                start_c = self.rng.randint(0, self.size - 1)
                
                # Check bounds
                end_r = start_r + dr * (len(word) - 1)
                end_c = start_c + dc * (len(word) - 1)
                
                if 0 <= end_r < self.size and 0 <= end_c < self.size:
                    # Verify overlap conflicts
                    can_place = True
                    coords = []
                    for i, char in enumerate(word):
                        curr_r = start_r + dr * i
                        curr_c = start_c + dc * i
                        if grid[curr_r][curr_c] not in ("", char):
                            can_place = False
                            break
                        coords.append((curr_r, curr_c))
                        
                    if can_place:
                        for idx, (r, c) in enumerate(coords):
                            grid[r][c] = word[idx]
                        solutions[word] = coords
                        placed_words.append(word)
                        placed = True
                        
        # Fill empty cells with random characters
        for r in range(self.size):
            for c in range(self.size):
                if grid[r][c] == "":
                    grid[r][c] = self.rng.choice(string.ascii_uppercase)
                    
        return grid, placed_words, solutions
