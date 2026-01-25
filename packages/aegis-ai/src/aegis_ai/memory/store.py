"""Persistent Agent Memory Store"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class MemoryType(str, Enum):
    EPISODIC = "episodic"  # Specific events
    SEMANTIC = "semantic"  # Facts/knowledge
    PROCEDURAL = "procedural"  # How to do things
    WORKING = "working"  # Current context


@dataclass
class Memory:
    id: str
    memory_type: MemoryType
    content: str
    agent_id: str
    patient_id: str | None = None
    importance: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryStore:
    """
    Persistent memory store for agents.
    
    Supports semantic search and importance-based retrieval.
    """
    
    def __init__(self, vector_store=None):
        self._memories: dict[str, Memory] = {}
        self._agent_index: dict[str, list[str]] = {}
        self._vector = vector_store
    
    def store(self, memory: Memory) -> str:
        """Store a new memory."""
        self._memories[memory.id] = memory
        
        if memory.agent_id not in self._agent_index:
            self._agent_index[memory.agent_id] = []
        self._agent_index[memory.agent_id].append(memory.id)
        
        # Store in vector DB for semantic search
        if self._vector:
            pass  # Would embed and store
        
        return memory.id
    
    def recall(self, agent_id: str, query: str | None = None,
              memory_type: MemoryType | None = None,
              limit: int = 10) -> list[Memory]:
        """Recall memories for an agent."""
        memory_ids = self._agent_index.get(agent_id, [])
        memories = [self._memories[mid] for mid in memory_ids if mid in self._memories]
        
        # Filter by type
        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]
        
        # Sort by importance and recency
        memories.sort(key=lambda m: (m.importance, m.accessed_at), reverse=True)
        
        # Update access stats
        for m in memories[:limit]:
            m.accessed_at = datetime.utcnow()
            m.access_count += 1
        
        return memories[:limit]
    
    def forget(self, memory_id: str):
        """Remove a memory."""
        if memory_id in self._memories:
            memory = self._memories.pop(memory_id)
            if memory.agent_id in self._agent_index:
                self._agent_index[memory.agent_id].remove(memory_id)
    
    def consolidate(self, agent_id: str, threshold: float = 0.3):
        """Remove low-importance, stale memories."""
        memory_ids = self._agent_index.get(agent_id, [])
        to_remove = []
        
        for mid in memory_ids:
            memory = self._memories.get(mid)
            if memory and memory.importance < threshold and memory.access_count < 2:
                to_remove.append(mid)
        
        for mid in to_remove:
            self.forget(mid)
        
        logger.info("Memory consolidated", agent=agent_id, removed=len(to_remove))
