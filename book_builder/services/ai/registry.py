from typing import Dict, Type
from book_builder.services.ai.interfaces import IAIProvider
from book_builder.services.ai.errors import AIUnknownProviderError

from book_builder.services.ai.providers.mock_provider import MockAIProvider
from book_builder.services.ai.providers.openai_provider import OpenAIProvider

class AIProviderRegistry:
    """
    Lightweight factory and registry for AI Providers.
    Allows registering provider classes (e.g., 'openai': OpenAIProvider).
    """
    _providers: Dict[str, Type[IAIProvider]] = {
        "mock": MockAIProvider,
        "openai": OpenAIProvider
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[IAIProvider]) -> None:
        cls._providers[name.lower()] = provider_class

    @classmethod
    def get_provider_instance(cls, name: str, **kwargs) -> IAIProvider:
        """
        Instantiates a provider by name.
        """
        name_lower = name.lower()
        if name_lower not in cls._providers:
            raise AIUnknownProviderError(f"AI Provider '{name}' is not registered or supported.")
        return cls._providers[name_lower](**kwargs)

    @classmethod
    def available_providers(cls) -> list[str]:
        return list(cls._providers.keys())
