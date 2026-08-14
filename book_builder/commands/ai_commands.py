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
    
    Currently supports mapping "storybook" specifications to 
    GenerateStorybookPagesCommand without duplicating rendering math.
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
            
            # Save the raw plan for future editing (Human in the loop / Persistence)
            self.project.custom_settings['ai_plan'] = self.spec.model_dump()
            
            # Map BookSpecification to the legacy dictionary format based on book_type
            if self.spec.book_type == "storybook":
                return self._apply_storybook()
            else:
                logger.error(f"Book type '{self.spec.book_type}' is not yet supported by the adapter.")
                return False
                
        except Exception as e:
            logger.error(f"ApplyBookSpecificationCommand: execution failed: {e}")
            return False

    def _apply_storybook(self) -> bool:
        """Adapts the AI spec to the format required by StorybookTemplateGenerator."""
        pages_data = []
        for page_spec in self.spec.pages:
            # Map layout strings to what the generator understands
            layout = page_spec.layout_type
            
            # Build the dict expected by GenerateStorybookPagesCommand
            p_dict = {
                "layout": layout,
                "text": page_spec.text_content or "",
            }
            if page_spec.image_prompt:
                p_dict["image_prompt"] = page_spec.image_prompt
            if page_spec.image_reference:
                p_dict["image_reference"] = page_spec.image_reference.model_dump()
                
            pages_data.append(p_dict)
            
        storybook_data = self.project.custom_settings.get("storybook_data", {})
        storybook_data["pages"] = pages_data
        
        # We can also store global style instructions if the UI/generator needs it later
        if "global_settings" not in storybook_data:
            storybook_data["global_settings"] = {}
        storybook_data["global_settings"]["style_prompt"] = self.spec.global_style_instructions
        
        self.project.custom_settings["storybook_data"] = storybook_data
        
        # Delegate to the deterministic generator
        self.delegate_command = GenerateStorybookPagesCommand(self.project)
        success = self.delegate_command.execute()
        
        if success:
            self.event_bus.publish(
                Event("PROJECT_MODIFIED", "ApplyBookSpecificationCommand", {"project_id": str(self.project.id)})
            )
        return success

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
