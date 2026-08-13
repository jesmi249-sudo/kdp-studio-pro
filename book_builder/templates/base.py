from abc import ABC, abstractmethod
from typing import List, Dict, Any
from book_builder.models.page import Page

class ITemplateGenerator(ABC):
    """Interface defining the contract for page template layout generation."""
    @abstractmethod
    def generate_page_objects(self, page: Page, template_type: str, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates a list of vector objects (lines, rectangles, ellipses) to populate
        on the given Page instance. No rendering logic.
        """
        pass
