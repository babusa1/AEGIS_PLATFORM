"""
Data Ingestion Routes

Endpoints for ingesting healthcare data (FHIR, synthetic).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from pydantic import BaseModel, Field

from aegis.api.auth import User, TenantContext, get_current_active_user, get_tenant_context, require_roles
from aegis.ingestion.service import IngestionService

router = APIRouter(prefix="/ingestion", tags=["Data Ingestion"])


# =============================================================================
# Request/Response Models
# =============================================================================

class FHIRIngestionRequest(BaseModel):
    """Request to ingest FHIR data."""
    bundle: dict = Field(..., description="FHIR R4 Bundle as JSON object")
    source_system: str = Field(default="fhir", description="Source system identifier")


class SyntheticDataRequest(BaseModel):
    """Request to generate synthetic data."""
    num_patients: int = Field(default=100, ge=1, le=10000, description="Number of patients to generate")
    encounters_per_patient_min: int = Field(default=1, ge=0, description="Min encounters per patient")
    encounters_per_patient_max: int = Field(default=5, ge=1, description="Max encounters per patient")
    denial_rate: float = Field(default=0.15, ge=0, le=1, description="Claim denial rate (0-1)")
    seed: int | None = Field(default=None, description="Random seed for reproducibility")


class IngestionResponse(BaseModel):
    """Response from ingestion operations."""
    status: str
    tenant_id: str
    counts: dict[str, int]
    message: str | None = None


class IngestionStatsResponse(BaseModel):
    """Response with ingestion statistics."""
    tenant_id: str
    entity_counts: dict[str, int]


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/fhir", response_model=IngestionResponse)
async def ingest_fhir_bundle(
    request: FHIRIngestionRequest,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Ingest a FHIR R4 Bundle into the knowledge graph.
    
    The bundle will be parsed and all resources will be written to the graph
    with appropriate relationships.
    
    **Supported FHIR Resources:**
    - Patient
    - Practitioner
    - Organization
    - Encounter
    - Condition (Diagnosis)
    - Procedure
    - Observation
    - MedicationRequest
    - Claim
    """
    try:
        service = IngestionService(
            tenant_id=tenant.tenant_id,
            source_system=request.source_system,
        )
        
        result = await service.ingest_fhir_bundle(request.bundle)
        
        return IngestionResponse(
            status=result["status"],
            tenant_id=result["tenant_id"],
            counts=result["counts"],
            message="FHIR bundle ingested successfully",
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest FHIR bundle: {str(e)}",
        )


@router.post("/fhir/file", response_model=IngestionResponse)
async def ingest_fhir_file(
    file: UploadFile = File(..., description="FHIR Bundle JSON file"),
    source_system: str = "fhir",
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Ingest a FHIR R4 Bundle from an uploaded JSON file.
    """
    import json
    
    if not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a JSON file",
        )
    
    try:
        content = await file.read()
        bundle = json.loads(content)
        
        service = IngestionService(
            tenant_id=tenant.tenant_id,
            source_system=source_system,
        )
        
        result = await service.ingest_fhir_bundle(bundle)
        
        return IngestionResponse(
            status=result["status"],
            tenant_id=result["tenant_id"],
            counts=result["counts"],
            message=f"FHIR bundle from '{file.filename}' ingested successfully",
        )
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in uploaded file",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest FHIR file: {str(e)}",
        )


@router.post("/synthetic", response_model=IngestionResponse)
async def generate_synthetic_data(
    request: SyntheticDataRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    _: User = Depends(require_roles("admin", "analyst")),
):
    """
    Generate and ingest synthetic healthcare data.
    
    Creates realistic synthetic patients, encounters, diagnoses, procedures,
    claims, and denials. Useful for demos and testing.
    
    **Requires:** admin or analyst role
    """
    try:
        service = IngestionService(
            tenant_id=tenant.tenant_id,
        )
        
        result = await service.ingest_synthetic_data(
            num_patients=request.num_patients,
            encounters_per_patient=(
                request.encounters_per_patient_min,
                request.encounters_per_patient_max,
            ),
            denial_rate=request.denial_rate,
            seed=request.seed,
        )
        
        return IngestionResponse(
            status=result["status"],
            tenant_id=result["tenant_id"],
            counts=result["counts"],
            message=f"Generated {request.num_patients} synthetic patients with {result['counts'].get('denials', 0)} denials",
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate synthetic data: {str(e)}",
        )


@router.get("/stats", response_model=IngestionStatsResponse)
async def get_ingestion_stats(
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Get statistics about ingested data for the current tenant.
    
    Returns counts of each entity type in the knowledge graph.
    """
    try:
        service = IngestionService(tenant_id=tenant.tenant_id)
        result = await service.get_ingestion_stats()
        
        return IngestionStatsResponse(
            tenant_id=result["tenant_id"],
            entity_counts=result["entity_counts"],
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ingestion stats: {str(e)}",
        )
