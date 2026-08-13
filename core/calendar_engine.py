import datetime
import calendar
from typing import List, Dict, Any
from core.logger import get_logger

logger = get_logger(__name__)

class CalendarEngine:
    
    @staticmethod
    def generate_daily_range(start_date: str, end_date: str) -> List[str]:
        """Generates a list of ISO date strings for every day in the range (inclusive)."""
        dates = []
        try:
            start = datetime.date.fromisoformat(start_date)
            end = datetime.date.fromisoformat(end_date)
            delta = datetime.timedelta(days=1)
            
            curr = start
            while curr <= end:
                dates.append(curr.isoformat())
                curr += delta
        except Exception as e:
            logger.error(f"Error generating daily range: {e}")
            
        return dates

    @staticmethod
    def generate_weekly_range(start_date: str, end_date: str, start_of_week: int = calendar.MONDAY) -> List[Dict[str, str]]:
        """
        Generates a list of dictionaries representing weeks.
        Returns: [{"week_start": "YYYY-MM-DD", "week_end": "YYYY-MM-DD"}, ...]
        """
        weeks = []
        try:
            start = datetime.date.fromisoformat(start_date)
            end = datetime.date.fromisoformat(end_date)
            
            # Adjust start date to the beginning of its week
            while start.weekday() != start_of_week:
                start -= datetime.timedelta(days=1)
                
            curr = start
            while curr <= end:
                week_end = curr + datetime.timedelta(days=6)
                weeks.append({
                    "week_start": curr.isoformat(),
                    "week_end": week_end.isoformat(),
                    "context_date": curr.isoformat() # Primary date context for the page
                })
                curr += datetime.timedelta(days=7)
        except Exception as e:
            logger.error(f"Error generating weekly range: {e}")
            
        return weeks
        
    @staticmethod
    def generate_monthly_range(start_year: int, start_month: int, count: int) -> List[Dict[str, Any]]:
        """
        Generates data for 'count' months.
        Returns grid data for monthly planners.
        """
        months = []
        y, m = start_year, start_month
        
        for _ in range(count):
            # context date is the 1st of the month
            context = datetime.date(y, m, 1).isoformat()
            
            # Get grid (list of weeks, which are lists of days 0=empty)
            cal = calendar.monthcalendar(y, m)
            
            months.append({
                "context_date": context,
                "year": y,
                "month": m,
                "grid": cal
            })
            
            m += 1
            if m > 12:
                m = 1
                y += 1
                
        return months
