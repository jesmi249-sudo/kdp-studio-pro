import random
from typing import List, Tuple, Set
from book_builder.generators.activity_utils import get_rng

class MazeGenerator:
    """Generates perfect grid-based mazes and solves them for answer keys."""
    def __init__(self, rows: int = 15, cols: int = 15, seed: int = None) -> None:
        self.rows = rows
        self.cols = cols
        self.rng = get_rng(seed)
        self.walls: Set[Tuple[Tuple[int, int], Tuple[int, int]]] = set()
        self.solution_path: List[Tuple[int, int]] = []
        
    def generate(self) -> Tuple[Set[Tuple[Tuple[int, int], Tuple[int, int]]], List[Tuple[int, int]]]:
        """
        Generates maze walls using randomized DFS backtracker.
        Returns:
            walls: set of grid-cell boundaries that are active (closed).
            solution_path: path from start (0,0) to end (rows-1, cols-1).
        """
        # Initially, all walls between adjacent cells are closed
        for r in range(self.rows):
            for c in range(self.cols):
                if r < self.rows - 1:
                    self.walls.add(((r, c), (r + 1, c)))
                if c < self.cols - 1:
                    self.walls.add(((r, c), (r, c + 1)))
                    
        visited = set()
        stack = []
        start = (0, 0)
        visited.add(start)
        stack.append(start)
        
        while stack:
            curr = stack[-1]
            r, c = curr
            
            # Find unvisited neighbors
            neighbors = []
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    if (nr, nc) not in visited:
                        neighbors.append((nr, nc))
                        
            if neighbors:
                next_cell = self.rng.choice(neighbors)
                # Remove wall between curr and next_cell
                w1 = (curr, next_cell)
                w2 = (next_cell, curr)
                if w1 in self.walls:
                    self.walls.remove(w1)
                elif w2 in self.walls:
                    self.walls.remove(w2)
                    
                visited.add(next_cell)
                stack.append(next_cell)
            else:
                stack.pop()
                
        # Solve the maze from (0,0) to (rows-1, cols-1) using simple DFS
        self.solution_path = self._solve()
        return self.walls, self.solution_path

    def _solve(self) -> List[Tuple[int, int]]:
        start = (0, 0)
        end = (self.rows - 1, self.cols - 1)
        visited = {start}
        queue = [[start]]
        
        while queue:
            path = queue.pop(0)
            curr = path[-1]
            if curr == end:
                return path
                
            r, c = curr
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    if (nr, nc) not in visited:
                        # Check if wall is open
                        w1 = (curr, (nr, nc))
                        w2 = ((nr, nc), curr)
                        if w1 not in self.walls and w2 not in self.walls:
                            visited.add((nr, nc))
                            queue.append(path + [(nr, nc)])
        return []
