"""
Vector Store

Store and search embeddings:
- OpenSearch (primary)
- In-memory (fallback)
- Hybrid search (vector + keyword)
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod
import json
import uuid

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Models
# =============================================================================

class Document(BaseModel):
    """A document stored in the vector store."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    embedding: Optional[List[float]] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Source info
    source: Optional[str] = None
    source_type: Optional[str] = None
    
    # Document info
    title: Optional[str] = None
    chunk_index: Optional[int] = None
    parent_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class SearchResult(BaseModel):
    """A search result from the vector store."""
    document: Document
    score: float
    
    # Search info
    search_type: str = "vector"  # vector, keyword, hybrid
    
    # Highlights (for keyword search)
    highlights: List[str] = Field(default_factory=list)


# =============================================================================
# Base Vector Store
# =============================================================================

class VectorStore(ABC):
    """Abstract base class for vector stores."""
    
    def __init__(self, index_name: str, dimensions: int):
        self.index_name = index_name
        self.dimensions = dimensions
    
    @abstractmethod
    async def create_index(self):
        """Create the index if it doesn't exist."""
        pass
    
    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to the store."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Dict[str, Any] = None,
    ) -> List[SearchResult]:
        """Search by vector similarity."""
        pass
    
    @abstractmethod
    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Dict[str, Any] = None,
    ) -> List[SearchResult]:
        """Search by keyword."""
        pass
    
    @abstractmethod
    async def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        vector_weight: float = 0.7,
        filters: Dict[str, Any] = None,
    ) -> List[SearchResult]:
        """Hybrid search combining vector and keyword."""
        pass
    
    @abstractmethod
    async def delete(self, document_ids: List[str]) -> int:
        """Delete documents by ID."""
        pass
    
    @abstractmethod
    async def get(self, document_id: str) -> Optional[Document]:
        """Get document by ID."""
        pass


# =============================================================================
# OpenSearch Vector Store
# =============================================================================

