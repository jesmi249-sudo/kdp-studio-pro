from typing import Dict, Any, Type, Optional
import customtkinter as ctk
from core.logger import get_logger

logger = get_logger(__name__)

class StudioMetadata:
    """Metadata representing a Studio plugin registered in the workspace."""
    def __init__(self, name: str, settings_panel_class: Type[ctk.CTkFrame], 
                 template_generator_class: Optional[Type[Any]] = None) -> None:
        self.name = name
        self.settings_panel_class = settings_panel_class
        self.template_generator_class = template_generator_class


class StudioRegistry:
    """Singleton registry class that manages the plugin studios (e.g. Notebook Studio, Planner Studio)."""
    _instance = None
    _studios: Dict[str, StudioMetadata] = {}

    def __new__(cls) -> "StudioRegistry":
        if cls._instance is None:
            cls._instance = super(StudioRegistry, cls).__new__(cls)
        return cls._instance

    def register_studio(self, project_type: str, metadata: StudioMetadata) -> None:
        """Registers a studio plugin for the given project type."""
        logger.info(f"StudioRegistry: registering studio '{metadata.name}' for type '{project_type}'")
        self._studios[project_type.lower()] = metadata

    def unregister_studio(self, project_type: str) -> None:
        """Unregisters a studio plugin."""
        key = project_type.lower()
        if key in self._studios:
            del self._studios[key]

    def get_studio_metadata(self, project_type: str) -> Optional[StudioMetadata]:
        """Returns metadata for the given project type, if registered."""
        return self._studios.get(project_type.lower())

    def get_settings_panel(self, project_type: str, parent: Any, controller: Any) -> Optional[ctk.CTkFrame]:
        """Instantiates and returns the settings panel for the registered project type."""
        meta = self.get_studio_metadata(project_type)
        if meta and meta.settings_panel_class:
            try:
                # Instantiate with parent and controller
                return meta.settings_panel_class(parent, controller)
            except Exception as e:
                logger.error(f"StudioRegistry: failed to instantiate settings panel for '{project_type}': {e}")
                return None
        return None

    def get_template_generator(self, project_type: str) -> Optional[Any]:
        """Instantiates and returns the template generator for the registered project type."""
        meta = self.get_studio_metadata(project_type)
        if meta and meta.template_generator_class:
            try:
                return meta.template_generator_class()
            except Exception as e:
                logger.error(f"StudioRegistry: failed to instantiate template generator for '{project_type}': {e}")
                return None
        return None
