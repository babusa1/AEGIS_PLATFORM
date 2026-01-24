"""Embedding Service"""
from dataclasses import dataclass
from enum import Enum
import hashlib
import structlog

logger = structlog.get_logger(__name__)


class EmbeddingModel(str, Enum):
    OPENAI_3_SMALL = "text-embedding-3-small"
    OPENAI_3_LARGE = "text-embedding-3-large"
    BEDROCK_TITAN = "amazon.titan-embed-text-v1"
    LOCAL = "local"


@dataclass
class EmbeddingResult:
    text: str
    embedding: list[float]
    model: str
    dimensions: int


class EmbeddingService:
    def __init__(self, model: EmbeddingModel = EmbeddingModel.LOCAL, api_key: str | None = None):
        self.model = model
        self.api_key = api_key
    
    async def embed(self, text: str) -> EmbeddingResult:
        if self.model.value.startswith("text-embedding"):
            return await self._embed_openai(text)
        return self._embed_local(text)
    
    async def _embed_openai(self, text: str) -> EmbeddingResult:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key)
            response = await client.embeddings.create(model=self.model.value, input=text)
            emb = response.data[0].embedding
            return EmbeddingResult(text[:100], emb, self.model.value, len(emb))
        except Exception as e:
            logger.warning("OpenAI failed, using local", error=str(e))
            return self._embed_local(text)
    
    def _embed_local(self, text: str) -> EmbeddingResult:
        h = hashlib.sha256(text.encode()).digest()
        emb = [float(b) / 255.0 for b in h] * 48
        return EmbeddingResult(text[:100], emb[:1536], "local", 1536)
