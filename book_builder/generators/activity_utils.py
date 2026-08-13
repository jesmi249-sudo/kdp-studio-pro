import random
from typing import Any, Dict, List, Tuple

def get_rng(seed: Any = None) -> random.Random:
    """Returns a deterministic random number generator for a given seed."""
    if isinstance(seed, random.Random):
        return seed
    if seed is None:
        return random.Random()
    return random.Random(seed)

def create_grid(rows: int, cols: int, default_val: Any = None) -> List[List[Any]]:
    """Helper to initialize a 2D grid matrix."""
    return [[default_val for _ in range(cols)] for _ in range(rows)]
