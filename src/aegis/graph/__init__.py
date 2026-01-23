"""
AEGIS Graph Module

Graph database operations for Neptune/JanusGraph using Gremlin.
"""

from aegis.graph.client import GraphClient
from aegis.graph.queries import GraphQueries

__all__ = ["GraphClient", "GraphQueries"]
