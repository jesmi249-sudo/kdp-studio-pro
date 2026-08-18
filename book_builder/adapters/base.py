from abc import ABC, abstractmethod
from typing import Any

class IBookTypeAdapter(ABC):
    @abstractmethod
    def convert_spec(self, project: Any, spec: Any) -> Any:
        """
        Converts the AI BookSpecification into a concrete command
        for the specific book type.
        
        Args:
            project: The BookProject instance.
            spec: The ai_agents.models.BookSpecification instance.
            
        Returns:
            A Command instance (e.g., GenerateStorybookPagesCommand, GenerateColoringPagesCommand)
        """
        pass
