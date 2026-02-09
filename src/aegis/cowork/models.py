"""
Cowork Models

Data models for Cowork sessions, state, participants, and artifacts.
"""

from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Cowork session status."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ArtifactType(str, Enum):
    """Types of artifacts in Cowork sessions."""
    SOAP_NOTE = "soap_note"
    REFERRAL_LETTER = "referral_letter"
    PRIOR_AUTH = "prior_auth"
    ORDER = "order"
    DISCHARGE_SUMMARY = "discharge_summary"
    PATIENT_INSTRUCTION = "patient_instruction"
    APPEAL_LETTER = "appeal_letter"
    OTHER = "other"


class CoworkParticipant(BaseModel):
    """A participant in a Cowork session."""
    user_id: str
    name: str
    role: str  # "physician", "nurse", "admin", etc.
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    permissions: List[str] = Field(default_factory=lambda: ["view", "comment"])  # view, comment, edit, approve


class CoworkArtifact(BaseModel):
    """An artifact being co-edited in a Cowork session."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ArtifactType
    title: str
    content: str = ""
    draft_version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str  # user_id
    edited_by: Optional[str] = None  # user_id of last editor
    status: Literal["draft", "review", "approved", "committed"] = "draft"
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Additional metadata (FHIR resource IDs, etc.)


class CoworkState(BaseModel):
    """
    The shared state of a Cowork session.
    
    This is the "Shared Memory" of the Cowork session, following the OODA loop:
    - Perception: Scout agent detects events
    - Orientation: Librarian agent gathers context
    - Decision: Guardian agent checks safety
    - Collaboration: Supervisor presents to human
    - Action: Human approves and commits
    """
    # Session metadata
    session_id: str
    patient_id: Optional[str] = None
    clinical_context: Dict[str, Any] = Field(default_factory=dict)  # Structured data (Labs, Meds)
    
    # Active artifacts (shared documents)
    active_artifacts: List[CoworkArtifact] = Field(default_factory=list)
    
    # Safety audit (Guardian logs)
    safety_audit: List[str] = Field(default_factory=list)
    
    # Evidence links (FHIR Resource IDs for every claim)
    evidence_links: List[str] = Field(default_factory=list)
    
    # Messages (collaboration thread)
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Status
    status: Literal["scanning", "verifying", "drafting", "approval_required", "completed"] = "scanning"
    
    # Participants
    participants: List[CoworkParticipant] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: str = "default"


class CoworkSession(BaseModel):
    """
    A Cowork session - the persistent environment for human-AI collaboration.
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = "default"
    patient_id: Optional[str] = None
    
    # Session info
    title: str = "Untitled Cowork Session"
    description: Optional[str] = None
    
    # State
    state: CoworkState
    
    # Status
    status: SessionStatus = SessionStatus.ACTIVE
    
    # Participants
    participants: List[CoworkParticipant] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_participant(self, user_id: str, name: str, role: str, permissions: List[str] = None):
        """Add a participant to the session."""
        if permissions is None:
            permissions = ["view", "comment"]
        
        participant = CoworkParticipant(
            user_id=user_id,
            name=name,
            role=role,
            permissions=permissions,
        )
        
        # Check if already exists
        existing = next((p for p in self.participants if p.user_id == user_id), None)
        if existing:
            existing.last_active = datetime.utcnow()
            existing.permissions = permissions  # Update permissions
        else:
            self.participants.append(participant)
            self.state.participants.append(participant)
        
        self.updated_at = datetime.utcnow()
    
    def remove_participant(self, user_id: str):
        """Remove a participant from the session."""
        self.participants = [p for p in self.participants if p.user_id != user_id]
        self.state.participants = [p for p in self.state.participants if p.user_id != user_id]
        self.updated_at = datetime.utcnow()
    
    def add_artifact(self, artifact: CoworkArtifact):
        """Add an artifact to the session."""
        self.state.active_artifacts.append(artifact)
        self.updated_at = datetime.utcnow()
    
    def update_artifact(self, artifact_id: str, updates: Dict[str, Any], edited_by: str):
        """Update an artifact."""
        artifact = next((a for a in self.state.active_artifacts if a.id == artifact_id), None)
        if artifact:
            artifact.content = updates.get("content", artifact.content)
            artifact.title = updates.get("title", artifact.title)
            artifact.draft_version += 1
            artifact.updated_at = datetime.utcnow()
            artifact.edited_by = edited_by
            artifact.metadata.update(updates.get("metadata", {}))
            self.updated_at = datetime.utcnow()
    
    def add_message(self, role: str, content: str, user_id: Optional[str] = None, metadata: Dict[str, Any] = None):
        """Add a message to the collaboration thread."""
        message = {
            "role": role,  # "user", "assistant", "system"
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "metadata": metadata or {},
        }
        self.state.messages.append(message)
        self.updated_at = datetime.utcnow()
    
    def add_safety_audit(self, audit_message: str):
        """Add a safety audit message from Guardian."""
        self.state.safety_audit.append(audit_message)
        self.updated_at = datetime.utcnow()
    
    def add_evidence_link(self, fhir_resource_id: str):
        """Add an evidence link (FHIR resource ID)."""
        if fhir_resource_id not in self.state.evidence_links:
            self.state.evidence_links.append(fhir_resource_id)
            self.updated_at = datetime.utcnow()
    
    def update_status(self, status: Literal["scanning", "verifying", "drafting", "approval_required", "completed"]):
        """Update the session status."""
        self.state.status = status
        self.updated_at = datetime.utcnow()
        
        if status == "completed":
            self.status = SessionStatus.COMPLETED
            self.completed_at = datetime.utcnow()
