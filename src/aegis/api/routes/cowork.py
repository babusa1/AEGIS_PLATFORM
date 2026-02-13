"""
Cowork API Routes

REST API endpoints for Cowork sessions - the collaborative workspace
for human-AI collaboration in healthcare.
"""

from typing import Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from aegis.api.auth import TenantContext, get_tenant_context, get_current_user, User
from aegis.cowork.engine import CoworkEngine
from aegis.cowork.models import (
    CoworkSession,
    CoworkArtifact,
    SessionStatus,
    ArtifactType,
)

router = APIRouter(prefix="/cowork", tags=["Cowork"])


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateSessionRequest(BaseModel):
    """Request to create a new Cowork session."""
    patient_id: Optional[str] = None
    title: str = "Untitled Cowork Session"
    description: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    """Request to update a Cowork session."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class SessionSummary(BaseModel):
    """Summary of a Cowork session for list view."""
    id: str
    patient_id: Optional[str]
    patient_name: Optional[str] = None
    title: str
    status: str
    participants: int
    artifacts_count: int
    last_activity: str
    created_at: str


class SessionListResponse(BaseModel):
    """Response for listing sessions."""
    sessions: List[SessionSummary]
    total: int


class UpdateArtifactRequest(BaseModel):
    """Request to update an artifact."""
    content: Optional[str] = None
    title: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================

def get_cowork_engine(request: Request) -> CoworkEngine:
    """Get CoworkEngine instance from app state or create new one."""
    # Check if engine is in app state
    if hasattr(request.app.state, "cowork_engine") and request.app.state.cowork_engine:
        return request.app.state.cowork_engine
    
    # Get database pool if available
    pool = None
    if hasattr(request.app.state, "db") and request.app.state.db:
        pool = getattr(request.app.state.db, "postgres", None)
    
    # Get Redis client if available
    redis_client = None
    if hasattr(request.app.state, "redis") and request.app.state.redis:
        redis_client = request.app.state.redis
    
    # Create engine
    engine = CoworkEngine(
        pool=pool,
        tenant_id="default",  # Will be overridden by tenant context
        redis_client=redis_client,
    )
    
    # Cache in app state
    if not hasattr(request.app.state, "cowork_engine"):
        request.app.state.cowork_engine = engine
    
    return engine


def session_to_summary(session: CoworkSession) -> SessionSummary:
    """Convert CoworkSession to SessionSummary."""
    # Get patient name if available (would query in production)
    patient_name = None
    if session.patient_id:
        # In production, would query patient data
        patient_name = f"Patient {session.patient_id[-3:]}"
    
    return SessionSummary(
        id=session.id,
        patient_id=session.patient_id,
        patient_name=patient_name,
        title=session.title,
        status=session.status.value,
        participants=len(session.participants),
        artifacts_count=len(session.state.active_artifacts),
        last_activity=session.updated_at.isoformat(),
        created_at=session.created_at.isoformat(),
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
):
    """
    List Cowork sessions.
    
    Returns all sessions the current user has access to, optionally filtered
    by patient_id or status.
    """
    try:
        engine = get_cowork_engine(request)
        engine.tenant_id = tenant.tenant_id
        
        # Parse status filter
        status_filter = None
        if status:
            try:
                status_filter = SessionStatus(status)
            except ValueError:
                pass
        
        sessions = await engine.list_sessions(
            patient_id=patient_id,
            user_id=current_user.id,
            status=status_filter,
            limit=100,
        )
        
        summaries = [session_to_summary(s) for s in sessions]
        
        return SessionListResponse(
            sessions=summaries,
            total=len(summaries),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}",
        )


@router.post("/sessions", response_model=CoworkSession)
async def create_session(
    request: CreateSessionRequest,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new Cowork session.
    
    Creates a collaborative workspace for human-AI collaboration.
    The creator is automatically added as a participant with full permissions.
    """
    try:
        engine = get_cowork_engine(req)
        engine.tenant_id = tenant.tenant_id
        
        session = await engine.create_session(
            patient_id=request.patient_id,
            title=request.title,
            description=request.description,
            user_id=current_user.id,
            user_name=current_user.full_name or current_user.email,
            user_role="physician",  # Could be derived from user roles
        )
        
        return session
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}",
        )


