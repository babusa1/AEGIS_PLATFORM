"""
Anthropic LLM Provider (Direct API)

Supports:
- Claude 3.5 Sonnet
- Claude 3 Opus, Sonnet, Haiku
"""

from typing import Any, AsyncIterator, Dict, List, Optional
from datetime import datetime
import json
import asyncio

import structlog
from pydantic import BaseModel

from aegis.llm.providers import (
    LLMProvider, LLMConfig, LLMResponse, Message, Role, 
    ToolDefinition, TokenUsage
)

logger = structlog.get_logger(__name__)

# Pricing per 1K tokens
ANTHROPIC_PRICING = {
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
}


class AnthropicProvider(LLMProvider):
    """
    Anthropic direct API provider.
    
    Use this for direct Anthropic API access (not through Bedrock).
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Anthropic client."""
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(
                api_key=self.config.api_key,
            )
            logger.info("Anthropic client initialized")
        except ImportError:
            logger.warning("anthropic package not installed, using mock client")
            self.client = None
        except Exception as e:
            logger.warning(f"Failed to initialize Anthropic client: {e}")
            self.client = None
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a single completion."""
        messages = [Message(role=Role.USER, content=prompt)]
        
        return await self.chat(
            messages,
            system_prompt=system_prompt,
            **kwargs,
        )
    
    async def chat(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        system_prompt: str = None,
        **kwargs,
    ) -> LLMResponse:
        """Multi-turn chat completion."""
        start_time = datetime.utcnow()
        
        if not self.client:
            return self._mock_response(messages, start_time)
        
        try:
            # Extract system message
            if not system_prompt:
                for msg in messages:
                    if msg.role == Role.SYSTEM:
                        system_prompt = msg.content
                        break
            
            # Format messages (exclude system)
            formatted_messages = [
                {"role": "user" if msg.role == Role.USER else "assistant", "content": msg.content}
                for msg in messages
                if msg.role != Role.SYSTEM
            ]
            
            # Build request
            request = {
                "model": self.config.model,
                "messages": formatted_messages,
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
            }
            
            if system_prompt:
                request["system"] = system_prompt
            
            if tools:
                request["tools"] = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.parameters,
                    }
                    for tool in tools
                ]
            
            # Call API
            response = await self.client.messages.create(**request)
            
            # Extract content
            content = ""
            tool_calls = None
            
            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input,
                    })
            
            # Usage
            usage = TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )
            usage = self.calculate_cost(usage)
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return LLMResponse(
                content=content,
                model=self.config.model,
                provider="anthropic",
                usage=usage,
                latency_ms=latency_ms,
                tool_calls=tool_calls,
                finish_reason=response.stop_reason or "stop",
            )
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return self._mock_response(messages, start_time)
    
    async def stream(
        self,
        messages: List[Message],
        system_prompt: str = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream generation."""
        if not self.client:
            yield "Streaming not available in mock mode."
            return
        
        formatted_messages = [
            {"role": "user" if msg.role == Role.USER else "assistant", "content": msg.content}
            for msg in messages
            if msg.role != Role.SYSTEM
        ]
        
        try:
            async with self.client.messages.stream(
                model=self.config.model,
                messages=formatted_messages,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
                system=system_prompt,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            yield f"Error: {str(e)}"
    
    def calculate_cost(self, usage: TokenUsage) -> TokenUsage:
        """Calculate cost based on model pricing."""
        pricing = ANTHROPIC_PRICING.get(self.config.model, {"input": 0.003, "output": 0.015})
        usage.input_cost = (usage.input_tokens / 1000) * pricing["input"]
        usage.output_cost = (usage.output_tokens / 1000) * pricing["output"]
        usage.total_cost = usage.input_cost + usage.output_cost
        return usage
    
    def _mock_response(self, messages: List[Message], start_time: datetime) -> LLMResponse:
        """Generate mock response for testing."""
        user_msg = next((m.content for m in reversed(messages) if m.role == Role.USER), "")
        
        mock_content = f"[Mock Anthropic Response] Analyzing: {user_msg[:100]}..."
        
        return LLMResponse(
            content=mock_content,
            model=self.config.model,
            provider="anthropic",
            usage=TokenUsage(
                input_tokens=len(user_msg.split()) * 2,
                output_tokens=len(mock_content.split()) * 2,
                total_tokens=len(user_msg.split()) * 2 + len(mock_content.split()) * 2,
            ),
            latency_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000) + 75,
            finish_reason="stop",
        )
