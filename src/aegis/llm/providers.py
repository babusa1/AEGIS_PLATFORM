"""
LLM Provider Base Classes

Abstract interfaces for LLM providers.
"""

from typing import Any, AsyncIterator, Dict, List, Optional
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


# =============================================================================
# Models
# =============================================================================

class Role(str, Enum):
    """Message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """A chat message."""
    role: Role
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[dict]] = None


class ToolDefinition(BaseModel):
    """A tool/function definition."""
    name: str
    description: str
    parameters: dict  # JSON Schema


class LLMConfig(BaseModel):
    """LLM configuration."""
    # Provider
    provider: str  # bedrock, openai, anthropic, ollama, azure
    model: str
    
    # Generation parameters
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    top_k: Optional[int] = None
    stop_sequences: List[str] = Field(default_factory=list)
    
    # Provider-specific
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    region: Optional[str] = None
    
    # Features
    stream: bool = False
    json_mode: bool = False
    
    # Retry
    max_retries: int = 3
    timeout_seconds: int = 60


class TokenUsage(BaseModel):
    """Token usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    # Cost (if available)
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0


class LLMResponse(BaseModel):
    """LLM response."""
    content: str
    
    # Metadata
    model: str
    provider: str
    
    # Usage
    usage: TokenUsage = Field(default_factory=TokenUsage)
    
    # Timing
    latency_ms: int = 0
    
    # Tool calls (if any)
    tool_calls: Optional[List[dict]] = None
    
    # Finish reason
    finish_reason: str = "stop"  # stop, length, tool_calls
    
    # Raw response
    raw_response: Optional[dict] = None


# =============================================================================
# Base Provider
# =============================================================================

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All providers must implement:
    - generate(): Single completion
    - chat(): Multi-turn conversation
    - stream(): Streaming generation
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.name = config.provider
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a single completion."""
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs,
    ) -> LLMResponse:
        """Multi-turn chat completion."""
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream generation."""
        pass
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Rough estimate: ~4 characters per token
        return len(text) // 4
    
    def calculate_cost(self, usage: TokenUsage) -> TokenUsage:
        """Calculate cost based on usage."""
        # Override in subclasses with actual pricing
        return usage
    
    async def health_check(self) -> bool:
        """Check if provider is healthy."""
        try:
            response = await self.generate("Hi", max_tokens=5)
            return len(response.content) > 0
        except:
            return False
