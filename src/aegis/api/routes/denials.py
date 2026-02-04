"""
Denials API Routes

Endpoints for denial management, analytics, and appeal workflow.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Literal

import structlog

from aegis.api.auth import get_current_user, User

logger = structlog.get_logger(__name__)


def get_postgres_pool(request: Request):
    """Get PostgreSQL pool from app state."""
    try:
        pool = getattr(request.app.state.db, "postgres", None)
        return pool
    except Exception:
        return None

router = APIRouter(prefix="/denials", tags=["Denials"])


# =============================================================================
# Models
# =============================================================================

class Denial(BaseModel):
    """Denial response model."""
    id: str
    claim_id: str
    claim_number: str
    patient_id: str
    patient_name: str
    mrn: str
    payer: str
    denial_code: str
    denial_category: str
    denial_reason: str
    denied_amount: float
    service_date: str | None
    denial_date: str | None
    appeal_deadline: str | None
    days_to_deadline: int | None
    appeal_status: str
    priority: str
    notes: str | None = None


class DenialListResponse(BaseModel):
    """Response for denial list."""
    denials: list[Denial]
    total: int
    page: int
    page_size: int


class DenialAnalytics(BaseModel):
    """Denial analytics summary."""
    total_denials: int
    total_denied_amount: float
    pending_count: int
    in_progress_count: int
    appealed_count: int
    won_count: int
    lost_count: int
    urgent_count: int
    win_rate: float
    by_category: list[dict]
    by_payer: list[dict]


class UpdateStatusRequest(BaseModel):
    """Request to update denial status."""
    status: Literal["pending", "in_progress", "appealed", "won", "lost"]
    notes: str | None = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=DenialListResponse)
async def list_denials(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by appeal status"),
    priority: str | None = Query(None, description="Filter by priority"),
    category: str | None = Query(None, description="Filter by denial category"),
    current_user: User = Depends(get_current_user),
):
    """
    List denials with filtering and pagination.
    
    Returns denials sorted by priority and deadline.
    """
    pool = get_postgres_pool(request)
    
    if pool is None:
        # Return mock data for demo
        return DenialListResponse(
            denials=[
                Denial(
                    id="denial-001",
                    claim_id="claim-011",
                    claim_number="CLM-2024-0011",
                    patient_id="patient-001",
                    patient_name="John Smith",
                    mrn="MRN001001",
                    payer="Blue Cross Blue Shield",
                    denial_code="PR-204",
                    denial_category="medical_necessity",
                    denial_reason="Medical necessity not established",
                    denied_amount=850.00,
                    service_date="2024-01-20",
                    denial_date="2024-01-25",
                    appeal_deadline="2024-02-25",
                    days_to_deadline=5,
                    appeal_status="pending",
                    priority="critical",
                )
            ],
            total=1,
            page=1,
            page_size=20
        )
    
    from aegis.db.postgres_repo import PostgresDenialsRepository
    repo = PostgresDenialsRepository(pool)
    
    offset = (page - 1) * page_size
    denials, total = await repo.list_denials(
        tenant_id=current_user.tenant_id,
        limit=page_size,
        offset=offset,
        status=status,
        priority=priority,
        category=category,
    )
    
    return DenialListResponse(
        denials=[Denial(**d) for d in denials],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/analytics", response_model=DenialAnalytics)
async def get_denial_analytics(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Get denial analytics summary.
    
    Returns aggregated statistics by category, payer, and status.
    """
    pool = get_postgres_pool(request)
    
    if pool is None:
        # Return mock analytics for demo
        return DenialAnalytics(
            total_denials=10,
            total_denied_amount=24505.00,
            pending_count=6,
            in_progress_count=2,
            appealed_count=1,
            won_count=0,
            lost_count=0,
            urgent_count=2,
            win_rate=0.68,
            by_category=[
                {"category": "medical_necessity", "count": 3, "amount": 14925.00},
                {"category": "authorization", "count": 3, "amount": 1180.00},
                {"category": "coverage", "count": 2, "amount": 1700.00},
                {"category": "documentation", "count": 1, "amount": 4500.00},
                {"category": "coding", "count": 1, "amount": 2200.00},
            ],
            by_payer=[
                {"payer": "Medicare", "count": 4, "amount": 17775.00},
                {"payer": "Aetna", "count": 1, "amount": 2200.00},
                {"payer": "United Healthcare", "count": 2, "amount": 1825.00},
                {"payer": "Blue Cross Blue Shield", "count": 1, "amount": 850.00},
                {"payer": "Cigna", "count": 2, "amount": 855.00},
            ]
        )
    
    from aegis.db.postgres_repo import PostgresDenialsRepository
    repo = PostgresDenialsRepository(pool)
    
    analytics = await repo.get_denial_analytics(tenant_id=current_user.tenant_id)
    return DenialAnalytics(**analytics)


@router.get("/{denial_id}")
async def get_denial(
    request: Request,
    denial_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get a single denial with full details."""
    pool = get_postgres_pool(request)
    
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    from aegis.db.postgres_repo import PostgresDenialsRepository
    repo = PostgresDenialsRepository(pool)
    
    denial = await repo.get_denial(denial_id)
    
    if not denial:
        raise HTTPException(status_code=404, detail="Denial not found")
    
    return denial


@router.patch("/{denial_id}/status")
async def update_denial_status(
    request: Request,
    denial_id: str,
    body: UpdateStatusRequest,
    current_user: User = Depends(get_current_user),
):
    """Update the appeal status of a denial."""
    pool = get_postgres_pool(request)
    
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    from aegis.db.postgres_repo import PostgresDenialsRepository
    repo = PostgresDenialsRepository(pool)
    
    success = await repo.update_denial_status(denial_id, body.status, body.notes)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update status")
    
    return {"status": "updated", "denial_id": denial_id, "new_status": body.status}
