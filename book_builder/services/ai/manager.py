import logging
from typing import Optional, Any, Dict, TypeVar

from book_builder.services.ai.interfaces import IAIProvider
from book_builder.services.ai.providers.image_interfaces import IImageProvider
from book_builder.services.ai.models import AIRequest, AIResponse
from book_builder.services.ai.errors import AIError, AIProviderUnavailableError
from book_builder.services.ai.registry import AIProviderRegistry, ImageProviderRegistry

logger = logging.getLogger(__name__)

T = TypeVar('T')

class AIManager:
    """
    Application-level entry point for AI operations.
    Handles provider selection, normalizes responses, and prevents AI crashes from propagating.
    """
    
    def __init__(self, credential_service=None):
        self._active_provider: Optional[IAIProvider] = None
        self._active_image_provider: Optional[IImageProvider] = None
        self._is_enabled: bool = False
        self._is_image_enabled: bool = False
        self._credential_service = credential_service

    def configure(self, provider_name: str, model_name: str = None, **kwargs) -> bool:
        """
        Configures the active AI provider securely using the credential service.
        Returns True if successful, False otherwise.
        """
        try:
            if not provider_name or provider_name.lower() == "none":
                self.disable()
                return True
                
            api_key = None
            if self._credential_service:
                api_key = self._credential_service.get_credential("kdp_studio_ai", provider_name.lower())
                
            if api_key:
                kwargs["api_key"] = api_key
            if model_name:
                kwargs["model_name"] = model_name
                
            self._active_provider = AIProviderRegistry.get_provider_instance(provider_name, **kwargs)
            self._is_enabled = True
            logger.info(f"AIManager configured with provider: {provider_name}")
            return True
        except AIError as e:
            logger.error(f"Failed to configure AIManager: {e}")
            self.disable()
            return False
            
    def configure_image_provider(self, provider_name: str, model_name: str = None, **kwargs) -> bool:
        """
        Configures the active AI image provider securely using the credential service.
        """
        try:
            if not provider_name or provider_name.lower() == "none":
                self._active_image_provider = None
                self._is_image_enabled = False
                return True
                
            api_key = None
            if self._credential_service:
                api_key = self._credential_service.get_credential("kdp_studio_ai", provider_name.lower())
                
            if api_key:
                kwargs["api_key"] = api_key
            if model_name:
                kwargs["model_name"] = model_name
                
            self._active_image_provider = ImageProviderRegistry.get_provider_instance(provider_name, **kwargs)
            self._is_image_enabled = True
            logger.info(f"AIManager configured with image provider: {provider_name}")
            return True
        except AIError as e:
            logger.error(f"Failed to configure AIManager image provider: {e}")
            self._active_image_provider = None
            self._is_image_enabled = False
            return False

    def disable(self) -> None:
        """Disables AI functionality, returning to offline/no-AI mode."""
        self._active_provider = None
        self._active_image_provider = None
        self._is_enabled = False
        self._is_image_enabled = False
        logger.info("AIManager disabled (Offline/No-AI Mode).")
        
    @property
    def is_enabled(self) -> bool:
        return self._is_enabled
        
    @property
    def is_image_enabled(self) -> bool:
        return self._is_image_enabled
        
    def _check_provider(self) -> None:
        if not self._is_enabled or not self._active_provider:
            raise AIProviderUnavailableError("AI is disabled or no provider is configured.")

    def _check_image_provider(self) -> None:
        if not self._is_image_enabled or not self._active_image_provider:
            raise AIProviderUnavailableError("AI Image Generation is disabled or no image provider is configured.")

    # --- Core AI Operations ---

    def generate_text(self, request: AIRequest) -> AIResponse[str]:
        try:
            self._check_provider()
            return self._active_provider.generate_text(request)
        except AIError as e:
            logger.error(f"AIManager generate_text failed: {e}")
            return AIResponse(success=False, error_message=str(e))
        except Exception as e:
            logger.exception(f"AIManager unexpected error in generate_text: {e}")
            return AIResponse(success=False, error_message="An unexpected AI error occurred.")

    def generate_structured_content(self, request: AIRequest) -> AIResponse[Any]:
        try:
            self._check_provider()
            if not request.structured_schema:
                raise ValueError("structured_schema must be provided for generate_structured_content")
            return self._active_provider.generate_structured_content(request)
        except ValueError as e:
            logger.error(f"AIManager ValueError in generate_structured_content: {e}")
            return AIResponse(success=False, error_message=str(e))
        except AIError as e:
            logger.error(f"AIManager generate_structured_content failed: {e}")
            return AIResponse(success=False, error_message=str(e))
        except Exception as e:
            logger.exception(f"AIManager unexpected error in generate_structured_content: {e}")
            return AIResponse(success=False, error_message="An unexpected AI error occurred.")

    def analyze_prompt(self, request: AIRequest) -> AIResponse[Dict[str, Any]]:
        try:
            self._check_provider()
            return self._active_provider.analyze_prompt(request)
        except AIError as e:
            logger.error(f"AIManager analyze_prompt failed: {e}")
            return AIResponse(success=False, error_message=str(e))
        except Exception as e:
            logger.exception(f"AIManager unexpected error in analyze_prompt: {e}")
            return AIResponse(success=False, error_message="An unexpected AI error occurred.")

    def generate_image_prompt(self, request: AIRequest) -> AIResponse[str]:
        try:
            self._check_provider()
            return self._active_provider.generate_image_prompt(request)
        except AIError as e:
            logger.error(f"AIManager generate_image_prompt failed: {e}")
            return AIResponse(success=False, error_message=str(e))
        except Exception as e:
            logger.exception(f"AIManager unexpected error in generate_image_prompt: {e}")
            return AIResponse(success=False, error_message="An unexpected AI error occurred.")

    def get_image_provider(self) -> IImageProvider:
        self._check_image_provider()
        return self._active_image_provider

