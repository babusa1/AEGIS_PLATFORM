"""
LLM Provider API Routes

Endpoints for:
- Multi-provider LLM access
- Streaming generation
- Usage tracking
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from aegis.llm import (
    LLMRegistry, get_llm_registry,
    LLMConfig, Message, Role,
)

router = APIRouter(prefix="/llm", tags=["llm"])


# =============================================================================
# Models
# =============================================================================

class GenerateRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    provider: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048


class ChatRequest(BaseModel):
    messages: List[dict]  # [{role, content}]
    provider: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048


class ProviderConfig(BaseModel):
    name: str
    provider: str  # bedrock, openai, anthropic, ollama
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    region: Optional[str] = None


# =============================================================================
# Provider Management
# =============================================================================

@router.get("/providers")
async def list_providers():
    """List all registered LLM providers."""
    registry = get_llm_registry()
    return registry.list_providers()


@router.post("/providers")
async def register_provider(config: ProviderConfig):
    """Register a new LLM provider."""
    registry = get_llm_registry()
    
    llm_config = LLMConfig(
        provider=config.provider,
        model=config.model,
        api_key=config.api_key,
        api_base=config.api_base,
        region=config.region,
    )
    
    registry.register_provider(config.name, llm_config)
    
    return {"status": "registered", "name": config.name}


@router.post("/providers/{name}/default")
async def set_default_provider(name: str):
    """Set the default provider."""
    registry = get_llm_registry()
    
    try:
        registry.set_default(name)
        return {"status": "updated", "default": name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/providers/health")
async def check_provider_health():
    """Check health of all providers."""
    registry = get_llm_registry()
    return await registry.health_check()


# =============================================================================
# Generation
# =============================================================================

@router.post("/generate")
async def generate(request: GenerateRequest):
    """Generate a single completion."""
    registry = get_llm_registry()
    
    try:
        response = await registry.generate(
            prompt=request.prompt,
            provider=request.provider,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        return {
            "content": response.content,
            "model": response.model,
            "provider": response.provider,
            "usage": response.usage.dict(),
            "latency_ms": response.latency_ms,
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(request: ChatRequest):
    """Multi-turn chat completion."""
    registry = get_llm_registry()
    
    # Convert messages
    messages = [
        Message(
            role=Role(m["role"]),
            content=m["content"],
        )
        for m in request.messages
    ]
    
    try:
        response = await registry.chat(
            messages=messages,
            provider=request.provider,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        return {
            "content": response.content,
            "model": response.model,
            "provider": response.provider,
            "usage": response.usage.dict(),
            "latency_ms": response.latency_ms,
            "tool_calls": response.tool_calls,
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def stream_generate(request: ChatRequest):
    """Stream generation."""
    registry = get_llm_registry()
    
    messages = [
        Message(role=Role(m["role"]), content=m["content"])
        for m in request.messages
    ]
    
    provider = registry.get_provider(request.provider)
    
    async def generate_stream():
        async for chunk in provider.stream(messages):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
    )


# =============================================================================
# Usage & Stats
# =============================================================================

@router.get("/usage")
async def get_usage_stats():
    """Get LLM usage statistics."""
    registry = get_llm_registry()
    return registry.get_usage_stats()


@router.get("/models")
async def list_available_models():
    """List available models by provider."""
    return {
        "bedrock": [
            {"model": "anthropic.claude-3-opus", "description": "Most capable Claude model"},
            {"model": "anthropic.claude-3-sonnet", "description": "Balanced performance"},
            {"model": "anthropic.claude-3-haiku", "description": "Fastest, most compact"},
            {"model": "meta.llama3-70b-instruct", "description": "Llama 3 70B"},
            {"model": "meta.llama3-8b-instruct", "description": "Llama 3 8B"},
        ],
        "openai": [
            {"model": "gpt-4o", "description": "Latest GPT-4 Omni"},
            {"model": "gpt-4o-mini", "description": "Smaller, faster GPT-4"},
            {"model": "gpt-4-turbo", "description": "GPT-4 Turbo"},
            {"model": "gpt-3.5-turbo", "description": "Fast and capable"},
            {"model": "o1-preview", "description": "Reasoning model"},
        ],
        "anthropic": [
            {"model": "claude-3-5-sonnet-20241022", "description": "Latest Sonnet"},
            {"model": "claude-3-opus-20240229", "description": "Most capable"},
            {"model": "claude-3-haiku-20240307", "description": "Fastest"},
        ],
        "ollama": [
            {"model": "llama3", "description": "Llama 3 8B local"},
            {"model": "llama3:70b", "description": "Llama 3 70B local"},
            {"model": "mistral", "description": "Mistral 7B"},
            {"model": "codellama", "description": "Code Llama"},
            {"model": "phi3", "description": "Microsoft Phi-3"},
        ],
    }
