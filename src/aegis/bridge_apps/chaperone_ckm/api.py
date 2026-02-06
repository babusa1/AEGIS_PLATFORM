"""
Chaperone CKM Bridge App API Endpoints

REST API for CKD patient dashboard, vital logging, and care gap tracking.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)

# Graceful imports
try:
    from aegis.api.auth import get_current_user
except (ImportError, AttributeError, TypeError):
    logger.warning("aegis.api.auth not available, using mock get_current_user")
    async def get_current_user():
        return {"id": "demo", "tenant_id": "default", "roles": ["user"]}

try:
    from aegis.agents.chaperone_ckm import ChaperoneCKMAgent
except ImportError:
    logger.warning("ChaperoneCKMAgent not available")
    ChaperoneCKMAgent = None

try:
    from aegis.agents.data_tools import DataMoatTools
except ImportError:
    logger.warning("DataMoatTools not available")
    DataMoatTools = None

try:
    from .service import ChaperoneCKMService
except ImportError:
    logger.warning("ChaperoneCKMService not available")
    ChaperoneCKMService = None

router = APIRouter(prefix="/bridge/chaperone-ckm", tags=["chaperone-ckm"])


# Request/Response Models
class VitalLogRequest(BaseModel):
    """Request to log a vital sign."""
    vital_type: str = Field(..., description="Type of vital: bp_systolic, bp_diastolic, weight, etc.")
    value: float = Field(..., description="Vital value")
    timestamp: Optional[datetime] = None
    additional_data: Optional[Dict[str, Any]] = None


class BloodPressureLogRequest(BaseModel):
    """Request to log blood pressure."""
    systolic: float = Field(..., description="Systolic BP")
    diastolic: float = Field(..., description="Diastolic BP")
    timestamp: Optional[datetime] = None


class DashboardResponse(BaseModel):
    """Response with patient dashboard data."""
    patient_id: str
    dashboard: Dict[str, Any]


class VitalLogResponse(BaseModel):
    """Response from vital logging."""
    logged: bool
    vital_type: str
    value: float
    timestamp: str
    alert: Optional[Dict[str, Any]] = None


# Helper function to get service
def get_ckm_service(
    patient_id: str,
    current_user: dict,
) -> ChaperoneCKMService:
    """Get ChaperoneCKMService instance."""
    if not ChaperoneCKMService:
        raise HTTPException(status_code=503, detail="ChaperoneCKMService not available")
    
    data_moat_tools = None
    ckm_agent = None
    
    if DataMoatTools:
        try:
            data_moat_tools = DataMoatTools(tenant_id=current_user.get("tenant_id", "default"))
        except Exception as e:
            logger.warning(f"DataMoatTools not available: {e}")
    
    if ChaperoneCKMAgent and data_moat_tools:
        try:
            ckm_agent = ChaperoneCKMAgent(
                tenant_id=current_user.get("tenant_id", "default"),
                data_moat_tools=data_moat_tools
            )
        except Exception as e:
            logger.warning(f"ChaperoneCKMAgent not available: {e}")
    
    return ChaperoneCKMService(
        patient_id=patient_id,
        data_moat_tools=data_moat_tools,
        ckm_agent=ckm_agent,
    )


# API Endpoints
@router.get("/dashboard/{patient_id}", response_model=DashboardResponse)
async def get_patient_dashboard(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get personalized CKD patient dashboard.
    
    Returns:
        Dashboard with eGFR trends, KFRE, care gaps, medications, vitals
    """
    try:
        service = get_ckm_service(patient_id, current_user)
        result = await service.get_patient_dashboard()
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return DashboardResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get dashboard", error=str(e), patient_id=patient_id)
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")


@router.post("/vitals/log/{patient_id}", response_model=VitalLogResponse)
async def log_vital(
    patient_id: str,
    request: VitalLogRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Log a vital sign (BP, weight, etc.).
    
    Returns:
        Logging result with real-time agent analysis
    """
    try:
        service = get_ckm_service(patient_id, current_user)
        result = await service.log_vital(
            vital_type=request.vital_type,
            value=request.value,
            timestamp=request.timestamp,
            additional_data=request.additional_data,
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return VitalLogResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to log vital", error=str(e), patient_id=patient_id)
        raise HTTPException(status_code=500, detail=f"Failed to log vital: {str(e)}")


@router.post("/vitals/bp/{patient_id}", response_model=VitalLogResponse)
async def log_blood_pressure(
    patient_id: str,
    request: BloodPressureLogRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Log blood pressure (convenience endpoint).
    
    Returns:
        Logging result with agent analysis
    """
    try:
        service = get_ckm_service(patient_id, current_user)
        result = await service.log_blood_pressure(
            systolic=request.systolic,
            diastolic=request.diastolic,
            timestamp=request.timestamp,
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return VitalLogResponse(
            logged=result["logged"],
            vital_type="blood_pressure",
            value=result["systolic"],  # Use systolic as primary value
            timestamp=result["timestamp"],
            alert=result.get("alert"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to log BP", error=str(e), patient_id=patient_id)
        raise HTTPException(status_code=500, detail=f"Failed to log BP: {str(e)}")


@router.get("/care-gaps/{patient_id}")
async def get_care_gaps(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get current care gaps for the patient.
    
    Returns:
        List of care gaps with priorities and recommendations
    """
    try:
        service = get_ckm_service(patient_id, current_user)
        care_gaps = await service.get_care_gaps()
        return {"patient_id": patient_id, "care_gaps": care_gaps}
    except Exception as e:
        logger.error("Failed to get care gaps", error=str(e), patient_id=patient_id)
        raise HTTPException(status_code=500, detail=f"Failed to get care gaps: {str(e)}")


@router.get("/medication-adherence/{patient_id}")
async def get_medication_adherence(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get medication adherence metrics.
    
    Returns:
        Adherence rate and medication details
    """
    try:
        service = get_ckm_service(patient_id, current_user)
        adherence = await service.get_medication_adherence()
        return {"patient_id": patient_id, **adherence}
    except Exception as e:
        logger.error("Failed to get medication adherence", error=str(e), patient_id=patient_id)
        raise HTTPException(status_code=500, detail=f"Failed to get medication adherence: {str(e)}")
