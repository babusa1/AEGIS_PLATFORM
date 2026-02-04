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


class X12IngestionRequest(BaseModel):
    """Request to ingest X12 EDI data."""
    content: str = Field(..., description="X12 EDI content (837, 835, 270/271, 276/277, 278)")
    transaction_type: str = Field(default="auto", description="Transaction type (837P, 837I, 835, 270, 271, 276, 277, 278, or auto)")
    source_system: str = Field(default="x12", description="Source system identifier")


class X12IngestionResponse(BaseModel):
    """Response from X12 ingestion."""
    status: str
    tenant_id: str
    transaction_type: str
    counts: dict[str, int]
    message: str | None = None


class HL7v2IngestionRequest(BaseModel):
    """Request to ingest HL7v2 message."""
    content: str = Field(..., description="HL7v2 message content")
    message_type: str = Field(default="auto", description="Message type (ADT, ORM, ORU, SIU, MDM, or auto)")
    source_system: str = Field(default="hl7v2", description="Source system identifier")


class StreamingStatusResponse(BaseModel):
    """Response with streaming service status."""
    running: bool
    consumers_active: int
    messages_processed: int
    messages_failed: int
    messages_dlq: int
    topics: list[str]


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


# =============================================================================
# X12 EDI Ingestion Endpoints
# =============================================================================

@router.post("/x12", response_model=X12IngestionResponse)
async def ingest_x12(
    request: X12IngestionRequest,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Ingest X12 EDI transaction data.
    
    **Supported Transaction Types:**
    - 837P: Professional Claims
    - 837I: Institutional Claims
    - 835: Payment/Remittance Advice
    - 270/271: Eligibility Inquiry/Response
    - 276/277: Claim Status Inquiry/Response
    - 278: Prior Authorization
    
    The transaction will be parsed and converted to FHIR resources
    which are then stored in the knowledge graph.
    """
    try:
        # Auto-detect transaction type if needed
        transaction_type = request.transaction_type
        if transaction_type == "auto":
            transaction_type = _detect_x12_transaction_type(request.content)
        
        service = IngestionService(
            tenant_id=tenant.tenant_id,
            source_system=request.source_system,
        )
        
        # Parse and ingest X12
        result = await service.ingest_x12(
            content=request.content,
            transaction_type=transaction_type,
        )
        
        return X12IngestionResponse(
            status=result.get("status", "success"),
            tenant_id=tenant.tenant_id,
            transaction_type=transaction_type,
            counts=result.get("counts", {}),
            message=f"X12 {transaction_type} transaction ingested successfully",
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest X12: {str(e)}",
        )


@router.post("/x12/file", response_model=X12IngestionResponse)
async def ingest_x12_file(
    file: UploadFile = File(..., description="X12 EDI file"),
    transaction_type: str = "auto",
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Ingest X12 EDI from an uploaded file.
    """
    try:
        content = (await file.read()).decode("utf-8")
        
        if transaction_type == "auto":
            transaction_type = _detect_x12_transaction_type(content)
        
        service = IngestionService(
            tenant_id=tenant.tenant_id,
            source_system="x12-file",
        )
        
        result = await service.ingest_x12(
            content=content,
            transaction_type=transaction_type,
        )
        
        return X12IngestionResponse(
            status=result.get("status", "success"),
            tenant_id=tenant.tenant_id,
            transaction_type=transaction_type,
            counts=result.get("counts", {}),
            message=f"X12 file '{file.filename}' ingested successfully",
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest X12 file: {str(e)}",
        )


# =============================================================================
# HL7v2 Ingestion Endpoints
# =============================================================================

@router.post("/hl7v2", response_model=IngestionResponse)
async def ingest_hl7v2(
    request: HL7v2IngestionRequest,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Ingest HL7v2 message.
    
    **Supported Message Types:**
    - ADT: Admission/Discharge/Transfer
    - ORM: Order messages
    - ORU: Observation results
    - SIU: Scheduling
    - MDM: Medical document management
    
    The message will be parsed and converted to FHIR resources.
    """
    try:
        service = IngestionService(
            tenant_id=tenant.tenant_id,
            source_system=request.source_system,
        )
        
        result = await service.ingest_hl7v2(
            content=request.content,
            message_type=request.message_type,
        )
        
        return IngestionResponse(
            status=result.get("status", "success"),
            tenant_id=tenant.tenant_id,
            counts=result.get("counts", {}),
            message=f"HL7v2 message ingested successfully",
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest HL7v2: {str(e)}",
        )


# =============================================================================
# Streaming Ingestion Endpoints
# =============================================================================

@router.get("/streaming/status", response_model=StreamingStatusResponse)
async def get_streaming_status():
    """
    Get status of the streaming ingestion service.
    """
    try:
        from aegis.ingestion.streaming import get_streaming_service
        
        service = await get_streaming_service()
        metrics = service.get_metrics()
        
        return StreamingStatusResponse(**metrics)
        
    except Exception as e:
        return StreamingStatusResponse(
            running=False,
            consumers_active=0,
            messages_processed=0,
            messages_failed=0,
            messages_dlq=0,
            topics=[],
        )


@router.post("/streaming/start")
async def start_streaming_ingestion(
    topics: list[str] | None = None,
    _: User = Depends(require_roles("admin")),
):
    """
    Start the streaming ingestion service.
    
    **Requires:** admin role
    """
    try:
        from aegis.ingestion.streaming import start_streaming_ingestion
        
        service = await start_streaming_ingestion(topics=topics)
        
        return {
            "status": "started",
            "topics": topics or ["all default topics"],
            "message": "Streaming ingestion started",
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start streaming: {str(e)}",
        )


@router.post("/streaming/stop")
async def stop_streaming_ingestion(
    _: User = Depends(require_roles("admin")),
):
    """
    Stop the streaming ingestion service.
    
    **Requires:** admin role
    """
    try:
        from aegis.ingestion.streaming import stop_streaming_ingestion
        
        await stop_streaming_ingestion()
        
        return {
            "status": "stopped",
            "message": "Streaming ingestion stopped",
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop streaming: {str(e)}",
        )


# =============================================================================
# Helper Functions
# =============================================================================

def _detect_x12_transaction_type(content: str) -> str:
    """Detect X12 transaction type from content."""
    # Look for GS segment which contains transaction set identifier
    lines = content.replace("~", "\n").split("\n")
    
    for line in lines:
        if line.startswith("GS"):
            segments = line.split("*")
            if len(segments) >= 2:
                func_id = segments[1]
                type_map = {
                    "HC": "837P",  # Healthcare Claim Professional
                    "HI": "837I",  # Healthcare Claim Institutional
                    "HP": "835",   # Payment/Remittance
                    "HB": "271",   # Eligibility Response
                    "HS": "270",   # Eligibility Inquiry
                    "HN": "277",   # Claim Status Response
                    "HR": "276",   # Claim Status Inquiry
                    "HJ": "278",   # Prior Authorization
                }
                return type_map.get(func_id, "unknown")
    
    # Fallback: look for ST segment
    for line in lines:
        if line.startswith("ST"):
            segments = line.split("*")
            if len(segments) >= 2:
                return segments[1]
    
    return "unknown"
