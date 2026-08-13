import random
from typing import List, Dict, Tuple, Any
from book_builder.generators.activity_utils import get_rng

class CrosswordGenerator:
    """Generates simple mini-crossword grids with intersection heuristics."""
    def __init__(self, size: int = 10, word_clues: List[Tuple[str, str]] = None, seed: int = None) -> None:
        self.size = size
        self.rng = get_rng(seed)
        # Default word list if none supplied
        self.word_clues = word_clues or [
            ("MAZE", "A puzzle of pathways"),
            ("GRID", "Sudoku is played on it"),
            ("WORD", "A unit of language"),
            ("PLAY", "To engage in activity for enjoyment"),
            ("EASY", "Not difficult")
        ]
        
    def generate(self) -> Tuple[List[List[Dict[str, Any]]], List[str], List[str]]:
        """
        Generates crossword layout.
        Returns:
            grid: 2D list of cells. Each cell is a dict:
                  {"letter": str, "number": int, "is_start": bool} or None.
            across_clues: List of clue strings for Across.
            down_clues: List of clue strings for Down.
        """
        grid = [[None for _ in range(self.size)] for _ in range(self.size)]
        across_clues = []
        down_clues = []
        
        placed_words = [] # list of dicts: {"word": str, "r": int, "c": int, "dir": str}
        clue_counter = 1
        
        # Shuffle word clues
        items = list(self.word_clues)
        self.rng.shuffle(items)
        
        # Place first word in the middle
        first_word, first_clue = items[0]
        first_word = first_word.upper()
        
        start_r = self.size // 2
        start_c = (self.size - len(first_word)) // 2
        
        placed_words.append({
            "word": first_word, "clue": first_clue,
            "r": start_r, "c": start_c, "dir": "A", "num": clue_counter
        })
        across_clues.append(f"{clue_counter}. ACROSS: {first_clue}")
        clue_counter += 1
        
        # Populate cells for first word
        for i, ch in enumerate(first_word):
            grid[start_r][start_c + i] = {
                "letter": ch, "number": 1 if i == 0 else 0, "is_start": i == 0
            }
            
        # Try to place other words intersecting the first
        for word, clue in items[1:]:
            word = word.upper()
            placed = False
            for p_info in placed_words:
                if placed:
                    break
                p_word = p_info["word"]
                p_r = p_info["r"]
                p_c = p_info["c"]
                p_dir = p_info["dir"]
                
                # Check for matching letter
                for i, ch in enumerate(word):
                    for j, pch in enumerate(p_word):
                        if ch == pch:
                            # Intersection point found!
                            # If parent is Across, place new word Down
                            if p_dir == "A":
                                new_r = p_r - i
                                new_c = p_c + j
                                new_dir = "D"
                            else:
                                new_r = p_r + j
                                new_c = p_c - i
                                new_dir = "A"
                                
                            # Verify bounds & overlapping cells
                            if 0 <= new_r < self.size and 0 <= new_c < self.size:
                                # Verify word fits in grid
                                fits = True
                                end_r = new_r + (len(word) - 1) if new_dir == "D" else new_r
                                end_c = new_c + (len(word) - 1) if new_dir == "A" else new_c
                                if not (0 <= end_r < self.size and 0 <= end_c < self.size):
                                    fits = False
                                    
                                if fits:
                                    # Ensure no conflict with neighboring cells
                                    for idx, char in enumerate(word):
                                        curr_r = new_r + idx if new_dir == "D" else new_r
                                        curr_c = new_c if new_dir == "D" else new_c + idx
                                        cell = grid[curr_r][curr_c]
                                        if cell is not None and cell["letter"] != char:
                                            fits = False
                                            break
                                            
                                if fits:
                                    # Place word!
                                    placed_words.append({
                                        "word": word, "clue": clue,
                                        "r": new_r, "c": new_c, "dir": new_dir, "num": clue_counter
                                    })
                                    if new_dir == "A":
                                        across_clues.append(f"{clue_counter}. ACROSS: {clue}")
                                    else:
                                        down_clues.append(f"{clue_counter}. DOWN: {clue}")
                                        
                                    for idx, char in enumerate(word):
                                        curr_r = new_r + idx if new_dir == "D" else new_r
                                        curr_c = new_c if new_dir == "D" else new_c + idx
                                        
                                        existing = grid[curr_r][curr_c]
                                        cell_num = clue_counter if idx == 0 else 0
                                        if existing:
                                            # Keep existing label or update if we are the start
                                            if cell_num > 0 and existing["number"] == 0:
                                                existing["number"] = cell_num
                                                existing["is_start"] = True
                                        else:
                                            grid[curr_r][curr_c] = {
                                                "letter": char, "number": cell_num, "is_start": cell_num > 0
                                            }
                                    clue_counter += 1
                                    placed = True
                                    break
                    if placed:
                        break
                        
        return grid, across_clues, down_clues
