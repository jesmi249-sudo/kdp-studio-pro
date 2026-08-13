from models.planner_object import PlannerObject

class LayoutEngine:
    """Generates parameterized primitive and composite planner objects."""
    
    @staticmethod
    def create_text(text: str, x: float, y: float, size: float = 12) -> PlannerObject:
        return PlannerObject(
            type="text",
            text=text,
            x=x,
            y=y,
            font_size=size
        )
        
    @staticmethod
    def create_rect(x: float, y: float, w: float, h: float, fill: str = "none") -> PlannerObject:
        return PlannerObject(
            type="rect",
            x=x,
            y=y,
            width=w,
            height=h,
            fill_color=fill
        )

    @staticmethod
    def create_table(x: float, y: float, w: float, h: float, rows: int, cols: int) -> PlannerObject:
        return PlannerObject(
            type="table",
            x=x,
            y=y,
            width=w,
            height=h,
            rows=rows,
            columns=cols
        )
        
    # --- Planner Object Library (Stage 6) ---
    
    @staticmethod
    def create_habit_tracker(x: float, y: float, width: float, height: float, days: int = 31) -> PlannerObject:
        return PlannerObject(type="habit_tracker", x=x, y=y, width=width, height=height, rows=1, columns=days)
        
    @staticmethod
    def create_dot_grid(x: float, y: float, width: float, height: float, spacing: float = 10.0) -> PlannerObject:
        return PlannerObject(type="dot_grid", x=x, y=y, width=width, height=height, spacing=spacing)
        
    @staticmethod
    def create_ruled_lines(x: float, y: float, width: float, height: float, spacing: float = 15.0) -> PlannerObject:
        return PlannerObject(type="ruled_lines", x=x, y=y, width=width, height=height, spacing=spacing)
        
    @staticmethod
    def create_checkbox(x: float, y: float, size: float = 15.0) -> PlannerObject:
        return PlannerObject(type="checkbox", x=x, y=y, width=size, height=size)

    @staticmethod
    def create_budget_table(x: float, y: float, width: float, height: float) -> PlannerObject:
        return PlannerObject(type="budget_table", x=x, y=y, width=width, height=height, rows=10, columns=4)

    @staticmethod
    def create_expense_tracker(x: float, y: float, width: float, height: float) -> PlannerObject:
        return PlannerObject(type="expense_tracker", x=x, y=y, width=width, height=height, rows=15, columns=4)

    @staticmethod
    def create_meal_planner(x: float, y: float, width: float, height: float) -> PlannerObject:
        return PlannerObject(type="meal_planner", x=x, y=y, width=width, height=height, rows=7, columns=4)

    @staticmethod
    def create_appointment_grid(x: float, y: float, width: float, height: float) -> PlannerObject:
        return PlannerObject(type="appointment_grid", x=x, y=y, width=width, height=height, rows=14, columns=2)

    @staticmethod
    def create_graph_paper(x: float, y: float, width: float, height: float, spacing: float = 10.0) -> PlannerObject:
        return PlannerObject(type="graph_paper", x=x, y=y, width=width, height=height, spacing=spacing)
        
    @staticmethod
    def create_calendar_block(x: float, y: float, width: float, height: float) -> PlannerObject:
        return PlannerObject(type="calendar_block", x=x, y=y, width=width, height=height, rows=6, columns=7)
