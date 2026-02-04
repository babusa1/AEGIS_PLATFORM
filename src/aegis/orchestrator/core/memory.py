"""
Memory Store

Multi-tier memory system for agents:
- Short-term memory (conversation)
- Long-term memory (persistent)
- Semantic memory (vector search)
- Episodic memory (event history)
"""

from typing import Any
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid
import hashlib

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Memory Types
# =============================================================================

class MemoryType(str, Enum):
    """Types of agent memory."""
    SHORT_TERM = "short_term"  # Conversation context
    LONG_TERM = "long_term"  # Persistent facts
    SEMANTIC = "semantic"  # Vector-based
    EPISODIC = "episodic"  # Event history


class MemoryEntry(BaseModel):
    """A single memory entry."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType
    namespace: str  # Tenant/agent namespace
    
    # Content
    key: str
    value: Any
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accessed_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = 0
    ttl_seconds: int | None = None  # Time to live
    
    # For semantic memory
    embedding: list[float] | None = None
    
    # Tags for filtering
    tags: list[str] = Field(default_factory=list)


class ConversationMessage(BaseModel):
    """A message in conversation memory."""
    role: str  # user, assistant, system, tool
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Memory Store
# =============================================================================

class MemoryStore:
    """
    Multi-tier memory store for agents.
    
    Features:
    - Namespace isolation (per tenant/agent)
    - TTL support
    - Semantic search (with vector DB)
    - Conversation history
    - Event logging
    """
    
    def __init__(self, pool=None, vector_client=None, redis_client=None):
        self.pool = pool
        self.vector_client = vector_client
        self.redis_client = redis_client
        
        # In-memory caches
        self._short_term: dict[str, list[ConversationMessage]] = {}
        self._long_term: dict[str, dict[str, MemoryEntry]] = {}
        self._episodic: dict[str, list[dict]] = {}
    
    # =========================================================================
    # Short-Term Memory (Conversation)
    # =========================================================================
    
    def add_message(
        self,
        namespace: str,
        role: str,
        content: str,
        name: str = None,
        tool_call_id: str = None,
    ):
        """Add a message to conversation memory."""
        if namespace not in self._short_term:
            self._short_term[namespace] = []
        
        message = ConversationMessage(
            role=role,
            content=content,
            name=name,
            tool_call_id=tool_call_id,
        )
        
        self._short_term[namespace].append(message)
        
        # Keep last N messages
        max_messages = 100
        if len(self._short_term[namespace]) > max_messages:
            self._short_term[namespace] = self._short_term[namespace][-max_messages:]
    
    def get_conversation(
        self,
        namespace: str,
        limit: int = 20,
        since: datetime = None,
    ) -> list[ConversationMessage]:
        """Get conversation history."""
        messages = self._short_term.get(namespace, [])
        
        if since:
            messages = [m for m in messages if m.timestamp >= since]
        
        return messages[-limit:]
    
    def clear_conversation(self, namespace: str):
        """Clear conversation memory."""
        self._short_term.pop(namespace, None)
    
    def get_conversation_context(
        self,
        namespace: str,
        max_tokens: int = 4000,
    ) -> str:
        """Get conversation as formatted context string."""
        messages = self.get_conversation(namespace)
        
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Rough token estimate
        
        for msg in reversed(messages):
            msg_text = f"{msg.role.upper()}: {msg.content}"
            if total_chars + len(msg_text) > max_chars:
                break
            context_parts.insert(0, msg_text)
            total_chars += len(msg_text)
        
        return "\n\n".join(context_parts)
    
    # =========================================================================
    # Long-Term Memory (Persistent Facts)
    # =========================================================================
    
    def store(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: int = None,
        tags: list[str] = None,
    ) -> MemoryEntry:
        """Store a value in long-term memory."""
        if namespace not in self._long_term:
            self._long_term[namespace] = {}
        
        entry = MemoryEntry(
            memory_type=MemoryType.LONG_TERM,
            namespace=namespace,
            key=key,
            value=value,
            ttl_seconds=ttl_seconds,
            tags=tags or [],
        )
        
        self._long_term[namespace][key] = entry
        
        # Persist to Redis if available
        if self.redis_client:
            self._persist_to_redis(entry)
        
        return entry
    
    def retrieve(self, namespace: str, key: str) -> Any | None:
        """Retrieve a value from long-term memory."""
        ns_memory = self._long_term.get(namespace, {})
        entry = ns_memory.get(key)
        
        if not entry:
            # Try Redis
            if self.redis_client:
                entry = self._load_from_redis(namespace, key)
            
            if not entry:
                return None
        
        # Check TTL
        if entry.ttl_seconds:
            age = (datetime.utcnow() - entry.created_at).total_seconds()
            if age > entry.ttl_seconds:
                self.forget(namespace, key)
                return None
        
        # Update access metadata
        entry.accessed_at = datetime.utcnow()
        entry.access_count += 1
        
        return entry.value
    
    def forget(self, namespace: str, key: str):
        """Remove a value from long-term memory."""
        if namespace in self._long_term:
            self._long_term[namespace].pop(key, None)
        
        if self.redis_client:
            # Would delete from Redis
            pass
    
    def search_by_tags(
        self,
        namespace: str,
        tags: list[str],
        match_all: bool = False,
    ) -> list[MemoryEntry]:
        """Search memory by tags."""
        ns_memory = self._long_term.get(namespace, {})
        
        results = []
        for entry in ns_memory.values():
            if match_all:
                if all(t in entry.tags for t in tags):
                    results.append(entry)
            else:
                if any(t in entry.tags for t in tags):
                    results.append(entry)
        
        return results
    
    def _persist_to_redis(self, entry: MemoryEntry):
        """Persist entry to Redis."""
        pass  # Would use redis_client
    
    def _load_from_redis(self, namespace: str, key: str) -> MemoryEntry | None:
        """Load entry from Redis."""
        pass  # Would use redis_client
    
    # =========================================================================
    # Semantic Memory (Vector Search)
    # =========================================================================
    
    async def store_semantic(
        self,
        namespace: str,
        key: str,
        text: str,
        metadata: dict = None,
    ) -> MemoryEntry:
        """Store text with embedding for semantic search."""
        # Generate embedding
        embedding = await self._generate_embedding(text)
        
        entry = MemoryEntry(
            memory_type=MemoryType.SEMANTIC,
            namespace=namespace,
            key=key,
            value=text,
            embedding=embedding,
            tags=list(metadata.keys()) if metadata else [],
        )
        
        # Store in vector DB
        if self.vector_client:
            await self._store_in_vector_db(entry, metadata)
        
        return entry
    
    async def search_semantic(
        self,
        namespace: str,
        query: str,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> list[dict]:
        """Semantic search using vector similarity."""
        query_embedding = await self._generate_embedding(query)
        
        if self.vector_client:
            results = await self._vector_search(
                namespace=namespace,
                embedding=query_embedding,
                limit=limit,
                threshold=threshold,
            )
            return results
        
        return []
    
    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text."""
        # Would use embedding model (e.g., OpenAI, Bedrock)
        # For now, return placeholder
        return [0.0] * 1536
    
    async def _store_in_vector_db(self, entry: MemoryEntry, metadata: dict):
        """Store in OpenSearch/vector DB."""
        pass  # Would use vector_client
    
    async def _vector_search(
        self,
        namespace: str,
        embedding: list[float],
        limit: int,
        threshold: float,
    ) -> list[dict]:
        """Search vector DB."""
        pass  # Would use vector_client
    
    # =========================================================================
    # Episodic Memory (Event History)
    # =========================================================================
    
    def log_event(
        self,
        namespace: str,
        event_type: str,
        data: dict,
        importance: float = 0.5,
    ):
        """Log an event to episodic memory."""
        if namespace not in self._episodic:
            self._episodic[namespace] = []
        
        event = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "data": data,
            "importance": importance,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self._episodic[namespace].append(event)
        
        # Keep most important/recent events
        max_events = 1000
        if len(self._episodic[namespace]) > max_events:
            # Sort by importance and recency, keep top
            events = self._episodic[namespace]
            events.sort(key=lambda e: (e["importance"], e["timestamp"]), reverse=True)
            self._episodic[namespace] = events[:max_events]
    
    def get_events(
        self,
        namespace: str,
        event_type: str = None,
        since: datetime = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get events from episodic memory."""
        events = self._episodic.get(namespace, [])
        
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        
        if since:
            events = [e for e in events if e["timestamp"] >= since.isoformat()]
        
        return events[-limit:]
    
    def summarize_events(
        self,
        namespace: str,
        event_type: str = None,
        time_period: timedelta = None,
    ) -> dict:
        """Get summary of events."""
        events = self._episodic.get(namespace, [])
        
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        
        if time_period:
            cutoff = (datetime.utcnow() - time_period).isoformat()
            events = [e for e in events if e["timestamp"] >= cutoff]
        
        # Aggregate by type
        by_type = {}
        for event in events:
            t = event["type"]
            if t not in by_type:
                by_type[t] = 0
            by_type[t] += 1
        
        return {
            "total_events": len(events),
            "by_type": by_type,
            "time_range": {
                "start": events[0]["timestamp"] if events else None,
                "end": events[-1]["timestamp"] if events else None,
            },
        }
    
    # =========================================================================
    # Utilities
    # =========================================================================
    
    def get_namespace_stats(self, namespace: str) -> dict:
        """Get memory statistics for a namespace."""
        return {
            "short_term": {
                "message_count": len(self._short_term.get(namespace, [])),
            },
            "long_term": {
                "entry_count": len(self._long_term.get(namespace, {})),
            },
            "episodic": {
                "event_count": len(self._episodic.get(namespace, [])),
            },
        }
    
    def clear_namespace(self, namespace: str):
        """Clear all memory for a namespace."""
        self._short_term.pop(namespace, None)
        self._long_term.pop(namespace, None)
        self._episodic.pop(namespace, None)
