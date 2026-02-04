"""
AEGIS RAG (Retrieval Augmented Generation) Pipeline

Complete RAG system for healthcare:
- Document ingestion (PDF, DOCX, clinical notes, policies)
- Intelligent chunking (semantic, sliding window, hierarchical)
- Embedding generation (Bedrock Titan, OpenAI, local)
- Vector storage (OpenSearch)
- Hybrid retrieval (vector + keyword + graph)
- Reranking and citation tracking
"""

from aegis.rag.loaders import (
    DocumentLoader,
    PDFLoader,
    DocxLoader,
    TextLoader,
    HL7Loader,
    FHIRLoader,
)
from aegis.rag.chunkers import (
    Chunker,
    SemanticChunker,
    SlidingWindowChunker,
    HierarchicalChunker,
)
from aegis.rag.embeddings import (
    EmbeddingModel,
    BedrockEmbeddings,
    OpenAIEmbeddings,
    LocalEmbeddings,
)
from aegis.rag.vectorstore import VectorStore, Document, SearchResult
from aegis.rag.retriever import RAGRetriever, RAGResponse
from aegis.rag.pipeline import RAGPipeline

__all__ = [
    # Loaders
    "DocumentLoader",
    "PDFLoader",
    "DocxLoader",
    "TextLoader",
    "HL7Loader",
    "FHIRLoader",
    # Chunkers
    "Chunker",
    "SemanticChunker",
    "SlidingWindowChunker",
    "HierarchicalChunker",
    # Embeddings
    "EmbeddingModel",
    "BedrockEmbeddings",
    "OpenAIEmbeddings",
    "LocalEmbeddings",
    # Vector Store
    "VectorStore",
    "Document",
    "SearchResult",
    # Retriever
    "RAGRetriever",
    "RAGResponse",
    # Pipeline
    "RAGPipeline",
]
