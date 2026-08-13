from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List

class IBookBuilder(ABC):
    """Core interface for the central Book Builder Engine."""
    
    @abstractmethod
    def create_project(self, name: str, book_type: str, settings: Dict[str, Any]) -> Any:
        """Initializes a new book project model."""
        pass

    @abstractmethod
    def load_project(self, project_id: int) -> Any:
        """Loads a book project state from the database."""
        pass

    @abstractmethod
    def save_project(self) -> bool:
        """Persists the active project model state."""
        pass

    @abstractmethod
    def close_project(self) -> None:
        """Closes the current project session and releases locks."""
        pass

    @abstractmethod
    def register_studio(self, studio_type: str, studio_instance: Any) -> None:
        """Registers a studio editor module with the engine."""
        pass

    @abstractmethod
    def execute_command(self, command: Any) -> bool:
        """Dispatches and executes a command on the active project."""
        pass

    @abstractmethod
    def get_active_project(self) -> Optional[Any]:
        """Returns the currently loaded project model, if any."""
        pass


class IStudio(ABC):
    """Core lifecycle interface that every editor studio module must implement."""
    
    @abstractmethod
    def initialize(self, app_context: Any) -> None:
        """Configures paths, actions, and menu hooks during startup."""
        pass

    @abstractmethod
    def load_project(self, project: Any) -> None:
        """Loads a project state into the studio's editor workspace widgets."""
        pass

    @abstractmethod
    def save_project(self) -> Any:
        """Compiles the studio editor canvas widgets back into a BookProject model."""
        pass

    @abstractmethod
    def generate_pages(self, options: Dict[str, Any]) -> None:
        """Executes automated page generation templates."""
        pass

    @abstractmethod
    def validate(self) -> Any:
        """Performs localized compliance checks on layout elements."""
        pass

    @abstractmethod
    def preview(self, page_number: int) -> Any:
        """Returns a low-resolution rendering of the specified page for UI display."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Cleans up widgets and disposes of temporary layout objects."""
        pass
