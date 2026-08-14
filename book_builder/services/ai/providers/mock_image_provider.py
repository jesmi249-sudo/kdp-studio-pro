import os
import tempfile
import time
from PIL import Image

from book_builder.services.ai.providers.image_interfaces import IImageProvider, ImageGenerationRequest, ImageGenerationResponse

class MockImageProvider(IImageProvider):
    """
    Mock implementation of IImageProvider for testing.
    Generates a solid color PIL image and saves it to a temp file.
    """
    def __init__(self, should_fail: bool = False, delay_seconds: float = 0.0):
        self.should_fail = should_fail
        self.delay_seconds = delay_seconds

    def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)
            
        if self.should_fail:
            return ImageGenerationResponse(
                success=False,
                error_message="Mock provider simulated failure",
                token_cost_estimate=0.0
            )
            
        # Determine size from aspect ratio
        width, height = 512, 512
        if request.aspect_ratio == "landscape":
            width, height = 768, 512
        elif request.aspect_ratio == "portrait":
            width, height = 512, 768
            
        # Create a temp file
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        
        # Generate dummy image
        img = Image.new('RGB', (width, height), color=(100, 150, 200))
        img.save(temp_path)
        
        return ImageGenerationResponse(
            success=True,
            local_temp_path=temp_path,
            token_cost_estimate=0.04
        )
