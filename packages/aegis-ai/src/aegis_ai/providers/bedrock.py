"""
AWS Bedrock Provider

Primary LLM provider using AWS Bedrock (Claude).
HIPAA-eligible for healthcare workloads.
"""

import json
import time
from typing import AsyncIterator
import structlog

from aegis_ai.providers.base import BaseLLMProvider, LLMError
from aegis_ai.models import LLMRequest, LLMResponse, ToolCall

logger = structlog.get_logger(__name__)


class BedrockProvider(BaseLLMProvider):
    """
    AWS Bedrock LLM provider.
    
    Supports Claude models via Bedrock's Converse API.
    HIPAA-eligible when using BAA-covered account.
    """
    
    # Model mappings
    MODEL_IDS = {
        "claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
        "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
        "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "claude-3-5-sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    }
    
    def __init__(
        self,
        model: str = "claude-3-sonnet",
        region: str = "us-east-1",
        **kwargs
    ):
        super().__init__(model=model, **kwargs)
        self.region = region
        self._client = None
    
    @property
    def provider_name(self) -> str:
        return "bedrock"
    
    @property
    def model_id(self) -> str:
        return self.MODEL_IDS.get(self.model, self.model)
    
    async def initialize(self) -> None:
        """Initialize Bedrock client."""
        try:
            import boto3
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self.region
            )
            self._initialized = True
            logger.info("Bedrock provider initialized", model=self.model)
        except Exception as e:
            logger.error("Failed to initialize Bedrock", error=str(e))
            raise LLMError(f"Bedrock initialization failed: {e}")
    
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Generate completion via Bedrock Converse API."""
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Format messages for Converse API
            messages = self._format_converse_messages(request.messages)
            
            # Build request
            converse_request = {
                "modelId": self.model_id,
                "messages": messages,
                "inferenceConfig": {
                    "maxTokens": request.max_tokens,
                    "temperature": request.temperature,
                }
            }
            
            # Add system prompt if present
            system_msgs = [m for m in request.messages if m.role.value == "system"]
            if system_msgs:
                converse_request["system"] = [{"text": system_msgs[0].content}]
            
            # Add tools if present
            if request.tools:
                converse_request["toolConfig"] = {
                    "tools": self._format_bedrock_tools(request.tools)
                }
            
            # Call Bedrock
            response = self._client.converse(**converse_request)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Parse response
            output = response.get("output", {})
            message = output.get("message", {})
            content_blocks = message.get("content", [])
            
            # Extract text and tool calls
            text_content = ""
            tool_calls = []
            
            for block in content_blocks:
                if "text" in block:
                    text_content += block["text"]
                elif "toolUse" in block:
                    tool_use = block["toolUse"]
                    tool_calls.append(ToolCall(
                        id=tool_use.get("toolUseId", ""),
                        name=tool_use.get("name", ""),
                        arguments=tool_use.get("input", {})
                    ))
            
            # Get usage
            usage = response.get("usage", {})
            
            return LLMResponse(
                content=text_content or None,
                tool_calls=tool_calls if tool_calls else None,
                finish_reason=response.get("stopReason"),
                provider=self.provider_name,
                model=self.model,
                input_tokens=usage.get("inputTokens", 0),
                output_tokens=usage.get("outputTokens", 0),
                total_tokens=usage.get("totalTokens", 0),
                latency_ms=latency_ms,
                request_id=request.request_id,
            )
            
        except Exception as e:
            logger.error("Bedrock completion failed", error=str(e))
            raise LLMError(f"Bedrock error: {e}")
    
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Stream completion via Bedrock."""
        if not self._initialized:
            await self.initialize()
        
        try:
            messages = self._format_converse_messages(request.messages)
            
            converse_request = {
                "modelId": self.model_id,
                "messages": messages,
                "inferenceConfig": {
                    "maxTokens": request.max_tokens,
                    "temperature": request.temperature,
                }
            }
            
            system_msgs = [m for m in request.messages if m.role.value == "system"]
            if system_msgs:
                converse_request["system"] = [{"text": system_msgs[0].content}]
            
            response = self._client.converse_stream(**converse_request)
            
            for event in response.get("stream", []):
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    if "text" in delta:
                        yield delta["text"]
                        
        except Exception as e:
            logger.error("Bedrock stream failed", error=str(e))
            raise LLMError(f"Bedrock stream error: {e}")
    
    def _format_converse_messages(self, messages: list) -> list[dict]:
        """Format messages for Bedrock Converse API."""
        formatted = []
        for msg in messages:
            if msg.role.value == "system":
                continue  # System handled separately
            
            role = "user" if msg.role.value == "user" else "assistant"
            
            if msg.role.value == "tool":
                # Tool result format
                formatted.append({
                    "role": "user",
                    "content": [{
                        "toolResult": {
                            "toolUseId": msg.tool_call_id,
                            "content": [{"text": msg.content}]
                        }
                    }]
                })
            else:
                formatted.append({
                    "role": role,
                    "content": [{"text": msg.content}]
                })
        
        return formatted
    
    def _format_bedrock_tools(self, tools: list[dict]) -> list[dict]:
        """Format tools for Bedrock."""
        bedrock_tools = []
        for tool in tools:
            if "function" in tool:
                func = tool["function"]
                bedrock_tools.append({
                    "toolSpec": {
                        "name": func.get("name"),
                        "description": func.get("description", ""),
                        "inputSchema": {
                            "json": func.get("parameters", {})
                        }
                    }
                })
        return bedrock_tools
