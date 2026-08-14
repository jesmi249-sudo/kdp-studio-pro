import os
from PIL import Image
from typing import Tuple, Optional

from book_builder.services.ai.errors import AIError

class ImageQualityValidator:
    """
    Validates AI-generated images before they are ingested into the AssetManager.
    Checks dimensions, aspect ratio matching, and file integrity.
    """
    
    @staticmethod
    def validate(file_path: str, expected_aspect_ratio: str, min_width: int = 512, min_height: int = 512) -> Tuple[bool, Optional[str]]:
        if not os.path.exists(file_path):
            return False, "Image file does not exist."
            
        try:
            with Image.open(file_path) as img:
                # Verify it's a valid image by loading it
                img.verify()
                
            # PIL verify closes the file, need to reopen to get dimensions safely
            with Image.open(file_path) as img:
                w, h = img.size
                
                if w < min_width or h < min_height:
                    return False, f"Image resolution ({w}x{h}) is below minimum required ({min_width}x{min_height})."
                    
                actual_ratio = w / h
                
                # We define target ratios roughly. 
                # DALL-E typically does 1:1, 16:9 (1.77), or 17:12 (1.41)
                # We want to ensure the generated image isn't the complete opposite orientation of what was requested.
                if expected_aspect_ratio == "landscape" and actual_ratio <= 1.1:
                    return False, f"Expected landscape image, but got portrait/square ({w}x{h})."
                elif expected_aspect_ratio == "portrait" and actual_ratio >= 0.9:
                    return False, f"Expected portrait image, but got landscape/square ({w}x{h})."
                elif expected_aspect_ratio == "square" and (actual_ratio < 0.9 or actual_ratio > 1.1):
                    # Be slightly lenient for square
                    return False, f"Expected square image, but got ({w}x{h})."
                    
                return True, None
                
        except Exception as e:
            return False, f"Failed to validate image file integrity: {str(e)}"
