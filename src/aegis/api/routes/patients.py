"""
Patient Routes

Endpoints for patient data and 360-degree views.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from aegis.api.auth import TenantContext, get_tenant_context
from aegis.graph.client import get_graph_client
from aegis.graph.queries import GraphQueries

router = APIRouter(prefix="/patients", tags=["Patients"])


# =============================================================================
# Response Models
# =============================================================================

class PatientSummary(BaseModel):
    """Basic patient information."""
    id: str
    mrn: str
    given_name: str
    family_name: str
    birth_date: str | None
    gender: str | None
    
    
class PatientListResponse(BaseModel):
    """List of patients."""
    patients: list[PatientSummary]
    total: int
    page: int
    page_size: int


class EncounterSummary(BaseModel):
    """Encounter summary for patient view."""
    id: str
    type: str
    status: str
    admit_date: str
    discharge_date: str | None
    diagnoses: list[dict] = Field(default_factory=list)
    procedures: list[dict] = Field(default_factory=list)


class ClaimSummary(BaseModel):
    """Claim summary for patient view."""
    id: str
    claim_number: str
    type: str
    status: str
    billed_amount: float
    paid_amount: float | None
    denial_reason: str | None = None


class Patient360Response(BaseModel):
    """Complete 360-degree patient view."""
    patient: dict
    encounters: list[EncounterSummary] = Field(default_factory=list)
    claims: list[ClaimSummary] = Field(default_factory=list)
    medications: list[dict] = Field(default_factory=list)
    risk_scores: dict = Field(default_factory=dict)
    financial_summary: dict = Field(default_factory=dict)


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=PatientListResponse)
async def list_patients(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(default=None, description="Search by name or MRN"),
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    List patients for the current tenant.
    
    Supports pagination and search.
    """
    try:
        client = await get_graph_client()
        
        # Build query
        offset = (page - 1) * page_size
        
        if search:
            query = """
            g.V()
                .hasLabel('Patient')
                .has('tenant_id', tenant_id)
                .or(
                    has('mrn', containing(search)),
                    has('given_name', containing(search)),
                    has('family_name', containing(search))
                )
                .order().by('family_name', asc)
                .range(offset, offset + limit)
                .valueMap(true)
            """
            bindings = {
                "tenant_id": tenant.tenant_id,
                "search": search,
                "offset": offset,
                "limit": page_size,
            }
        else:
            query = """
            g.V()
                .hasLabel('Patient')
                .has('tenant_id', tenant_id)
                .order().by('family_name', asc)
                .range(offset, offset + limit)
                .valueMap(true)
            """
            bindings = {
                "tenant_id": tenant.tenant_id,
                "offset": offset,
                "limit": page_size,
            }
        
        results = await client.execute(query, bindings)
        
        # Count total
        count_query = """
        g.V()
            .hasLabel('Patient')
            .has('tenant_id', tenant_id)
            .count()
        """
        count_result = await client.execute(count_query, {"tenant_id": tenant.tenant_id})
        total = count_result[0] if count_result else 0
        
        # Transform results
        patients = []
        for row in results:
            patients.append(PatientSummary(
                id=str(row.get("id", [""])[0] if isinstance(row.get("id"), list) else row.get("id", "")),
                mrn=row.get("mrn", [""])[0] if isinstance(row.get("mrn"), list) else row.get("mrn", ""),
                given_name=row.get("given_name", [""])[0] if isinstance(row.get("given_name"), list) else row.get("given_name", ""),
                family_name=row.get("family_name", [""])[0] if isinstance(row.get("family_name"), list) else row.get("family_name", ""),
                birth_date=row.get("birth_date", [None])[0] if isinstance(row.get("birth_date"), list) else row.get("birth_date"),
                gender=row.get("gender", [None])[0] if isinstance(row.get("gender"), list) else row.get("gender"),
            ))
        
        return PatientListResponse(
            patients=patients,
            total=total,
            page=page,
            page_size=page_size,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list patients: {str(e)}",
        )


