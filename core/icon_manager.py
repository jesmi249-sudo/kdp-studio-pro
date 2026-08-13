import os
from PIL import Image
import customtkinter as ctk
from core.logger import get_logger

logger = get_logger(__name__)

class IconManager:
    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IconManager, cls).__new__(cls)
            cls._instance.icons_dir = os.path.join(os.getcwd(), 'assets', 'icons')
        return cls._instance

    def get_icon(self, name, size=(24, 24)):
        """Loads and caches an icon. Returns a CTkImage."""
        cache_key = f"{name}_{size[0]}x{size[1]}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        path = os.path.join(self.icons_dir, name)
        if not os.path.exists(path):
            logger.warning(f"Icon not found: {path}")
            return None
            
        try:
            pil_img = Image.open(path).convert("RGBA")
            # For this simple placeholder, use the same image for light/dark mode
            # Real icons might be tinted dynamically based on mode.
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
            self._cache[cache_key] = ctk_img
            return ctk_img
        except Exception as e:
            logger.error(f"Failed to load icon {name}: {e}")
            return None
