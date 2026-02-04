"""
RAG API Routes

Endpoints for:
- Document ingestion
- Retrieval
- Query with generation
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel

from aegis.rag.pipeline import get_rag_pipeline, RAGConfig

router = APIRouter(prefix="/rag", tags=["rag"])


# =============================================================================
# Request/Response Models
# =============================================================================

class IngestTextRequest(BaseModel):
    text: str
    title: str = "Untitled"
    source: str = "direct_input"
    metadata: dict = None


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: dict = None
    include_citations: bool = True


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    search_type: str = "hybrid"  # vector, keyword, hybrid
    filters: dict = None


# =============================================================================
# Ingestion Endpoints
# =============================================================================

@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    metadata: Optional[str] = None,
):
    """
    Ingest a document file (PDF, DOCX, TXT, etc.)
    
    The document will be chunked, embedded, and stored for retrieval.
    """
    pipeline = get_rag_pipeline()
    
    # Read file content
    content = await file.read()
    
    # Parse metadata if provided
    meta = None
    if metadata:
        import json
        try:
            meta = json.loads(metadata)
        except:
            pass
    
    # Ingest
    result = await pipeline.ingest_bytes(content, file.filename, meta)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return {
        "document_id": result.document_id,
        "filename": result.filename,
        "source_type": result.source_type,
        "chunks_created": result.chunk_count,
        "total_characters": result.total_chars,
        "ingestion_time_ms": result.ingestion_time_ms,
    }


@router.post("/ingest/text")
async def ingest_text(request: IngestTextRequest):
    """Ingest raw text directly."""
    pipeline = get_rag_pipeline()
    
    result = await pipeline.ingest_text(
        text=request.text,
        title=request.title,
        source=request.source,
        metadata=request.metadata,
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return {
        "document_id": result.document_id,
        "chunks_created": result.chunk_count,
        "total_characters": result.total_chars,
    }


@router.post("/ingest/url")
async def ingest_url(url: str = Query(...)):
    """Ingest document from URL (PDF, etc.)"""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail="Failed to fetch URL")
                
                content = await response.read()
                filename = url.split("/")[-1] or "document"
                
                pipeline = get_rag_pipeline()
                result = await pipeline.ingest_bytes(
                    content, filename, {"source_url": url}
                )
                
                return {
                    "document_id": result.document_id,
                    "chunks_created": result.chunk_count,
                }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Retrieval Endpoints
# =============================================================================

@router.post("/search")
async def search(request: SearchRequest):
    """
    Search for relevant documents.
    
    Returns matching chunks without LLM generation.
    """
    pipeline = get_rag_pipeline()
    
    response = await pipeline.retrieve(
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
    )
    
    return {
        "query": response.query,
        "total_results": response.total_results,
        "retrieval_time_ms": response.retrieval_time_ms,
        "results": [
            {
                "id": r.document.id,
                "content": r.document.content[:500],
                "score": r.score,
                "source": r.document.source,
                "title": r.document.title,
                "highlights": r.highlights,
            }
            for r in response.results
        ],
        "citations": [c.dict() for c in response.citations],
    }


@router.post("/query")
async def query(request: QueryRequest):
    """
    Query the knowledge base with RAG.
    
    Retrieves relevant documents and generates an answer with citations.
    """
    pipeline = get_rag_pipeline()
    
    result = await pipeline.query(
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
    )
    
    return result


# =============================================================================
# Management Endpoints
# =============================================================================

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document from the knowledge base."""
    pipeline = get_rag_pipeline()
    
    success = await pipeline.delete_document(document_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"status": "deleted", "document_id": document_id}


@router.get("/stats")
async def get_stats():
    """Get RAG pipeline statistics."""
    pipeline = get_rag_pipeline()
    return await pipeline.get_stats()


@router.post("/configure")
async def configure_pipeline(config: RAGConfig):
    """Update RAG pipeline configuration."""
    from aegis.rag.pipeline import configure_rag_pipeline
    
    configure_rag_pipeline(config=config)
    
    return {"status": "configured", "config": config.dict()}