@router.get("/{patient_id}", response_model=Patient360Response)
async def get_patient_360(
    patient_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Get a complete 360-degree view of a patient.
    
    Includes:
    - Patient demographics
    - All encounters with diagnoses and procedures
    - Claims and payment status
    - Active medications
    - Risk scores
    - Financial summary
    """
    try:
        client = await get_graph_client()
        queries = GraphQueries(client)
        
        # Get patient 360 data
        data = await queries.get_patient_360_view(patient_id)
        
        if not data or not data.get("patient"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found",
            )
        
        # Transform encounters
        encounters = []
        for enc in data.get("encounters", []):
            encounters.append(EncounterSummary(
                id=str(enc.get("encounter", {}).get("id", "")),
                type=enc.get("encounter", {}).get("type", [""])[0] if isinstance(enc.get("encounter", {}).get("type"), list) else enc.get("encounter", {}).get("type", ""),
                status=enc.get("encounter", {}).get("status", [""])[0] if isinstance(enc.get("encounter", {}).get("status"), list) else enc.get("encounter", {}).get("status", ""),
                admit_date=enc.get("encounter", {}).get("admit_date", [""])[0] if isinstance(enc.get("encounter", {}).get("admit_date"), list) else enc.get("encounter", {}).get("admit_date", ""),
                discharge_date=enc.get("encounter", {}).get("discharge_date", [None])[0] if isinstance(enc.get("encounter", {}).get("discharge_date"), list) else enc.get("encounter", {}).get("discharge_date"),
                diagnoses=enc.get("diagnoses", []),
                procedures=enc.get("procedures", []),
            ))
        
        # Transform claims
        claims = []
        for clm in data.get("claims", []):
            claim_data = clm.get("claim", {})
            denials = clm.get("denials", [])
            
            claims.append(ClaimSummary(
                id=str(claim_data.get("id", "")),
                claim_number=claim_data.get("claim_number", [""])[0] if isinstance(claim_data.get("claim_number"), list) else claim_data.get("claim_number", ""),
                type=claim_data.get("type", [""])[0] if isinstance(claim_data.get("type"), list) else claim_data.get("type", ""),
                status=claim_data.get("status", [""])[0] if isinstance(claim_data.get("status"), list) else claim_data.get("status", ""),
                billed_amount=float(claim_data.get("billed_amount", [0])[0] if isinstance(claim_data.get("billed_amount"), list) else claim_data.get("billed_amount", 0)),
                paid_amount=float(claim_data.get("paid_amount", [0])[0]) if claim_data.get("paid_amount") else None,
                denial_reason=denials[0].get("reason_code", [""])[0] if denials else None,
            ))
        
        # Calculate financial summary
        total_billed = sum(c.billed_amount for c in claims)
        total_paid = sum(c.paid_amount or 0 for c in claims)
        total_denied = sum(c.billed_amount for c in claims if c.status == "denied")
        
        # Calculate risk scores (placeholder - would be computed by agents)
        risk_scores = {
            "readmission_30day": 0.0,
            "mortality": 0.0,
            "fall_risk": "low",
        }
        
        return Patient360Response(
            patient=data.get("patient", {}),
            encounters=encounters,
            claims=claims,
            medications=data.get("medications", []),
            risk_scores=risk_scores,
            financial_summary={
                "total_billed": total_billed,
                "total_paid": total_paid,
                "total_denied": total_denied,
                "collection_rate": total_paid / total_billed if total_billed > 0 else 0,
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patient 360 view: {str(e)}",
        )


@router.get("/mrn/{mrn}", response_model=Patient360Response)
async def get_patient_by_mrn(
    mrn: str,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Get a patient by MRN (Medical Record Number).
    """
    try:
        client = await get_graph_client()
        queries = GraphQueries(client)
        
        # Find patient by MRN
        patient = await queries.get_patient_by_mrn(mrn, tenant.tenant_id)
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with MRN {mrn} not found",
            )
        
        # Get patient ID and fetch 360 view
        patient_id = patient.get("id", [None])[0] if isinstance(patient.get("id"), list) else patient.get("id")
        
        if not patient_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with MRN {mrn} not found",
            )
        
        # Reuse the 360 endpoint logic
        return await get_patient_360(str(patient_id), tenant)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patient by MRN: {str(e)}",
        )
