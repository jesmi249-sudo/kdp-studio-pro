import datetime
from core.variable_registry import registry
from core.logger import get_logger

logger = get_logger(__name__)

class VariableEngine:
    """
    Replaces static tags like {DATE} and {PAGE_NUMBER} with contextual data.
    """
    
    @staticmethod
    def resolve_text(text: str, page_number: int, date_context: str = None) -> str:
        """
        Parses text and replaces variables.
        :param text: Raw string (e.g. "Page {PAGE_NUMBER} - {DATE}")
        :param page_number: Current page integer
        :param date_context: ISO date string (YYYY-MM-DD) if applicable
        """
        if not text or "{" not in text:
            return text
            
        # 1. Resolve Globals
        globals_dict = registry.get_globals()
        for k, v in globals_dict.items():
            token = f"{{{k}}}"
            if token in text:
                text = text.replace(token, v)
                
        # 2. Resolve Page Context
        text = text.replace("{PAGE_NUMBER}", str(page_number))
        
        # 3. Resolve Date Context
        if date_context:
            try:
                dt = datetime.date.fromisoformat(date_context)
                
                # Standard tags
                text = text.replace("{DATE}", dt.strftime("%Y-%m-%d"))
                text = text.replace("{DAY}", str(dt.day))
                text = text.replace("{DAY_NAME}", dt.strftime("%A"))
                text = text.replace("{MONTH}", str(dt.month))
                text = text.replace("{MONTH_NAME}", dt.strftime("%B"))
                text = text.replace("{YEAR}", str(dt.year))
                
            except ValueError as e:
                logger.error(f"Invalid date_context format for VariableEngine: {date_context}. Expected YYYY-MM-DD.")
                
        return text
