from typing import List
from book_builder.commands.base import Command
from book_builder.models.book import BookProject
from book_builder.commands.storybook_commands import GenerateStorybookPagesCommand
from book_builder.services.ai.schemas import BookSpecification
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from core.logger import get_logger

logger = get_logger(__name__)

class ApplyBookSpecificationCommand(Command):
    """
    Adapter command that takes an AI-generated BookSpecification,
    converts it into the format expected by the existing generators,
    and delegates to them.
    
    It delegates to the correct book type adapter via the get_adapter factory.
    """
    def __init__(self, project: BookProject, spec: BookSpecification) -> None:
        self.project = project
        self.spec = spec
        self.event_bus = EventBus()
        self.delegate_command = None

    def execute(self) -> bool:
        logger.info(f"ApplyBookSpecificationCommand: converting spec for '{self.project.name}'")
        try:
            # Update basic project settings that came from the AI plan
            self.project.name = self.spec.title
            
            # Save the raw plan for future editing
            self.project.custom_settings['ai_plan'] = self.spec.model_dump()
            
            from book_builder.adapters import get_adapter
            adapter = get_adapter(self.spec.book_type)
            self.delegate_command = adapter.convert_spec(self.project, self.spec)
            
            success = self.delegate_command.execute()
            if success:
                self.event_bus.publish(
                    Event("PROJECT_MODIFIED", "ApplyBookSpecificationCommand", {"project_id": str(self.project.id)})
                )
            return success
                
        except Exception as e:
            logger.error(f"ApplyBookSpecificationCommand: execution failed: {e}")
            return False


    def undo(self) -> bool:
        if self.delegate_command:
            success = self.delegate_command.undo()
            if success:
                self.event_bus.publish(
                    Event("PROJECT_MODIFIED", "ApplyBookSpecificationCommand", {"project_id": str(self.project.id)})
                )
            return success
        return False

    def redo(self) -> bool:
        if self.delegate_command:
            success = self.delegate_command.redo()
            if success:
                self.event_bus.publish(
                    Event("PROJECT_MODIFIED", "ApplyBookSpecificationCommand", {"project_id": str(self.project.id)})
                )
            return success
        return False

    def get_description(self) -> str:
        return f"Apply AI Book Specification"
