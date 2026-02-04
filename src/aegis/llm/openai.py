"""
OpenAI LLM Provider

Supports:
- GPT-4o, GPT-4 Turbo
- GPT-3.5 Turbo
- o1-preview, o1-mini
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
OPENAI_PRICING = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "o1-preview": {"input": 0.015, "output": 0.06},
    "o1-mini": {"input": 0.003, "output": 0.012},
}


class OpenAIProvider(LLMProvider):
    """
    OpenAI LLM provider.
    
    Supports GPT-4, GPT-3.5, and o1 models.
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenAI client."""
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout_seconds,
            )
            logger.info("OpenAI client initialized")
        except ImportError:
            logger.warning("openai package not installed, using mock client")
            self.client = None
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}")
            self.client = None
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a single completion."""
        messages = []
        if system_prompt:
            messages.append(Message(role=Role.SYSTEM, content=system_prompt))
        messages.append(Message(role=Role.USER, content=prompt))
        
        return await self.chat(messages, **kwargs)
    
    async def chat(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs,
    ) -> LLMResponse:
        """Multi-turn chat completion."""
        start_time = datetime.utcnow()
        
        if not self.client:
            return self._mock_response(messages, start_time)
        
        try:
            # Format messages
            formatted_messages = [
                {"role": msg.role.value, "content": msg.content}
                for msg in messages
            ]
            
            # Build request
            request = {
                "model": self.config.model,
                "messages": formatted_messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }
            
            # Add tools if provided
            if tools:
                request["tools"] = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters,
                        },
                    }
                    for tool in tools
                ]
            
            # JSON mode
            if self.config.json_mode:
                request["response_format"] = {"type": "json_object"}
            
            # Call API
            response = await self.client.chat.completions.create(**request)
            
            # Extract content
            choice = response.choices[0]
            content = choice.message.content or ""
            
            # Extract tool calls
            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                    for tc in choice.message.tool_calls
                ]
            
            # Usage
            usage = TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
            usage = self.calculate_cost(usage)
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return LLMResponse(
                content=content,
                model=self.config.model,
                provider="openai",
                usage=usage,
                latency_ms=latency_ms,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                raw_response=response.model_dump(),
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._mock_response(messages, start_time)
    
    async def stream(
        self,
        messages: List[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream generation."""
        if not self.client:
            yield "Streaming not available in mock mode."
            return
        
        formatted_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.config.model,
                messages=formatted_messages,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                stream=True,
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            yield f"Error: {str(e)}"
    
    def calculate_cost(self, usage: TokenUsage) -> TokenUsage:
        """Calculate cost based on model pricing."""
        pricing = OPENAI_PRICING.get(self.config.model, {"input": 0.005, "output": 0.015})
        usage.input_cost = (usage.input_tokens / 1000) * pricing["input"]
        usage.output_cost = (usage.output_tokens / 1000) * pricing["output"]
        usage.total_cost = usage.input_cost + usage.output_cost
        return usage
    
    def _mock_response(self, messages: List[Message], start_time: datetime) -> LLMResponse:
        """Generate mock response for testing."""
        user_msg = next((m.content for m in reversed(messages) if m.role == Role.USER), "")
        
        mock_content = f"[Mock OpenAI Response] Processing: {user_msg[:100]}..."
        
        return LLMResponse(
            content=mock_content,
            model=self.config.model,
            provider="openai",
            usage=TokenUsage(
                input_tokens=len(user_msg.split()) * 2,
                output_tokens=len(mock_content.split()) * 2,
                total_tokens=len(user_msg.split()) * 2 + len(mock_content.split()) * 2,
            ),
            latency_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000) + 50,
            finish_reason="stop",
        )