@router.get("/sessions/{session_id}", response_model=CoworkSession)
async def get_session(
    session_id: str,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific Cowork session by ID.
    
    Returns the full session including state, participants, artifacts, and messages.
    """
    try:
        engine = get_cowork_engine(req)
        engine.tenant_id = tenant.tenant_id
        
        session = await engine.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        
        # Check if user has access (is participant or admin)
        is_participant = any(p.user_id == current_user.id for p in session.participants)
        is_admin = "admin" in current_user.roles
        
        if not (is_participant or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this session",
            )
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}",
        )


@router.put("/sessions/{session_id}", response_model=CoworkSession)
async def update_session(
    session_id: str,
    update_request: UpdateSessionRequest,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
):
    """
    Update a Cowork session.
    
    Updates session metadata like title, description, or status.
    """
    try:
        engine = get_cowork_engine(req)
        engine.tenant_id = tenant.tenant_id
        
        session = await engine.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        
        # Check permissions
        is_participant = any(p.user_id == current_user.id for p in session.participants)
        is_admin = "admin" in current_user.roles
        
        if not (is_participant or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this session",
            )
        
        updates = {}
        if update_request.title is not None:
            updates["title"] = update_request.title
        if update_request.description is not None:
            updates["description"] = update_request.description
        if update_request.status is not None:
            try:
                updates["status"] = SessionStatus(update_request.status)
            except ValueError:
                pass
        
        if updates:
            updated_session = await engine.update_session(session_id, updates)
            return updated_session
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session: {str(e)}",
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a Cowork session.
    
    Only admins or session creators can delete sessions.
    """
    try:
        engine = get_cowork_engine(req)
        engine.tenant_id = tenant.tenant_id
        
        session = await engine.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        
        # Check permissions (admin only for now)
        is_admin = "admin" in current_user.roles
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete sessions",
            )
        
        # In production, would actually delete from Redis/DB
        # For now, just mark as archived
        await engine.update_session(session_id, {"status": SessionStatus.ARCHIVED})
        
        return {"status": "deleted", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}",
        )


@router.get("/sessions/{session_id}/artifacts/{artifact_id}", response_model=CoworkArtifact)
async def get_artifact(
    session_id: str,
    artifact_id: str,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific artifact from a Cowork session.
    """
    try:
        engine = get_cowork_engine(req)
        engine.tenant_id = tenant.tenant_id
        
        session = await engine.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        
        # Find artifact
        artifact = next(
            (a for a in session.state.active_artifacts if a.id == artifact_id),
            None
        )
        
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact {artifact_id} not found in session",
            )
        
        return artifact
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get artifact: {str(e)}",
        )


@router.put("/sessions/{session_id}/artifacts/{artifact_id}", response_model=CoworkArtifact)
async def update_artifact(
    session_id: str,
    artifact_id: str,
    update_request: UpdateArtifactRequest,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
):
    """
    Update an artifact in a Cowork session.
    
    Updates the content or title of an artifact. Increments the draft version.
    """
    try:
        engine = get_cowork_engine(req)
        engine.tenant_id = tenant.tenant_id
        
        session = await engine.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        
        # Check permissions
        is_participant = any(p.user_id == current_user.id for p in session.participants)
        is_admin = "admin" in current_user.roles
        
        if not (is_participant or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to edit artifacts in this session",
            )
        
        # Update artifact
        updates = {}
        if update_request.content is not None:
            updates["content"] = update_request.content
        if update_request.title is not None:
            updates["title"] = update_request.title
        
        if updates:
            await engine.update_artifact(
                session_id=session_id,
                artifact_id=artifact_id,
                updates=updates,
                edited_by=current_user.id,
            )
            
            # Reload session to get updated artifact
            session = await engine.get_session(session_id)
            artifact = next(
                (a for a in session.state.active_artifacts if a.id == artifact_id),
                None
            )
            
            if artifact:
                return artifact
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update artifact: {str(e)}",
        )


@router.post("/sessions/{session_id}/artifacts/{artifact_id}/approve")
async def approve_artifact(
    session_id: str,
    artifact_id: str,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
):
    """
    Approve an artifact in a Cowork session.
    
    Changes artifact status from "draft" or "review" to "approved".
    Only participants with "approve" permission can approve artifacts.
    """
    try:
        engine = get_cowork_engine(req)
        engine.tenant_id = tenant.tenant_id
        
        session = await engine.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        
        # Check permissions
        participant = next(
            (p for p in session.participants if p.user_id == current_user.id),
            None
        )
        is_admin = "admin" in current_user.roles
        
        if not participant and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a participant in this session",
            )
        
        if not is_admin and "approve" not in participant.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to approve artifacts",
            )
        
        # Find and update artifact
        artifact = next(
            (a for a in session.state.active_artifacts if a.id == artifact_id),
            None
        )
        
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact {artifact_id} not found",
            )
        
        # Update artifact status
        artifact.status = "approved"
        artifact.updated_at = datetime.utcnow()
        
        # Persist the session (accessing private method for persistence)
        # This is acceptable in the API layer when we need to persist state changes
        await engine._save_session(session)
        
        return {
            "status": "approved",
            "artifact_id": artifact_id,
            "session_id": session_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve artifact: {str(e)}",
        )
