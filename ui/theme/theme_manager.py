import customtkinter as ctk
from core.config import config
from core.logger import get_logger
from .colors import Colors
from .fonts import Fonts
from .spacing import Spacing

logger = get_logger(__name__)

class ThemeManager:
    @staticmethod
    def apply_theme():
        """Applies the current theme from config."""
        theme_mode = config.get("theme", "dark")
        logger.info(f"Applying theme: {theme_mode}")
        ctk.set_appearance_mode(theme_mode)
        ctk.set_default_color_theme("blue")

    @staticmethod
    def toggle_theme():
        """Toggles between light and dark themes."""
        current_mode = ctk.get_appearance_mode().lower()
        new_mode = "light" if current_mode == "dark" else "dark"
        config.set("theme", new_mode)
        ThemeManager.apply_theme()
        return new_mode
