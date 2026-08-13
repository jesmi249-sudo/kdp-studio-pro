import unittest
import os
from models.planner import PlannerProject, PlannerPage, MasterPage
from models.planner_object import PlannerObject
from core.variable_engine import VariableEngine
from core.calendar_engine import CalendarEngine
from core.layout_engine import LayoutEngine
from core.master_page import MasterPageEngine
from core.planner_engine import PlannerEngine

class TestPlannerStudio(unittest.TestCase):
    
    def test_variable_engine(self):
        ctx = "2026-07-30"
        res = VariableEngine.resolve_text("Date: {DATE} - {DAY_NAME}", 5, ctx)
        self.assertEqual(res, "Date: 2026-07-30 - Thursday")
        
        res_page = VariableEngine.resolve_text("Page {PAGE_NUMBER}", 10)
        self.assertEqual(res_page, "Page 10")
        
    def test_calendar_engine(self):
        # Daily range
        daily = CalendarEngine.generate_daily_range("2026-01-01", "2026-01-03")
        self.assertEqual(len(daily), 3)
        self.assertEqual(daily[2], "2026-01-03")
        
        # Monthly range
        monthly = CalendarEngine.generate_monthly_range(2026, 1, 2)
        self.assertEqual(len(monthly), 2)
        self.assertEqual(monthly[0]["month"], 1)
        self.assertEqual(monthly[1]["month"], 2)

    def test_layout_engine(self):
        tracker = LayoutEngine.create_habit_tracker(10, 10, 200, 50, days=31)
        self.assertEqual(tracker.type, "habit_tracker")
        self.assertEqual(tracker.columns, 31)

    def test_master_page_engine(self):
        project = PlannerProject()
        
        master = MasterPage(id="m1")
        master.objects.append(PlannerObject(type="text", text="Header"))
        project.master_pages.append(master)
        
        page = PlannerPage(master_page_id="m1")
        page.objects.append(PlannerObject(type="text", text="Body"))
        project.pages.append(page)
        
        merged = MasterPageEngine.get_merged_objects(page, project)
        self.assertEqual(len(merged), 2)
        
    def test_export_pdf(self):
        project = PlannerProject(name="Test Planner")
        page = PlannerPage(page_number=1)
        page.objects.append(PlannerObject(type="text", text="Hello PDF", x=100, y=100))
        project.pages.append(page)
        
        output = "test_planner.pdf"
        success = PlannerEngine.export_pdf(project, output)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output))
        
        if os.path.exists(output):
            os.remove(output)

    def test_database_integration(self):
        from database.db import db
        # Create dummy project
        project = PlannerProject(name="DB Test Planner")
        page = PlannerPage(page_number=1)
        page.objects.append(PlannerObject(type="text", text="DB Object"))
        project.pages.append(page)
        
        # Save
        success = db.save_planner_project(project)
        self.assertTrue(success)
        self.assertIsNotNone(project.id)
        
        # Load
        loaded_project = db.load_planner_project(project.id)
        self.assertIsNotNone(loaded_project)
        self.assertEqual(loaded_project.name, "DB Test Planner")
        self.assertEqual(len(loaded_project.pages), 1)
        self.assertEqual(loaded_project.pages[0].objects[0].text, "DB Object")
        
        # Cleanup
        db.delete_project(project.id)

if __name__ == '__main__':
    unittest.main()
