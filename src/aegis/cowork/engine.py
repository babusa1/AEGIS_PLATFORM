"""
Cowork Engine

The Cowork Engine wraps WorkflowEngine and adds Cowork-specific features:
- Session persistence (Redis)
- Multi-user collaboration
- State synchronization
- Artifact management
- OODA loop workflow (Perceive-Orient-Decide-Act)
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json
import hashlib

import structlog
from pydantic import ValidationError

from aegis.orchestrator.engine import WorkflowEngine
from aegis.orchestrator.models import WorkflowDefinition, ExecutionStatus
from aegis.cowork.models import (
    CoworkSession,
    CoworkState,
    CoworkParticipant,
    CoworkArtifact,
    SessionStatus,
    ArtifactType,
)

logger = structlog.get_logger(__name__)


class CoworkEngine:
    """
    Cowork Engine - The Agentic Collaborative Framework
    
    Cowork is the persistent environment where Human and AI collaborate.
    It wraps WorkflowEngine and adds:
    - Session persistence (Redis)
    - Multi-user collaboration
    - Real-time state synchronization
    - Artifact co-editing
    - OODA loop workflow
    
    The Cowork follows a Perceive-Orient-Decide-Act (OODA) loop:
    1. Perception (Scout Agent): Detects events (e.g., patient logs "Severe Fatigue")
    2. Orientation (Librarian Agent): Gathers context (e.g., pulls CBC/CMP, finds Hemoglobin drop)
    3. Decision (Guardian Agent): Checks safety (e.g., flags dose hold requirement)
    4. Collaboration (Supervisor): Presents case to Doctor in Sidebar
    5. Action (Human): Doctor reviews, edits, clicks Commit
    """
    
    def __init__(
        self,
        pool=None,
        tenant_id: str = "default",
        redis_client=None,
    ):
        """
        Initialize Cowork Engine.
        
        Args:
            pool: Database connection pool
            tenant_id: Tenant ID
            redis_client: Redis client for session persistence
        """
        self.pool = pool
        self.tenant_id = tenant_id
        self.redis_client = redis_client
        
        # Wrap WorkflowEngine
        self.workflow_engine = WorkflowEngine(pool=pool, tenant_id=tenant_id)
        
        # Session cache (in-memory for fast access)
        self._session_cache: Dict[str, CoworkSession] = {}
        
        # Redis key prefix
        self._redis_prefix = f"cowork:{tenant_id}:session:"
        
        logger.info("CoworkEngine initialized", tenant_id=tenant_id)
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    async def create_session(
        self,
        patient_id: Optional[str] = None,
        title: str = "Untitled Cowork Session",
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        user_role: str = "physician",
    ) -> CoworkSession:
        """
        Create a new Cowork session.
        
        Args:
            patient_id: Optional patient ID
            title: Session title
            description: Session description
            user_id: User ID of creator
            user_name: User name of creator
            user_role: User role (physician, nurse, etc.)
            
        Returns:
            CoworkSession
        """
        # Create state
        state = CoworkState(
            session_id="",  # Will be set after session creation
            patient_id=patient_id,
            status="scanning",
            tenant_id=self.tenant_id,
        )
        
        # Create session
        session = CoworkSession(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            title=title,
            description=description,
            state=state,
            status=SessionStatus.ACTIVE,
        )
        
        # Set session ID in state
        session.state.session_id = session.id
        
        # Add creator as participant
        if user_id:
            session.add_participant(
                user_id=user_id,
                name=user_name or "Unknown",
                role=user_role,
                permissions=["view", "comment", "edit", "approve"],
            )
        
        # Persist to Redis
        await self._save_session(session)
        
        # Cache in memory
        self._session_cache[session.id] = session
        
        logger.info(
            "Cowork session created",
            session_id=session.id,
            patient_id=patient_id,
            user_id=user_id,
        )
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[CoworkSession]:
        """
        Get a Cowork session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            CoworkSession or None if not found
        """
        # Check cache first
        if session_id in self._session_cache:
            return self._session_cache[session_id]
        
        # Load from Redis
        session = await self._load_session(session_id)
        if session:
            self._session_cache[session_id] = session
        
        return session
    
    async def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any],
    ) -> Optional[CoworkSession]:
        """
        Update a Cowork session.
        
        Args:
            session_id: Session ID
            updates: Dictionary of updates
            
        Returns:
            Updated CoworkSession or None if not found
        """
        session = await self.get_session(session_id)
        if not session:
            return None
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        session.updated_at = datetime.utcnow()
        
        # Persist
        await self._save_session(session)
        
        logger.info("Cowork session updated", session_id=session_id)
        
        return session
    
    async def list_sessions(
        self,
        patient_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 50,
    ) -> List[CoworkSession]:
        """
        List Cowork sessions.
        
        Args:
            patient_id: Filter by patient ID
            user_id: Filter by user ID (participant)
            status: Filter by status
            limit: Maximum number of sessions to return
            
        Returns:
            List of CoworkSession
        """
        # In production, would query Redis or database
        # For now, return cached sessions
        sessions = list(self._session_cache.values())
        
        # Apply filters
        if patient_id:
            sessions = [s for s in sessions if s.patient_id == patient_id]
        
        if user_id:
            sessions = [
                s for s in sessions
                if any(p.user_id == user_id for p in s.participants)
            ]
        
        if status:
            sessions = [s for s in sessions if s.status == status]
        
        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        
        return sessions[:limit]
    
    # =========================================================================
    # OODA Loop Workflow
    # =========================================================================
    
    async def perceive(
        self,
        session_id: str,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> CoworkSession:
        """
        Step 1: Perception (Scout Agent)
        
        Triggered when an event is detected (e.g., patient logs "Severe Fatigue").
        Updates session status to "scanning".
        
        Args:
            session_id: Session ID
            event_type: Type of event (e.g., "lab_result", "vital_abnormal", "symptom_logged")
            event_data: Event data
            
        Returns:
            Updated CoworkSession
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Add message from Scout
        session.add_message(
            role="system",
            content=f"Scout detected event: {event_type}",
            metadata={"event_type": event_type, "event_data": event_data},
        )
        
        # Update status
        session.update_status("scanning")
        
        # Update clinical context if patient-related
        if "patient_id" in event_data:
            session.state.patient_id = event_data["patient_id"]
        
        # Persist
        await self._save_session(session)
        
        logger.info(
            "Cowork perceive step",
            session_id=session_id,
            event_type=event_type,
        )
        
        return session
    
    async def orient(
        self,
        session_id: str,
        context_data: Dict[str, Any],
    ) -> CoworkSession:
        """
        Step 2: Orientation (Librarian Agent)
        
        Gathers patient context (e.g., pulls CBC/CMP, finds Hemoglobin drop).
        Updates session status to "verifying".
        
        Args:
            session_id: Session ID
            context_data: Clinical context data (labs, meds, vitals, etc.)
            
        Returns:
            Updated CoworkSession
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Update clinical context
        session.state.clinical_context.update(context_data)
        
        # Add message from Librarian
        session.add_message(
            role="assistant",
            content="Librarian: Retrieved patient context and identified key findings.",
            metadata={"context_summary": self._summarize_context(context_data)},
        )
        
        # Update status
        session.update_status("verifying")
        
        # Persist
        await self._save_session(session)
        
        logger.info("Cowork orient step", session_id=session_id)
        
        return session
    
    async def decide(
        self,
        session_id: str,
        safety_audit: List[str],
        evidence_links: List[str],
    ) -> CoworkSession:
        """
        Step 3: Decision (Guardian Agent)
        
        Checks safety and guidelines (e.g., flags dose hold requirement).
        Updates session status to "drafting".
        
        Args:
            session_id: Session ID
            safety_audit: List of safety audit messages
            evidence_links: List of FHIR resource IDs (evidence)
            
        Returns:
            Updated CoworkSession
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Add safety audit messages
        for audit_msg in safety_audit:
            session.add_safety_audit(audit_msg)
        
        # Add evidence links
        for evidence_id in evidence_links:
            session.add_evidence_link(evidence_id)
        
        # Add message from Guardian
        session.add_message(
            role="assistant",
            content=f"Guardian: Safety check completed. {len(safety_audit)} flags raised.",
            metadata={"safety_flags": len(safety_audit)},
        )
        
        # Update status
        session.update_status("drafting")
        
        # Persist
        await self._save_session(session)
        
        logger.info(
            "Cowork decide step",
            session_id=session_id,
            safety_flags=len(safety_audit),
        )
        
        return session
    
    async def collaborate(
        self,
        session_id: str,
        artifacts: List[CoworkArtifact],
    ) -> CoworkSession:
        """
        Step 4: Collaboration (Supervisor)
        
        Presents case to Doctor in Sidebar with artifacts (orders, notes, etc.).
        Updates session status to "approval_required".
        
        Args:
            session_id: Session ID
            artifacts: List of artifacts to present
            
        Returns:
            Updated CoworkSession
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Add artifacts
        for artifact in artifacts:
            session.add_artifact(artifact)
        
        # Add message from Supervisor
        artifact_titles = [a.title for a in artifacts]
        session.add_message(
            role="assistant",
            content=f"Supervisor: I've prepared {len(artifacts)} artifact(s) for your review: {', '.join(artifact_titles)}",
            metadata={"artifacts": artifact_titles},
        )
        
        # Update status
        session.update_status("approval_required")
        
        # Persist
        await self._save_session(session)
        
        logger.info(
            "Cowork collaborate step",
            session_id=session_id,
            artifact_count=len(artifacts),
        )
        
        return session
    
    async def act(
        self,
        session_id: str,
        user_id: str,
        action: str,
        artifact_updates: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> CoworkSession:
        """
        Step 5: Action (Human)
        
        Doctor reviews, edits, and commits artifacts.
        Updates session status to "completed".
        
        Args:
            session_id: Session ID
            user_id: User ID of person taking action
            action: Action taken ("approve", "reject", "edit", "commit")
            artifact_updates: Optional updates to artifacts (artifact_id -> updates dict)
            
        Returns:
            Updated CoworkSession
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Apply artifact updates
        if artifact_updates:
            for artifact_id, updates in artifact_updates.items():
                session.update_artifact(artifact_id, updates, edited_by=user_id)
        
        # Add message from user
        session.add_message(
            role="user",
            content=f"User action: {action}",
            user_id=user_id,
            metadata={"action": action},
        )
        
        # Update artifact statuses based on action
        if action == "approve":
            for artifact in session.state.active_artifacts:
                if artifact.status == "review":
                    artifact.status = "approved"
        elif action == "commit":
            for artifact in session.state.active_artifacts:
                if artifact.status == "approved":
                    artifact.status = "committed"
            # Complete session
            session.update_status("completed")
        
        # Persist
        await self._save_session(session)
        
        logger.info(
            "Cowork act step",
            session_id=session_id,
            user_id=user_id,
            action=action,
        )
        
        return session
    
    # =========================================================================
    # Artifact Management
    # =========================================================================
    
    async def add_artifact(
        self,
        session_id: str,
        artifact: CoworkArtifact,
    ) -> CoworkSession:
        """Add an artifact to a session."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        session.add_artifact(artifact)
        await self._save_session(session)
        
        return session
    
    async def update_artifact(
        self,
        session_id: str,
        artifact_id: str,
        updates: Dict[str, Any],
        edited_by: str,
    ) -> CoworkSession:
        """Update an artifact in a session."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        session.update_artifact(artifact_id, updates, edited_by)
        await self._save_session(session)
        
        return session
    
    # =========================================================================
    # Participant Management
    # =========================================================================
    
    async def add_participant(
        self,
        session_id: str,
        user_id: str,
        name: str,
        role: str,
        permissions: Optional[List[str]] = None,
    ) -> CoworkSession:
        """Add a participant to a session."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        session.add_participant(user_id, name, role, permissions)
        await self._save_session(session)
        
        return session
    
    async def remove_participant(
        self,
        session_id: str,
        user_id: str,
    ) -> CoworkSession:
        """Remove a participant from a session."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        session.remove_participant(user_id)
        await self._save_session(session)
        
        return session
    
    # =========================================================================
    # Redis Persistence
    # =========================================================================
    
    async def _save_session(self, session: CoworkSession):
        """Save session to Redis."""
        if not self.redis_client:
            logger.warning("Redis not available, session not persisted", session_id=session.id)
            return
        
        try:
            key = f"{self._redis_prefix}{session.id}"
            # Serialize session
            session_dict = session.model_dump(mode="json")
            session_json = json.dumps(session_dict, default=str)
            
            # Save with TTL (7 days)
            ttl_seconds = 7 * 24 * 60 * 60
            await self.redis_client.setex(key, ttl_seconds, session_json)
            
            logger.debug("Session saved to Redis", session_id=session.id)
        except Exception as e:
            logger.error("Failed to save session to Redis", session_id=session.id, error=str(e))
    
    async def _load_session(self, session_id: str) -> Optional[CoworkSession]:
        """Load session from Redis."""
        if not self.redis_client:
            return None
        
        try:
            key = f"{self._redis_prefix}{session_id}"
            session_json = await self.redis_client.get(key)
            
            if not session_json:
                return None
            
            # Deserialize
            session_dict = json.loads(session_json)
            session = CoworkSession(**session_dict)
            
            logger.debug("Session loaded from Redis", session_id=session_id)
            return session
        except Exception as e:
            logger.error("Failed to load session from Redis", session_id=session_id, error=str(e))
            return None
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _summarize_context(self, context_data: Dict[str, Any]) -> str:
        """Summarize clinical context for logging."""
        summary_parts = []
        
        if "labs" in context_data:
            summary_parts.append(f"{len(context_data['labs'])} lab(s)")
        if "meds" in context_data:
            summary_parts.append(f"{len(context_data['meds'])} medication(s)")
        if "vitals" in context_data:
            summary_parts.append(f"{len(context_data['vitals'])} vital(s)")
        
        return ", ".join(summary_parts) if summary_parts else "No context"
