"""
Claims Routes

Endpoints for claim management and denial workflows.
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from aegis.api.auth import TenantContext, get_tenant_context
from aegis.graph.client import get_graph_client
from aegis.graph.queries import GraphQueries

router = APIRouter(prefix="/claims", tags=["Claims"])


# =============================================================================
# Response Models
# =============================================================================

class ClaimListItem(BaseModel):
    """Claim item for list view."""
    id: str
    claim_number: str
    type: str
    status: str
    service_date: str
    billed_amount: float
    paid_amount: float | None
    patient_mrn: str | None
    payer_name: str | None


class ClaimListResponse(BaseModel):
    """List of claims."""
    claims: list[ClaimListItem]
    total: int
    page: int
    page_size: int


class DenialDetail(BaseModel):
    """Denial details."""
    id: str
    reason_code: str
    category: str
    description: str
    denied_amount: float
    denial_date: str
    appeal_deadline: str | None


class ClaimDetailResponse(BaseModel):
    """Detailed claim view."""
    id: str
    claim_number: str
    type: str
    status: str
    service_date_start: str
    service_date_end: str | None
    submission_date: str | None
    billed_amount: float
    allowed_amount: float | None
    paid_amount: float | None
    patient_responsibility: float | None
    patient: dict | None
    encounter: dict | None
    payer: dict | None
    diagnoses: list[dict] = Field(default_factory=list)
    procedures: list[dict] = Field(default_factory=list)
    denials: list[DenialDetail] = Field(default_factory=list)


class DeniedClaimSummary(BaseModel):
    """Summary of denied claims."""
    claim_id: str
    claim_number: str
    patient_mrn: str
    patient_name: str
    denial_reason: str
    denial_category: str
    denied_amount: float
    appeal_deadline: str | None
    days_to_deadline: int | None


class DeniedClaimsResponse(BaseModel):
    """List of denied claims for review."""
    denied_claims: list[DeniedClaimSummary]
    total: int
    total_denied_amount: float
    by_category: dict[str, int]


class DenialAnalyticsResponse(BaseModel):
    """Denial analytics summary."""
    total_denials: int
    total_denied_amount: float
    by_reason_category: dict[str, dict]
    by_payer: dict[str, dict]
    top_denial_codes: list[dict]
    trend: list[dict]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=ClaimListResponse)
async def list_claims(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    payer_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    List claims for the current tenant.
    
    Supports filtering by status, payer, and date range.
    """
    try:
        client = await get_graph_client()
        
        offset = (page - 1) * page_size
        
        # Build dynamic query
        query = """
        g.V()
            .hasLabel('Claim')
            .has('tenant_id', tenant_id)
        """
        
        bindings = {"tenant_id": tenant.tenant_id}
        
        if status_filter:
            query += ".has('status', status_filter)"
            bindings["status_filter"] = status_filter
        
        query += """
            .order().by('service_date_start', desc)
            .range(offset, offset + limit)
            .project('claim', 'patient_mrn')
            .by(valueMap(true))
            .by(
                coalesce(
                    in('BILLED_FOR').in('HAS_ENCOUNTER').values('mrn'),
                    constant('N/A')
                )
            )
        """
        
        bindings["offset"] = offset
        bindings["limit"] = page_size
        
        results = await client.execute(query, bindings)
        
        # Count total
        count_query = """
        g.V()
            .hasLabel('Claim')
            .has('tenant_id', tenant_id)
            .count()
        """
        count_result = await client.execute(count_query, {"tenant_id": tenant.tenant_id})
        total = count_result[0] if count_result else 0
        
        # Transform results
        claims = []
        for row in results:
            claim_data = row.get("claim", {})
            claims.append(ClaimListItem(
                id=str(claim_data.get("id", [""])[0] if isinstance(claim_data.get("id"), list) else claim_data.get("id", "")),
                claim_number=claim_data.get("claim_number", [""])[0] if isinstance(claim_data.get("claim_number"), list) else claim_data.get("claim_number", ""),
                type=claim_data.get("type", [""])[0] if isinstance(claim_data.get("type"), list) else claim_data.get("type", ""),
                status=claim_data.get("status", [""])[0] if isinstance(claim_data.get("status"), list) else claim_data.get("status", ""),
                service_date=claim_data.get("service_date_start", [""])[0] if isinstance(claim_data.get("service_date_start"), list) else claim_data.get("service_date_start", ""),
                billed_amount=float(claim_data.get("billed_amount", [0])[0] if isinstance(claim_data.get("billed_amount"), list) else claim_data.get("billed_amount", 0)),
                paid_amount=float(claim_data.get("paid_amount", [0])[0]) if claim_data.get("paid_amount") else None,
                patient_mrn=row.get("patient_mrn"),
                payer_name=None,  # Would need additional join
            ))
        
        return ClaimListResponse(
            claims=claims,
            total=total,
            page=page,
            page_size=page_size,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list claims: {str(e)}",
        )


