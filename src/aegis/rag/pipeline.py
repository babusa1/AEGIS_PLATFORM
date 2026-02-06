"""
RAG Pipeline

Complete end-to-end RAG pipeline:
1. Document ingestion
2. Chunking
3. Embedding
4. Storage
5. Retrieval
6. Generation (with citations)
"""

from typing import Any, Dict, List, Optional, Optional, BinaryIO
from datetime import datetime
from pathlib import Path
import asyncio

import structlog
from pydantic import BaseModel, Field

from aegis.rag.loaders import DocumentLoader, DocumentLoaderFactory, LoadedDocument
from aegis.rag.chunkers import Chunker, SemanticChunker, Chunk
from aegis.rag.embeddings import EmbeddingModel, EmbeddingModelFactory
from aegis.rag.vectorstore import VectorStore, Document, InMemoryVectorStore
from aegis.rag.retriever import RAGRetriever, RAGResponse

logger = structlog.get_logger(__name__)


# =============================================================================
# Pipeline Configuration
# =============================================================================

class RAGConfig(BaseModel):
    """RAG pipeline configuration."""
    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200
    chunker_type: str = "semantic"  # semantic, sliding, hierarchical
    
    # Embedding
    embedding_provider: str = "bedrock"  # bedrock, openai, local
    embedding_model: str = "amazon.titan-embed-text-v1"
    
    # Retrieval
    top_k: int = 5
    search_type: str = "hybrid"  # vector, keyword, hybrid
    rerank: bool = True
    expand_queries: bool = False
    
    # Generation
    include_citations: bool = True
    max_context_length: int = 8000


# =============================================================================
# Ingestion Result
# =============================================================================

class IngestionResult(BaseModel):
    """Result of document ingestion."""
    document_id: str
    filename: str
    source_type: str
    
    # Stats
    chunk_count: int
    total_chars: int
    
    # Status
    success: bool = True
    error: Optional[str] = None
    
    # Timing
    ingestion_time_ms: int = 0


# =============================================================================
# RAG Pipeline
# =============================================================================

