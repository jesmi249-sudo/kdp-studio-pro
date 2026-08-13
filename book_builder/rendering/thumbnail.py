import os
import hashlib
from typing import Optional, Tuple
from PIL import Image
from book_builder.models.page import Page
from book_builder.rendering.engine import RenderingEngine
from book_builder.rendering.cache import get_page_content_hash
from core.logger import get_logger

logger = get_logger(__name__)

PAGE_THUMBNAIL_CACHE_DIR = os.path.join(".cache", "page_thumbnails")
os.makedirs(PAGE_THUMBNAIL_CACHE_DIR, exist_ok=True)

class PageThumbnailGenerator:
    """
    Generates and manages disk-cached thumbnail images for abstract Page models.
    Prevents redundant rendering by utilizing page content hashes.
    """
    def __init__(self, rendering_engine: Optional[RenderingEngine] = None) -> None:
        self.rendering_engine = rendering_engine or RenderingEngine()

    def get_thumbnail_path(self, page: Page, size: Tuple[int, int] = (150, 150)) -> str:
        """
        Returns the file path to a cached thumbnail of the page.
        Generates and saves the thumbnail if it is not already cached.
        """
        os.makedirs(PAGE_THUMBNAIL_CACHE_DIR, exist_ok=True)
        content_hash = get_page_content_hash(page)
        cache_filename = f"{content_hash}_{size[0]}x{size[1]}.png"
        cache_path = os.path.join(PAGE_THUMBNAIL_CACHE_DIR, cache_filename)
        
        if os.path.exists(cache_path):
            logger.debug(f"PageThumbnailGenerator: cache hit for page {page.id} ({size[0]}x{size[1]})")
            return cache_path

        logger.info(f"PageThumbnailGenerator: cache miss for page {page.id}, generating thumbnail")
        try:
            # Render page layout at screen-density DPI (e.g. 100 DPI) for thumbnail scaling
            # Low DPI rendering is much faster and uses less memory
            img = self.rendering_engine.render(page, dpi=100)
            
            # Create thumbnail
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Save to cache
            img.save(cache_path, format="PNG")
            return cache_path
        except Exception as e:
            logger.error(f"PageThumbnailGenerator: failed to generate thumbnail for page {page.id}: {e}")
            # Generate a simple placeholder image on failure
            placeholder_img = Image.new("RGBA", size, (220, 220, 220, 255))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(placeholder_img)
            draw.rectangle([(0, 0), (size[0]-1, size[1]-1)], outline="red", width=2)
            draw.text((10, size[1] // 2 - 5), "RENDER ERROR", fill="red")
            
            try:
                placeholder_img.save(cache_path, format="PNG")
                return cache_path
            except Exception as save_err:
                logger.error(f"PageThumbnailGenerator: failed to write placeholder: {save_err}")
                return ""
                
    def clear_cache(self) -> None:
        """
        Clears all cached page thumbnail files from disk.
        """
        try:
            for file in os.listdir(PAGE_THUMBNAIL_CACHE_DIR):
                if file.endswith(".png"):
                    os.remove(os.path.join(PAGE_THUMBNAIL_CACHE_DIR, file))
            logger.info("PageThumbnailGenerator: disk cache cleared")
        except Exception as e:
            logger.error(f"PageThumbnailGenerator: failed to clear cache directory: {e}")
