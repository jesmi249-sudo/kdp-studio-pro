from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel

class ImageGenerationRequest(BaseModel):
    prompt: str
    aspect_ratio: str  # "square", "landscape", "portrait"
    style_preset: Optional[str] = None
    provider_name: Optional[str] = None
    model_name: Optional[str] = None

class ImageGenerationResponse(BaseModel):
    success: bool
    local_temp_path: Optional[str] = None
    error_message: Optional[str] = None
    token_cost_estimate: float = 0.0

class IImageProvider(ABC):
    """
    Abstract interface for AI image generation providers.
    """
    
    @abstractmethod
    def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """
        Synchronously generates an image, downloads it to a temp file, and returns the response.
        Raises AIError if an unrecoverable provider error occurs.
        """
        pass
