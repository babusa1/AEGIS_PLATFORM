"""
AEGIS Graph Package

Production graph database for healthcare knowledge graph.
Supports JanusGraph (local/on-prem) and AWS Neptune (cloud).
"""

from aegis_graph.provider import GraphProvider, get_graph_provider
from aegis_graph.providers.base import BaseGraphProvider
from aegis_graph.connection import GraphConnectionPool, get_graph_pool
from aegis_graph.schema import SCHEMA, AegisGraphSchema
from aegis_graph.queries import (
    PatientQueries,
    EncounterQueries,
    ClaimQueries,
    CareGapQueries,
    GraphWriter,
)

__version__ = "0.1.0"

__all__ = [
    "GraphProvider",
    "get_graph_provider",
    "BaseGraphProvider",
    "GraphConnectionPool",
    "get_graph_pool",
    "SCHEMA",
    "AegisGraphSchema",
    "PatientQueries",
    "EncounterQueries",
    "ClaimQueries",
    "CareGapQueries",
    "GraphWriter",
]
