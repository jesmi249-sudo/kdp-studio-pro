from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Type, Generic, TypeVar

T = TypeVar('T')

@dataclass
class AIRequest:
    """Standardized AI Request object."""
    prompt: str
    system_instruction: str = ""
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    # For structured output, you'd pass a type/schema here.
    structured_schema: Optional[Type[Any]] = None

@dataclass
class AIResponse(Generic[T]):
    """Standardized AI Response object."""
    success: bool
    content: Optional[str] = None
    structured_data: Optional[T] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
