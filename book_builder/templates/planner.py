import os
import datetime
import calendar
from typing import List, Dict, Any, Optional
from book_builder.models.page import Page
from book_builder.templates.base import ITemplateGenerator
from core.calendar_engine import CalendarEngine
from core.logger import get_logger

logger = get_logger(__name__)

class PlannerTemplateGenerator(ITemplateGenerator):
    """
    Layout generator for low-content KDP Planner books.
    Outputs parameterized shape/text lists rendering grids, tables, and agendas.
    """
    def generate_page_objects(self, page: Page, template_type: str, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Clear existing page properties
        page.images = []
        page.text_blocks = []
        
        # Dimensions & margins
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
        
        # Style theme configurations
        theme_color = settings.get("theme_color", "#000000")
        line_color = settings.get("line_color", "#D3D3D3")
        text_color = settings.get("text_color", "#333333")
        
        # Resolve Date Context
        start_date_str = settings.get("start_date", "2026-01-01")
        try:
            start_date = datetime.date.fromisoformat(start_date_str)
        except Exception:
            start_date = datetime.date(2026, 1, 1)
            
        layout = template_type.lower().replace(" ", "_")
        
        # Build Header Title & Date Label
        date_str = ""
        if layout == "daily_planner" or layout == "daily":
            current_date = start_date + datetime.timedelta(days=page.page_number - 1)
            date_str = current_date.strftime("%A, %B %d, %Y")
        elif layout == "weekly_planner" or layout == "weekly":
            start_of_week = int(settings.get("start_weekday", 0)) # 0=Mon, 6=Sun
            weeks = CalendarEngine.generate_weekly_range(start_date_str, (start_date + datetime.timedelta(days=page.page_number * 7)).isoformat(), start_of_week)
            if len(weeks) >= page.page_number:
                week_info = weeks[page.page_number - 1]
                week_start = datetime.date.fromisoformat(week_info["week_start"])
                week_end = datetime.date.fromisoformat(week_info["week_end"])
                date_str = f"Week: {week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"
            else:
                date_str = f"Week {page.page_number}"
        elif layout == "monthly_planner" or layout == "monthly":
            months = CalendarEngine.generate_monthly_range(start_date.year, start_date.month, page.page_number)
            month_info = months[-1]
            date_str = datetime.date(month_info["year"], month_info["month"], 1).strftime("%B %Y")
        elif layout == "yearly_planner" or layout == "yearly":
            date_str = f"Year {start_date.year + (page.page_number - 1)}"
        else:
            date_str = f"Page {page.page_number}"
            
        # Draw header text
        header_text = settings.get("header_text", "").strip()
        if not header_text:
            header_text = template_type.upper()
            
        vector_objects.append({
            "shape_type": "text_block",
            "text": f"{header_text} - {date_str}".upper(),
            "geometry": {"x": x_start, "y": y_end - 15.0, "width": printable_w, "height": 15.0},
            "properties": {"font_size": 11.0, "color": theme_color, "alignment": "center"}
        })
        vector_objects.append({
            "shape_type": "line",
            "geometry": {"x": x_start, "y": y_end - 18.0, "width": printable_w, "height": 0.0},
            "properties": {"stroke_color": theme_color, "stroke_width": 1.25, "fill_color": "none"}
        })
        
        content_y_end = y_end - 30.0
        content_h = content_y_end - y_start
        
        # 12 Layout Implementations
        if layout == "daily_planner" or layout == "daily":
            # Left: Schedule slots
            col1_w = printable_w * 0.55
            col2_w = printable_w * 0.40
            col2_x = x_start + col1_w + (printable_w * 0.05)
            
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": y_start, "width": col1_w, "height": content_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": "  TODAY'S SCHEDULE",
                "geometry": {"x": x_start, "y": content_y_end - 12.0, "width": col1_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
            })
            # 10 Hour slots
            row_h = (content_h - 15.0) / 10
            for r in range(10):
                row_y = y_start + (r * row_h)
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x_start, "y": row_y, "width": col1_w, "height": 0.0},
                    "properties": {"stroke_color": line_color, "stroke_width": 0.75, "fill_color": "none"}
                })
                hour = 8 + (9 - r)
                time_lbl = f"{hour:02d}:00"
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": time_lbl,
                    "geometry": {"x": x_start + 5.0, "y": row_y + 4.0, "width": 40.0, "height": 10.0},
                    "properties": {"font_size": 7.0, "color": text_color, "alignment": "left"}
                })
                
            # Right: To-Do & Water
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": col2_x, "y": y_start + 40.0, "width": col2_w, "height": content_h - 40.0},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": "  TO-DO LIST",
                "geometry": {"x": col2_x, "y": content_y_end - 12.0, "width": col2_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
            })
            todo_row_h = (content_h - 55.0) / 8
            for r in range(8):
                row_y = y_start + 40.0 + (r * todo_row_h)
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": col2_x, "y": row_y, "width": col2_w, "height": 0.0},
                    "properties": {"stroke_color": line_color, "stroke_width": 0.75, "fill_color": "none"}
                })
                vector_objects.append({
                    "shape_type": "rectangle",
                    "geometry": {"x": col2_x + 5.0, "y": row_y + 4.0, "width": 8.0, "height": 8.0},
                    "properties": {"stroke_color": theme_color, "stroke_width": 0.75, "fill_color": "none"}
                })
                
            # Water intake
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": col2_x, "y": y_start, "width": col2_w, "height": 30.0},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": "WATER INTAKE",
                "geometry": {"x": col2_x + 5.0, "y": y_start + 18.0, "width": col2_w - 10.0, "height": 8.0},
                "properties": {"font_size": 7.0, "color": theme_color, "alignment": "center"}
            })
            circle_spacing = (col2_w - 10.0) / 9
            for c in range(8):
                cx = col2_x + 5.0 + ((c + 1) * circle_spacing)
                vector_objects.append({
                    "shape_type": "ellipse",
                    "geometry": {"x": cx - 4.0, "y": y_start + 6.0, "width": 8.0, "height": 8.0},
                    "properties": {"stroke_color": theme_color, "stroke_width": 0.75, "fill_color": "none"}
                })
                
        elif layout == "weekly_planner" or layout == "weekly":
            # 2 columns x 4 rows
            box_w = (printable_w - 15.0) / 2
            box_h = (content_h - 30.0) / 4
            gap_x = 15.0
            gap_y = 10.0
            labels = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY", "NOTES"]
            
            for i in range(8):
                col = i % 2
                row = i // 2
                bx = x_start + col * (box_w + gap_x)
                by = content_y_end - (row + 1) * box_h - row * gap_y
                
                vector_objects.append({
                    "shape_type": "rectangle",
                    "geometry": {"x": bx, "y": by, "width": box_w, "height": box_h},
                    "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
                })
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": labels[7 - i],
                    "geometry": {"x": bx + 5.0, "y": by + box_h - 12.0, "width": box_w - 10.0, "height": 10.0},
                    "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
                })
                inner_rows = 3
                inner_h = (box_h - 15.0) / inner_rows
                for r in range(1, inner_rows):
                    vector_objects.append({
                        "shape_type": "line",
                        "geometry": {"x": bx + 5.0, "y": by + r * inner_h, "width": box_w - 10.0, "height": 0.0},
                        "properties": {"stroke_color": line_color, "stroke_width": 0.5, "fill_color": "none"}
                    })
                    
        elif layout == "monthly_planner" or layout == "monthly":
            cols = 7
            rows = 5
            box_w = printable_w / cols
            box_h = (content_h - 20.0) / rows
            
            days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
            for c in range(cols):
                bx = x_start + c * box_w
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": days[c],
                    "geometry": {"x": bx, "y": content_y_end - 15.0, "width": box_w, "height": 10.0},
                    "properties": {"font_size": 8.0, "color": theme_color, "alignment": "center"}
                })
                
            for r in range(rows):
                ry = y_start + r * box_h
                for c in range(cols):
                    cx = x_start + c * box_w
                    vector_objects.append({
                        "shape_type": "rectangle",
                        "geometry": {"x": cx, "y": ry, "width": box_w, "height": box_h},
                        "properties": {"stroke_color": theme_color, "stroke_width": 0.75, "fill_color": "none"}
                    })
                    # Calendar date placeholder
                    vector_objects.append({
                        "shape_type": "rectangle",
                        "geometry": {"x": cx + box_w - 12.0, "y": ry + box_h - 12.0, "width": 8.0, "height": 8.0},
                        "properties": {"stroke_color": line_color, "stroke_width": 0.5, "fill_color": "none"}
                    })
                    
        elif layout == "yearly_planner" or layout == "yearly":
            box_w = (printable_w - 20.0) / 3
            box_h = (content_h - 30.0) / 4
            gap_x = 10.0
            gap_y = 10.0
            months = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
            
            for i in range(12):
                col = i % 3
                row = i // 3
                bx = x_start + col * (box_w + gap_x)
                by = content_y_end - (row + 1) * box_h - row * gap_y
                
                vector_objects.append({
                    "shape_type": "rectangle",
                    "geometry": {"x": bx, "y": by, "width": box_w, "height": box_h},
                    "properties": {"stroke_color": theme_color, "stroke_width": 0.75, "fill_color": "none"}
                })
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": months[11 - i],
                    "geometry": {"x": bx, "y": by + box_h - 12.0, "width": box_w, "height": 10.0},
                    "properties": {"font_size": 7.0, "color": theme_color, "alignment": "center"}
                })
                
                # Render miniature days
                mini_rows = 4
                mini_cols = 7
                mcw = (box_w - 6.0) / mini_cols
                mch = (box_h - 15.0) / mini_rows
                for mr in range(mini_rows):
                    mry = by + 3.0 + mr * mch
                    for mc in range(mini_cols):
                        mcx = bx + 3.0 + mc * mcw
                        vector_objects.append({
                            "shape_type": "rectangle",
                            "geometry": {"x": mcx, "y": mry, "width": mcw - 1.0, "height": mch - 1.0},
                            "properties": {"stroke_color": line_color, "stroke_width": 0.25, "fill_color": "none"}
                        })
                        
        elif layout == "habit_tracker":
            row_count = 10
            col_count = 31
            lbl_w = 80.0
            grid_w = printable_w - lbl_w
            cw = grid_w / col_count
            ch = content_h / (row_count + 1)
            
            for c in range(col_count):
                cx = x_start + lbl_w + c * cw
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": str(c + 1),
                    "geometry": {"x": cx, "y": content_y_end - ch + 3.0, "width": cw, "height": 8.0},
                    "properties": {"font_size": 6.0, "color": text_color, "alignment": "center"}
                })
                
            for r in range(row_count):
                ry = y_start + r * ch
                vector_objects.append({
                    "shape_type": "rectangle",
                    "geometry": {"x": x_start, "y": ry, "width": lbl_w, "height": ch},
                    "properties": {"stroke_color": theme_color, "stroke_width": 0.75, "fill_color": "none"}
                })
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": f" Habit {row_count - r}",
                    "geometry": {"x": x_start + 2.0, "y": ry + 3.0, "width": lbl_w - 4.0, "height": ch - 4.0},
                    "properties": {"font_size": 7.0, "color": text_color, "alignment": "left"}
                })
                for c in range(col_count):
                    cx = x_start + lbl_w + c * cw
                    vector_objects.append({
                        "shape_type": "rectangle",
                        "geometry": {"x": cx, "y": ry, "width": cw, "height": ch},
                        "properties": {"stroke_color": line_color, "stroke_width": 0.5, "fill_color": "none"}
                    })
                    
        elif layout == "budget_tracker" or layout == "budget_planner":
            table_w = printable_w
            col_w = [table_w * 0.4, table_w * 0.2, table_w * 0.2, table_w * 0.2]
            
            exp_h = content_h * 0.60
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": y_start, "width": table_w, "height": exp_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": " EXPENSES TRACKER",
                "geometry": {"x": x_start + 5.0, "y": y_start + exp_h - 12.0, "width": table_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
            })
            
            inc_h = content_h * 0.35
            inc_y = y_start + exp_h + (content_h * 0.05)
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": inc_y, "width": table_w, "height": inc_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": " INCOME TRACKER",
                "geometry": {"x": x_start + 5.0, "y": inc_y + inc_h - 12.0, "width": table_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
            })
            
            for ty, th in [(y_start, exp_h), (inc_y, inc_h)]:
                headers = ["Description", "Projected", "Actual", "Difference"]
                curr_x = x_start
                for c in range(4):
                    vector_objects.append({
                        "shape_type": "text_block",
                        "text": headers[c],
                        "geometry": {"x": curr_x, "y": ty + th - 24.0, "width": col_w[c], "height": 8.0},
                        "properties": {"font_size": 7.0, "color": theme_color, "alignment": "center"}
                    })
                    if c > 0:
                        vector_objects.append({
                            "shape_type": "line",
                            "geometry": {"x": curr_x, "y": ty, "width": 0.0, "height": th - 12.0},
                            "properties": {"stroke_color": line_color, "stroke_width": 0.75, "fill_color": "none"}
                        })
                    curr_x += col_w[c]
                    
        elif layout == "goal_planner" or layout == "goal_tracker":
            panel_h = (content_h - 20.0) / 3
            headers = ["1. OBJECTIVES & MILESTONES", "2. ACTION PLAN STEPS", "3. RESULTS & REFLECTION"]
            for i in range(3):
                py = y_start + i * (panel_h + 10.0)
                vector_objects.append({
                    "shape_type": "rectangle",
                    "geometry": {"x": x_start, "y": py, "width": printable_w, "height": panel_h},
                    "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
                })
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": "  " + headers[2 - i],
                    "geometry": {"x": x_start, "y": py + panel_h - 12.0, "width": printable_w, "height": 10.0},
                    "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
                })
                inner_rows = 4
                inner_h = (panel_h - 15.0) / inner_rows
                for r in range(1, inner_rows):
                    vector_objects.append({
                        "shape_type": "line",
                        "geometry": {"x": x_start + 5.0, "y": py + r * inner_h, "width": printable_w - 10.0, "height": 0.0},
                        "properties": {"stroke_color": line_color, "stroke_width": 0.5, "fill_color": "none"}
                    })
                    
        elif layout == "meal_planner":
            cols = 4
            rows = 7
            day_w = 60.0
            grid_w = printable_w - day_w
            col_w = grid_w / cols
            cell_h = (content_h - 20.0) / rows
            
            headers = ["BREAKFAST", "LUNCH", "DINNER", "SNACKS/NOTES"]
            for c in range(cols):
                cx = x_start + day_w + c * col_w
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": headers[c],
                    "geometry": {"x": cx, "y": content_y_end - 15.0, "width": col_w, "height": 10.0},
                    "properties": {"font_size": 8.0, "color": theme_color, "alignment": "center"}
                })
                
            days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
            for r in range(rows):
                ry = y_start + r * cell_h
                vector_objects.append({
                    "shape_type": "rectangle",
                    "geometry": {"x": x_start, "y": ry, "width": day_w, "height": cell_h},
                    "properties": {"stroke_color": theme_color, "stroke_width": 0.75, "fill_color": "none"}
                })
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": days[6 - r],
                    "geometry": {"x": x_start, "y": ry + (cell_h - 8.0) / 2.0, "width": day_w, "height": 8.0},
                    "properties": {"font_size": 8.0, "color": theme_color, "alignment": "center"}
                })
                for c in range(cols):
                    cx = x_start + day_w + c * col_w
                    vector_objects.append({
                        "shape_type": "rectangle",
                        "geometry": {"x": cx, "y": ry, "width": col_w, "height": cell_h},
                        "properties": {"stroke_color": line_color, "stroke_width": 0.5, "fill_color": "none"}
                    })
                    
        elif layout == "fitness_planner":
            panel_h = (content_h - 20.0) / 3
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": y_start + 2 * (panel_h + 10.0), "width": printable_w, "height": panel_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": "  WORKOUT LOG (EXERCISE, SETS, REPS, WEIGHT)",
                "geometry": {"x": x_start, "y": y_start + 3 * panel_h + 10.0 - 12.0, "width": printable_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
            })
            for r in range(1, 4):
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x_start + 5.0, "y": y_start + 2 * (panel_h + 10.0) + r * (panel_h / 4.0), "width": printable_w - 10.0, "height": 0.0},
                    "properties": {"stroke_color": line_color, "stroke_width": 0.5, "fill_color": "none"}
                })
                
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": y_start + panel_h + 10.0, "width": printable_w, "height": panel_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": "  DIET & NUTRITION LOG (MEAL, CALORIES, PROTEIN)",
                "geometry": {"x": x_start, "y": y_start + 2 * panel_h + 10.0 - 12.0, "width": printable_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
            })
            
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": y_start, "width": printable_w, "height": panel_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": "  STATS & PROGRESS",
                "geometry": {"x": x_start, "y": y_start + panel_h - 12.0, "width": printable_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
            })
            
        elif layout == "reading_log":
            table_w = printable_w
            col_w = [table_w * 0.4, table_w * 0.3, table_w * 0.15, table_w * 0.15]
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": y_start, "width": table_w, "height": content_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            
            row_h = content_h / 13
            headers = ["Book Title", "Author", "Rating", "Finished"]
            curr_x = x_start
            for c in range(4):
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": headers[c],
                    "geometry": {"x": curr_x, "y": content_y_end - row_h + 3.0, "width": col_w[c], "height": 10.0},
                    "properties": {"font_size": 8.0, "color": theme_color, "alignment": "center"}
                })
                if c > 0:
                    vector_objects.append({
                        "shape_type": "line",
                        "geometry": {"x": curr_x, "y": y_start, "width": 0.0, "height": content_h},
                        "properties": {"stroke_color": line_color, "stroke_width": 0.75, "fill_color": "none"}
                    })
                curr_x += col_w[c]
            for r in range(12):
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x_start, "y": y_start + r * row_h, "width": table_w, "height": 0.0},
                    "properties": {"stroke_color": line_color, "stroke_width": 0.5, "fill_color": "none"}
                })
                
        elif layout == "project_planner":
            top_h = content_h * 0.35
            bot_h = content_h * 0.60
            
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": y_start + bot_h + (content_h * 0.05), "width": printable_w, "height": top_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": "  PROJECT OVERVIEW & KEY DELIVERABLES",
                "geometry": {"x": x_start, "y": content_y_end - 12.0, "width": printable_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
            })
            
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": y_start, "width": printable_w, "height": bot_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": "  ACTION ITEMS & TASK LIST",
                "geometry": {"x": x_start, "y": y_start + bot_h - 12.0, "width": printable_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
            })
            
            task_rows = 8
            task_row_h = (bot_h - 15.0) / task_rows
            for r in range(1, task_rows):
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x_start + 5.0, "y": y_start + r * task_row_h, "width": printable_w - 10.0, "height": 0.0},
                    "properties": {"stroke_color": line_color, "stroke_width": 0.5, "fill_color": "none"}
                })
                vector_objects.append({
                    "shape_type": "rectangle",
                    "geometry": {"x": x_start + 8.0, "y": y_start + r * task_row_h + 3.0, "width": 8.0, "height": 8.0},
                    "properties": {"stroke_color": theme_color, "stroke_width": 0.75, "fill_color": "none"}
                })
                
        elif layout == "appointment_planner" or layout == "appointment_layouts":
            table_w = printable_w
            col_w = [table_w * 0.15, table_w * 0.35, table_w * 0.25, table_w * 0.25]
            
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": y_start, "width": table_w, "height": content_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            row_h = content_h / 14
            headers = ["Time", "Client / Description", "Service Type", "Contact Info"]
            curr_x = x_start
            for c in range(4):
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": headers[c],
                    "geometry": {"x": curr_x, "y": content_y_end - row_h + 3.0, "width": col_w[c], "height": 10.0},
                    "properties": {"font_size": 8.0, "color": theme_color, "alignment": "center"}
                })
                if c > 0:
                    vector_objects.append({
                        "shape_type": "line",
                        "geometry": {"x": curr_x, "y": y_start, "width": 0.0, "height": content_h},
                        "properties": {"stroke_color": line_color, "stroke_width": 0.75, "fill_color": "none"}
                    })
                curr_x += col_w[c]
                
            for r in range(13):
                ry = y_start + r * row_h
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x_start, "y": ry, "width": table_w, "height": 0.0},
                    "properties": {"stroke_color": line_color, "stroke_width": 0.5, "fill_color": "none"}
                })
                hour = 8 + (12 - r)
                hour_str = f"{hour:02d}:00" if hour < 12 else (f"{hour:02d}:00" if hour == 12 else f"{hour-12:02d}:00")
                if hour < 12:
                    hour_str += " AM"
                else:
                    hour_str += " PM"
                vector_objects.append({
                    "shape_type": "text_block",
                    "text": hour_str,
                    "geometry": {"x": x_start + 2.0, "y": ry + 3.0, "width": col_w[0] - 4.0, "height": 8.0},
                    "properties": {"font_size": 6.5, "color": text_color, "alignment": "center"}
                })
                
        else:
            # CUSTOM PLANNER TEMPLATE (DEFAULT / BLANK DOT GRID)
            notes_h = 100.0
            vector_objects.append({
                "shape_type": "rectangle",
                "geometry": {"x": x_start, "y": y_start, "width": printable_w, "height": notes_h},
                "properties": {"stroke_color": theme_color, "stroke_width": 1.0, "fill_color": "none"}
            })
            vector_objects.append({
                "shape_type": "text_block",
                "text": "  NOTES / IDEAS",
                "geometry": {"x": x_start, "y": y_start + notes_h - 12.0, "width": printable_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": theme_color, "alignment": "left"}
            })
            for r in range(1, 4):
                vector_objects.append({
                    "shape_type": "line",
                    "geometry": {"x": x_start + 5.0, "y": y_start + r * (notes_h / 4.0), "width": printable_w - 10.0, "height": 0.0},
                    "properties": {"stroke_color": line_color, "stroke_width": 0.5, "fill_color": "none"}
                })
                
            grid_h = content_h - notes_h - 10.0
            grid_y = y_start + notes_h + 10.0
            spacing = 15.0
            dot_sz = 1.5
            r_dot = dot_sz / 2.0
            
            y = grid_y + 10.0
            while y <= grid_y + grid_h - 10.0:
                x = x_start + 10.0
                while x <= x_end - 10.0:
                    vector_objects.append({
                        "shape_type": "ellipse",
                        "geometry": {"x": x - r_dot, "y": y - r_dot, "width": dot_sz, "height": dot_sz},
                        "properties": {"fill_color": line_color, "stroke_color": line_color, "stroke_width": 0.0}
                    })
                    x += spacing
                y += spacing
                
        # Optional page numbers at bottom
        show_page_number = settings.get("show_page_number", True)
        if show_page_number:
            align = "right" if is_odd else "left"
            vector_objects.append({
                "shape_type": "text_block",
                "text": str(page.page_number),
                "geometry": {"x": x_start, "y": y_start - 18.0, "width": printable_w, "height": 10.0},
                "properties": {"font_size": 8.0, "color": text_color, "alignment": align}
            })
            
        return vector_objects
