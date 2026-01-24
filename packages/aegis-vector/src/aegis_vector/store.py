"""Vector Store - High-level API for clinical vector operations"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

from aegis_vector.client import VectorClient, VectorRecord, SearchResult, InMemoryVectorClient
from aegis_vector.embeddings import EmbeddingService, EmbeddingModel

logger = structlog.get_logger(__name__)


class ContentType(str, Enum):
    CLINICAL_NOTE = "clinical_note"
    DISCHARGE_SUMMARY = "discharge_summary"
    LAB_RESULT = "lab_result"
    RADIOLOGY_REPORT = "radiology_report"
    PATHOLOGY_REPORT = "pathology_report"
    PATIENT_SUMMARY = "patient_summary"
    GUIDELINE = "guideline"
    PROTOCOL = "protocol"
    AGENT_MEMORY = "agent_memory"


@dataclass
class ClinicalDocument:
    id: str
    content: str
    content_type: ContentType
    patient_id: str | None = None
    encounter_id: str | None = None
    tenant_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass
class SimilarPatient:
    patient_id: str
    similarity_score: float
    matching_conditions: list[str] = field(default_factory=list)
    matching_medications: list[str] = field(default_factory=list)
    summary: str | None = None


class VectorStore:
    """High-level vector store for clinical data."""
    
    NAMESPACES = {
        "notes": "clinical_notes",
        "patients": "patient_summaries",
        "guidelines": "clinical_guidelines",
        "memory": "agent_memory",
    }
    
    def __init__(self, client: VectorClient | None = None,
                 embedding_service: EmbeddingService | None = None):
        self.client = client or InMemoryVectorClient()
        self.embeddings = embedding_service or EmbeddingService(EmbeddingModel.LOCAL)
    
    async def index_document(self, doc: ClinicalDocument) -> str:
        """Index a clinical document for semantic search."""
        # Generate embedding
        result = await self.embeddings.embed(doc.content)
        
        # Determine namespace
        namespace = self._get_namespace(doc.content_type)
        
        # Build metadata
        metadata = {
            "content_type": doc.content_type.value,
            "patient_id": doc.patient_id,
            "encounter_id": doc.encounter_id,
            "tenant_id": doc.tenant_id,
            "created_at": (doc.created_at or datetime.utcnow()).isoformat(),
            "text_preview": doc.content[:500],
            **doc.metadata
        }
        
        # Upsert
        record = VectorRecord(id=doc.id, embedding=result.embedding,
            metadata=metadata, text=doc.content)
        await self.client.upsert([record], namespace=namespace)
        
        logger.info("Indexed document", doc_id=doc.id, namespace=namespace)
        return doc.id
    
    async def search_similar(self, query: str, content_type: ContentType | None = None,
                            tenant_id: str | None = None, top_k: int = 10) -> list[dict]:
        """Search for similar clinical documents."""
        # Generate query embedding
        result = await self.embeddings.embed(query)
        
        # Determine namespace
        namespace = self._get_namespace(content_type) if content_type else "clinical_notes"
        
        # Build filter
        filter_dict = {}
        if tenant_id:
            filter_dict["tenant_id"] = tenant_id
        if content_type:
            filter_dict["content_type"] = content_type.value
        
        # Search
        search_result = await self.client.search(
            embedding=result.embedding, top_k=top_k,
            filter=filter_dict if filter_dict else None, namespace=namespace)
        
        return [{"id": r.id, "score": r.score, **r.metadata} for r in search_result.records]
    
    async def find_similar_patients(self, patient_summary: str, tenant_id: str,
                                   top_k: int = 5) -> list[SimilarPatient]:
        """Find patients with similar clinical profiles."""
        result = await self.embeddings.embed(patient_summary)
        
        search_result = await self.client.search(
            embedding=result.embedding, top_k=top_k + 1,  # +1 to exclude self
            filter={"tenant_id": tenant_id}, namespace="patient_summaries")
        
        similar = []
        for r in search_result.records:
            if r.score and r.score > 0.5:  # Similarity threshold
                similar.append(SimilarPatient(
                    patient_id=r.metadata.get("patient_id", r.id),
                    similarity_score=r.score,
                    summary=r.metadata.get("text_preview")
                ))
        return similar[:top_k]
    
    async def store_agent_memory(self, agent_id: str, memory_type: str,
                                content: str, metadata: dict | None = None) -> str:
        """Store agent memory for retrieval."""
        result = await self.embeddings.embed(content)
        
        memory_id = f"{agent_id}:{memory_type}:{datetime.utcnow().timestamp()}"
        record = VectorRecord(
            id=memory_id,
            embedding=result.embedding,
            metadata={
                "agent_id": agent_id,
                "memory_type": memory_type,
                "content": content[:1000],
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            },
            text=content
        )
        
        await self.client.upsert([record], namespace="agent_memory")
        return memory_id
    
    async def recall_agent_memory(self, agent_id: str, query: str,
                                 top_k: int = 5) -> list[dict]:
        """Recall relevant memories for an agent."""
        result = await self.embeddings.embed(query)
        
        search_result = await self.client.search(
            embedding=result.embedding, top_k=top_k,
            filter={"agent_id": agent_id}, namespace="agent_memory")
        
        return [{"memory_id": r.id, "score": r.score, **r.metadata}
                for r in search_result.records]
    
    async def index_guideline(self, guideline_id: str, title: str,
                             content: str, conditions: list[str] | None = None) -> str:
        """Index a clinical guideline for RAG."""
        result = await self.embeddings.embed(f"{title}\n\n{content}")
        
        record = VectorRecord(
            id=guideline_id,
            embedding=result.embedding,
            metadata={
                "content_type": "guideline",
                "title": title,
                "conditions": conditions or [],
                "text_preview": content[:500],
            },
            text=content
        )
        
        await self.client.upsert([record], namespace="clinical_guidelines")
        return guideline_id
    
    async def search_guidelines(self, clinical_context: str, top_k: int = 3) -> list[dict]:
        """Search for relevant clinical guidelines."""
        result = await self.embeddings.embed(clinical_context)
        
        search_result = await self.client.search(
            embedding=result.embedding, top_k=top_k, namespace="clinical_guidelines")
        
        return [{"id": r.id, "score": r.score, "title": r.metadata.get("title"),
                "conditions": r.metadata.get("conditions"), "preview": r.metadata.get("text_preview")}
                for r in search_result.records]
    
    def _get_namespace(self, content_type: ContentType | None) -> str:
        if not content_type:
            return "clinical_notes"
        if content_type in (ContentType.GUIDELINE, ContentType.PROTOCOL):
            return "clinical_guidelines"
        if content_type == ContentType.PATIENT_SUMMARY:
            return "patient_summaries"
        if content_type == ContentType.AGENT_MEMORY:
            return "agent_memory"
        return "clinical_notes"
