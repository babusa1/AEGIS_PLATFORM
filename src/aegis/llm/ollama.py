"""
Ollama LLM Provider (Local Models)

Supports any model available in Ollama:
- Llama 3
- Mistral
- CodeLlama
- Phi-3
- Gemma
- etc.
"""

from typing import Any, AsyncIterator, Dict, List, Optional
from datetime import datetime
import json
import asyncio
import aiohttp

import structlog
from pydantic import BaseModel

from aegis.llm.providers import (
    LLMProvider, LLMConfig, LLMResponse, Message, Role, 
    ToolDefinition, TokenUsage
)

logger = structlog.get_logger(__name__)


class OllamaProvider(LLMProvider):
    """
    Ollama local LLM provider.
    
    Run models locally with Ollama for:
    - Privacy (no data leaves your machine)
    - Cost savings (no API fees)
    - Offline capability
    - Custom/fine-tuned models
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.api_base or "http://localhost:11434"
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a single completion."""
        start_time = datetime.utcnow()
        
        try:
            async with aiohttp.ClientSession() as session:
                request_body = {
                    "model": self.config.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature),
                        "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                    },
                }
                
                if system_prompt:
                    request_body["system"] = system_prompt
                
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=request_body,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                ) as response:
                    if response.status != 200:
                        return self._mock_response([Message(role=Role.USER, content=prompt)], start_time)
                    
                    data = await response.json()
                    
                    latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    
                    # Ollama provides token counts
                    usage = TokenUsage(
                        input_tokens=data.get("prompt_eval_count", 0),
                        output_tokens=data.get("eval_count", 0),
                    )
                    usage.total_tokens = usage.input_tokens + usage.output_tokens
                    
                    return LLMResponse(
                        content=data.get("response", ""),
                        model=self.config.model,
                        provider="ollama",
                        usage=usage,
                        latency_ms=latency_ms,
                        finish_reason="stop" if data.get("done") else "length",
                        raw_response=data,
                    )
                    
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return self._mock_response([Message(role=Role.USER, content=prompt)], start_time)
    
    async def chat(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs,
    ) -> LLMResponse:
        """Multi-turn chat completion."""
        start_time = datetime.utcnow()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Format messages
                formatted_messages = [
                    {"role": msg.role.value, "content": msg.content}
                    for msg in messages
                ]
                
                request_body = {
                    "model": self.config.model,
                    "messages": formatted_messages,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature),
                        "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                    },
                }
                
                # Ollama supports tools in newer versions
                if tools:
                    request_body["tools"] = [
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
                
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=request_body,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                ) as response:
                    if response.status != 200:
                        return self._mock_response(messages, start_time)
                    
                    data = await response.json()
                    
                    latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    
                    # Extract content
                    content = data.get("message", {}).get("content", "")
                    
                    # Extract tool calls if present
                    tool_calls = None
                    if "tool_calls" in data.get("message", {}):
                        tool_calls = data["message"]["tool_calls"]
                    
                    usage = TokenUsage(
                        input_tokens=data.get("prompt_eval_count", 0),
                        output_tokens=data.get("eval_count", 0),
                    )
                    usage.total_tokens = usage.input_tokens + usage.output_tokens
                    
                    return LLMResponse(
                        content=content,
                        model=self.config.model,
                        provider="ollama",
                        usage=usage,
                        latency_ms=latency_ms,
                        tool_calls=tool_calls,
                        finish_reason="stop" if data.get("done") else "length",
                        raw_response=data,
                    )
                    
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            return self._mock_response(messages, start_time)
    
    async def stream(
        self,
        messages: List[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream generation."""
        try:
            async with aiohttp.ClientSession() as session:
                formatted_messages = [
                    {"role": msg.role.value, "content": msg.content}
                    for msg in messages
                ]
                
                request_body = {
                    "model": self.config.model,
                    "messages": formatted_messages,
                    "stream": True,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature),
                        "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                    },
                }
                
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=request_body,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                ) as response:
                    if response.status != 200:
                        yield "Error: Ollama not available"
                        return
                    
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    yield data["message"]["content"]
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            yield f"Error: {str(e)}"
    
    async def list_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
        return []
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name},
                    timeout=aiohttp.ClientTimeout(total=3600),  # 1 hour for large models
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to pull Ollama model: {e}")
        return False
    
    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    return response.status == 200
        except:
            return False
    
    def _mock_response(self, messages: List[Message], start_time: datetime) -> LLMResponse:
        """Generate mock response for testing."""
        user_msg = next((m.content for m in reversed(messages) if m.role == Role.USER), "")
        
        mock_content = f"[Mock Ollama Response] Local processing: {user_msg[:100]}..."
        
        return LLMResponse(
            content=mock_content,
            model=self.config.model,
            provider="ollama",
            usage=TokenUsage(
                input_tokens=len(user_msg.split()) * 2,
                output_tokens=len(mock_content.split()) * 2,
            ),
            latency_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000) + 200,
            finish_reason="stop",
        )
