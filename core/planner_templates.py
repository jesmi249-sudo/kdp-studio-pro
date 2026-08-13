from models.planner import PlannerProject, MasterPage, PlannerPage
from core.layout_engine import LayoutEngine

class PlannerTemplates:
    @staticmethod
    def create_blank_project() -> PlannerProject:
        project = PlannerProject(name="New Blank Planner")
        
        # Create a default Master Page
        master = MasterPage(name="Default Master", type="right")
        project.master_pages.append(master)
        
        # Create a single blank page linked to the master
        page = PlannerPage(page_number=1, master_page_id=master.id)
        project.pages.append(page)
        
        return project

    @staticmethod
    def create_daily_planner(days: int = 365) -> PlannerProject:
        project = PlannerProject(name="Daily Planner")
        
        # Create Left/Right masters
        left_master = MasterPage(name="Left Page", type="left")
        right_master = MasterPage(name="Right Page", type="right")
        
        # Add a date variable to the masters
        date_txt = LayoutEngine.create_text("{DAY_NAME}, {MONTH_NAME} {DAY}, {YEAR}", x=50, y=50, size=18)
        right_master.objects.append(date_txt)
        left_master.objects.append(date_txt)
        
        project.master_pages.extend([left_master, right_master])
        
        # We don't generate 365 pages in memory initially to save RAM.
        # This is just a scaffold.
        for i in range(1, 4):
            master_id = right_master.id if i % 2 != 0 else left_master.id
            page = PlannerPage(page_number=i, master_page_id=master_id)
            project.pages.append(page)
            
        return project
