import logging
from typing import Optional, Dict, Any

from book_builder.services.ai.manager import AIManager
from book_builder.services.ai.models import AIRequest
from book_builder.services.ai.schemas import BookSpecification
from book_builder.services.ai.errors import AIError

logger = logging.getLogger(__name__)

class AIBookPlannerService:
    """
    Backend service responsible for converting user ideas into structured 
    BookSpecifications via the AI Manager.
    """
    def __init__(self, ai_manager: AIManager):
        self.ai_manager = ai_manager

    def generate_book_plan(self, prompt: str, book_type: str = "storybook", 
                           page_count: int = 24, trim_width: float = 8.5, 
                           trim_height: float = 11.0) -> BookSpecification:
        """
        Sends a request to the configured AI Provider to generate a BookSpecification.
        Raises AIErrors on failure.
        """
        logger.info(f"AIBookPlannerService: generating {page_count}-page {book_type} plan.")
        
        system_instruction = (
            f"You are a professional KDP Book Creator. "
            f"Design a highly engaging, age-appropriate {book_type}."
            f"\nConstraints:"
            f"\n- MUST have exactly {page_count} pages."
            f"\n- Trim size is {trim_width}x{trim_height} inches."
            f"\n- Layout types must be standard (e.g. 'image_top', 'text_bottom', 'full_bleed_image', 'text_only', 'image_only')."
            f"\n- Provide a rich 'image_prompt' for every page that features artwork."
            f"\n- Text content must be proofread and suitable for the audience."
        )

        request = AIRequest(
            prompt=prompt,
            system_instruction=system_instruction,
            structured_schema=BookSpecification,
            temperature=0.7,
            max_tokens=None # Allow the model to decide or use defaults, as 24 pages might be large
        )

        response = self.ai_manager.generate_structured_content(request)
        
        if not response.success:
            raise AIError(f"Failed to generate book plan: {response.error_message}")
            
        spec = response.structured_data
        
        # Ensure the provider respected the strict constraints
        if spec.page_count != page_count:
            logger.warning(f"AI returned {spec.page_count} pages, expected {page_count}. Correcting.")
            spec.page_count = page_count
            
        return spec
