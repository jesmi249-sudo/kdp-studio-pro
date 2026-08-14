from typing import Callable, Any, Optional
import logging

from book_builder.jobs.base import Task, CancellationToken, ProgressEvent
from book_builder.services.ai.schemas import GeneratedImageReference
from book_builder.services.ai.image_service import ImageGenerationService

logger = logging.getLogger(__name__)

class GenerateImageTask(Task):
    """
    Background task to generate an AI image for a specific page layout block.
    """
    def __init__(self, 
                 reference: GeneratedImageReference, 
                 aspect_ratio: str,
                 image_service: ImageGenerationService,
                 category: str = "Storybook Illustrations",
                 project_id: Optional[int] = None,
                 priority: int = 10):
        super().__init__(priority=priority)
        self.reference = reference
        self.aspect_ratio = aspect_ratio
        self.image_service = image_service
        self.category = category
        self.project_id = project_id

    def execute(self, progress_callback: Callable[[ProgressEvent], None], token: CancellationToken) -> Any:
        progress_callback(ProgressEvent(self.id, 0.1, "Starting image generation..."))
        
        if token.is_cancelled():
            return
            
        try:
            # The generation call is synchronous and can take 10-30 seconds.
            # We pass the token down if the provider supports it in the future, 
            # but for now it's blocking on the HTTP request.
            progress_callback(ProgressEvent(self.id, 0.4, "Waiting for provider..."))
            
            result = self.image_service.generate_and_ingest(
                reference=self.reference,
                aspect_ratio=self.aspect_ratio,
                category=self.category,
                project_id=self.project_id
            )
            
            progress_callback(ProgressEvent(self.id, 1.0, "Generation complete."))
            return result
            
        except Exception as e:
            logger.error(f"Task {self.id} failed: {e}")
            raise
