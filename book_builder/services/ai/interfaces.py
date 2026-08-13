from abc import ABC, abstractmethod
from typing import Dict, Any, TypeVar
from book_builder.services.ai.models import AIRequest, AIResponse

T = TypeVar('T')

class IAIProvider(ABC):
    """
    Interface for AI providers (OpenAI, Gemini, Anthropic, etc.).
    """
    
    @abstractmethod
    def generate_text(self, request: AIRequest) -> AIResponse[str]:
        """
        Generates unstructured text based on the request.
        """
        pass
        
    @abstractmethod
    def generate_structured_content(self, request: AIRequest) -> AIResponse[T]:
        """
        Generates structured content based on the request's schema.
        """
        pass
        
    @abstractmethod
    def analyze_prompt(self, request: AIRequest) -> AIResponse[Dict[str, Any]]:
        """
        Analyzes a prompt and extracts structured components.
        """
        pass
        
    @abstractmethod
    def generate_image_prompt(self, request: AIRequest) -> AIResponse[str]:
        """
        Generates an optimized image generation prompt.
        """
        pass
