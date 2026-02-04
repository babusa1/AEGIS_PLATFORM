"""
Embedding Models

Generate embeddings for text:
- AWS Bedrock Titan
- OpenAI Ada
- Local models (sentence-transformers)
"""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
import asyncio

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Base Embedding Model
# =============================================================================

class EmbeddingModel(ABC):
    """Abstract base class for embedding models."""
    
    def __init__(self, model_name: str, dimensions: int):
        self.model_name = model_name
        self.dimensions = dimensions
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        pass
    
    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text.split()) * 1.3  # Rough estimate


# =============================================================================
# AWS Bedrock Titan Embeddings
# =============================================================================

class BedrockEmbeddings(EmbeddingModel):
    """
    AWS Bedrock Titan Embeddings.
    
    Model: amazon.titan-embed-text-v1
    Dimensions: 1536
    Max tokens: 8192
    """
    
    def __init__(
        self,
        model_name: str = "amazon.titan-embed-text-v1",
        region: str = "us-east-1",
    ):
        super().__init__(model_name, dimensions=1536)
        self.region = region
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Bedrock client."""
        try:
            import boto3
            self.client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
            )
            logger.info("Bedrock embeddings client initialized")
        except ImportError:
            logger.warning("boto3 not installed")
        except Exception as e:
            logger.warning(f"Failed to initialize Bedrock client: {e}")
    
    async def embed(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        if not self.client:
            return self._mock_embedding()
        
        try:
            import json
            
            response = await asyncio.to_thread(
                self.client.invoke_model,
                modelId=self.model_name,
                body=json.dumps({"inputText": text}),
            )
            
            result = json.loads(response["body"].read())
            return result["embedding"]
            
        except Exception as e:
            logger.error(f"Bedrock embedding failed: {e}")
            return self._mock_embedding()
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        # Bedrock doesn't support batch, so we parallelize
        tasks = [self.embed(text) for text in texts]
        return await asyncio.gather(*tasks)
    
    def _mock_embedding(self) -> List[float]:
        """Generate mock embedding for testing."""
        import random
        return [random.uniform(-1, 1) for _ in range(self.dimensions)]


# =============================================================================
# OpenAI Embeddings
# =============================================================================

class OpenAIEmbeddings(EmbeddingModel):
    """
    OpenAI Embeddings.
    
    Model: text-embedding-3-small (1536 dims) or text-embedding-3-large (3072 dims)
    """
    
    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        api_key: str = None,
    ):
        dims = 3072 if "large" in model_name else 1536
        super().__init__(model_name, dimensions=dims)
        self.api_key = api_key
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenAI client."""
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=self.api_key)
            logger.info("OpenAI embeddings client initialized")
        except ImportError:
            logger.warning("openai package not installed")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}")
    
    async def embed(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        if not self.client:
            return self._mock_embedding()
        
        try:
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=text,
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            return self._mock_embedding()
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not self.client:
            return [self._mock_embedding() for _ in texts]
        
        try:
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
            return [item.embedding for item in response.data]
            
        except Exception as e:
            logger.error(f"OpenAI batch embedding failed: {e}")
            return [self._mock_embedding() for _ in texts]
    
    def _mock_embedding(self) -> List[float]:
        """Generate mock embedding for testing."""
        import random
        return [random.uniform(-1, 1) for _ in range(self.dimensions)]


# =============================================================================
# Local Embeddings (Sentence Transformers)
# =============================================================================

class LocalEmbeddings(EmbeddingModel):
    """
    Local embeddings using sentence-transformers.
    
    Models:
    - all-MiniLM-L6-v2 (384 dims, fast)
    - all-mpnet-base-v2 (768 dims, better quality)
    - gte-large (1024 dims, best quality)
    """
    
    MODEL_DIMS = {
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "sentence-transformers/gte-large": 1024,
        "BAAI/bge-large-en-v1.5": 1024,
    }
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
    ):
        dims = self.MODEL_DIMS.get(model_name, 768)
        super().__init__(model_name, dimensions=dims)
        self.device = device
        self.model = None
        self._init_model()
    
    def _init_model(self):
        """Initialize sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"Loaded local model: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}")
    
    async def embed(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        if not self.model:
            return self._mock_embedding()
        
        try:
            embedding = await asyncio.to_thread(
                self.model.encode,
                text,
                convert_to_numpy=True,
            )
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            return self._mock_embedding()
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not self.model:
            return [self._mock_embedding() for _ in texts]
        
        try:
            embeddings = await asyncio.to_thread(
                self.model.encode,
                texts,
                convert_to_numpy=True,
                batch_size=32,
            )
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"Local batch embedding failed: {e}")
            return [self._mock_embedding() for _ in texts]
    
    def _mock_embedding(self) -> List[float]:
        """Generate mock embedding for testing."""
        import random
        return [random.uniform(-1, 1) for _ in range(self.dimensions)]


# =============================================================================
# Embedding Model Factory
# =============================================================================

class EmbeddingModelFactory:
    """Factory for creating embedding models."""
    
    @staticmethod
    def create(
        provider: str = "bedrock",
        model_name: str = None,
        **kwargs,
    ) -> EmbeddingModel:
        """Create an embedding model."""
        if provider == "bedrock":
            return BedrockEmbeddings(
                model_name=model_name or "amazon.titan-embed-text-v1",
                **kwargs,
            )
        elif provider == "openai":
            return OpenAIEmbeddings(
                model_name=model_name or "text-embedding-3-small",
                **kwargs,
            )
        elif provider == "local":
            return LocalEmbeddings(
                model_name=model_name or "all-MiniLM-L6-v2",
                **kwargs,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
