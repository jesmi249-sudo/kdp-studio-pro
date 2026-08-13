from core.logger import get_logger

logger = get_logger(__name__)

class CommandDispatcher:
    """Centralized command dispatcher to route toolbar clicks to active views."""
    _instance = None
    _active_view = None
    _global_handler = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CommandDispatcher, cls).__new__(cls)
        return cls._instance

    def set_global_handler(self, handler):
        """Register the global app handler for fallback command routing."""
        self._global_handler = handler

    def set_active_view(self, view):
        """Register the currently active view handling commands."""
        self._active_view = view
        logger.debug(f"CommandDispatcher active view set to: {type(view).__name__ if view else 'None'}")

    def execute(self, command_name, *args, **kwargs):
        """Dispatch a command to the active view, falling back to global handler."""
        method_name = f"cmd_{command_name}"
        
        # Try active view first
        if self._active_view and hasattr(self._active_view, method_name):
            try:
                method = getattr(self._active_view, method_name)
                method(*args, **kwargs)
                return True
            except Exception as e:
                logger.error(f"Error executing command '{command_name}' on active view: {e}")
                return False
                
        # Try global handler
        if self._global_handler and hasattr(self._global_handler, method_name):
            try:
                method = getattr(self._global_handler, method_name)
                method(*args, **kwargs)
                return True
            except Exception as e:
                logger.error(f"Error executing command '{command_name}' on global handler: {e}")
                return False

        logger.debug(f"Command '{command_name}' not supported.")
        return False
