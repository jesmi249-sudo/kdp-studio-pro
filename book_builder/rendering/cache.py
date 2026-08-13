import hashlib
import json
import threading
from collections import OrderedDict
from typing import Optional, Dict, Any, Tuple
from PIL import Image
from book_builder.models.page import Page
from core.logger import get_logger

logger = get_logger(__name__)

def get_page_content_hash(page: Page) -> str:
    """
    Computes a deterministic MD5 hash of the visual layout definition of a Page.
    Any changes to page dimensions, text, vector objects, or images will produce a new hash.
    """
    # Build a deterministic dictionary of layout-relevant attributes
    layout_data = {
        "width_pt": page.width_pt,
        "height_pt": page.height_pt,
        "background_asset_id": str(page.background_asset_id) if page.background_asset_id else "",
        "images": page.images,
        "text_blocks": page.text_blocks,
        "vector_objects": page.vector_objects
    }
    try:
        # Use sort_keys=True for deterministic JSON serialization
        serialized = json.dumps(layout_data, sort_keys=True)
    except Exception as e:
        logger.error(f"Failed to serialize page {page.id} for hashing: {e}")
        # Fallback to simple signature
        serialized = f"{page.id}_{page.width_pt}_{page.height_pt}_{len(page.images)}_{len(page.text_blocks)}_{len(page.vector_objects)}"
        
    return hashlib.md5(serialized.encode("utf-8")).hexdigest()


class PreviewCache:
    """
    Thread-safe in-memory cache for low-resolution page preview images.
    Implements an LRU (Least Recently Used) eviction policy and validates content hashes.
    """
    def __init__(self, max_size: int = 128) -> None:
        self.max_size = max_size
        self._cache: OrderedDict[Tuple[str, float], Tuple[Image.Image, str]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, page: Page, zoom_level: float) -> Optional[Image.Image]:
        """
        Retrieves a cached preview image if it exists and matches the current page content hash.
        """
        key = (str(page.id), zoom_level)
        current_hash = get_page_content_hash(page)
        
        with self._lock:
            if key in self._cache:
                image, cached_hash = self._cache[key]
                if cached_hash == current_hash:
                    # Move to end to represent recent use
                    self._cache.move_to_end(key)
                    logger.debug(f"PreviewCache: hit for page {page.id} (zoom {zoom_level})")
                    return image
                else:
                    # Content has changed, evict invalid entry
                    logger.debug(f"PreviewCache: hash mismatch for page {page.id}, invalidating cache")
                    del self._cache[key]
            return None

    def set(self, page: Page, zoom_level: float, image: Image.Image) -> None:
        """
        Stores a preview image in the cache, associated with the current page content hash.
        Evicts the oldest items if the cache exceeds max_size.
        """
        key = (str(page.id), zoom_level)
        current_hash = get_page_content_hash(page)
        
        with self._lock:
            # If key already exists, delete it so we can update it at the end
            if key in self._cache:
                del self._cache[key]
            
            self._cache[key] = (image, current_hash)
            logger.debug(f"PreviewCache: stored preview for page {page.id} (zoom {zoom_level})")
            
            # Evict if cache exceeded size limit
            if len(self._cache) > self.max_size:
                oldest_key, _ = self._cache.popitem(last=False)
                logger.debug(f"PreviewCache: evicted oldest entry key {oldest_key}")

    def remove(self, page_id: Any) -> None:
        """
        Removes all cached previews associated with a specific page ID.
        """
        page_id_str = str(page_id)
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k[0] == page_id_str]
            for k in keys_to_delete:
                del self._cache[k]
        if keys_to_delete:
            logger.debug(f"PreviewCache: removed {len(keys_to_delete)} entries for page {page_id_str}")

    def clear(self) -> None:
        """
        Clears all cached previews from memory.
        """
        with self._lock:
            self._cache.clear()
        logger.info("PreviewCache: cleared all cached previews")

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)
