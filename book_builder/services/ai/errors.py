class AIError(Exception):
    """Base class for all AI-related exceptions."""
    pass

class AIProviderUnavailableError(AIError):
    """Raised when the requested provider is completely unavailable or disabled."""
    pass

class AIMissingCredentialsError(AIError):
    """Raised when credentials/API keys are missing or not configured."""
    pass

class AIAuthenticationError(AIError):
    """Raised when the provider rejects the provided credentials."""
    pass

class AIRateLimitError(AIError):
    """Raised when the provider rate limit is exceeded."""
    pass

class AITimeoutError(AIError):
    """Raised when the provider request times out."""
    pass

class AIMalformedResponseError(AIError):
    """Raised when the provider response cannot be parsed or does not match the requested structure."""
    pass

class AIUnsupportedOperationError(AIError):
    """Raised when the provider does not support the requested operation."""
    pass

class AIUnknownProviderError(AIError):
    """Raised when attempting to use a provider that is not registered."""
    pass
