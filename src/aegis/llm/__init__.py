"""
AEGIS LLM Module

Multi-provider LLM support:
- AWS Bedrock (Claude, Llama, Titan)
- OpenAI (GPT-4, GPT-3.5)
- Azure OpenAI
- Anthropic (Claude direct)
- Ollama (local models)
- Google Vertex AI
"""

from aegis.llm.providers import (
    LLMProvider,
    LLMConfig,
    LLMResponse,
    Message,
    Role,
)
from aegis.llm.registry import LLMRegistry, get_llm_registry
from aegis.llm.bedrock import BedrockProvider
from aegis.llm.openai import OpenAIProvider
from aegis.llm.anthropic import AnthropicProvider
from aegis.llm.ollama import OllamaProvider

__all__ = [
    "LLMProvider",
    "LLMConfig",
    "LLMResponse",
    "Message",
    "Role",
    "LLMRegistry",
    "get_llm_registry",
    "BedrockProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
]
