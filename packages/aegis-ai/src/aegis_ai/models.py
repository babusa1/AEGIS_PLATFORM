"""
AI Domain Models

Core models for LLM interactions and agent orchestration.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message roles in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """A message in a conversation."""
    role: MessageRole
    content: str
    name: str | None = None  # For tool messages
    tool_call_id: str | None = None  # For tool responses
    
    @classmethod
    def system(cls, content: str) -> "Message":
        return cls(role=MessageRole.SYSTEM, content=content)
    
    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role=MessageRole.USER, content=content)
    
    @classmethod
    def assistant(cls, content: str) -> "Message":
        return cls(role=MessageRole.ASSISTANT, content=content)
    
    @classmethod
    def tool(cls, content: str, name: str, tool_call_id: str) -> "Message":
        return cls(
            role=MessageRole.TOOL,
            content=content,
            name=name,
            tool_call_id=tool_call_id
        )


class ToolCall(BaseModel):
    """A tool call requested by the LLM."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    arguments: dict[str, Any]


class LLMRequest(BaseModel):
    """Request to an LLM provider."""
    messages: list[Message]
    model: str | None = None  # Override default model
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: list[dict] | None = None  # Tool definitions
    tool_choice: str | dict | None = None  # auto, none, or specific
    
    # Healthcare-specific
    tenant_id: str | None = None
    user_id: str | None = None
    purpose: str | None = None  # For audit logging
    
    # Request metadata
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LLMResponse(BaseModel):
    """Response from an LLM provider."""
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    finish_reason: str | None = None
    
    # Provider info
    provider: str
    model: str
    
    # Usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    # Timing
    latency_ms: int = 0
    
    # Request tracking
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentState(BaseModel):
    """
    State for LangGraph agent.
    
    Carries conversation history, tool results, and workflow state.
    """
    messages: list[Message] = Field(default_factory=list)
    
    # Current context
    patient_id: str | None = None
    encounter_id: str | None = None
    
    # Tool execution
    pending_tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: dict[str, Any] = Field(default_factory=dict)
    
    # Workflow state
    current_step: str = "start"
    completed_steps: list[str] = Field(default_factory=list)
    
    # Human-in-the-loop
    awaiting_approval: bool = False
    approval_request: dict | None = None
    
    # Error handling
    errors: list[str] = Field(default_factory=list)
    retry_count: int = 0
    
    # Metadata
    agent_id: str | None = None
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str | None = None
    user_id: str | None = None


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    name: str
    description: str
    
    # Model settings
    model: str = "claude-3-sonnet"
    temperature: float = 0.3
    max_tokens: int = 4096
    
    # System prompt
    system_prompt: str
    
    # Available tools
    tools: list[str] = Field(default_factory=list)
    
    # Workflow
    max_iterations: int = 10
    require_approval_for: list[str] = Field(default_factory=list)
    
    # Healthcare-specific
    allowed_purposes: list[str] = Field(default_factory=list)
    phi_access_level: Literal["none", "limited", "full"] = "limited"
