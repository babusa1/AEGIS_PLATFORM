"""AEGIS Vector Database - Semantic memory and RAG"""
from aegis_vector.client import VectorClient, PineconeClient, WeaviateClient, InMemoryVectorClient
from aegis_vector.store import VectorStore

__version__ = "0.1.0"
__all__ = ["VectorClient", "PineconeClient", "WeaviateClient", "InMemoryVectorClient", "VectorStore"]