class RAGPipeline:
    """
    Complete RAG pipeline for healthcare documents.
    
    Features:
    - Multi-format document ingestion
    - Intelligent chunking
    - Multi-provider embedding
    - Hybrid retrieval
    - Citation tracking
    - LLM generation with context
    """
    
    def __init__(
        self,
        config: RAGConfig = None,
        vector_store: VectorStore = None,
        embedding_model: EmbeddingModel = None,
        llm_client=None,
    ):
        self.config = config or RAGConfig()
        
        # Initialize components
        self.vector_store = vector_store or InMemoryVectorStore()
        self.embedding_model = embedding_model or EmbeddingModelFactory.create(
            self.config.embedding_provider,
            self.config.embedding_model,
        )
        self.llm_client = llm_client
        
        # Initialize chunker
        self.chunker = self._create_chunker()
        
        # Initialize retriever (graph client will be set lazily if needed for GraphRAG)
        self.retriever = RAGRetriever(
            vector_store=self.vector_store,
            embedding_model=self.embedding_model,
            llm_client=llm_client,
            graph_client=None,  # Set lazily when GraphRAG is used
        )
    
    def _create_chunker(self) -> Chunker:
        """Create chunker based on config."""
        if self.config.chunker_type == "sliding":
            from aegis.rag.chunkers import SlidingWindowChunker
            return SlidingWindowChunker(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
            )
        elif self.config.chunker_type == "hierarchical":
            from aegis.rag.chunkers import HierarchicalChunker
            return HierarchicalChunker()
        else:  # semantic
            return SemanticChunker(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
            )
    
    # =========================================================================
    # Ingestion
    # =========================================================================
    
    async def ingest_file(
        self,
        file_path: str,
        metadata: Dict[str, Any] = None,
    ) -> IngestionResult:
        """
        Ingest a single file into the RAG system.
        
        Supports: PDF, DOCX, TXT, HL7, FHIR JSON
        """
        start_time = datetime.utcnow()
        
        try:
            # Load document
            loader = DocumentLoaderFactory.get_loader(file_path)
            documents = loader.load(file_path)
            
            if not documents:
                return IngestionResult(
                    document_id="",
                    filename=file_path,
                    source_type="unknown",
                    chunk_count=0,
                    total_chars=0,
                    success=False,
                    error="No documents extracted",
                )
            
            # Process each loaded document
            total_chunks = 0
            total_chars = 0
            doc_id = documents[0].id
            
            for loaded_doc in documents:
                result = await self._process_document(loaded_doc, metadata)
                total_chunks += result["chunk_count"]
                total_chars += result["char_count"]
            
            ingestion_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            logger.info(
                f"Ingested {file_path}: {total_chunks} chunks, {total_chars} chars"
            )
            
            return IngestionResult(
                document_id=doc_id,
                filename=file_path,
                source_type=documents[0].source_type,
                chunk_count=total_chunks,
                total_chars=total_chars,
                success=True,
                ingestion_time_ms=ingestion_time,
            )
            
        except Exception as e:
            logger.error(f"Ingestion failed for {file_path}: {e}")
            return IngestionResult(
                document_id="",
                filename=file_path,
                source_type="unknown",
                chunk_count=0,
                total_chars=0,
                success=False,
                error=str(e),
            )
    
    async def ingest_bytes(
        self,
        data: bytes,
        filename: str,
        metadata: Dict[str, Any] = None,
    ) -> IngestionResult:
        """Ingest document from bytes."""
        start_time = datetime.utcnow()
        
        try:
            loader = DocumentLoaderFactory.get_loader(filename)
            documents = loader.load_bytes(data, filename)
            
            if not documents:
                return IngestionResult(
                    document_id="",
                    filename=filename,
                    source_type="unknown",
                    chunk_count=0,
                    total_chars=0,
                    success=False,
                    error="No documents extracted",
                )
            
            total_chunks = 0
            total_chars = 0
            doc_id = documents[0].id
            
            for loaded_doc in documents:
                result = await self._process_document(loaded_doc, metadata)
                total_chunks += result["chunk_count"]
                total_chars += result["char_count"]
            
            ingestion_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return IngestionResult(
                document_id=doc_id,
                filename=filename,
                source_type=documents[0].source_type,
                chunk_count=total_chunks,
                total_chars=total_chars,
                success=True,
                ingestion_time_ms=ingestion_time,
            )
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            return IngestionResult(
                document_id="",
                filename=filename,
                source_type="unknown",
                chunk_count=0,
                total_chars=0,
                success=False,
                error=str(e),
            )
    
    async def ingest_text(
        self,
        text: str,
        title: str = "Untitled",
        source: str = "direct_input",
        metadata: Dict[str, Any] = None,
    ) -> IngestionResult:
        """Ingest raw text directly."""
        start_time = datetime.utcnow()
        
        loaded_doc = LoadedDocument(
            id=f"text_{datetime.utcnow().timestamp()}",
            content=text,
            source=source,
            source_type="text",
            title=title,
        )
        
        try:
            result = await self._process_document(loaded_doc, metadata)
            
            ingestion_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return IngestionResult(
                document_id=loaded_doc.id,
                filename=title,
                source_type="text",
                chunk_count=result["chunk_count"],
                total_chars=result["char_count"],
                success=True,
                ingestion_time_ms=ingestion_time,
            )
            
        except Exception as e:
            return IngestionResult(
                document_id="",
                filename=title,
                source_type="text",
                chunk_count=0,
                total_chars=0,
                success=False,
                error=str(e),
            )
    
    async def _process_document(
        self,
        loaded_doc: LoadedDocument,
        metadata: Dict[str, Any] = None,
    ) -> dict:
        """Process a loaded document: chunk, embed, store."""
        # Chunk the document
        chunks = self.chunker.chunk(
            document_id=loaded_doc.id,
            content=loaded_doc.content,
            metadata={
                **(metadata or {}),
                "source": loaded_doc.source,
                "source_type": loaded_doc.source_type,
                "title": loaded_doc.title,
            },
        )
        
        # Generate embeddings
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = await self.embedding_model.embed_batch(chunk_texts)
        
        # Create documents for vector store
        documents = []
        for chunk, embedding in zip(chunks, embeddings):
            doc = Document(
                id=chunk.id,
                content=chunk.content,
                embedding=embedding,
                metadata=chunk.metadata,
                source=loaded_doc.source,
                source_type=loaded_doc.source_type,
                title=loaded_doc.title,
                chunk_index=chunk.chunk_index,
                parent_id=chunk.parent_id,
            )
            documents.append(doc)
        
        # Store in vector store
        await self.vector_store.add_documents(documents)
        
        return {
            "chunk_count": len(chunks),
            "char_count": sum(len(c.content) for c in chunks),
        }
    
    # =========================================================================
    # Retrieval
    # =========================================================================
    
    async def retrieve(
        self,
        query: str,
        top_k: int = None,
        filters: Dict[str, Any] = None,
        use_graphrag: bool = False,
        graph_entity_id: Optional[str] = None,
        temporal_priority: bool = False,
        time_window_days: Optional[int] = None,
    ) -> RAGResponse:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: User query
            top_k: Number of results
            filters: Metadata filters
            use_graphrag: Enable GraphRAG (graph traversal + RAG)
            graph_entity_id: Starting entity ID for graph traversal
        """
        # Lazy-load graph client if GraphRAG is requested
        if use_graphrag and not self.retriever.graph_client:
            try:
                from aegis.graph.client import get_graph_client
                self.retriever.graph_client = await get_graph_client()
            except Exception:
                logger.warning("Graph client not available for GraphRAG")
        
        return await self.retriever.retrieve(
            query=query,
            top_k=top_k or self.config.top_k,
            search_type="graphrag" if use_graphrag else self.config.search_type,
            filters=filters,
            expand_queries=self.config.expand_queries,
            rerank=self.config.rerank,
            use_graphrag=use_graphrag,
            graph_entity_id=graph_entity_id,
            temporal_priority=temporal_priority,
            time_window_days=time_window_days,
        )
    
    # =========================================================================
    # Generation
    # =========================================================================
    
    async def query(
        self,
        query: str,
        top_k: int = None,
        filters: Dict[str, Any] = None,
        system_prompt: str = None,
    ) -> Dict[str, Any]:
        """
        Complete RAG query: retrieve + generate.
        
        Returns response with answer and citations.
        """
        # Retrieve relevant documents
        rag_response = await self.retrieve(query, top_k, filters)
        
        if not self.llm_client:
            return {
                "query": query,
                "answer": "LLM not configured. Here is the relevant context:",
                "context": rag_response.context,
                "citations": [c.dict() for c in rag_response.citations],
                "retrieval_time_ms": rag_response.retrieval_time_ms,
            }
        
        # Build prompt with context
        context = rag_response.get_context_with_citations() if self.config.include_citations else rag_response.context
        
        # Truncate context if too long
        if len(context) > self.config.max_context_length:
            context = context[:self.config.max_context_length] + "\n[Context truncated...]"
        
        prompt = f"""Based on the following context, answer the user's question. 
