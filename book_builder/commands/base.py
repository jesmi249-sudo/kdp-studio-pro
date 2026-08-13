from abc import ABC, abstractmethod
from typing import List

class Command(ABC):
    """Abstract Base Class for all undoable structural operations modifying project models."""
    
    @abstractmethod
    def execute(self) -> bool:
        """Executes the command mutations. Returns True if successful."""
        pass

    @abstractmethod
    def undo(self) -> bool:
        """Rollbacks the mutations applied in execute(). Returns True if successful."""
        pass

    @abstractmethod
    def redo(self) -> bool:
        """Re-executes the command after an undo. Returns True if successful."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Returns a user-facing description of the operation (e.g. 'Add Page 5')."""
        pass


class HistoryStack:
    """Bounded command stack for undo/redo memory capping."""
    def __init__(self, max_depth: int = 50) -> None:
        self.max_depth = max_depth
        self._stack: List[Command] = []

    def push(self, command: Command) -> None:
        """Pushes a command onto the stack, evicting oldest item if max depth exceeded."""
        self._stack.append(command)
        if len(self._stack) > self.max_depth:
            self._stack.pop(0)

    def pop(self) -> Command:
        """Pops the most recent command from the stack."""
        return self._stack.pop()

    def clear(self) -> None:
        """Clears the stack contents."""
        self._stack.clear()

    def is_empty(self) -> bool:
        """Returns True if the stack contains no commands."""
        return len(self._stack) == 0

    def size(self) -> int:
        """Returns the number of commands in the stack."""
        return len(self._stack)
