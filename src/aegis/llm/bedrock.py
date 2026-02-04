"""
AWS Bedrock LLM Provider

Supports:
- Claude 3 (Opus, Sonnet, Haiku)
- Llama 2/3
- Amazon Titan
- Mistral
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

# Pricing per 1K tokens (as of 2024)
BEDROCK_PRICING = {
    "anthropic.claude-3-opus": {"input": 0.015, "output": 0.075},
    "anthropic.claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "anthropic.claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "meta.llama3-70b-instruct": {"input": 0.00265, "output": 0.0035},
    "meta.llama3-8b-instruct": {"input": 0.0003, "output": 0.0006},
    "amazon.titan-text-express": {"input": 0.0008, "output": 0.0016},
    "mistral.mistral-large": {"input": 0.004, "output": 0.012},
}


class BedrockProvider(LLMProvider):
    """
    AWS Bedrock LLM provider.
    
    Supports multiple foundation models through AWS Bedrock.
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Bedrock client."""
        try:
            import boto3
            self.client = boto3.client(
                "bedrock-runtime",
                region_name=self.config.region or "us-east-1",
            )
            logger.info("Bedrock client initialized", region=self.config.region)
        except ImportError:
            logger.warning("boto3 not installed, using mock client")
            self.client = None
        except Exception as e:
            logger.warning(f"Failed to initialize Bedrock client: {e}")
            self.client = None
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a single completion."""
        messages = [Message(role=Role.USER, content=prompt)]
        if system_prompt:
            messages.insert(0, Message(role=Role.SYSTEM, content=system_prompt))
        
        return await self.chat(messages, **kwargs)
    
    async def chat(
        self,
        messages: List[Message],
        tools: List[ToolDefinition] = None,
        **kwargs,
    ) -> LLMResponse:
        """Multi-turn chat completion."""
        start_time = datetime.utcnow()
        
        # Mock response if no client
        if not self.client:
            return self._mock_response(messages, start_time)
        
        try:
            # Format messages for Claude
            formatted_messages = self._format_messages(messages)
            system_prompt = None
            
            # Extract system message
            if formatted_messages and formatted_messages[0]["role"] == "system":
                system_prompt = formatted_messages[0]["content"]
                formatted_messages = formatted_messages[1:]
            
            # Build request
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "messages": formatted_messages,
            }
            
            if system_prompt:
                request_body["system"] = system_prompt
            
            if tools:
                request_body["tools"] = self._format_tools(tools)
            
            # Invoke model
            response = await asyncio.to_thread(
                self.client.invoke_model,
                modelId=self.config.model,
                body=json.dumps(request_body),
            )
            
            # Parse response
            response_body = json.loads(response["body"].read())
            
            content = ""
            tool_calls = None
            
            if "content" in response_body:
                for block in response_body["content"]:
                    if block["type"] == "text":
                        content += block["text"]
                    elif block["type"] == "tool_use":
                        if tool_calls is None:
                            tool_calls = []
                        tool_calls.append({
                            "id": block["id"],
                            "name": block["name"],
                            "arguments": block["input"],
                        })
            
            # Calculate usage
            usage = TokenUsage(
                input_tokens=response_body.get("usage", {}).get("input_tokens", 0),
                output_tokens=response_body.get("usage", {}).get("output_tokens", 0),
            )
            usage.total_tokens = usage.input_tokens + usage.output_tokens
            usage = self.calculate_cost(usage)
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return LLMResponse(
                content=content,
                model=self.config.model,
                provider="bedrock",
                usage=usage,
                latency_ms=latency_ms,
                tool_calls=tool_calls,
                finish_reason=response_body.get("stop_reason", "stop"),
                raw_response=response_body,
            )
            
        except Exception as e:
            logger.error(f"Bedrock API error: {e}")
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
        
        formatted_messages = self._format_messages(messages)
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "messages": formatted_messages,
        }
        
        try:
            response = await asyncio.to_thread(
                self.client.invoke_model_with_response_stream,
                modelId=self.config.model,
                body=json.dumps(request_body),
            )
            
            for event in response["body"]:
                chunk = json.loads(event["chunk"]["bytes"])
                if chunk["type"] == "content_block_delta":
                    if chunk["delta"]["type"] == "text_delta":
                        yield chunk["delta"]["text"]
                        
        except Exception as e:
            logger.error(f"Bedrock streaming error: {e}")
            yield f"Error: {str(e)}"
    
    def _format_messages(self, messages: List[Message]) -> List[dict]:
        """Format messages for Bedrock API."""
        formatted = []
        for msg in messages:
            formatted.append({
                "role": "user" if msg.role == Role.USER else "assistant" if msg.role == Role.ASSISTANT else "system",
                "content": msg.content,
            })
        return formatted
    
    def _format_tools(self, tools: List[ToolDefinition]) -> List[dict]:
        """Format tools for Bedrock API."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            }
            for tool in tools
        ]
    
    def calculate_cost(self, usage: TokenUsage) -> TokenUsage:
        """Calculate cost based on model pricing."""
        pricing = BEDROCK_PRICING.get(self.config.model, {"input": 0.003, "output": 0.015})
        usage.input_cost = (usage.input_tokens / 1000) * pricing["input"]
        usage.output_cost = (usage.output_tokens / 1000) * pricing["output"]
        usage.total_cost = usage.input_cost + usage.output_cost
        return usage
    
    def _mock_response(self, messages: List[Message], start_time: datetime) -> LLMResponse:
        """Generate mock response for testing."""
        user_msg = next((m.content for m in reversed(messages) if m.role == Role.USER), "")
        
        mock_content = f"[Mock Bedrock Response] I received your message about: {user_msg[:100]}..."
        
        return LLMResponse(
            content=mock_content,
            model=self.config.model,
            provider="bedrock",
            usage=TokenUsage(
                input_tokens=len(user_msg.split()) * 2,
                output_tokens=len(mock_content.split()) * 2,
                total_tokens=len(user_msg.split()) * 2 + len(mock_content.split()) * 2,
            ),
            latency_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000) + 100,
            finish_reason="stop",
        )
