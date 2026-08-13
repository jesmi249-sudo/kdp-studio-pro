import os
import random
from typing import List, Dict, Any, Optional
from book_builder.models.page import Page
from book_builder.templates.base import ITemplateGenerator

# Import Generators
from book_builder.generators.maze_generator import MazeGenerator
from book_builder.generators.sudoku_generator import SudokuGenerator
from book_builder.generators.wordsearch_generator import WordSearchGenerator
from book_builder.generators.crossword_generator import CrosswordGenerator
from book_builder.generators.tracing_generator import TracingGenerator
from book_builder.generators.dot_to_dot_generator import DotToDotGenerator
from book_builder.generators.matching_generator import MatchingGenerator
from core.logger import get_logger

logger = get_logger(__name__)

class ActivityTemplateGenerator(ITemplateGenerator):
    """
    Template generator for KDP Activity Books.
    Generates shapes, grids, letters, and guidelines representing interactive puzzles.
    """
    def generate_page_objects(self, page: Page, template_type: str, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        page.images = []
        page.text_blocks = []
        
        w = page.width_pt
        h = page.height_pt
        
        m_top = page.margin_top_pt if page.margin_top_pt is not None else 36.0
        m_bottom = page.margin_bottom_pt if page.margin_bottom_pt is not None else 36.0
        m_inside = page.margin_inside_pt if page.margin_inside_pt is not None else 36.0
        m_outside = page.margin_outside_pt if page.margin_outside_pt is not None else 36.0
        
        gutter = settings.get("gutter_pt", 0.0)
        mirror = settings.get("mirror_margins", True)
        is_odd = (page.page_number % 2 != 0)
        
        if mirror:
            if is_odd:
                m_left = m_inside + gutter
                m_right = m_outside
            else:
                m_left = m_outside
                m_right = m_inside + gutter
        else:
            m_left = m_inside + gutter
            m_right = m_outside
            
        x_start = m_left
        x_end = w - m_right
        y_start = m_bottom
        y_end = h - m_top
        
        printable_w = x_end - x_start
        printable_h = y_end - y_start
        
        vector_objects: List[Dict[str, Any]] = []
        
        theme_color = settings.get("theme_color", "#000000")
        line_color = settings.get("line_color", "#A0A0A0")
        text_color = settings.get("text_color", "#000000")
        
        # Difficulty & seed resolving
        difficulty = settings.get("difficulty", "Medium")
        seed = settings.get("seed")
        if seed is None:
            seed = 42 + page.page_number
        else:
            try:
                seed = int(seed) + page.page_number
            except Exception:
                seed = 42 + page.page_number
                
        is_answer_key = settings.get("is_answer_key", False)
        
        # Heading Title Properties
        title_font = settings.get("font_family", "Helvetica")
        title_size = float(settings.get("title_font_size", 22.0 if is_answer_key else 26.0))
        title_color = settings.get("theme_color", "#000000")
        title_align = settings.get("title_alignment", "center")
        title_spacing = float(settings.get("title_spacing", 20.0))
        
        title_text = settings.get("header_text", "").strip()
        if not title_text:
            title_text = f"{template_type.upper()}"
            if is_answer_key:
                title_text += " (ANSWER KEY)"
                
        # Draw Title
        vector_objects.append({
            "shape_type": "text_block",
            "text": title_text,
            "geometry": {"x": x_start, "y": y_end - title_size - 5.0, "width": printable_w, "height": title_size + 4.0},
            "properties": {"font_size": title_size, "color": title_color, "alignment": title_align, "font_name": title_font}
        })
        
        # Customizable Instruction Text
        instruction_text = settings.get("instruction_text", "Find your way through the maze!" if not is_answer_key else "").strip()
        instruction_size = float(settings.get("instruction_font_size", 11.0))
        instruction_color = settings.get("text_color", "#4A4A4A")
        instruction_align = settings.get("instruction_alignment", "center")
        
        if instruction_text:
            # Draw Instructions below title
            instr_y = y_end - title_size - 10.0 - instruction_size
            vector_objects.append({
                "shape_type": "text_block",
                "text": instruction_text,
                "geometry": {"x": x_start, "y": instr_y, "width": printable_w, "height": instruction_size + 3.0},
                "properties": {"font_size": instruction_size, "color": instruction_color, "alignment": instruction_align, "font_name": title_font}
            })
            content_y_end = instr_y - title_spacing
        else:
            content_y_end = y_end - title_size - 10.0 - title_spacing
            
        content_h = content_y_end - y_start
        
        layout = template_type.lower().replace(" ", "_").replace("-", "_")
        
        # Match layouts
        if "maze" in layout:
            rows = int(settings.get("grid_rows", 15))
            cols = int(settings.get("grid_cols", 15))
            
            # Start and Finish marker settings
            start_marker = settings.get("start_marker", "text")
            finish_marker = settings.get("finish_marker", "text")
            
            # Helper to draw Start/Finish markers inside a cell (centered at cx, cy)
            def draw_marker_icon(v_objs, marker_type, cx, cy, cell_size, label):
                if marker_type == "text":
                    v_objs.append({
                        "shape_type": "text_block",
                        "text": label,
                        "geometry": {"x": cx - 0.5 * cell_size, "y": cy - 4.0, "width": cell_size, "height": 8.0},
                        "properties": {"font_size": min(7.0, cell_size * 0.4), "color": theme_color, "alignment": "center"}
                    })
                elif marker_type == "flag":
                    # flagpole
                    v_objs.append({
                        "shape_type": "line",
                        "geometry": {"x": cx - 0.15 * cell_size, "y": cy - 0.3 * cell_size, "width": 0.0, "height": 0.6 * cell_size},
                        "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
                    })
                    # banner flag (triangle)
                    v_objs.append({
                        "shape_type": "line",
                        "geometry": {"x": cx - 0.15 * cell_size, "y": cy + 0.15 * cell_size, "width": 0.35 * cell_size, "height": 0.0},
                        "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
                    })
                    v_objs.append({
                        "shape_type": "line",
                        "geometry": {"x": cx + 0.2 * cell_size, "y": cy + 0.15 * cell_size, "width": -0.35 * cell_size, "height": 0.15 * cell_size},
                        "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
                    })
                    v_objs.append({
                        "shape_type": "line",
                        "geometry": {"x": cx - 0.15 * cell_size, "y": cy + 0.3 * cell_size, "width": 0.35 * cell_size, "height": 0.0},
                        "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
                    })
                elif marker_type == "arrow":
                    # Draw arrow pointing right
                    v_objs.append({
                        "shape_type": "line",
                        "geometry": {"x": cx - 0.25 * cell_size, "y": cy, "width": 0.5 * cell_size, "height": 0.0},
                        "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
                    })
                    v_objs.append({
                        "shape_type": "line",
                        "geometry": {"x": cx + 0.25 * cell_size, "y": cy, "width": -0.15 * cell_size, "height": 0.15 * cell_size},
                        "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
                    })
                    v_objs.append({
                        "shape_type": "line",
                        "geometry": {"x": cx + 0.25 * cell_size, "y": cy, "width": -0.15 * cell_size, "height": -0.15 * cell_size},
                        "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
                    })
                elif marker_type == "star":
                    v_objs.append({
                        "shape_type": "text_block",
                        "text": "★",
                        "geometry": {"x": cx - 0.5 * cell_size, "y": cy - 6.0, "width": cell_size, "height": 12.0},
                        "properties": {"font_size": min(11.0, cell_size * 0.6), "color": theme_color, "alignment": "center"}
                    })
                elif marker_type == "circle":
                    v_objs.append({
                        "shape_type": "ellipse",
                        "geometry": {"x": cx - 0.2 * cell_size, "y": cy - 0.2 * cell_size, "width": 0.4 * cell_size, "height": 0.4 * cell_size},
                        "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
                    })
            
            # Helper to draw a single maze grid at a given x_off, y_off, width, height
            def draw_single_maze(v_objs, m_seed, m_is_solution, x_off, y_off, w_limit, h_limit, title_lbl=None):
                gen = MazeGenerator(rows=rows, cols=cols, seed=m_seed)
                m_walls, m_sol = gen.generate()
                
                # Deterministic aspect ratio scaling (78% of boundaries)
                max_w = w_limit * 0.78
                max_h = h_limit * 0.78
                c_sz = min(max_w / cols, max_h / rows)
                
                maze_w = c_sz * cols
                maze_h = c_sz * rows
                
                # Center within available area
                gx = x_off + (w_limit - maze_w) / 2
                gy = y_off + (h_limit - maze_h) / 2
                
                # If title_lbl is provided, draw it at the top of the sub-puzzle
                if title_lbl:
                    v_objs.append({
                        "shape_type": "text_block",
                        "text": title_lbl,
                        "geometry": {"x": x_off, "y": y_off + h_limit - 12.0, "width": w_limit, "height": 10.0},
                        "properties": {"font_size": 8.0, "color": theme_color, "alignment": "center"}
                    })
                
                # Draw outer boundaries with start/finish gaps
                # Start at (0,0) (bottom-left), Finish at (rows-1, cols-1) (top-right)
                # Bottom border (row 0), gap at col 0
                v_objs.append({
                    "shape_type": "line",
                    "geometry": {"x": gx + c_sz, "y": gy, "width": maze_w - c_sz, "height": 0.0},
                    "properties": {"stroke_color": theme_color, "stroke_width": 2.0, "fill_color": "none"}
                })
                # Top border (row rows), gap at col cols-1
                v_objs.append({
                    "shape_type": "line",
                    "geometry": {"x": gx, "y": gy + rows * c_sz, "width": maze_w - c_sz, "height": 0.0},
                    "properties": {"stroke_color": theme_color, "stroke_width": 2.0, "fill_color": "none"}
                })
                # Left border (col 0)
                v_objs.append({
                    "shape_type": "line",
                    "geometry": {"x": gx, "y": gy, "width": 0.0, "height": rows * c_sz},
                    "properties": {"stroke_color": theme_color, "stroke_width": 2.0, "fill_color": "none"}
                })
                # Right border (col cols)
                v_objs.append({
                    "shape_type": "line",
                    "geometry": {"x": gx + maze_w, "y": gy, "width": 0.0, "height": rows * c_sz},
                    "properties": {"stroke_color": theme_color, "stroke_width": 2.0, "fill_color": "none"}
                })
                
                # Draw internal walls
                for w_pair in m_walls:
                    (r1, c1), (r2, c2) = w_pair
                    if r1 == r2: # vertical
                        col = max(c1, c2)
                        wx = gx + col * c_sz
                        wy1 = gy + r1 * c_sz
                        v_objs.append({
                            "shape_type": "line",
                            "geometry": {"x": wx, "y": wy1, "width": 0.0, "height": c_sz},
                            "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
                        })
                    else: # horizontal
                        row = max(r1, r2)
                        wx1 = gx + c1 * c_sz
                        wy = gy + row * c_sz
                        v_objs.append({
                            "shape_type": "line",
                            "geometry": {"x": wx1, "y": wy, "width": c_sz, "height": 0.0},
                            "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
                        })
                
                # Draw Start/Finish Markers
                scx = gx + 0.5 * c_sz
                scy = gy + 0.5 * c_sz
                draw_marker_icon(v_objs, start_marker, scx, scy, c_sz, "START")
                
                ecx = gx + (cols - 0.5) * c_sz
                ecy = gy + (rows - 0.5) * c_sz
                draw_marker_icon(v_objs, finish_marker, ecx, ecy, c_sz, "END")
                
                # Draw solution path
                if m_is_solution:
                    # Optional color (from settings, defaulting to red)
                    sol_color = settings.get("solution_color", "#D32F2F")
                    for idx in range(len(m_sol) - 1):
                        (r1, c1) = m_sol[idx]
                        (r2, c2) = m_sol[idx + 1]
                        cx1 = gx + (c1 + 0.5) * c_sz
                        cy1 = gy + (r1 + 0.5) * c_sz
                        cx2 = gx + (c2 + 0.5) * c_sz
                        cy2 = gy + (r2 + 0.5) * c_sz
                        v_objs.append({
                            "shape_type": "line",
                            "geometry": {"x": cx1, "y": cy1, "width": cx2 - cx1, "height": cy2 - cy1},
                            "properties": {"stroke_color": sol_color, "stroke_width": max(1.5, c_sz * 0.18), "fill_color": "none"}
                        })
            
            # Determine if we render a single maze, or packed answers
            if is_answer_key and settings.get("pack_answers", True) and "puzzle_range" in settings:
                puzzle_start, puzzle_end = settings["puzzle_range"]
                puzzles_to_draw = list(range(puzzle_start, puzzle_end + 1))
                
                # Draw up to 4 solutions in a 2x2 grid
                # Available region: printable_w by content_h
                sub_w = printable_w / 2
                sub_h = content_h / 2
                
                for idx, p_num in enumerate(puzzles_to_draw):
                    row_grid = idx // 2
                    col_grid = idx % 2
                    
                    px_off = x_start + col_grid * sub_w
                    py_off = y_start + (1 - row_grid) * sub_h
                    
                    p_seed = settings.get("seed", 42) + p_num
                    draw_single_maze(vector_objects, p_seed, True, px_off, py_off, sub_w, sub_h, f"Puzzle {p_num} Solution")
            else:
                # Single maze layout
                draw_single_maze(vector_objects, seed, is_answer_key or settings.get("draw_solution", False), x_start, y_start, printable_w, content_h)
                    
        elif "sudoku" in layout:
            gen = SudokuGenerator(difficulty=difficulty, seed=seed)
            solved, puzzle = gen.generate()
            board = solved if is_answer_key else puzzle
            
            grid_sz = min(printable_w, content_h - 40.0) * 0.9
            grid_x = x_start + (printable_w - grid_sz) / 2
            grid_y = y_start + (content_h - grid_sz) / 2
            
            cell_sz = grid_sz / 9
            
            # Outer board
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": grid_x, "y": grid_y, "width": grid_sz, "height": grid_sz},
                "properties": {"stroke_color": theme_color, "stroke_width": 2.5, "fill_color": "none"}
            })
            
            # Internal lines
            for i in range(1, 9):
                w_thick = 2.0 if i % 3 == 0 else 0.75
                # Vertical
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": grid_x + i * cell_sz, "y": grid_y, "width": 0.0, "height": grid_sz},
                    "properties": {"stroke_color": theme_color, "stroke_width": w_thick, "fill_color": "none"}
                })
                # Horizontal
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": grid_x, "y": grid_y + i * cell_sz, "width": grid_sz, "height": 0.0},
                    "properties": {"stroke_color": theme_color, "stroke_width": w_thick, "fill_color": "none"}
                })
                
            # Populate numbers
            for r in range(9):
                for c in range(9):
                    num = board[r][c]
                    if num > 0:
                        is_clue = (puzzle[r][c] > 0)
                        lbl_color = theme_color if is_clue else "#4A4A4A"
                        # Grid row origin starts at bottom, so swap row order to match standard top-left sudoku format
                        cy = grid_y + (8 - r) * cell_sz
                        cx = grid_x + c * cell_sz
                        vector_objects.append({
                            "shape_type": "text_block",
                            "text": str(num),
                            "geometry": {"x": cx, "y": cy + cell_sz * 0.25, "width": cell_sz, "height": cell_sz * 0.5},
                            "properties": {"font_size": 14.0, "color": lbl_color, "alignment": "center"}
                        })
                        
        elif "word_search" in layout:
            words = settings.get("words_list")
            gen = WordSearchGenerator(size=12, words=words, seed=seed)
            grid, placed, solution = gen.generate()
            
            grid_sz = min(printable_w, content_h * 0.6)
            grid_x = x_start + (printable_w - grid_sz) / 2
            grid_y = y_start + content_h * 0.35
            
            cell_sz = grid_sz / 12
            
            # Render grid of letters
            for r in range(12):
                for c in range(12):
                    ch = grid[r][c]
                    cx = grid_x + c * cell_sz
                    cy = grid_y + (11 - r) * cell_sz
                    vector_objects.append({
                        "shape_type": "text_block",
                        "text": ch,
                        "geometry": {"x": cx, "y": cy + cell_sz * 0.2, "width": cell_sz, "height": cell_sz * 0.6},
                        "properties": {"font_size": 11.0, "color": text_color, "alignment": "center"}
                    })
                    
            # Draw surrounding border
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": grid_x - 4.0, "y": grid_y - 4.0, "width": grid_sz + 8.0, "height": grid_sz + 8.0},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
            })
            
            # Words Clues panel at bottom
            clues_y = y_start
            clues_h = content_h * 0.28
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": clues_y, "width": printable_w, "height": clues_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": "FIND THESE WORDS:",
                "geometry": {"x": x_start + 10.0, "y": clues_y + clues_h - 12.0, "width": printable_w - 20.0, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
            })
            
            # Render word items in 3 columns
            col_w = (printable_w - 30.0) / 3
            for idx, word in enumerate(placed):
                col = idx % 3
                row = idx // 3
                wx = x_start + 10.0 + col * col_w
                wy = clues_y + clues_h - 26.0 - row * 12.0
                if wy >= clues_y + 4.0:
                    vector_objects.append({
                        "shape_type": "text_block",
                        "text": f"• {word}",
                        "geometry": {"x": wx, "y": wy, "width": col_w, "height": 10.0},
                        "properties": {"font_size": 8.0, "color": text_color, "alignment": "left"}
                    })
                    
            # Answer key highlights
            if is_answer_key or settings.get("draw_solution", False):
                for word, coords in solution.items():
                    if len(coords) >= 2:
                        (r1, c1) = coords[0]
                        (r2, c2) = coords[-1]
                        cx1 = grid_x + (c1 + 0.5) * cell_sz
                        cy1 = grid_y + (11 - r1 + 0.5) * cell_sz
                        cx2 = grid_x + (c2 + 0.5) * cell_sz
                        cy2 = grid_y + (11 - r2 + 0.5) * cell_sz
                        vector_objects.append({
                            "shape_type": "line",
                            "geometry": {"x": cx1, "y": cy1, "width": cx2 - cx1, "height": cy2 - cy1},
                            "properties": {"stroke_color": "#D32F2F", "stroke_width": 8.0, "fill_color": "none"}
                        })
                        
        elif "crossword" in layout:
            word_clues = settings.get("crossword_clues")
            gen = CrosswordGenerator(size=10, word_clues=word_clues, seed=seed)
            grid, across, down = gen.generate()
            
            grid_sz = min(printable_w, content_h * 0.45)
            grid_x = x_start + (printable_w - grid_sz) / 2
            grid_y = y_start + content_h * 0.48
            
            cell_sz = grid_sz / 10
            
            # Render grid cells
            for r in range(10):
                for c in range(10):
                    cell = grid[r][c]
                    cx = grid_x + c * cell_sz
                    cy = grid_y + (9 - r) * cell_sz
                    if cell:
                        # Draw grid square
                        vector_objects.append({
                            "shape_type": "rectangle",
                            "geometry": {"x": cx, "y": cy, "width": cell_sz, "height": cell_sz},
                            "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
                        })
                        
                        # Number label
                        if cell["number"] > 0:
                            vector_objects.append({
                                "shape_type": "text_block",
                                "text": str(cell["number"]),
                                "geometry": {"x": cx + 1.0, "y": cy + cell_sz - 6.0, "width": 8.0, "height": 5.0},
                                "properties": {"font_size": 4.5, "color": theme_color, "alignment": "left"}
                            })
                            
                        # Letter (for key/answer)
                        if is_answer_key:
                            vector_objects.append({
                                "shape_type": "text_block",
                                "text": cell["letter"],
                                "geometry": {"x": cx, "y": cy + cell_sz * 0.25, "width": cell_sz, "height": cell_sz * 0.5},
                                "properties": {"font_size": 8.0, "color": "#D32F2F", "alignment": "center"}
                            })
                    else:
                        # Blocked/solid filled square
                        vector_objects.append({
                            "shape_type": "rectangle",
                            "geometry": {"x": cx, "y": cy, "width": cell_sz, "height": cell_sz},
                            "properties": {"stroke_color": theme_color, "stroke_width": 0.5, "fill_color": line_color}
                        })
                        
            # Clues panel at bottom
            clues_y = y_start
            clues_h = content_h * 0.42
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": clues_y, "width": printable_w, "height": clues_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            
            half_w = (printable_w - 20.0) / 2
            # Across Clues list
            vector_objects.append({
                "shape_type": "text_block",
                "text": "ACROSS",
                "geometry": {"x": x_start + 10.0, "y": clues_y + clues_h - 12.0, "width": half_w, "height": 10.0},
                "properties": {"font_size": 7.0, "color": theme_color, "alignment": "left"}
            })
            for idx, clue in enumerate(across):
                wy = clues_y + clues_h - 22.0 - idx * 10.0
                if wy >= clues_y + 4.0:
                    vector_objects.append({
                        "shape_type": "text_block",
                        "text": clue,
                        "geometry": {"x": x_start + 10.0, "y": wy, "width": half_w, "height": 8.0},
                        "properties": {"font_size": 6.0, "color": text_color, "alignment": "left"}
                    })
                    
            # Down Clues list
            vector_objects.append({
                "shape_type": "text_block",
                "text": "DOWN",
                "geometry": {"x": x_start + 10.0 + half_w + 10.0, "y": clues_y + clues_h - 12.0, "width": half_w, "height": 10.0},
                "properties": {"font_size": 7.0, "color": theme_color, "alignment": "left"}
            })
            for idx, clue in enumerate(down):
                wy = clues_y + clues_h - 22.0 - idx * 10.0
                if wy >= clues_y + 4.0:
                    vector_objects.append({
                        "shape_type": "text_block",
                        "text": clue,
                        "geometry": {"x": x_start + 10.0 + half_w + 10.0, "y": wy, "width": half_w, "height": 8.0},
                        "properties": {"font_size": 6.0, "color": text_color, "alignment": "left"}
                    })
                    
        elif "dot_to_dot" in layout:
            shape_type = settings.get("dot_shape", "star")
            gen = DotToDotGenerator()
            points = gen.generate(shape_type)
            
            # Map normalized coordinates (0-1) to printable page coordinates
            puzzle_sz = min(printable_w, content_h - 40.0) * 0.85
            offset_x = x_start + (printable_w - puzzle_sz) / 2
            offset_y = y_start + (content_h - puzzle_sz) / 2
            
            mapped_pts = []
            for px, py in points:
                mx = offset_x + px * puzzle_sz
                my = offset_y + py * puzzle_sz
                mapped_pts.append((mx, my))
                
            # Draw Dots & numbers
            for idx, (mx, my) in enumerate(mapped_pts):
                # Circle dot
                vector_objects.append({
                    "shape_type": "ellipse",
                    "geometry": {"x": mx - 2.5, "y": my - 2.5, "width": 5.0, "height": 5.0},
                    "properties": {"fill_color": theme_color, "stroke_color": theme_color, "stroke_width": 0.0}
                })
                # Label number
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": str(idx + 1),
                    "geometry": {"x": mx + 5.0, "y": my - 4.0, "width": 15.0, "height": 8.0},
                    "properties": {"font_size": 6.0, "color": text_color, "alignment": "left"}
                })
                
            # Draw solved connecting outline
            if is_answer_key or settings.get("draw_solution", False):
                for idx in range(len(mapped_pts)):
                    (x1, y1) = mapped_pts[idx]
                    (x2, y2) = mapped_pts[(idx + 1) % len(mapped_pts)]
                    vector_objects.append({
                        "shape_type": "line",
                        "geometry": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1},
                        "properties": {"stroke_color": "#D32F2F", "stroke_width": 1.25, "fill_color": "none"}
                    })
                    
        elif "tracing" in layout or "practice" in layout:
            gen = TracingGenerator()
            # Determine target trace (letter or shape)
            char = settings.get("trace_character", "A")
            shape = settings.get("trace_shape", "star")
            
            if "letter" in layout or "alphabet" in layout:
                paths = gen.get_letter_paths(char)
            elif "number" in layout:
                paths = gen.get_number_paths(char)
            else:
                paths = gen.get_shape_paths(shape)
                
            # Render paths on a grid for writing practice
            # Scale coordinates into writing lines
            box_sz = min(printable_w, content_h - 40.0) * 0.8
            bx = x_start + (printable_w - box_sz) / 2
            by = y_start + (content_h - box_sz) / 2
            
            # Render practice grid guidelines
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": bx, "y": by, "width": box_sz, "height": box_sz},
                "properties": {"stroke_color": line_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            
            # Center dashed guideline
            vector_objects.append({
                "shape_type": "line",
                "geometry": {"x": bx, "y": by + box_sz * 0.5, "width": box_sz, "height": 0.0},
                "properties": {"stroke_color": line_color, "stroke_width": 0.75, "fill_color": "none"} # dashed in renderer
            })
            
            for path in paths:
                # Plot sequence of tiny dots representing tracing line
                for i in range(len(path) - 1):
                    x1, y1 = path[i]
                    x2, y2 = path[i + 1]
                    px1 = bx + x1 * box_sz
                    py1 = by + y1 * box_sz
                    px2 = bx + x2 * box_sz
                    py2 = by + y2 * box_sz
                    
                    # Convert segment into dots spacing
                    seg_len = ((px2 - px1) ** 2 + (py2 - py1) ** 2) ** 0.5
                    dot_dist = 5.0 # pixels/points
                    dots_count = max(2, int(seg_len / dot_dist))
                    
                    for step in range(dots_count):
                        t = step / (dots_count - 1)
                        dx = px1 + t * (px2 - px1)
                        dy = py1 + t * (py2 - py1)
                        vector_objects.append({
                            "shape_type": "ellipse",
                            "geometry": {"x": dx - 1.0, "y": dy - 1.0, "width": 2.0, "height": 2.0},
                            "properties": {"fill_color": line_color, "stroke_color": line_color, "stroke_width": 0.0}
                        })
                        
        elif "matching" in layout:
            pairs = settings.get("matching_pairs")
            gen = MatchingGenerator(pairs=pairs, seed=seed)
            left_col, right_col, solutions = gen.generate()
            
            # 2 columns coordinate distribution
            item_h = content_h / (len(left_col) + 1)
            
            for idx, item in enumerate(left_col):
                ly = y_start + (len(left_col) - idx) * item_h - item_h * 0.5
                # Left item text
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": item,
                    "geometry": {"x": x_start + 20.0, "y": ly - 5.0, "width": 100.0, "height": 12.0},
                    "properties": {"font_size": 9.0, "color": text_color, "alignment": "left"}
                })
                # Left connector dot
                vector_objects.append({
                    "shape_type": "ellipse",
                    "geometry": {"x": x_start + 125.0 - 2.5, "y": ly - 2.5, "width": 5.0, "height": 5.0},
                    "properties": {"fill_color": theme_color, "stroke_color": theme_color, "stroke_width": 0.0}
                })
                
            for idx, item in enumerate(right_col):
                ry = y_start + (len(right_col) - idx) * item_h - item_h * 0.5
                # Right item text
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": item,
                    "geometry": {"x": x_end - 120.0, "y": ry - 5.0, "width": 100.0, "height": 12.0},
                    "properties": {"font_size": 9.0, "color": text_color, "alignment": "right"}
                })
                # Right connector dot
                vector_objects.append({
                    "shape_type": "ellipse",
                    "geometry": {"x": x_end - 125.0 - 2.5, "y": ry - 2.5, "width": 5.0, "height": 5.0},
                    "properties": {"fill_color": theme_color, "stroke_color": theme_color, "stroke_width": 0.0}
                })
                
            # Draw solutions
            if is_answer_key or settings.get("draw_solution", False):
                for l_idx, r_idx in solutions:
                    ly = y_start + (len(left_col) - l_idx) * item_h - item_h * 0.5
                    ry = y_start + (len(right_col) - r_idx) * item_h - item_h * 0.5
                    vector_objects.append({
                        "shape_type": "line",
                        "geometry": {"x": x_start + 125.0, "y": ly, "width": (x_end - 125.0) - (x_start + 125.0), "height": ry - ly},
                        "properties": {"stroke_color": "#D32F2F", "stroke_width": 1.25, "fill_color": "none"}
                    })
                    
        else:
            # DEFAULT BLANK / WORD SCRAMBLE / CUSTOM TEMPLATE
            # Draw dotted lines at bottom
            lines_y = y_start
            lines_h = content_h * 0.40
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": lines_y, "width": printable_w, "height": lines_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": "  NOTES / SCRATCHPAD",
                "geometry": {"x": x_start, "y": lines_y + lines_h - 12.0, "width": printable_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
            })
            for r in range(1, 5):
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x_start + 5.0, "y": lines_y + r * (lines_h / 5.0), "width": printable_w - 10.0, "height": 0.0},
                    "properties": {"stroke_color": line_color, "stroke_width": 0.5, "fill_color": "none"}
                })
                
            # Draw decorative coloring illustration outline
            # A simple polygonal butterfly
            wing_points = [
                (0.5, 0.7), (0.7, 0.85), (0.85, 0.75), (0.75, 0.6), (0.85, 0.45), (0.68, 0.4), (0.5, 0.5),
                (0.32, 0.4), (0.15, 0.45), (0.25, 0.6), (0.15, 0.75), (0.3, 0.85), (0.5, 0.7)
            ]
            fig_sz = min(printable_w, content_h * 0.5)
            ox = x_start + (printable_w - fig_sz) / 2
            oy = y_start + lines_h + (content_h - lines_h - fig_sz) / 2
            
            for idx in range(len(wing_points) - 1):
                x1, y1 = wing_points[idx]
                x2, y2 = wing_points[idx + 1]
                px1 = ox + x1 * fig_sz
                py1 = oy + y1 * fig_sz
                px2 = ox + x2 * fig_sz
                py2 = oy + y2 * fig_sz
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": px1, "y": py1, "width": px2 - px1, "height": py2 - py1},
                    "properties": {"stroke_color": theme_color, "stroke_width": 1.25, "fill_color": "none"}
                })
                
        # Optional page number at bottom
        show_page_number = settings.get("show_page_number", True)
        if show_page_number:
            align = "right" if is_odd else "left"
            vector_objects.append({
                "shape_type": "text_block",
                "text": str(page.page_number),
                "geometry": {"x": x_start, "y": y_start - 18.0, "width": printable_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": align}
            })
            
        return vector_objects
