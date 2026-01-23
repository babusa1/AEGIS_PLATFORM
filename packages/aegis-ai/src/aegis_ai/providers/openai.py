"""
OpenAI Provider

Fallback LLM provider using OpenAI API.
Also supports Azure OpenAI for enterprise deployments.
"""

import time
from typing import AsyncIterator
import structlog

from aegis_ai.providers.base import BaseLLMProvider, LLMError, RateLimitError
from aegis_ai.models import LLMRequest, LLMResponse, ToolCall

logger = structlog.get_logger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI LLM provider.
    
    Supports GPT-4 and GPT-3.5 models.
    Can use Azure OpenAI for BAA-covered deployments.
    """
    
    def __init__(
        self,
        model: str = "gpt-4-turbo",
        api_key: str | None = None,
        organization: str | None = None,
        azure_endpoint: str | None = None,
        azure_deployment: str | None = None,
        **kwargs
    ):
        super().__init__(model=model, api_key=api_key, **kwargs)
        self.organization = organization
        self.azure_endpoint = azure_endpoint
        self.azure_deployment = azure_deployment
        self._client = None
    
    @property
    def provider_name(self) -> str:
        return "azure-openai" if self.azure_endpoint else "openai"
    
    @property
    def is_azure(self) -> bool:
        return self.azure_endpoint is not None
    
    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        try:
            import openai
            
            if self.is_azure:
                self._client = openai.AzureOpenAI(
                    api_key=self.api_key,
                    azure_endpoint=self.azure_endpoint,
                    api_version="2024-02-15-preview"
                )
            else:
                self._client = openai.OpenAI(
                    api_key=self.api_key,
                    organization=self.organization
                )
            
            self._initialized = True
            logger.info("OpenAI provider initialized", model=self.model)
            
        except Exception as e:
            logger.error("Failed to initialize OpenAI", error=str(e))
            raise LLMError(f"OpenAI initialization failed: {e}")
    
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Generate completion via OpenAI."""
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            messages = self._format_openai_messages(request.messages)
            
            kwargs = {
                "model": self.azure_deployment if self.is_azure else (request.model or self.model),
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }
            
            if request.tools:
                kwargs["tools"] = request.tools
                if request.tool_choice:
                    kwargs["tool_choice"] = request.tool_choice
            
            response = self._client.chat.completions.create(**kwargs)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            choice = response.choices[0]
            message = choice.message
            
            # Extract tool calls
            tool_calls = None
            if message.tool_calls:
                tool_calls = []
                for tc in message.tool_calls:
                    import json
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments)
                    ))
            
            return LLMResponse(
                content=message.content,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                provider=self.provider_name,
                model=response.model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                latency_ms=latency_ms,
                request_id=request.request_id,
            )
            
        except Exception as e:
            error_str = str(e)
            if "rate_limit" in error_str.lower():
                raise RateLimitError(f"OpenAI rate limit: {e}")
            logger.error("OpenAI completion failed", error=error_str)
            raise LLMError(f"OpenAI error: {e}")
    
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Stream completion via OpenAI."""
        if not self._initialized:
            await self.initialize()
        
        try:
            messages = self._format_openai_messages(request.messages)
            
            kwargs = {
                "model": self.azure_deployment if self.is_azure else (request.model or self.model),
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": True,
            }
            
            response = self._client.chat.completions.create(**kwargs)
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error("OpenAI stream failed", error=str(e))
            raise LLMError(f"OpenAI stream error: {e}")
    
    def _format_openai_messages(self, messages: list) -> list[dict]:
        """Format messages for OpenAI API."""
        formatted = []
        for msg in messages:
            entry = {
                "role": msg.role.value,
                "content": msg.content,
            }
            if msg.name:
                entry["name"] = msg.name
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            formatted.append(entry)
        return formatted
