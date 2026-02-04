"""
LLM Registry

Central registry for managing multiple LLM providers.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

import structlog
from pydantic import BaseModel, Field

from aegis.llm.providers import LLMProvider, LLMConfig, LLMResponse, Message
from aegis.llm.bedrock import BedrockProvider
from aegis.llm.openai import OpenAIProvider
from aegis.llm.anthropic import AnthropicProvider
from aegis.llm.ollama import OllamaProvider

logger = structlog.get_logger(__name__)


# =============================================================================
# Provider Factory
# =============================================================================

PROVIDER_CLASSES = {
    "bedrock": BedrockProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
}

# Model to provider mapping
MODEL_PROVIDERS = {
    # Bedrock models
    "anthropic.claude-3-opus": "bedrock",
    "anthropic.claude-3-sonnet": "bedrock",
    "anthropic.claude-3-haiku": "bedrock",
    "meta.llama3-70b-instruct": "bedrock",
    "meta.llama3-8b-instruct": "bedrock",
    "amazon.titan-text-express": "bedrock",
    "mistral.mistral-large": "bedrock",
    
    # OpenAI models
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gpt-4-turbo": "openai",
    "gpt-4": "openai",
    "gpt-3.5-turbo": "openai",
    "o1-preview": "openai",
    "o1-mini": "openai",
    
    # Anthropic direct
    "claude-3-5-sonnet-20241022": "anthropic",
    "claude-3-opus-20240229": "anthropic",
    "claude-3-sonnet-20240229": "anthropic",
    "claude-3-haiku-20240307": "anthropic",
    
    # Ollama (local)
    "llama3": "ollama",
    "llama3:70b": "ollama",
    "mistral": "ollama",
    "codellama": "ollama",
    "phi3": "ollama",
    "gemma": "ollama",
}


# =============================================================================
# LLM Registry
# =============================================================================

class LLMRegistry:
    """
    Central registry for LLM providers.
    
    Features:
    - Multiple provider support
    - Automatic provider selection
    - Fallback handling
    - Usage tracking
    - Cost aggregation
    """
    
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._default_provider: Optional[str] = None
        self._usage_history: List[dict] = []
        self._total_cost: float = 0.0
    
    def register_provider(
        self,
        name: str,
        config: LLMConfig,
    ) -> LLMProvider:
        """Register a provider."""
        provider_class = PROVIDER_CLASSES.get(config.provider)
        if not provider_class:
            raise ValueError(f"Unknown provider: {config.provider}")
        
        provider = provider_class(config)
        self._providers[name] = provider
        
        # Set as default if first provider
        if self._default_provider is None:
            self._default_provider = name
        
        logger.info(
            "Registered LLM provider",
            name=name,
            provider=config.provider,
            model=config.model,
        )
        
        return provider
    
    def get_provider(self, name: str = None) -> LLMProvider:
        """Get a provider by name."""
        name = name or self._default_provider
        if not name or name not in self._providers:
            raise ValueError(f"Provider not found: {name}")
        return self._providers[name]
    
    def set_default(self, name: str):
        """Set the default provider."""
        if name not in self._providers:
            raise ValueError(f"Provider not found: {name}")
        self._default_provider = name
    
    def list_providers(self) -> List[dict]:
        """List all registered providers."""
        return [
            {
                "name": name,
                "provider": p.config.provider,
                "model": p.config.model,
                "is_default": name == self._default_provider,
            }
            for name, p in self._providers.items()
        ]
    
    async def generate(
        self,
        prompt: str,
        provider: str = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate using a provider."""
        p = self.get_provider(provider)
        response = await p.generate(prompt, **kwargs)
        self._record_usage(p.name, response)
        return response
    
    async def chat(
        self,
        messages: List[Message],
        provider: str = None,
        **kwargs,
    ) -> LLMResponse:
        """Chat using a provider."""
        p = self.get_provider(provider)
        response = await p.chat(messages, **kwargs)
        self._record_usage(p.name, response)
        return response
    
    def _record_usage(self, provider_name: str, response: LLMResponse):
        """Record usage for tracking."""
        self._usage_history.append({
            "provider": provider_name,
            "model": response.model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cost": response.usage.total_cost,
            "latency_ms": response.latency_ms,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        self._total_cost += response.usage.total_cost
        
        # Limit history
        if len(self._usage_history) > 10000:
            self._usage_history = self._usage_history[-10000:]
    
    def get_usage_stats(self) -> dict:
        """Get usage statistics."""
        by_provider = {}
        by_model = {}
        
        for usage in self._usage_history:
            p = usage["provider"]
            m = usage["model"]
            
            if p not in by_provider:
                by_provider[p] = {"count": 0, "tokens": 0, "cost": 0.0}
            by_provider[p]["count"] += 1
            by_provider[p]["tokens"] += usage["input_tokens"] + usage["output_tokens"]
            by_provider[p]["cost"] += usage["cost"]
            
            if m not in by_model:
                by_model[m] = {"count": 0, "tokens": 0, "cost": 0.0}
            by_model[m]["count"] += 1
            by_model[m]["tokens"] += usage["input_tokens"] + usage["output_tokens"]
            by_model[m]["cost"] += usage["cost"]
        
        return {
            "total_requests": len(self._usage_history),
            "total_cost": round(self._total_cost, 4),
            "by_provider": by_provider,
            "by_model": by_model,
        }
    
    async def health_check(self) -> dict:
        """Check health of all providers."""
        results = {}
        for name, provider in self._providers.items():
            try:
                healthy = await provider.health_check()
                results[name] = {"healthy": healthy}
            except Exception as e:
                results[name] = {"healthy": False, "error": str(e)}
        return results


# =============================================================================
# Global Registry
# =============================================================================

_registry: Optional[LLMRegistry] = None


def get_llm_registry() -> LLMRegistry:
    """Get global LLM registry."""
    global _registry
    if _registry is None:
        _registry = LLMRegistry()
        
        # Register default providers
        _registry.register_provider(
            "bedrock-claude",
            LLMConfig(
                provider="bedrock",
                model="anthropic.claude-3-sonnet",
                region="us-east-1",
            ),
        )
        
        _registry.register_provider(
            "ollama-llama",
            LLMConfig(
                provider="ollama",
                model="llama3",
                api_base="http://localhost:11434",
            ),
        )
    
    return _registry


def get_provider_for_model(model: str) -> str:
    """Get provider name for a model."""
    return MODEL_PROVIDERS.get(model, "bedrock")
