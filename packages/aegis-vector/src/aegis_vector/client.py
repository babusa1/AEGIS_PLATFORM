"""Vector Database Clients - Pinecone and Weaviate"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class VectorDBType(str, Enum):
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    IN_MEMORY = "in_memory"


@dataclass
class VectorRecord:
    id: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    text: str | None = None
    score: float | None = None


@dataclass
class SearchResult:
    records: list[VectorRecord]
    query_embedding: list[float] | None = None
    latency_ms: float = 0


class VectorClient(ABC):
    """Abstract vector database client."""
    
    @abstractmethod
    async def upsert(self, records: list[VectorRecord], namespace: str = "") -> int:
        """Insert or update vectors."""
        pass
    
    @abstractmethod
    async def search(self, embedding: list[float], top_k: int = 10,
                    filter: dict | None = None, namespace: str = "") -> SearchResult:
        """Search for similar vectors."""
        pass
    
    @abstractmethod
    async def delete(self, ids: list[str], namespace: str = "") -> int:
        """Delete vectors by ID."""
        pass


class PineconeClient(VectorClient):
    """Pinecone vector database client."""
    
    def __init__(self, api_key: str, index_name: str, environment: str = ""):
        self.api_key = api_key
        self.index_name = index_name
        self.environment = environment
        self._index = None
    
    def _get_index(self):
        if not self._index:
            try:
                from pinecone import Pinecone
                pc = Pinecone(api_key=self.api_key)
                self._index = pc.Index(self.index_name)
            except ImportError:
                logger.error("pinecone-client not installed")
                raise
        return self._index
    
    async def upsert(self, records: list[VectorRecord], namespace: str = "") -> int:
        index = self._get_index()
        vectors = [(r.id, r.embedding, r.metadata) for r in records]
        response = index.upsert(vectors=vectors, namespace=namespace)
        return response.upserted_count
    
    async def search(self, embedding: list[float], top_k: int = 10,
                    filter: dict | None = None, namespace: str = "") -> SearchResult:
        import time
        start = time.time()
        index = self._get_index()
        response = index.query(vector=embedding, top_k=top_k,
            filter=filter, namespace=namespace, include_metadata=True)
        records = [VectorRecord(id=m.id, embedding=[], metadata=m.metadata or {},
            score=m.score) for m in response.matches]
        return SearchResult(records=records, query_embedding=embedding,
            latency_ms=(time.time() - start) * 1000)
    
    async def delete(self, ids: list[str], namespace: str = "") -> int:
        index = self._get_index()
        index.delete(ids=ids, namespace=namespace)
        return len(ids)


class WeaviateClient(VectorClient):
    """Weaviate vector database client."""
    
    def __init__(self, url: str, api_key: str | None = None, class_name: str = "Clinical"):
        self.url = url
        self.api_key = api_key
        self.class_name = class_name
        self._client = None
    
    def _get_client(self):
        if not self._client:
            try:
                import weaviate
                if self.api_key:
                    self._client = weaviate.connect_to_wcs(
                        cluster_url=self.url, auth_credentials=weaviate.auth.AuthApiKey(self.api_key))
                else:
                    self._client = weaviate.connect_to_local(host=self.url.replace("http://", ""))
            except ImportError:
                logger.error("weaviate-client not installed")
                raise
        return self._client
    
    async def upsert(self, records: list[VectorRecord], namespace: str = "") -> int:
        client = self._get_client()
        collection = client.collections.get(self.class_name)
        count = 0
        for r in records:
            collection.data.insert(properties=r.metadata, vector=r.embedding, uuid=r.id)
            count += 1
        return count
    
    async def search(self, embedding: list[float], top_k: int = 10,
                    filter: dict | None = None, namespace: str = "") -> SearchResult:
        import time
        start = time.time()
        client = self._get_client()
        collection = client.collections.get(self.class_name)
        response = collection.query.near_vector(near_vector=embedding, limit=top_k)
        records = [VectorRecord(id=str(o.uuid), embedding=[], metadata=o.properties,
            score=o.metadata.distance if o.metadata else None) for o in response.objects]
        return SearchResult(records=records, latency_ms=(time.time() - start) * 1000)
    
    async def delete(self, ids: list[str], namespace: str = "") -> int:
        client = self._get_client()
        collection = client.collections.get(self.class_name)
        for id in ids:
            collection.data.delete_by_id(id)
        return len(ids)


class InMemoryVectorClient(VectorClient):
    """In-memory vector client for testing."""
    
    def __init__(self):
        self.vectors: dict[str, dict[str, VectorRecord]] = {}
    
    async def upsert(self, records: list[VectorRecord], namespace: str = "") -> int:
        if namespace not in self.vectors:
            self.vectors[namespace] = {}
        for r in records:
            self.vectors[namespace][r.id] = r
        return len(records)
    
    async def search(self, embedding: list[float], top_k: int = 10,
                    filter: dict | None = None, namespace: str = "") -> SearchResult:
        import numpy as np
        if namespace not in self.vectors:
            return SearchResult(records=[])
        # Cosine similarity
        records = []
        query = np.array(embedding)
        for r in self.vectors[namespace].values():
            vec = np.array(r.embedding)
            score = np.dot(query, vec) / (np.linalg.norm(query) * np.linalg.norm(vec) + 1e-9)
            records.append(VectorRecord(id=r.id, embedding=[], metadata=r.metadata,
                text=r.text, score=float(score)))
        records.sort(key=lambda x: x.score or 0, reverse=True)
        return SearchResult(records=records[:top_k], query_embedding=embedding)
    
    async def delete(self, ids: list[str], namespace: str = "") -> int:
        if namespace not in self.vectors:
            return 0
        count = 0
        for id in ids:
            if id in self.vectors[namespace]:
                del self.vectors[namespace][id]
                count += 1
        return count
