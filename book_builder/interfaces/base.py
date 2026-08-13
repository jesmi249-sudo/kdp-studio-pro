from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from book_builder.interfaces.core import IStudio
from book_builder.interfaces.services import IRenderer, IPlugin, IBackgroundTask

class BaseStudio(IStudio, ABC):
    """Abstract base class for editor studio views."""
    def __init__(self, master: Any, **kwargs: Any) -> None:
        self.master = master
        self.active_project: Optional[Any] = None
        self.app_context: Optional[Any] = None

    def initialize(self, app_context: Any) -> None:
        self.app_context = app_context

    def load_project(self, project: Any) -> None:
        self.active_project = project

    def cleanup(self) -> None:
        self.active_project = None


class BaseService(ABC):
    """Abstract base class for core business service layer."""
    def __init__(self) -> None:
        pass


class BaseCommand(ABC):
    """Abstract base class for event history state mutations."""
    @abstractmethod
    def execute(self) -> bool:
        """Runs the command operation."""
        pass

    @abstractmethod
    def undo(self) -> bool:
        """Rollbacks the command changes."""
        pass

    @abstractmethod
    def redo(self) -> bool:
        """Re-applies the undone changes."""
        pass


class BaseJob(IBackgroundTask, ABC):
    """Abstract base class for prioritize-based background worker tasks."""
    def __init__(self, priority: int = 1) -> None:
        self.priority = priority


class BaseRenderer(IRenderer, ABC):
    """Abstract base class for document compilers."""
    pass


class BasePlugin(IPlugin, ABC):
    """Abstract base class for external extensions."""
    pass
