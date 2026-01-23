"""
Base LLM Provider

Abstract interface for LLM providers.
Supports Bedrock, OpenAI, Gemini, and custom providers.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator
import structlog

from aegis_ai.models import LLMRequest, LLMResponse, Message

logger = structlog.get_logger(__name__)


class BaseLLMProvider(ABC):
    """
    Abstract base for LLM providers.
    
    All providers (Bedrock, OpenAI, Gemini) must implement this interface.
    """
    
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        **kwargs
    ):
        self.model = model
        self.api_key = api_key
        self._initialized = False
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of this provider."""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider (validate credentials, etc.)."""
        pass
    
    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a completion.
        
        Args:
            request: LLM request with messages and settings
            
        Returns:
            LLM response with content and/or tool calls
        """
        pass
    
    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """
        Stream a completion token by token.
        
        Args:
            request: LLM request
            
        Yields:
            Content tokens as they arrive
        """
        pass
    
    def format_messages(self, messages: list[Message]) -> list[dict]:
        """
        Format messages for this provider's API.
        
        Override in subclasses for provider-specific formatting.
        """
        formatted = []
        for msg in messages:
            formatted.append({
                "role": msg.role.value,
                "content": msg.content,
            })
        return formatted
    
    def format_tools(self, tools: list[dict] | None) -> list[dict] | None:
        """
        Format tool definitions for this provider.
        
        Override in subclasses for provider-specific tool format.
        """
        return tools


class LLMError(Exception):
    """LLM provider error."""
    pass


class RateLimitError(LLMError):
    """Rate limit exceeded."""
    pass


class TokenLimitError(LLMError):
    """Token limit exceeded."""
    pass
