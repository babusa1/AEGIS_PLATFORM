"""
AEGIS Cowork: The Agentic Collaborative Framework

Cowork is the persistent environment where Human and AI collaborate.
It provides:
- Session persistence (Redis)
- Multi-user collaboration
- Real-time state synchronization
- Artifact co-editing
- Approval workflows
"""

from aegis.cowork.engine import CoworkEngine
from aegis.cowork.models import (
    CoworkSession,
    CoworkState,
    CoworkParticipant,
    CoworkArtifact,
    SessionStatus,
    ArtifactType,
)

__all__ = [
    "CoworkEngine",
    "CoworkSession",
    "CoworkState",
    "CoworkParticipant",
    "CoworkArtifact",
    "SessionStatus",
    "ArtifactType",
]
