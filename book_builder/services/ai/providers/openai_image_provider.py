import os
import tempfile
import urllib.request
import logging

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from book_builder.services.ai.providers.image_interfaces import IImageProvider, ImageGenerationRequest, ImageGenerationResponse
from book_builder.services.ai.errors import (
    AIProviderUnavailableError, AIMissingCredentialsError, AIAuthenticationError,
    AIRateLimitError, AITimeoutError, AIError
)

logger = logging.getLogger(__name__)

class OpenAIImageProvider(IImageProvider):
    """
    OpenAI Provider implementing the IImageProvider interface (DALL-E 3).
    """
    
    def __init__(self, api_key: str = None, default_model: str = "dall-e-3"):
        if not OPENAI_AVAILABLE:
            raise AIProviderUnavailableError("OpenAI SDK is not installed.")
            
        if not api_key:
            raise AIMissingCredentialsError("OpenAI API key is missing. Please configure it in AI Settings.")
            
        self.api_key = api_key
        self.default_model = default_model
        self.client = OpenAI(api_key=self.api_key)

    def _handle_openai_error(self, e: Exception) -> None:
        """Maps OpenAI SDK exceptions to our standard AIError hierarchy."""
        if isinstance(e, openai.AuthenticationError):
            raise AIAuthenticationError("Invalid OpenAI API key.")
        elif isinstance(e, openai.RateLimitError):
            raise AIRateLimitError("OpenAI rate limit exceeded or insufficient quota.")
        elif isinstance(e, openai.APITimeoutError):
            raise AITimeoutError("OpenAI request timed out.")
        elif isinstance(e, openai.APIConnectionError):
            raise AIProviderUnavailableError("Failed to connect to OpenAI API.")
        elif isinstance(e, openai.OpenAIError):
            raise AIError(f"OpenAI error: {str(e)}")
        else:
            raise AIError(f"Unexpected error: {str(e)}")

    def _map_aspect_ratio_to_size(self, aspect_ratio: str) -> str:
        # DALL-E 3 supported sizes: 1024x1024, 1024x1792, 1792x1024
        if aspect_ratio == "landscape":
            return "1792x1024"
        elif aspect_ratio == "portrait":
            return "1024x1792"
        return "1024x1024" # default square

    def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        try:
            model = request.model_name or self.default_model
            size = self._map_aspect_ratio_to_size(request.aspect_ratio)
            
            # Append style preset if provided
            final_prompt = request.prompt
            if request.style_preset:
                final_prompt = f"{request.prompt}. Style: {request.style_preset}"
                
            # DALL-E 3 defaults to 'standard' quality and 'vivid' style. 
            response = self.client.images.generate(
                model=model,
                prompt=final_prompt,
                size=size,
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            
            # Download the image
            req_dl = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_dl, timeout=30) as response_dl:
                img_data = response_dl.read()
            
            # Create a temp file
            fd, temp_path = tempfile.mkstemp(suffix=".png")
            with os.fdopen(fd, 'wb') as f:
                f.write(img_data)
            
            # Estimate cost (DALL-E 3 standard is currently $0.040 / image)
            # We hardcode a generic estimate for now.
            cost = 0.04
            
            return ImageGenerationResponse(
                success=True,
                local_temp_path=temp_path,
                token_cost_estimate=cost
            )
            
        except Exception as e:
            self._handle_openai_error(e)
