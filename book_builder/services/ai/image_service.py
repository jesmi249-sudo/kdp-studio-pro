import os
from datetime import datetime, timezone
from typing import Optional
import logging

from book_builder.services.ai.manager import AIManager
from book_builder.services.ai.schemas import GeneratedImageReference
from book_builder.services.ai.providers.image_interfaces import ImageGenerationRequest
from book_builder.services.ai.image_validator import ImageQualityValidator
from core.asset_manager import AssetManager

logger = logging.getLogger(__name__)

class ImageGenerationService:
    """
    Orchestrates the image generation lifecycle:
    Provider -> Quality Validator -> AssetManager -> Project Reference Update.
    """
    
    def __init__(self, ai_manager: AIManager, asset_manager: AssetManager):
        self.ai_manager = ai_manager
        self.asset_manager = asset_manager

    def generate_and_ingest(self, reference: GeneratedImageReference, aspect_ratio: str, 
                            category: str = "Storybook Illustrations", 
                            project_id: Optional[int] = None) -> GeneratedImageReference:
        """
        Executes the generation lifecycle. Updates the passed reference in place and returns it.
        """
        try:
            # 1. Setup
            reference.status = "generating"
            provider = self.ai_manager.get_image_provider()
            
            req = ImageGenerationRequest(
                prompt=reference.image_prompt,
                aspect_ratio=aspect_ratio,
                provider_name=reference.provider,
                model_name=reference.model
            )
            
            # 2. Generate (Blocking, should be run in TaskQueue)
            logger.info(f"Generating image for prompt: {req.prompt[:30]}...")
            response = provider.generate_image(req)
            
            if not response.success or not response.local_temp_path:
                reference.status = "failed"
                raise RuntimeError(response.error_message or "Unknown provider failure")
                
            reference.status = "generated"
            temp_path = response.local_temp_path
            
            # 3. Validate
            reference.status = "validating"
            is_valid, val_error = ImageQualityValidator.validate(temp_path, aspect_ratio)
            if not is_valid:
                reference.status = "failed"
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise RuntimeError(f"Quality validation failed: {val_error}")
                
            # 4. Ingest into AssetManager
            asset = self.asset_manager.import_asset(temp_path, category=category, project_id=project_id)
            if not asset:
                reference.status = "failed"
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise RuntimeError("Failed to ingest asset into AssetManager")
                
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            # 5. Update Reference
            # If regenerating, preserve the old asset in history
            if reference.asset_id:
                reference.generation_history.append(reference.asset_id)
                
            reference.asset_id = asset.id
            reference.image_path = asset.file_path
            reference.status = "ready"
            reference.creation_timestamp = datetime.now(timezone.utc)
            
            return reference
            
        except Exception as e:
            reference.status = "failed"
            logger.error(f"ImageGenerationService failed: {str(e)}")
            raise e
