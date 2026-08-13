import logging
from typing import Dict, Any, TypeVar

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from pydantic import BaseModel

from book_builder.services.ai.interfaces import IAIProvider
from book_builder.services.ai.models import AIRequest, AIResponse
from book_builder.services.ai.errors import (
    AIProviderUnavailableError, AIMissingCredentialsError, AIAuthenticationError,
    AIRateLimitError, AITimeoutError, AIError
)

logger = logging.getLogger(__name__)
T = TypeVar('T')

class OpenAIProvider(IAIProvider):
    """
    OpenAI Provider implementing the IAIProvider interface.
    """
    
    def __init__(self, api_key: str = None, model_name: str = "gpt-4o-mini", **kwargs):
        if not OPENAI_AVAILABLE:
            raise AIProviderUnavailableError("OpenAI SDK is not installed.")
            
        if not api_key:
            raise AIMissingCredentialsError("OpenAI API key is missing. Please configure it in AI Settings.")
            
        self.api_key = api_key
        self.default_model = model_name
        self.client = OpenAI(api_key=self.api_key)

    def _handle_openai_error(self, e: Exception) -> None:
        """Maps OpenAI SDK exceptions to our standard AIError hierarchy."""
        if isinstance(e, openai.AuthenticationError):
            raise AIAuthenticationError("Invalid OpenAI API key.")
        elif isinstance(e, openai.RateLimitError):
            raise AIRateLimitError("OpenAI rate limit exceeded or insufficient quota.")
        elif isinstance(e, openai.APITimeoutError):
            raise AITimeoutError("OpenAI request timed out.")
        elif isinstance(e, openai.APIConnectionError):
            raise AIProviderUnavailableError("Failed to connect to OpenAI API.")
        elif isinstance(e, openai.OpenAIError):
            raise AIError(f"OpenAI error: {str(e)}")
        else:
            raise AIError(f"Unexpected error: {str(e)}")

    def _build_messages(self, request: AIRequest) -> list:
        messages = []
        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})
        messages.append({"role": "user", "content": request.prompt})
        return messages

    def generate_text(self, request: AIRequest) -> AIResponse[str]:
        try:
            model = request.model or self.default_model
            kwargs = {
                "model": model,
                "messages": self._build_messages(request),
                "temperature": request.temperature,
            }
            if request.max_tokens:
                kwargs["max_tokens"] = request.max_tokens

            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            
            metadata = {}
            if response.usage:
                metadata["total_tokens"] = response.usage.total_tokens
                metadata["prompt_tokens"] = response.usage.prompt_tokens
                metadata["completion_tokens"] = response.usage.completion_tokens

            return AIResponse(success=True, content=content, metadata=metadata)
            
        except Exception as e:
            self._handle_openai_error(e)

    def generate_structured_content(self, request: AIRequest) -> AIResponse[T]:
        try:
            model = request.model or self.default_model
            schema = request.structured_schema
            
            if not schema or not issubclass(schema, BaseModel):
                raise ValueError("OpenAIProvider requires a Pydantic BaseModel for structured_schema.")

            kwargs = {
                "model": model,
                "messages": self._build_messages(request),
                "temperature": request.temperature,
                "response_format": schema,
            }
            if request.max_tokens:
                kwargs["max_tokens"] = request.max_tokens

            response = self.client.beta.chat.completions.parse(**kwargs)
            parsed_data = response.choices[0].message.parsed
            
            metadata = {}
            if response.usage:
                metadata["total_tokens"] = response.usage.total_tokens
                metadata["prompt_tokens"] = response.usage.prompt_tokens
                metadata["completion_tokens"] = response.usage.completion_tokens

            return AIResponse(success=True, structured_data=parsed_data, metadata=metadata)

        except Exception as e:
            self._handle_openai_error(e)

    def analyze_prompt(self, request: AIRequest) -> AIResponse[Dict[str, Any]]:
        # This can use generate_structured_content internally in the future
        # For now, it returns a placeholder or simple text parsing
        return AIResponse(success=False, error_message="Not implemented for OpenAI Provider yet.")

    def generate_image_prompt(self, request: AIRequest) -> AIResponse[str]:
        # Simple text generation specialized for image prompts
        req = AIRequest(
            prompt=f"Create a highly detailed Midjourney prompt for the following request: {request.prompt}",
            system_instruction="You are an expert prompt engineer. Output ONLY the raw prompt, no chat.",
            temperature=0.7,
            model=request.model
        )
        return self.generate_text(req)
