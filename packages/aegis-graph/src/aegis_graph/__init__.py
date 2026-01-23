"""
AEGIS Graph Package

Graph database abstraction layer supporting multiple backends:
- JanusGraph (local development)
- AWS Neptune (production)
- Neo4j (alternative)
"""

from aegis_graph.provider import GraphProvider, get_graph_provider
from aegis_graph.providers.base import BaseGraphProvider

__version__ = "0.1.0"
__all__ = ["GraphProvider", "get_graph_provider", "BaseGraphProvider"]
