"""
LLM Gateway

Unified interface to multiple LLM providers with:
- Automatic failover
- Load balancing
- Rate limiting
- Cost tracking
- Audit logging
"""

import time
from typing import AsyncIterator
import structlog

from aegis_ai.models import LLMRequest, LLMResponse, Message
from aegis_ai.providers.base import BaseLLMProvider, LLMError, RateLimitError
from aegis_ai.providers.bedrock import BedrockProvider
from aegis_ai.providers.openai import OpenAIProvider

logger = structlog.get_logger(__name__)


class LLMGateway:
    """
    Unified LLM Gateway.
    
    Routes requests to appropriate providers with failover support.
    Tracks usage and costs for billing.
    """
    
    # Cost per 1K tokens (approximate)
    TOKEN_COSTS = {
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }
    
    def __init__(
        self,
        primary_provider: str = "bedrock",
        fallback_providers: list[str] | None = None,
        config: dict | None = None
    ):
        self.primary_provider = primary_provider
        self.fallback_providers = fallback_providers or ["openai"]
        self.config = config or {}
        
        self._providers: dict[str, BaseLLMProvider] = {}
        self._initialized = False
        
        # Usage tracking
        self._total_requests = 0
        self._total_tokens = 0
        self._total_cost = 0.0
    
    async def initialize(self) -> None:
        """Initialize all configured providers."""
        all_providers = [self.primary_provider] + self.fallback_providers
        
        for provider_name in all_providers:
            try:
                provider = self._create_provider(provider_name)
                await provider.initialize()
                self._providers[provider_name] = provider
                logger.info(f"Initialized {provider_name} provider")
            except Exception as e:
                logger.warning(f"Failed to initialize {provider_name}", error=str(e))
        
        if not self._providers:
            raise LLMError("No LLM providers available")
        
        self._initialized = True
    
    def _create_provider(self, name: str) -> BaseLLMProvider:
        """Create a provider instance."""
        provider_config = self.config.get(name, {})
        
        if name == "bedrock":
            return BedrockProvider(
                model=provider_config.get("model", "claude-3-sonnet"),
                region=provider_config.get("region", "us-east-1"),
            )
        elif name == "openai":
            return OpenAIProvider(
                model=provider_config.get("model", "gpt-4-turbo"),
                api_key=provider_config.get("api_key"),
                azure_endpoint=provider_config.get("azure_endpoint"),
            )
        else:
            raise ValueError(f"Unknown provider: {name}")
    
    async def complete(
        self,
        messages: list[Message] | str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a completion with automatic failover.
        
        Args:
            messages: Conversation messages or simple prompt string
            model: Optional model override
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            tools: Tool definitions for function calling
            **kwargs: Additional request parameters
            
        Returns:
            LLM response
        """
        if not self._initialized:
            await self.initialize()
        
        # Convert string to messages
        if isinstance(messages, str):
            messages = [Message.user(messages)]
        
        request = LLMRequest(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            **kwargs
        )
        
        # Try providers in order
        providers_to_try = [self.primary_provider] + self.fallback_providers
        last_error = None
        
        for provider_name in providers_to_try:
            provider = self._providers.get(provider_name)
            if not provider:
                continue
            
            try:
                response = await provider.complete(request)
                
                # Track usage
                self._track_usage(response)
                
                # Log for audit
                self._log_request(request, response)
                
                return response
                
            except RateLimitError as e:
                logger.warning(f"Rate limited on {provider_name}, trying fallback")
                last_error = e
                continue
                
            except LLMError as e:
                logger.warning(f"Error on {provider_name}: {e}, trying fallback")
                last_error = e
                continue
        
        raise LLMError(f"All providers failed. Last error: {last_error}")
    
    async def stream(
        self,
        messages: list[Message] | str,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a completion."""
        if not self._initialized:
            await self.initialize()
        
        if isinstance(messages, str):
            messages = [Message.user(messages)]
        
        request = LLMRequest(messages=messages, **kwargs)
        
        provider = self._providers.get(self.primary_provider)
        if not provider:
            provider = list(self._providers.values())[0]
        
        async for token in provider.stream(request):
            yield token
    
    async def chat(
        self,
        prompt: str,
        system: str | None = None,
        **kwargs
    ) -> str:
        """
        Simple chat interface.
        
        Args:
            prompt: User message
            system: Optional system prompt
            **kwargs: Additional parameters
            
        Returns:
            Assistant response text
        """
        messages = []
        if system:
            messages.append(Message.system(system))
        messages.append(Message.user(prompt))
        
        response = await self.complete(messages, **kwargs)
        return response.content or ""
    
    def _track_usage(self, response: LLMResponse) -> None:
        """Track token usage and cost."""
        self._total_requests += 1
        self._total_tokens += response.total_tokens
        
        # Calculate cost
        costs = self.TOKEN_COSTS.get(response.model, {"input": 0.01, "output": 0.03})
        cost = (
            (response.input_tokens / 1000) * costs["input"] +
            (response.output_tokens / 1000) * costs["output"]
        )
        self._total_cost += cost
    
    def _log_request(self, request: LLMRequest, response: LLMResponse) -> None:
        """Log request for audit trail."""
        logger.info(
            "LLM request",
            request_id=request.request_id,
            provider=response.provider,
            model=response.model,
            tokens=response.total_tokens,
            latency_ms=response.latency_ms,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        )
    
    def get_usage_stats(self) -> dict:
        """Get usage statistics."""
        return {
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "total_cost_usd": round(self._total_cost, 4),
        }


# Global gateway instance
_gateway: LLMGateway | None = None


async def get_llm_gateway(config: dict | None = None) -> LLMGateway:
    """Get the global LLM gateway."""
    global _gateway
    
    if _gateway is None:
        _gateway = LLMGateway(config=config)
        await _gateway.initialize()
    
    return _gateway
