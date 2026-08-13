from typing import Dict, Any, TypeVar
import json
from dataclasses import is_dataclass, asdict

from book_builder.services.ai.interfaces import IAIProvider
from book_builder.services.ai.models import AIRequest, AIResponse
from book_builder.services.ai.errors import AITimeoutError, AIProviderUnavailableError

T = TypeVar('T')

class MockAIProvider(IAIProvider):
    """
    Fake AI Provider for unit tests and local development without API keys.
    """
    
    def __init__(self, simulate_timeout=False, simulate_failure=False):
        self.simulate_timeout = simulate_timeout
        self.simulate_failure = simulate_failure

    def _check_simulation(self):
        if self.simulate_timeout:
            raise AITimeoutError("Mock provider simulated timeout")
        if self.simulate_failure:
            raise AIProviderUnavailableError("Mock provider simulated failure")

    def generate_text(self, request: AIRequest) -> AIResponse[str]:
        self._check_simulation()
        return AIResponse(
            success=True,
            content=f"Mock text response for: {request.prompt[:20]}...",
            metadata={"tokens": 42}
        )
        
    def generate_structured_content(self, request: AIRequest) -> AIResponse[T]:
        self._check_simulation()
        # In a real mock, we might inspect request.structured_schema to build a fake object
        # For phase A, we just return a dictionary or dummy instance
        
        # If a schema is provided, we try to instantiate it with dummy data if it's a dataclass
        # otherwise return an empty dict
        data = {}
        if request.structured_schema:
            try:
                # Naive dummy instantiation for test purposes
                schema_cls = request.structured_schema
                if is_dataclass(schema_cls):
                    # Will only work for dataclasses with default fields, or simple tests
                    data = schema_cls() 
                else:
                    data = {"mock": "structured_data"}
            except Exception:
                data = {"mock": "structured_data"}
                
        return AIResponse(
            success=True,
            structured_data=data,
            metadata={"schema": str(request.structured_schema)}
        )
        
    def analyze_prompt(self, request: AIRequest) -> AIResponse[Dict[str, Any]]:
        self._check_simulation()
        return AIResponse(
            success=True,
            structured_data={"subject": "Mock subject", "action": "Mock action"},
        )
        
    def generate_image_prompt(self, request: AIRequest) -> AIResponse[str]:
        self._check_simulation()
        return AIResponse(
            success=True,
            content="A beautiful mock image prompt, vibrant colors",
        )