class OpenSearchVectorStore(VectorStore):
    """
    OpenSearch vector store.
    
    Features:
    - KNN (k-nearest neighbors) search
    - BM25 keyword search
    - Hybrid search with RRF (Reciprocal Rank Fusion)
    - Filtering by metadata
    """
    
    def __init__(
        self,
        index_name: str = "aegis_documents",
        dimensions: int = 1536,
        client=None,
    ):
        super().__init__(index_name, dimensions)
        self.client = client
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenSearch client."""
        if self.client:
            return
        
        try:
            from opensearchpy import AsyncOpenSearch
            self.client = AsyncOpenSearch(
                hosts=[{"host": "localhost", "port": 9200}],
                http_auth=None,
                use_ssl=False,
            )
            logger.info("OpenSearch client initialized")
        except ImportError:
            logger.warning("opensearch-py not installed, using in-memory store")
            self.client = None
        except Exception as e:
            logger.warning(f"Failed to connect to OpenSearch: {e}")
            self.client = None
    
    async def create_index(self):
        """Create the index with KNN mapping."""
        if not self.client:
            return
        
        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100,
                },
                "analysis": {
                    "analyzer": {
                        "clinical_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop", "snowball"],
                        }
                    }
                },
            },
            "mappings": {
                "properties": {
                    "content": {
                        "type": "text",
                        "analyzer": "clinical_analyzer",
                    },
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": self.dimensions,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 24,
                            },
                        },
                    },
                    "title": {"type": "text"},
                    "source": {"type": "keyword"},
                    "source_type": {"type": "keyword"},
                    "chunk_index": {"type": "integer"},
                    "parent_id": {"type": "keyword"},
                    "metadata": {"type": "object"},
                    "created_at": {"type": "date"},
                },
            },
        }
        
        try:
            exists = await self.client.indices.exists(index=self.index_name)
            if not exists:
                await self.client.indices.create(index=self.index_name, body=index_body)
                logger.info(f"Created index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
    
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to OpenSearch."""
        if not self.client:
            logger.warning("No OpenSearch client, documents not stored")
            return [d.id for d in documents]
        
        ids = []
        
        for doc in documents:
            body = {
                "content": doc.content,
                "embedding": doc.embedding,
                "title": doc.title,
                "source": doc.source,
                "source_type": doc.source_type,
                "chunk_index": doc.chunk_index,
                "parent_id": doc.parent_id,
                "metadata": doc.metadata,
                "created_at": doc.created_at.isoformat(),
            }
            
            try:
                await self.client.index(
                    index=self.index_name,
                    id=doc.id,
                    body=body,
                )
                ids.append(doc.id)
            except Exception as e:
                logger.error(f"Failed to index document {doc.id}: {e}")
        
        logger.info(f"Indexed {len(ids)} documents")
        return ids
    
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Dict[str, Any] = None,
    ) -> List[SearchResult]:
        """Vector similarity search."""
        if not self.client:
            return []
        
        query = {
            "size": top_k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": top_k,
                    }
                }
            },
        }
        
        # Add filters
        if filters:
            query["query"] = {
                "bool": {
                    "must": [query["query"]],
                    "filter": self._build_filters(filters),
                }
            }
        
        try:
            response = await self.client.search(index=self.index_name, body=query)
            return self._parse_results(response, "vector")
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Dict[str, Any] = None,
    ) -> List[SearchResult]:
        """BM25 keyword search."""
        if not self.client:
            return []
        
        search_query = {
            "size": top_k,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["content^2", "title"],
                    "type": "best_fields",
                }
            },
            "highlight": {
                "fields": {
                    "content": {"fragment_size": 150, "number_of_fragments": 3}
                }
            },
        }
        
        if filters:
            search_query["query"] = {
                "bool": {
                    "must": [search_query["query"]],
                    "filter": self._build_filters(filters),
                }
            }
        
        try:
            response = await self.client.search(index=self.index_name, body=search_query)
            return self._parse_results(response, "keyword")
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    async def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        vector_weight: float = 0.7,
        filters: Dict[str, Any] = None,
    ) -> List[SearchResult]:
        """
        Hybrid search using Reciprocal Rank Fusion (RRF).
        
        Combines vector and keyword results.
        """
        # Get both result sets
        vector_results = await self.search(query_embedding, top_k * 2, filters)
        keyword_results = await self.keyword_search(query, top_k * 2, filters)
        
        # RRF fusion
        k = 60  # RRF constant
        scores = {}
        doc_map = {}
        
        for rank, result in enumerate(vector_results):
            doc_id = result.document.id
            rrf_score = vector_weight / (k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score
            doc_map[doc_id] = result
        
        keyword_weight = 1 - vector_weight
        for rank, result in enumerate(keyword_results):
            doc_id = result.document.id
            rrf_score = keyword_weight / (k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score
            if doc_id not in doc_map:
                doc_map[doc_id] = result
        
        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        results = []
        for doc_id in sorted_ids[:top_k]:
            result = doc_map[doc_id]
            result.score = scores[doc_id]
            result.search_type = "hybrid"
            results.append(result)
        
        return results
    
    async def delete(self, document_ids: List[str]) -> int:
        """Delete documents by ID."""
        if not self.client:
            return 0
        
        deleted = 0
        for doc_id in document_ids:
            try:
                await self.client.delete(index=self.index_name, id=doc_id)
                deleted += 1
            except Exception as e:
                logger.error(f"Failed to delete {doc_id}: {e}")
        
        return deleted
    
    async def get(self, document_id: str) -> Optional[Document]:
        """Get document by ID."""
        if not self.client:
            return None
        
        try:
            response = await self.client.get(index=self.index_name, id=document_id)
            source = response["_source"]
            
            return Document(
                id=response["_id"],
                content=source.get("content", ""),
                embedding=source.get("embedding"),
                metadata=source.get("metadata", {}),
                source=source.get("source"),
                source_type=source.get("source_type"),
                title=source.get("title"),
                chunk_index=source.get("chunk_index"),
                parent_id=source.get("parent_id"),
            )
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None
    
    def _build_filters(self, filters: Dict[str, Any]) -> List[dict]:
        """Build OpenSearch filter clauses."""
        clauses = []
        for key, value in filters.items():
            if isinstance(value, list):
                clauses.append({"terms": {key: value}})
            else:
                clauses.append({"term": {key: value}})
        return clauses
    
    def _parse_results(self, response: dict, search_type: str) -> List[SearchResult]:
        """Parse OpenSearch response into SearchResult objects."""
        results = []
        
        for hit in response.get("hits", {}).get("hits", []):
            source = hit["_source"]
            
            doc = Document(
                id=hit["_id"],
                content=source.get("content", ""),
                embedding=source.get("embedding"),
                metadata=source.get("metadata", {}),
                source=source.get("source"),
                source_type=source.get("source_type"),
                title=source.get("title"),
                chunk_index=source.get("chunk_index"),
                parent_id=source.get("parent_id"),
            )
            
            highlights = []
            if "highlight" in hit:
                for field, frags in hit["highlight"].items():
                    highlights.extend(frags)
            
            results.append(SearchResult(
                document=doc,
                score=hit.get("_score", 0),
                search_type=search_type,
                highlights=highlights,
            ))
        
        return results


# =============================================================================
# In-Memory Vector Store (Fallback)
# =============================================================================

class InMemoryVectorStore(VectorStore):
    """
    Simple in-memory vector store for testing.
    
    Uses cosine similarity for search.
    """
    
    def __init__(self, index_name: str = "default", dimensions: int = 1536):
        super().__init__(index_name, dimensions)
        self.documents: Dict[str, Document] = {}
    
    async def create_index(self):
        """No-op for in-memory store."""
        pass
    
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to memory."""
        ids = []
        for doc in documents:
            self.documents[doc.id] = doc
            ids.append(doc.id)
        logger.info(f"Added {len(ids)} documents to in-memory store")
        return ids
    
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Dict[str, Any] = None,
    ) -> List[SearchResult]:
        """Vector similarity search using cosine similarity."""
        import math
        
        def cosine_similarity(a: List[float], b: List[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(y * y for y in b))
            return dot / (norm_a * norm_b) if norm_a and norm_b else 0
        
        results = []
        for doc in self.documents.values():
            if doc.embedding:
                # Apply filters
                if filters and not self._matches_filters(doc, filters):
                    continue
                
                score = cosine_similarity(query_embedding, doc.embedding)
                results.append(SearchResult(
                    document=doc,
                    score=score,
                    search_type="vector",
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Dict[str, Any] = None,
    ) -> List[SearchResult]:
        """Simple keyword search."""
        query_terms = query.lower().split()
        results = []
        
        for doc in self.documents.values():
            if filters and not self._matches_filters(doc, filters):
                continue
            
            content_lower = doc.content.lower()
            score = sum(1 for term in query_terms if term in content_lower)
            
            if score > 0:
                results.append(SearchResult(
                    document=doc,
                    score=score,
                    search_type="keyword",
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    async def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        vector_weight: float = 0.7,
        filters: Dict[str, Any] = None,
    ) -> List[SearchResult]:
        """Combine vector and keyword search."""
        vector_results = await self.search(query_embedding, top_k, filters)
        keyword_results = await self.keyword_search(query, top_k, filters)
        
        # Simple combination
        scores = {}
        doc_map = {}
        
        for r in vector_results:
            scores[r.document.id] = r.score * vector_weight
            doc_map[r.document.id] = r
        
        for r in keyword_results:
            keyword_score = r.score / 10  # Normalize
            scores[r.document.id] = scores.get(r.document.id, 0) + keyword_score * (1 - vector_weight)
            if r.document.id not in doc_map:
                doc_map[r.document.id] = r
        
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        return [
            SearchResult(
                document=doc_map[doc_id].document,
                score=scores[doc_id],
                search_type="hybrid",
            )
            for doc_id in sorted_ids[:top_k]
        ]
    
    async def delete(self, document_ids: List[str]) -> int:
        """Delete documents."""
        deleted = 0
        for doc_id in document_ids:
            if doc_id in self.documents:
                del self.documents[doc_id]
                deleted += 1
        return deleted
    
    async def get(self, document_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self.documents.get(document_id)
    
    def _matches_filters(self, doc: Document, filters: Dict[str, Any]) -> bool:
        """Check if document matches filters."""
        for key, value in filters.items():
            doc_value = doc.metadata.get(key) or getattr(doc, key, None)
            if isinstance(value, list):
                if doc_value not in value:
                    return False
            elif doc_value != value:
                return False
        return True
