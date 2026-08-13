from typing import List, Optional
from book_builder.commands.base import Command, HistoryStack
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from core.logger import get_logger

logger = get_logger(__name__)

class CommandManager:
    """Orchestrator managing transactional command histories and event broadcasts."""
    def __init__(self, max_depth: int = 50) -> None:
        self.undo_stack = HistoryStack(max_depth)
        self.redo_stack = HistoryStack(max_depth)
        self.event_bus = EventBus()

    def execute(self, command: Command) -> bool:
        """Executes the given command, clears redo stack, and registers it in history."""
        try:
            logger.debug(f"CommandManager: executing '{command.get_description()}'")
            if command.execute():
                self.undo_stack.push(command)
                self.redo_stack.clear()
                
                # Notify the workspace that layouts have updated
                self.event_bus.publish(
                    Event("PROJECT_MODIFIED", "CommandManager", {"description": command.get_description()})
                )
                return True
        except Exception as e:
            logger.error(f"Failed to execute command '{command.get_description()}': {e}")
        return False

    def undo(self) -> bool:
        """Pops and reverts the most recent command, transferring it to the redo stack."""
        if self.undo_stack.is_empty():
            logger.warning("Undo requested but undo stack is empty.")
            return False
            
        command = self.undo_stack.pop()
        try:
            logger.debug(f"CommandManager: undoing '{command.get_description()}'")
            if command.undo():
                self.redo_stack.push(command)
                self.event_bus.publish(
                    Event("PROJECT_MODIFIED", "CommandManager", {"action": "undo", "description": command.get_description()})
                )
                return True
        except Exception as e:
            logger.error(f"Failed to undo command '{command.get_description()}': {e}")
        return False

    def redo(self) -> bool:
        """Re-applies the most recently undone command, returning it to the undo stack."""
        if self.redo_stack.is_empty():
            logger.warning("Redo requested but redo stack is empty.")
            return False
            
        command = self.redo_stack.pop()
        try:
            logger.debug(f"CommandManager: redoing '{command.get_description()}'")
            if command.redo():
                self.undo_stack.push(command)
                self.event_bus.publish(
                    Event("PROJECT_MODIFIED", "CommandManager", {"action": "redo", "description": command.get_description()})
                )
                return True
        except Exception as e:
            logger.error(f"Failed to redo command '{command.get_description()}': {e}")
        return False


class Transaction(Command):
    """Composite command allowing multiple operations to succeed or fail as a single unit."""
    def __init__(self, description: str = "Grouped Transaction") -> None:
        self.description = description
        self.sub_commands: List[Command] = []
        self._completed_commands: List[Command] = []

    def add(self, command: Command) -> None:
        """Appends a command to the transaction stack."""
        self.sub_commands.append(command)

    def execute(self) -> bool:
        """Executes all sub-commands sequentially. Rolls back complete list on failure."""
        self._completed_commands.clear()
        for cmd in self.sub_commands:
            try:
                if cmd.execute():
                    self._completed_commands.append(cmd)
                else:
                    logger.error(f"Sub-command '{cmd.get_description()}' failed inside transaction. Initiating rollback...")
                    self.rollback()
                    return False
            except Exception as e:
                logger.error(f"Sub-command execution exception in transaction: {e}. Initiating rollback...")
                self.rollback()
                return False
        return True

    def undo(self) -> bool:
        """Undoes all completed sub-commands in reverse order."""
        for cmd in reversed(self.sub_commands):
            try:
                cmd.undo()
            except Exception as e:
                logger.error(f"Failed to undo sub-command '{cmd.get_description()}' in transaction undo loop: {e}")
                return False
        return True

    def redo(self) -> bool:
        """Redoes all sub-commands sequentially."""
        for cmd in self.sub_commands:
            try:
                cmd.redo()
            except Exception as e:
                logger.error(f"Failed to redo sub-command '{cmd.get_description()}' in transaction redo loop: {e}")
                return False
        return True

    def rollback(self) -> None:
        """Rolls back only completed sub-commands on a partial transaction failure."""
        for cmd in reversed(self._completed_commands):
            try:
                cmd.undo()
            except Exception as rollback_err:
                logger.critical(f"Critical: failed to rollback sub-command '{cmd.get_description()}': {rollback_err}")

    def get_description(self) -> str:
        return self.description
