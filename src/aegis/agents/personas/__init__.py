"""
Agent Personas

Explicit agent personas matching the AEGIS specification:
- LibrarianAgent: Contextual retrieval (GraphRAG, temporal delta, recursive summarization)
- GuardianAgent: Governance & safety (guideline cross-check, conflict detection)
- ScribeAgent: Action execution (SOAP notes, referral letters, prior auth)
- ScoutAgent: Continuous monitoring (Kafka events, proactive triage)
"""

from aegis.agents.personas.librarian import LibrarianAgent
from aegis.agents.personas.guardian import GuardianAgent
from aegis.agents.personas.scribe import ScribeAgent
from aegis.agents.personas.scout import ScoutAgent

__all__ = [
    "LibrarianAgent",
    "GuardianAgent",
    "ScribeAgent",
    "ScoutAgent",
]
