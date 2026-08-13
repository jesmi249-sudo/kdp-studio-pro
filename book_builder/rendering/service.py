from typing import Any, Optional
from PIL import Image
from book_builder.interfaces.services import IPreviewService
from book_builder.models.page import Page
from book_builder.rendering.engine import RenderingEngine
from book_builder.rendering.cache import PreviewCache
from core.logger import get_logger

logger = get_logger(__name__)

class PreviewService(IPreviewService):
    """
    Implements IPreviewService to render fast, zoom-scaled page previews using PreviewCache.
    """
    def __init__(self, rendering_engine: Optional[RenderingEngine] = None, preview_cache: Optional[PreviewCache] = None) -> None:
        self.rendering_engine = rendering_engine or RenderingEngine()
        self.preview_cache = preview_cache or PreviewCache()

    def generate_preview(self, page: Page, zoom_level: float) -> Image.Image:
        """
        Generates or retrieves a low-resolution cached raster graphic of a page at the specified zoom level.
        The zoom_level determines the DPI used to render the canvas (zoom_level 1.0 = 72 DPI).
        """
        # Ensure zoom_level is positive and reasonable
        if zoom_level <= 0.0:
            zoom_level = 1.0
            
        # Constrain zoom level to avoid excessive memory allocations (e.g. maximum 8.0x zoom, minimum 0.1x)
        constrained_zoom = max(0.1, min(8.0, zoom_level))
        
        # Check cache
        cached_img = self.preview_cache.get(page, constrained_zoom)
        if cached_img is not None:
            return cached_img

        # 72 points per inch. Screen-density rendering scale: 1.0 zoom -> 72 DPI.
        dpi = int(72.0 * constrained_zoom)
        
        # Ensure a safe range of DPI values (min 10, max 600)
        dpi = max(10, min(600, dpi))
        
        logger.info(f"PreviewService: rendering page {page.id} layout at {dpi} DPI (zoom {constrained_zoom})")
        
        # Render image
        rendered_img = self.rendering_engine.render(page, dpi=dpi)
        
        # Store in cache
        self.preview_cache.set(page, constrained_zoom, rendered_img)
        
        return rendered_img

    def clear_cache(self) -> None:
        """
        Disposes of cached preview images to release memory.
        """
        self.preview_cache.clear()
