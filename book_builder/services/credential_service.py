import keyring
from abc import ABC, abstractmethod
from typing import Optional

class ICredentialService(ABC):
    """
    Interface for secure credential storage and retrieval.
    """
    @abstractmethod
    def set_credential(self, service_name: str, username: str, password: str) -> bool:
        pass

    @abstractmethod
    def get_credential(self, service_name: str, username: str) -> Optional[str]:
        pass

    @abstractmethod
    def delete_credential(self, service_name: str, username: str) -> bool:
        pass

class KeyringCredentialService(ICredentialService):
    """
    Secure credential storage using OS-level keyring (Windows Credential Locker, macOS Keychain).
    """
    def set_credential(self, service_name: str, username: str, password: str) -> bool:
        try:
            keyring.set_password(service_name, username, password)
            return True
        except Exception:
            return False

    def get_credential(self, service_name: str, username: str) -> Optional[str]:
        try:
            return keyring.get_password(service_name, username)
        except Exception:
            return None

    def delete_credential(self, service_name: str, username: str) -> bool:
        try:
            keyring.delete_password(service_name, username)
            return True
        except Exception:
            return False

class MockCredentialService(ICredentialService):
    """
    In-memory credential store for tests or environments without a keyring.
    """
    def __init__(self):
        self._store = {}

    def set_credential(self, service_name: str, username: str, password: str) -> bool:
        self._store[f"{service_name}:{username}"] = password
        return True

    def get_credential(self, service_name: str, username: str) -> Optional[str]:
        return self._store.get(f"{service_name}:{username}")

    def delete_credential(self, service_name: str, username: str) -> bool:
        key = f"{service_name}:{username}"
        if key in self._store:
            del self._store[key]
            return True
        return False