@router.get("/denied", response_model=DeniedClaimsResponse)
async def list_denied_claims(
    min_amount: float | None = Query(default=None, description="Minimum denied amount"),
    payer_id: str | None = Query(default=None),
    category: str | None = Query(default=None, description="Denial category filter"),
    limit: int = Query(default=50, ge=1, le=200),
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    List denied claims for review and appeal.
    
    Returns claims with active denials, sorted by denied amount.
    Useful for prioritizing appeal work.
    """
    try:
        client = await get_graph_client()
        queries = GraphQueries(client)
        
        results = await queries.get_denied_claims(
            tenant_id=tenant.tenant_id,
            payer_id=payer_id,
            min_amount=min_amount,
            limit=limit,
        )
        
        denied_claims = []
        total_denied = 0.0
        by_category: dict[str, int] = {}
        
        for row in results:
            claim_data = row.get("claim", {})
            denial_reasons = row.get("denial_reason", [])
            patient_mrn = row.get("patient_mrn", "N/A")
            
            denied_amount = float(claim_data.get("billed_amount", [0])[0] if isinstance(claim_data.get("billed_amount"), list) else claim_data.get("billed_amount", 0))
            total_denied += denied_amount
            
            # Count by category (simplified)
            category = denial_reasons[0] if denial_reasons else "other"
            by_category[category] = by_category.get(category, 0) + 1
            
            denied_claims.append(DeniedClaimSummary(
                claim_id=str(claim_data.get("id", [""])[0] if isinstance(claim_data.get("id"), list) else claim_data.get("id", "")),
                claim_number=claim_data.get("claim_number", [""])[0] if isinstance(claim_data.get("claim_number"), list) else claim_data.get("claim_number", ""),
                patient_mrn=patient_mrn,
                patient_name="",  # Would need additional query
                denial_reason=denial_reasons[0] if denial_reasons else "Unknown",
                denial_category=category,
                denied_amount=denied_amount,
                appeal_deadline=None,  # Would need to join with Denial vertex
                days_to_deadline=None,
            ))
        
        return DeniedClaimsResponse(
            denied_claims=denied_claims,
            total=len(denied_claims),
            total_denied_amount=total_denied,
            by_category=by_category,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list denied claims: {str(e)}",
        )


@router.get("/analytics/denials", response_model=DenialAnalyticsResponse)
async def get_denial_analytics(
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Get denial analytics summary.
    
    Returns aggregated denial statistics by category, payer, and time.
    """
    try:
        client = await get_graph_client()
        queries = GraphQueries(client)
        
        summary = await queries.get_denial_summary(tenant.tenant_id)
        
        # Transform results
        by_reason_category = {}
        total_denials = 0
        total_amount = 0.0
        
        for category, data in (summary[0] if summary else {}).items():
            count = data.get("count", 0)
            amount = data.get("total_amount", 0)
            total_denials += count
            total_amount += amount
            by_reason_category[category] = {
                "count": count,
                "amount": amount,
            }
        
        return DenialAnalyticsResponse(
            total_denials=total_denials,
            total_denied_amount=total_amount,
            by_reason_category=by_reason_category,
            by_payer={},  # Would need additional query
            top_denial_codes=[],  # Would need additional query
            trend=[],  # Would need time-series query
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get denial analytics: {str(e)}",
        )


@router.get("/{claim_id}", response_model=ClaimDetailResponse)
async def get_claim_detail(
    claim_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Get detailed claim information with full context.
    
    Includes patient, encounter, diagnoses, procedures, and denial details.
    """
    try:
        client = await get_graph_client()
        queries = GraphQueries(client)
        
        data = await queries.get_claim_with_context(claim_id)
        
        if not data or not data.get("claim"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim {claim_id} not found",
            )
        
        claim_data = data.get("claim", {})
        
        # Transform denials
        denials = []
        for denial in data.get("denials", []):
            denials.append(DenialDetail(
                id=str(denial.get("id", [""])[0] if isinstance(denial.get("id"), list) else denial.get("id", "")),
                reason_code=denial.get("reason_code", [""])[0] if isinstance(denial.get("reason_code"), list) else denial.get("reason_code", ""),
                category=denial.get("category", [""])[0] if isinstance(denial.get("category"), list) else denial.get("category", ""),
                description=denial.get("description", [""])[0] if isinstance(denial.get("description"), list) else denial.get("description", ""),
                denied_amount=float(denial.get("denied_amount", [0])[0] if isinstance(denial.get("denied_amount"), list) else denial.get("denied_amount", 0)),
                denial_date=denial.get("denial_date", [""])[0] if isinstance(denial.get("denial_date"), list) else denial.get("denial_date", ""),
                appeal_deadline=denial.get("appeal_deadline", [None])[0] if denial.get("appeal_deadline") else None,
            ))
        
        return ClaimDetailResponse(
            id=str(claim_data.get("id", [""])[0] if isinstance(claim_data.get("id"), list) else claim_data.get("id", "")),
            claim_number=claim_data.get("claim_number", [""])[0] if isinstance(claim_data.get("claim_number"), list) else claim_data.get("claim_number", ""),
            type=claim_data.get("type", [""])[0] if isinstance(claim_data.get("type"), list) else claim_data.get("type", ""),
            status=claim_data.get("status", [""])[0] if isinstance(claim_data.get("status"), list) else claim_data.get("status", ""),
            service_date_start=claim_data.get("service_date_start", [""])[0] if isinstance(claim_data.get("service_date_start"), list) else claim_data.get("service_date_start", ""),
            service_date_end=claim_data.get("service_date_end", [None])[0] if claim_data.get("service_date_end") else None,
            submission_date=claim_data.get("submission_date", [None])[0] if claim_data.get("submission_date") else None,
            billed_amount=float(claim_data.get("billed_amount", [0])[0] if isinstance(claim_data.get("billed_amount"), list) else claim_data.get("billed_amount", 0)),
            allowed_amount=float(claim_data.get("allowed_amount", [0])[0]) if claim_data.get("allowed_amount") else None,
            paid_amount=float(claim_data.get("paid_amount", [0])[0]) if claim_data.get("paid_amount") else None,
            patient_responsibility=float(claim_data.get("patient_responsibility", [0])[0]) if claim_data.get("patient_responsibility") else None,
            patient=data.get("patient"),
            encounter=data.get("encounter"),
            payer=None,  # Would need additional query
            diagnoses=data.get("diagnoses", []),
            procedures=data.get("procedures", []),
            denials=denials,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get claim detail: {str(e)}",
        )
