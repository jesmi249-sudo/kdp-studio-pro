from typing import Dict, Any, List
from book_builder.interfaces.template import IActivityLayoutGenerator

# Import Generators
from book_builder.generators.maze_generator import MazeGenerator
from book_builder.generators.sudoku_generator import SudokuGenerator
from book_builder.generators.wordsearch_generator import WordSearchGenerator
from book_builder.generators.crossword_generator import CrosswordGenerator
from book_builder.generators.tracing_generator import TracingGenerator
from book_builder.generators.dot_to_dot_generator import DotToDotGenerator
from book_builder.generators.matching_generator import MatchingGenerator

class MazeLayoutGenerator(IActivityLayoutGenerator):
    def generate_layout(self, context: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        vector_objects: List[Dict[str, Any]] = []
        
        x_start = context["x_start"]
        y_start = context["y_start"]
        printable_w = context["printable_w"]
        content_h = context["content_h"]
        theme_color = context["theme_color"]
        
        seed = context["seed"]
        is_answer_key = context["is_answer_key"]
        
        rows = int(settings.get("grid_rows", 15))
        cols = int(settings.get("grid_cols", 15))
        
        start_marker = settings.get("start_marker", "text")
        finish_marker = settings.get("finish_marker", "text")
        
        def draw_marker_icon(v_objs, marker_type, cx, cy, cell_size, label):
            if marker_type == "text":
                v_objs.append({
                    "shape_type": "text_block",
                    "text": label,
                    "geometry": {"x": cx - 0.5 * cell_size, "y": cy - 4.0, "width": cell_size, "height": 8.0},
                    "properties": {"font_size": min(7.0, cell_size * 0.4), "color": theme_color, "alignment": "center"}
                })
            elif marker_type == "flag":
                v_objs.append({
                    "shape_type": "line",
                    "geometry": {"x": cx - 0.15 * cell_size, "y": cy - 0.3 * cell_size, "width": 0.0, "height": 0.6 * cell_size},
                    "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
                })
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
        
        def draw_single_maze(v_objs, m_seed, m_is_solution, x_off, y_off, w_limit, h_limit, title_lbl=None):
            gen = MazeGenerator(rows=rows, cols=cols, seed=m_seed)
            m_walls, m_sol = gen.generate()
            
            max_w = w_limit * 0.78
            max_h = h_limit * 0.78
            c_sz = min(max_w / cols, max_h / rows)
            
            maze_w = c_sz * cols
            maze_h = c_sz * rows
            
            gx = x_off + (w_limit - maze_w) / 2
            gy = y_off + (h_limit - maze_h) / 2
            
            if title_lbl:
                v_objs.append({
                    "shape_type": "text_block",
                    "text": title_lbl,
                    "geometry": {"x": x_off, "y": y_off + h_limit - 12.0, "width": w_limit, "height": 10.0},
                    "properties": {"font_size": 8.0, "color": theme_color, "alignment": "center"}
                })
            
            v_objs.append({
                "shape_type": "line",
                "geometry": {"x": gx + c_sz, "y": gy, "width": maze_w - c_sz, "height": 0.0},
                "properties": {"stroke_color": theme_color, "stroke_width": 2.0, "fill_color": "none"}
            })
            v_objs.append({
                "shape_type": "line",
                "geometry": {"x": gx, "y": gy + rows * c_sz, "width": maze_w - c_sz, "height": 0.0},
                "properties": {"stroke_color": theme_color, "stroke_width": 2.0, "fill_color": "none"}
            })
            v_objs.append({
                "shape_type": "line",
                "geometry": {"x": gx, "y": gy, "width": 0.0, "height": rows * c_sz},
                "properties": {"stroke_color": theme_color, "stroke_width": 2.0, "fill_color": "none"}
            })
            v_objs.append({
                "shape_type": "line",
                "geometry": {"x": gx + maze_w, "y": gy, "width": 0.0, "height": rows * c_sz},
                "properties": {"stroke_color": theme_color, "stroke_width": 2.0, "fill_color": "none"}
            })
            
            for w_pair in m_walls:
                (r1, c1), (r2, c2) = w_pair
                if r1 == r2:
                    col = max(c1, c2)
                    wx = gx + col * c_sz
                    wy1 = gy + r1 * c_sz
                    v_objs.append({
                        "shape_type": "line",
                        "geometry": {"x": wx, "y": wy1, "width": 0.0, "height": c_sz},
                        "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
                    })
                else:
                    row = max(r1, r2)
                    wx1 = gx + c1 * c_sz
                    wy = gy + row * c_sz
                    v_objs.append({
                        "shape_type": "line",
                        "geometry": {"x": wx1, "y": wy, "width": c_sz, "height": 0.0},
                        "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
                    })
            
            scx = gx + 0.5 * c_sz
            scy = gy + 0.5 * c_sz
            draw_marker_icon(v_objs, start_marker, scx, scy, c_sz, "START")
            
            ecx = gx + (cols - 0.5) * c_sz
            ecy = gy + (rows - 0.5) * c_sz
            draw_marker_icon(v_objs, finish_marker, ecx, ecy, c_sz, "END")
            
            if m_is_solution:
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

        if is_answer_key and settings.get("pack_answers", True) and "puzzle_range" in settings:
            puzzle_start, puzzle_end = settings["puzzle_range"]
            puzzles_to_draw = list(range(puzzle_start, puzzle_end + 1))
            
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
            draw_single_maze(vector_objects, seed, is_answer_key or settings.get("draw_solution", False), x_start, y_start, printable_w, content_h)

        return vector_objects

class SudokuLayoutGenerator(IActivityLayoutGenerator):
    def generate_layout(self, context: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        vector_objects: List[Dict[str, Any]] = []
        
        x_start = context["x_start"]
        y_start = context["y_start"]
        printable_w = context["printable_w"]
        content_h = context["content_h"]
        theme_color = context["theme_color"]
        
        seed = context["seed"]
        is_answer_key = context["is_answer_key"]
        difficulty = context["difficulty"]
        
        gen = SudokuGenerator(difficulty=difficulty, seed=seed)
        solved, puzzle = gen.generate()
        board = solved if is_answer_key else puzzle
        
        grid_sz = min(printable_w, content_h - 40.0) * 0.9
        grid_x = x_start + (printable_w - grid_sz) / 2
        grid_y = y_start + (content_h - grid_sz) / 2
        
        cell_sz = grid_sz / 9
        
        vector_objects.append({
            "shape_type": "rectangle",
            "geometry": {"x": grid_x, "y": grid_y, "width": grid_sz, "height": grid_sz},
            "properties": {"stroke_color": theme_color, "stroke_width": 2.5, "fill_color": "none"}
        })
        
        for i in range(1, 9):
            w_thick = 2.0 if i % 3 == 0 else 0.75
            vector_objects.append({
                "shape_type": "line",
                "geometry": {"x": grid_x + i * cell_sz, "y": grid_y, "width": 0.0, "height": grid_sz},
                "properties": {"stroke_color": theme_color, "stroke_width": w_thick, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "line",
                "geometry": {"x": grid_x, "y": grid_y + i * cell_sz, "width": grid_sz, "height": 0.0},
                "properties": {"stroke_color": theme_color, "stroke_width": w_thick, "fill_color": "none"}
            })
            
        for r in range(9):
            for c in range(9):
                num = board[r][c]
                if num > 0:
                    is_clue = (puzzle[r][c] > 0)
                    lbl_color = theme_color if is_clue else "#4A4A4A"
                    cy = grid_y + (8 - r) * cell_sz
                    cx = grid_x + c * cell_sz
                    vector_objects.append({
                        "shape_type": "text_block",
                        "text": str(num),
                        "geometry": {"x": cx, "y": cy + cell_sz * 0.25, "width": cell_sz, "height": cell_sz * 0.5},
                        "properties": {"font_size": 14.0, "color": lbl_color, "alignment": "center"}
                    })
                    
        return vector_objects

class WordSearchLayoutGenerator(IActivityLayoutGenerator):
    def generate_layout(self, context: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        vector_objects: List[Dict[str, Any]] = []
        
        x_start = context["x_start"]
        y_start = context["y_start"]
        printable_w = context["printable_w"]
        content_h = context["content_h"]
        theme_color = context["theme_color"]
        text_color = context["text_color"]
        
        seed = context["seed"]
        is_answer_key = context["is_answer_key"]
        
        words = settings.get("words_list")
        gen = WordSearchGenerator(size=12, words=words, seed=seed)
        grid, placed, solution = gen.generate()
        
        grid_sz = min(printable_w, content_h * 0.6)
        grid_x = x_start + (printable_w - grid_sz) / 2
        grid_y = y_start + content_h * 0.35
        
        cell_sz = grid_sz / 12
        
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
                
        vector_objects.append({
            "shape_type": "rectangle",
            "geometry": {"x": grid_x - 4.0, "y": grid_y - 4.0, "width": grid_sz + 8.0, "height": grid_sz + 8.0},
            "properties": {"stroke_color": theme_color, "stroke_width": 1.5, "fill_color": "none"}
        })
        
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
                    
        return vector_objects

class CrosswordLayoutGenerator(IActivityLayoutGenerator):
    def generate_layout(self, context: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        vector_objects: List[Dict[str, Any]] = []
        
        x_start = context["x_start"]
        y_start = context["y_start"]
        printable_w = context["printable_w"]
        content_h = context["content_h"]
        theme_color = context["theme_color"]
        text_color = context["text_color"]
        line_color = context["line_color"]
        
        seed = context["seed"]
        is_answer_key = context["is_answer_key"]
        
        word_clues = settings.get("crossword_clues")
        gen = CrosswordGenerator(size=10, word_clues=word_clues, seed=seed)
        grid, across, down = gen.generate()
        
        grid_sz = min(printable_w, content_h * 0.45)
        grid_x = x_start + (printable_w - grid_sz) / 2
        grid_y = y_start + content_h * 0.48
        
        cell_sz = grid_sz / 10
        
        for r in range(10):
            for c in range(10):
                cell = grid[r][c]
                cx = grid_x + c * cell_sz
                cy = grid_y + (9 - r) * cell_sz
                if cell:
                    vector_objects.append({
                        "shape_type": "rectangle",
                        "geometry": {"x": cx, "y": cy, "width": cell_sz, "height": cell_sz},
                        "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
                    })
                    
                    if cell["number"] > 0:
                        vector_objects.append({
                            "shape_type": "text_block",
                            "text": str(cell["number"]),
                            "geometry": {"x": cx + 1.0, "y": cy + cell_sz - 6.0, "width": 8.0, "height": 5.0},
                            "properties": {"font_size": 4.5, "color": theme_color, "alignment": "left"}
                        })
                        
                    if is_answer_key:
                        vector_objects.append({
                            "shape_type": "text_block",
                            "text": cell["letter"],
                            "geometry": {"x": cx, "y": cy + cell_sz * 0.25, "width": cell_sz, "height": cell_sz * 0.5},
                            "properties": {"font_size": 8.0, "color": "#D32F2F", "alignment": "center"}
                        })
                else:
                    vector_objects.append({
                        "shape_type": "rectangle",
                        "geometry": {"x": cx, "y": cy, "width": cell_sz, "height": cell_sz},
                        "properties": {"stroke_color": theme_color, "stroke_width": 0.5, "fill_color": line_color}
                    })
                    
        clues_y = y_start
        clues_h = content_h * 0.42
        vector_objects.append({
            "shape_type": "rectangle",
            "geometry": {"x": x_start, "y": clues_y, "width": printable_w, "height": clues_h},
            "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
        })
        
        half_w = (printable_w - 20.0) / 2
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
                
        return vector_objects

class DotToDotLayoutGenerator(IActivityLayoutGenerator):
    def generate_layout(self, context: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        vector_objects: List[Dict[str, Any]] = []
        
        x_start = context["x_start"]
        y_start = context["y_start"]
        printable_w = context["printable_w"]
        content_h = context["content_h"]
        theme_color = context["theme_color"]
        text_color = context["text_color"]
        is_answer_key = context["is_answer_key"]
        
        shape_type = settings.get("dot_shape", "star")
        gen = DotToDotGenerator()
        points = gen.generate(shape_type)
        
        puzzle_sz = min(printable_w, content_h - 40.0) * 0.85
        offset_x = x_start + (printable_w - puzzle_sz) / 2
        offset_y = y_start + (content_h - puzzle_sz) / 2
        
        mapped_pts = []
        for px, py in points:
            mx = offset_x + px * puzzle_sz
            my = offset_y + py * puzzle_sz
            mapped_pts.append((mx, my))
            
        for idx, (mx, my) in enumerate(mapped_pts):
            vector_objects.append({
                "shape_type": "ellipse",
                "geometry": {"x": mx - 2.5, "y": my - 2.5, "width": 5.0, "height": 5.0},
                "properties": {"fill_color": theme_color, "stroke_color": theme_color, "stroke_width": 0.0}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": str(idx + 1),
                "geometry": {"x": mx + 5.0, "y": my - 4.0, "width": 15.0, "height": 8.0},
                "properties": {"font_size": 6.0, "color": text_color, "alignment": "left"}
            })
            
        if is_answer_key or settings.get("draw_solution", False):
            for idx in range(len(mapped_pts)):
                (x1, y1) = mapped_pts[idx]
                (x2, y2) = mapped_pts[(idx + 1) % len(mapped_pts)]
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1},
                    "properties": {"stroke_color": "#D32F2F", "stroke_width": 1.25, "fill_color": "none"}
                })
                
        return vector_objects

class TracingLayoutGenerator(IActivityLayoutGenerator):
    def generate_layout(self, context: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        vector_objects: List[Dict[str, Any]] = []
        
        x_start = context["x_start"]
        y_start = context["y_start"]
        printable_w = context["printable_w"]
        content_h = context["content_h"]
        line_color = context["line_color"]
        layout = context["layout"]
        
        gen = TracingGenerator()
        char = settings.get("trace_character", "A")
        shape = settings.get("trace_shape", "star")
        
        if "letter" in layout or "alphabet" in layout:
            paths = gen.get_letter_paths(char)
        elif "number" in layout:
            paths = gen.get_number_paths(char)
        else:
            paths = gen.get_shape_paths(shape)
            
        box_sz = min(printable_w, content_h - 40.0) * 0.8
        bx = x_start + (printable_w - box_sz) / 2
        by = y_start + (content_h - box_sz) / 2
        
        vector_objects.append({
            "shape_type": "rectangle",
            "geometry": {"x": bx, "y": by, "width": box_sz, "height": box_sz},
            "properties": {"stroke_color": line_color, "stroke_width": 1.0, "fill_color": "none"}
        })
        
        vector_objects.append({
            "shape_type": "line",
            "geometry": {"x": bx, "y": by + box_sz * 0.5, "width": box_sz, "height": 0.0},
            "properties": {"stroke_color": line_color, "stroke_width": 0.75, "fill_color": "none"}
        })
        
        for path in paths:
            for i in range(len(path) - 1):
                x1, y1 = path[i]
                x2, y2 = path[i + 1]
                px1 = bx + x1 * box_sz
                py1 = by + y1 * box_sz
                px2 = bx + x2 * box_sz
                py2 = by + y2 * box_sz
                
                seg_len = ((px2 - px1) ** 2 + (py2 - py1) ** 2) ** 0.5
                dot_dist = 5.0
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
                    
        return vector_objects

class MatchingLayoutGenerator(IActivityLayoutGenerator):
    def generate_layout(self, context: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        vector_objects: List[Dict[str, Any]] = []
        
        x_start = context["x_start"]
        x_end = context["x_end"]
        y_start = context["y_start"]
        content_h = context["content_h"]
        theme_color = context["theme_color"]
        text_color = context["text_color"]
        
        seed = context["seed"]
        is_answer_key = context["is_answer_key"]
        
        pairs = settings.get("matching_pairs")
        gen = MatchingGenerator(pairs=pairs, seed=seed)
        left_col, right_col, solutions = gen.generate()
        
        item_h = content_h / (len(left_col) + 1)
        
        for idx, item in enumerate(left_col):
            ly = y_start + (len(left_col) - idx) * item_h - item_h * 0.5
            vector_objects.append({
                "shape_type": "text_block",
                "text": item,
                "geometry": {"x": x_start + 20.0, "y": ly - 5.0, "width": 100.0, "height": 12.0},
                "properties": {"font_size": 9.0, "color": text_color, "alignment": "left"}
            })
            vector_objects.append({
                "shape_type": "ellipse",
                "geometry": {"x": x_start + 125.0 - 2.5, "y": ly - 2.5, "width": 5.0, "height": 5.0},
                "properties": {"fill_color": theme_color, "stroke_color": theme_color, "stroke_width": 0.0}
            })
            
        for idx, item in enumerate(right_col):
            ry = y_start + (len(right_col) - idx) * item_h - item_h * 0.5
            vector_objects.append({
                "shape_type": "text_block",
                "text": item,
                "geometry": {"x": x_end - 120.0, "y": ry - 5.0, "width": 100.0, "height": 12.0},
                "properties": {"font_size": 9.0, "color": text_color, "alignment": "right"}
            })
            vector_objects.append({
                "shape_type": "ellipse",
                "geometry": {"x": x_end - 125.0 - 2.5, "y": ry - 2.5, "width": 5.0, "height": 5.0},
                "properties": {"fill_color": theme_color, "stroke_color": theme_color, "stroke_width": 0.0}
            })
            
        if is_answer_key or settings.get("draw_solution", False):
            for l_idx, r_idx in solutions:
                ly = y_start + (len(left_col) - l_idx) * item_h - item_h * 0.5
                ry = y_start + (len(right_col) - r_idx) * item_h - item_h * 0.5
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x_start + 125.0, "y": ly, "width": (x_end - 125.0) - (x_start + 125.0), "height": ry - ly},
                    "properties": {"stroke_color": "#D32F2F", "stroke_width": 1.25, "fill_color": "none"}
                })
                
        return vector_objects

class DefaultLayoutGenerator(IActivityLayoutGenerator):
    def generate_layout(self, context: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        vector_objects: List[Dict[str, Any]] = []
        
        x_start = context["x_start"]
        y_start = context["y_start"]
        printable_w = context["printable_w"]
        content_h = context["content_h"]
        theme_color = context["theme_color"]
        line_color = context["line_color"]
        
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
            
        return vector_objects

# Register all layouts
from book_builder.templates.registry import ActivityTemplateRegistry

ActivityTemplateRegistry.register("maze", MazeLayoutGenerator)
ActivityTemplateRegistry.register("sudoku", SudokuLayoutGenerator)
ActivityTemplateRegistry.register("word_search", WordSearchLayoutGenerator)
ActivityTemplateRegistry.register("crossword", CrosswordLayoutGenerator)
ActivityTemplateRegistry.register("dot_to_dot", DotToDotLayoutGenerator)
ActivityTemplateRegistry.register("tracing", TracingLayoutGenerator)
ActivityTemplateRegistry.register("practice", TracingLayoutGenerator)
ActivityTemplateRegistry.register("letter", TracingLayoutGenerator)
ActivityTemplateRegistry.register("alphabet", TracingLayoutGenerator)
ActivityTemplateRegistry.register("number", TracingLayoutGenerator)
ActivityTemplateRegistry.register("matching", MatchingLayoutGenerator)
ActivityTemplateRegistry.register("default", DefaultLayoutGenerator)



