from typing import Any
from .base import IBookTypeAdapter
from book_builder.commands.storybook_commands import GenerateStorybookPagesCommand

class StorybookAdapter(IBookTypeAdapter):
    def convert_spec(self, project: Any, spec: Any) -> Any:
        pages_data = []
        for page_spec in spec.pages:
            layout = page_spec.layout_type
            
            p_dict = {
                "layout": layout,
                "text": page_spec.text_content or "",
            }
            if page_spec.image_prompt:
                p_dict["image_prompt"] = page_spec.image_prompt
            if page_spec.image_reference:
                p_dict["image_reference"] = page_spec.image_reference.model_dump()
                
            pages_data.append(p_dict)
            
        storybook_data = project.custom_settings.get("storybook_data", {})
        storybook_data["pages"] = pages_data
        
        if "global_settings" not in storybook_data:
            storybook_data["global_settings"] = {}
        storybook_data["global_settings"]["style_prompt"] = spec.global_style_instructions
        
        project.custom_settings["storybook_data"] = storybook_data
        
        return GenerateStorybookPagesCommand(project)
