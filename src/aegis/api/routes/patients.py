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


class ConditionSummary(BaseModel):
    """Condition summary for patient view."""
    id: str
    code: str
    display: str
    status: str


class VitalSign(BaseModel):
    """Vital sign reading."""
    type: str
    value: float
    unit: str
    timestamp: str | None = None


class Patient360Response(BaseModel):
    """Complete 360-degree patient view."""
    patient: dict
    conditions: list[ConditionSummary] = Field(default_factory=list)
    encounters: list[EncounterSummary] = Field(default_factory=list)
    claims: list[ClaimSummary] = Field(default_factory=list)
    medications: list[dict] = Field(default_factory=list)
    vitals: list[VitalSign] = Field(default_factory=list)
    risk_scores: dict = Field(default_factory=dict)
    patient_status: dict = Field(default_factory=dict)
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


def _extract_value(data: dict, key: str, default=""):
    """Extract value from graph result, handling list wrapping."""
    val = data.get(key, [default])
    return val[0] if isinstance(val, list) and val else val if val else default


def _calculate_risk_scores(conditions: list, medications: list, patient: dict) -> dict:
    """Calculate real risk scores based on patient data."""
    risk_score = 0.0
    risk_factors = []
    
    # High-risk conditions
    high_risk_codes = {
        "E11": ("Diabetes", 0.15),
        "I10": ("Hypertension", 0.10),
        "I50": ("Heart Failure", 0.25),
        "J44": ("COPD", 0.20),
        "N18": ("Chronic Kidney Disease", 0.20),
        "E78": ("Hyperlipidemia", 0.05),
    }
    
    for cond in conditions:
        code = cond.get("code", "")[:3]
        if code in high_risk_codes:
            name, score = high_risk_codes[code]
            risk_score += score
            risk_factors.append(name)
    
    # Age factor
    birth_date = _extract_value(patient, "birth_date", "")
    if birth_date:
        try:
            from datetime import datetime
            birth_year = int(birth_date[:4])
            age = datetime.now().year - birth_year
            if age > 65:
                risk_score += 0.10
                risk_factors.append("Age > 65")
            if age > 80:
                risk_score += 0.15
                risk_factors.append("Age > 80")
        except:
            pass
    
    # Polypharmacy risk
    if len(medications) >= 5:
        risk_score += 0.10
        risk_factors.append("Polypharmacy (5+ medications)")
    
    # Cap at 1.0
    risk_score = min(risk_score, 1.0)
    
    # Determine risk level
    if risk_score >= 0.6:
        risk_level = "high"
    elif risk_score >= 0.3:
        risk_level = "moderate"
    else:
        risk_level = "low"
    
    return {
        "overall_score": round(risk_score, 2),
        "risk_level": risk_level,
        "readmission_30day": round(risk_score * 0.8, 2),
        "fall_risk": "high" if risk_score > 0.5 else "moderate" if risk_score > 0.25 else "low",
        "risk_factors": risk_factors,
    }


def _calculate_patient_status(conditions: list, risk_scores: dict) -> dict:
    """Calculate patient status indicator (Green/Yellow/Red)."""
    risk_level = risk_scores.get("risk_level", "low")
    
    if risk_level == "high":
        return {
            "status": "RED",
            "label": "High Risk",
            "message": "Patient requires close monitoring",
            "factors": risk_scores.get("risk_factors", [])
        }
    elif risk_level == "moderate":
        return {
            "status": "YELLOW",
            "label": "Moderate Risk", 
            "message": "Patient needs regular follow-up",
            "factors": risk_scores.get("risk_factors", [])
        }
    else:
        return {
            "status": "GREEN",
            "label": "Stable",
            "message": "Patient condition is stable",
            "factors": []
        }


@router.get("/{patient_id}", response_model=Patient360Response)
async def get_patient_360(
    patient_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Get a complete 360-degree view of a patient.
    
    Includes:
    - Patient demographics
    - Active conditions
    - All encounters with diagnoses and procedures
    - Claims and payment status
    - Active medications
    - Recent vitals
    - Risk scores (calculated)
    - Patient status indicator
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
        
        # Get conditions
        conditions_query = f"g.V('{patient_id}').out('HAS_CONDITION').valueMap(true)"
        conditions_data = await client.execute(conditions_query, {"patient_id": patient_id})
        
        conditions = []
        for cond in conditions_data:
            conditions.append(ConditionSummary(
                id=_extract_value(cond, "id"),
                code=_extract_value(cond, "code"),
                display=_extract_value(cond, "display"),
                status=_extract_value(cond, "status", "active"),
            ))
        
        # Transform encounters
        encounters = []
        for enc in data.get("encounters", []):
            enc_data = enc.get("encounter", {})
            encounters.append(EncounterSummary(
                id=str(_extract_value(enc_data, "id")),
                type=_extract_value(enc_data, "type"),
                status=_extract_value(enc_data, "status"),
                admit_date=_extract_value(enc_data, "admit_date"),
                discharge_date=_extract_value(enc_data, "discharge_date") or None,
                diagnoses=enc.get("diagnoses", []),
                procedures=enc.get("procedures", []),
            ))
        
        # Transform claims
        claims = []
        for clm in data.get("claims", []):
            claim_data = clm.get("claim", {})
            denials = clm.get("denials", [])
            
            billed = _extract_value(claim_data, "billed_amount", 0)
            paid = _extract_value(claim_data, "paid_amount", 0)
            
            claims.append(ClaimSummary(
                id=str(_extract_value(claim_data, "id")),
                claim_number=_extract_value(claim_data, "claim_number"),
                type=_extract_value(claim_data, "type"),
                status=_extract_value(claim_data, "status"),
                billed_amount=float(billed) if billed else 0.0,
                paid_amount=float(paid) if paid else None,
                denial_reason=_extract_value(denials[0], "reason_code") if denials else None,
            ))
        
        # Sample vitals (would come from TimescaleDB in production)
        vitals = [
            VitalSign(type="Blood Pressure", value=128, unit="mmHg (systolic)", timestamp="2024-01-15T10:30:00Z"),
            VitalSign(type="Heart Rate", value=72, unit="bpm", timestamp="2024-01-15T10:30:00Z"),
            VitalSign(type="Temperature", value=98.6, unit="°F", timestamp="2024-01-15T10:30:00Z"),
            VitalSign(type="SpO2", value=98, unit="%", timestamp="2024-01-15T10:30:00Z"),
        ]
        
        # Calculate real risk scores
        medications = data.get("medications", [])
        risk_scores = _calculate_risk_scores(
            [c.model_dump() for c in conditions],
            medications,
            data.get("patient", {})
        )
        
        # Calculate patient status
        patient_status = _calculate_patient_status(
            [c.model_dump() for c in conditions],
            risk_scores
        )
        
        # Calculate financial summary
        total_billed = sum(c.billed_amount for c in claims)
        total_paid = sum(c.paid_amount or 0 for c in claims)
        total_denied = sum(c.billed_amount for c in claims if c.status == "denied")
        
        return Patient360Response(
            patient=data.get("patient", {}),
            conditions=conditions,
            encounters=encounters,
            claims=claims,
            medications=medications,
            vitals=vitals,
            risk_scores=risk_scores,
            patient_status=patient_status,
            financial_summary={
                "total_billed": total_billed,
                "total_paid": total_paid,
                "total_denied": total_denied,
                "collection_rate": round(total_paid / total_billed, 2) if total_billed > 0 else 0,
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
