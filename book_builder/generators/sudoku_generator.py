import random
from typing import List, Tuple
from book_builder.generators.activity_utils import get_rng

class SudokuGenerator:
    """Generates standard 9x9 Sudoku puzzles of varying difficulties."""
    def __init__(self, difficulty: str = "Medium", seed: int = None) -> None:
        self.difficulty = difficulty
        self.rng = get_rng(seed)
        
    def generate(self) -> Tuple[List[List[int]], List[List[int]]]:
        """
        Generates a 9x9 Sudoku grid.
        Returns:
            solved: Complete 9x9 solved grid.
            puzzle: 9x9 grid with empty cells (0).
        """
        # Generate base solved board
        base = 3
        side = base * base
        
        # Helper pattern for grid generation
        def pattern(r: int, c: int) -> int:
            return (base * (r % base) + r // base + c) % side

        # Shuffle helper
        def shuffle(s: List[int]) -> List[int]:
            return self.rng.sample(s, len(s))
            
        r_base = range(base)
        rows = [g * base + r for g in shuffle(list(r_base)) for r in shuffle(list(r_base))]
        cols = [g * base + c for g in shuffle(list(r_base)) for c in shuffle(list(r_base))]
        nums = shuffle(list(range(1, side + 1)))
        
        # Build solved board
        solved = [[nums[pattern(r, c)] for c in cols] for r in rows]
        
        # Copy and remove elements based on difficulty
        puzzle = [row[:] for row in solved]
        
        if self.difficulty.lower() == "easy":
            remove_count = 35
        elif self.difficulty.lower() == "hard":
            remove_count = 54
        else:
            remove_count = 45 # Medium
            
        # Get random coordinates
        cells = [(r, c) for r in range(side) for c in range(side)]
        self.rng.shuffle(cells)
        
        for r, c in cells[:remove_count]:
            puzzle[r][c] = 0
            
        return solved, puzzle
