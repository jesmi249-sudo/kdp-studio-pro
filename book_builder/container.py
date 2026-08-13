import threading
from typing import Dict, Type, Any

class Container:
    """Thread-safe Dependency Injection (DI) Service Registry."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> "Container":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Container, cls).__new__(cls)
                cls._instance._registry = {}
                cls._instance._registry_lock = threading.Lock()
        return cls._instance

    def register(self, interface: Type[Any], implementation: Any) -> None:
        """Registers a service implementation instance for a specific interface class type."""
        with self._registry_lock:
            self._registry[interface] = implementation

    def resolve(self, interface: Type[Any]) -> Any:
        """Retrieves and returns the registered service implementation for the interface type."""
        with self._registry_lock:
            if interface in self._registry:
                return self._registry[interface]
        raise ValueError(f"Service interface '{interface.__name__}' has not been registered in the Container.")

    def clear(self) -> None:
        """Removes all registered service mappings from the Container."""
        with self._registry_lock:
            self._registry.clear()
