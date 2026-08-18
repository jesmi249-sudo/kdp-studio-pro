from typing import Any
from .base import IBookTypeAdapter
from book_builder.commands.storybook_commands import GenerateStorybookPagesCommand

class ColoringAdapter(IBookTypeAdapter):
    """
    Adapter for Coloring Books. 
    Currently leverages the deterministic template engine's full-page image 
    capabilities by mapping to a 'full_image' layout with no text.
    """
    def convert_spec(self, project: Any, spec: Any) -> Any:
        pages_data = []
        for page_spec in spec.pages:
            # Force layout to full_image for coloring pages
            p_dict = {
                "layout": "full_image",
                "text": "", # Coloring books generally don't have body text on the coloring page
            }
            if page_spec.image_prompt:
                # We might append styles to the prompt like "line art, black and white"
                p_dict["image_prompt"] = f"black and white line art coloring page, {page_spec.image_prompt}"
            if page_spec.image_reference:
                p_dict["image_reference"] = page_spec.image_reference.model_dump()
                
            pages_data.append(p_dict)
            
        # Store in custom_settings for the Workspace tabs to pick up
        # We reuse 'storybook_data' key for now because BookWorkspaceView reads from it
        storybook_data = project.custom_settings.get("storybook_data", {})
        storybook_data["pages"] = pages_data
        
        if "global_settings" not in storybook_data:
            storybook_data["global_settings"] = {}
        # Ensure black and white style
        base_style = spec.global_style_instructions or ""
        storybook_data["global_settings"]["style_prompt"] = f"coloring book line art, {base_style}"
        
        project.custom_settings["storybook_data"] = storybook_data
        
        # We reuse the deterministic page generator since it places images correctly
        return GenerateStorybookPagesCommand(project)
