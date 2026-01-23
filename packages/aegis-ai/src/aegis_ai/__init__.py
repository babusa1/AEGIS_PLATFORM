"""
AEGIS AI Package

AI/ML infrastructure for healthcare agents:
- LLM Gateway with multi-provider support (Bedrock, OpenAI, Gemini)
- LangGraph agent orchestration
- Tool registry for agent capabilities
- Human-in-the-loop workflows
"""

from aegis_ai.gateway import LLMGateway, get_llm_gateway
from aegis_ai.models import (
    LLMRequest, LLMResponse, Message, ToolCall,
    AgentState, AgentConfig
)
from aegis_ai.tools import Tool, ToolRegistry, get_tool_registry

__version__ = "0.1.0"

__all__ = [
    # Gateway
    "LLMGateway",
    "get_llm_gateway",
    # Models
    "LLMRequest",
    "LLMResponse",
    "Message",
    "ToolCall",
    "AgentState",
    "AgentConfig",
    # Tools
    "Tool",
    "ToolRegistry",
    "get_tool_registry",
]
