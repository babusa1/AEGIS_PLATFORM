"""
AEGIS Google Vertex AI / Gemini Provider

Supports Gemini models via Google Cloud Vertex AI.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator
import asyncio
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class VertexAIConfig:
    """Configuration for Vertex AI."""
    project_id: str
    location: str = "us-central1"
    model_id: str = "gemini-1.5-pro"
    max_output_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class VertexAIResponse:
    """Response from Vertex AI."""
    content: str
    model: str
    finish_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0


VERTEX_MODELS = {
    "gemini-1.5-pro": {
        "display_name": "Gemini 1.5 Pro",
        "max_tokens": 8192,
        "context_window": 1000000,
    },
    "gemini-1.5-flash": {
        "display_name": "Gemini 1.5 Flash",
        "max_tokens": 8192,
        "context_window": 1000000,
    },
}


class VertexAIProvider:
    """Google Vertex AI provider for Gemini models."""
    
    def __init__(self, config: VertexAIConfig):
        self.config = config
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the Vertex AI client."""
        try:
            import vertexai
            vertexai.init(project=self.config.project_id, location=self.config.location)
            self._initialized = True
            logger.info("Vertex AI initialized", model=self.config.model_id)
            return True
        except Exception as e:
            logger.error("Vertex AI init failed", error=str(e))
            return False
    
    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> VertexAIResponse:
        """Generate a response from Gemini."""
        if not self._initialized:
            await self.initialize()
        
        start = datetime.now(timezone.utc)
        
        try:
            from vertexai.generative_models import GenerativeModel, Part, Content
            
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(Content(role=role, parts=[Part.from_text(msg["content"])]))
            
            model = GenerativeModel(self.config.model_id, system_instruction=system_prompt)
            response = await asyncio.to_thread(
                model.generate_content,
                contents,
                generation_config={
                    "max_output_tokens": max_tokens or self.config.max_output_tokens,
                    "temperature": temperature or self.config.temperature,
                },
            )
            
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            
            return VertexAIResponse(
                content=response.text if hasattr(response, "text") else "",
                model=self.config.model_id,
                finish_reason="stop",
                latency_ms=latency,
            )
        except Exception as e:
            logger.error("Vertex AI generation failed", error=str(e))
            raise
    
    async def stream(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """Stream response from Gemini."""
        response = await self.generate(messages, **kwargs)
        for word in response.content.split():
            yield word + " "
    
    async def embed(self, texts: list[str], model: str = "textembedding-gecko@003") -> list[list[float]]:
        """Generate embeddings."""
        try:
            from vertexai.language_models import TextEmbeddingModel
            embedding_model = TextEmbeddingModel.from_pretrained(model)
            results = await asyncio.to_thread(embedding_model.get_embeddings, texts)
            return [r.values for r in results]
        except Exception as e:
            logger.error("Embedding failed", error=str(e))
            raise


class MockVertexAIProvider(VertexAIProvider):
    """Mock provider for development."""
    
    async def initialize(self) -> bool:
        self._initialized = True
        return True
    
    async def generate(self, messages: list[dict[str, str]], **kwargs) -> VertexAIResponse:
        return VertexAIResponse(
            content="[Mock Gemini Response]",
            model=self.config.model_id,
            usage={"prompt_tokens": 100, "completion_tokens": 50},
            latency_ms=100,
        )
    
    async def embed(self, texts: list[str], **kwargs) -> list[list[float]]:
        import random
        return [[random.random() for _ in range(768)] for _ in texts]


def get_vertex_provider(project_id: str | None = None, model_id: str = "gemini-1.5-pro", use_mock: bool = False) -> VertexAIProvider:
    """Get a Vertex AI provider instance."""
    config = VertexAIConfig(project_id=project_id or "mock-project", model_id=model_id)
    if use_mock or not project_id:
        return MockVertexAIProvider(config)
    return VertexAIProvider(config)