If you use information from the context, cite the source using [1], [2], etc.
If the context doesn't contain relevant information, say so.

Context:
{context}

Question: {query}

Answer:"""
        
        default_system = """You are a helpful healthcare AI assistant. 
Provide accurate, evidence-based answers using the provided context.
Always cite your sources when using information from the context.
Be concise but thorough."""
        
        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt or default_system,
            )
            
            return {
                "query": query,
                "answer": response.content,
                "citations": [c.dict() for c in rag_response.citations],
                "retrieval_time_ms": rag_response.retrieval_time_ms,
                "generation_tokens": response.usage.output_tokens if response.usage else 0,
            }
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {
                "query": query,
                "answer": f"Generation failed: {e}",
                "context": rag_response.context,
                "citations": [c.dict() for c in rag_response.citations],
                "error": str(e),
            }
    
    # =========================================================================
    # Management
    # =========================================================================
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks."""
        # This would need to find all chunks with this document_id
        # For now, delete by ID
        deleted = await self.vector_store.delete([document_id])
        return deleted > 0
    
    async def get_stats(self) -> dict:
        """Get pipeline statistics."""
        # Would query vector store for stats
        return {
            "embedding_model": self.config.embedding_model,
            "chunker_type": self.config.chunker_type,
            "search_type": self.config.search_type,
        }


# =============================================================================
# Global Pipeline Instance
# =============================================================================

_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    """Get global RAG pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


def configure_rag_pipeline(
    config: RAGConfig = None,
    vector_store: VectorStore = None,
    embedding_model: EmbeddingModel = None,
    llm_client=None,
) -> RAGPipeline:
    """Configure and return global RAG pipeline."""
    global _pipeline
    _pipeline = RAGPipeline(
        config=config,
        vector_store=vector_store,
        embedding_model=embedding_model,
        llm_client=llm_client,
    )
    return _pipeline
