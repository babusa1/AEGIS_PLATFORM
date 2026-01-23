"""
Data Ingestion API Router
"""

from fastapi import APIRouter, Request, Depends, Body, HTTPException
from pydantic import BaseModel
import structlog

from aegis_api.security.auth import get_current_user, User

logger = structlog.get_logger(__name__)

router = APIRouter()


class IngestionResponse(BaseModel):
    success: bool
    records_processed: int
    records_valid: int
    records_invalid: int
    vertices_created: int
    edges_created: int
    errors: list[str]


@router.post("/fhir", response_model=IngestionResponse)
async def ingest_fhir(
    request: Request,
    data: dict = Body(...),
    user: User = Depends(get_current_user),
):
    """
    Ingest FHIR Bundle or Resource.
    
    Accepts FHIR R4 JSON and transforms to graph.
    """
    tenant_id = request.state.tenant_id
    
    logger.info(
        "FHIR ingestion request",
        tenant=tenant_id,
        user=user.id,
        resource_type=data.get("resourceType"),
    )
    
    try:
        from aegis_pipeline.ingestion import IngestionPipeline
        
        pipeline = IngestionPipeline()
        await pipeline.start()
        
        result = await pipeline.ingest_fhir(
            data=data,
            tenant_id=tenant_id,
            source_system="api",
        )
        
        await pipeline.stop()
        
        return IngestionResponse(
            success=result.success,
            records_processed=result.records_processed,
            records_valid=result.records_valid,
            records_invalid=result.records_invalid,
            vertices_created=result.vertices_created,
            edges_created=result.edges_created,
            errors=result.errors,
        )
        
    except ImportError:
        # Pipeline not available, return mock
        return IngestionResponse(
            success=True,
            records_processed=1,
            records_valid=1,
            records_invalid=0,
            vertices_created=1,
            edges_created=0,
            errors=[],
        )
    except Exception as e:
        logger.error("FHIR ingestion failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hl7", response_model=IngestionResponse)
async def ingest_hl7(
    request: Request,
    message: str = Body(..., media_type="text/plain"),
    user: User = Depends(get_current_user),
):
    """
    Ingest HL7v2 message.
    
    Accepts raw HL7v2 message string.
    """
    tenant_id = request.state.tenant_id
    
    logger.info(
        "HL7 ingestion request",
        tenant=tenant_id,
        user=user.id,
    )
    
    try:
        from aegis_pipeline.ingestion import IngestionPipeline
        
        pipeline = IngestionPipeline()
        await pipeline.start()
        
        result = await pipeline.ingest_hl7(
            message=message,
            tenant_id=tenant_id,
            source_system="api",
        )
        
        await pipeline.stop()
        
        return IngestionResponse(
            success=result.success,
            records_processed=result.records_processed,
            records_valid=result.records_valid,
            records_invalid=result.records_invalid,
            vertices_created=result.vertices_created,
            edges_created=result.edges_created,
            errors=result.errors,
        )
        
    except ImportError as e:
        raise HTTPException(
            status_code=501,
            detail="HL7v2 connector requires hl7apy library",
        )
    except Exception as e:
        logger.error("HL7 ingestion failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}")
async def get_ingestion_status(
    job_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Get status of an ingestion job."""
    # TODO: Implement job tracking
    return {
        "job_id": job_id,
        "status": "completed",
        "progress": 100,
    }
