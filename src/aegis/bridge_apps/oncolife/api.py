"""
Oncolife Bridge App API Endpoints

REST API for symptom checker and integration with OncolifeAgent.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import structlog

logger = structlog.get_logger(__name__)

# Graceful imports with fallbacks
try:
    from aegis.api.auth import get_current_user
except ImportError:
    logger.warning("aegis.api.auth not available, using mock get_current_user")
    async def get_current_user():
        return {"id": "demo", "tenant_id": "default", "roles": ["user"]}

try:
    from aegis.agents.oncolife import OncolifeAgent
except ImportError:
    logger.warning("OncolifeAgent not available")
    OncolifeAgent = None

try:
    from aegis.agents.data_tools import DataMoatTools
except ImportError:
    logger.warning("DataMoatTools not available")
    DataMoatTools = None

try:
    from .symptom_checker import SymptomCheckerService
except ImportError:
    logger.warning("SymptomCheckerService not available")
    SymptomCheckerService = None

router = APIRouter(prefix="/bridge/oncolife", tags=["oncolife"])


class SymptomSessionRequest(BaseModel):
    """Request to start a symptom checker session."""
    patient_id: str


class SymptomResponseRequest(BaseModel):
    """Request to process a user response."""
    user_response: Any
    session_state: Optional[Dict[str, Any]] = None


class SymptomSessionResponse(BaseModel):
    """Response from symptom checker."""
    message: str
    message_type: str
    options: Optional[list] = None
    triage_level: Optional[str] = None
    session_state: Optional[Dict[str, Any]] = None
    patient_id: Optional[str] = None


@router.post("/symptom-checker/start", response_model=SymptomSessionResponse)
async def start_symptom_session(
    request: SymptomSessionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Start a new symptom checker session with patient context loading.
    
    Returns the initial disclaimer and emergency check screen.
    """
    try:
        # Initialize service with Data Moat and agent if available
        data_moat_tools = None
        oncolife_agent = None
        
        if DataMoatTools:
            try:
                data_moat_tools = DataMoatTools(tenant_id=current_user.get("tenant_id", "default"))
            except Exception as e:
                logger.warning(f"DataMoatTools not available: {e}")
        
        if OncolifeAgent and data_moat_tools:
            try:
                oncolife_agent = OncolifeAgent(
                    tenant_id=current_user.get("tenant_id", "default"),
                    data_moat_tools=data_moat_tools
                )
            except Exception as e:
                logger.warning(f"OncolifeAgent not available: {e}")
        
        service = SymptomCheckerService(
            patient_id=request.patient_id,
            data_moat_tools=data_moat_tools,
            oncolife_agent=oncolife_agent,
        )
        
        response = service.start_session()
        
        return SymptomSessionResponse(
            message=response.get("message", ""),
            message_type=response.get("message_type", "text"),
            options=response.get("options", []),
            session_state=service.get_session_state(),
            patient_id=request.patient_id
        )
    except Exception as e:
        logger.error("Failed to start symptom session", error=str(e), patient_id=request.patient_id)
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@router.post("/symptom-checker/respond", response_model=SymptomSessionResponse)
async def process_symptom_response(
    request: SymptomResponseRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Process a user response in the symptom checker conversation with real-time agent integration.
    
    Returns the next question, summary, or triage recommendation, enriched with agent insights.
    """
    try:
        # Initialize service with Data Moat and agent if available
        data_moat_tools = None
        oncolife_agent = None
        
        if DataMoatTools:
            try:
                data_moat_tools = DataMoatTools(tenant_id=current_user.get("tenant_id", "default"))
            except Exception as e:
                logger.warning(f"DataMoatTools not available: {e}")
        
        if OncolifeAgent and data_moat_tools:
            try:
                oncolife_agent = OncolifeAgent(
                    tenant_id=current_user.get("tenant_id", "default"),
                    data_moat_tools=data_moat_tools
                )
            except Exception as e:
                logger.warning(f"OncolifeAgent not available: {e}")
        
        # Get patient_id from session state if available
        patient_id = None
        if request.session_state:
            patient_id = request.session_state.get("patient_id")
        
        service = SymptomCheckerService(
            patient_id=patient_id,
            data_moat_tools=data_moat_tools,
            oncolife_agent=oncolife_agent,
        )
        
        # Process response (now async with agent consultation)
        response = await service.process_user_response(
            user_response=request.user_response,
            session_state=request.session_state
        )
        
        # If session is complete, get comprehensive agent recommendations
        if response.get("is_complete"):
            triage_level = service.get_triage_level()
            summary = service.get_summary()
            
            if patient_id and triage_level != "none" and oncolife_agent:
                try:
                    # Get comprehensive oncology status
                    recommendations = await oncolife_agent.analyze_patient_oncology_status(patient_id)
                    response["agent_recommendations"] = recommendations
                except Exception as e:
                    logger.warning("Failed to get agent recommendations", error=str(e))
        
        return SymptomSessionResponse(
            message=response.get("message", ""),
            message_type=response.get("message_type", "text"),
            options=response.get("options", []),
            triage_level=response.get("triage_level") or service.get_triage_level(),
            session_state=service.get_session_state(),
            patient_id=patient_id or response.get("patient_id")
        )
    except Exception as e:
        logger.error("Failed to process symptom response", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process response: {str(e)}")


@router.get("/symptom-checker/summary/{session_id}")
async def get_session_summary(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get summary of a completed symptom checker session.
    """
    # In production, retrieve session from storage
    # For now, return placeholder
    return {
        "session_id": session_id,
        "message": "Session summary retrieval not yet implemented. Use session_state from responses."
    }


@router.get("/symptom-checker/symptoms")
async def get_available_symptoms(current_user: dict = Depends(get_current_user)):
    """
    Get list of available symptoms for selection.
    """
    try:
        from .symptom_engine import SymptomCheckerEngine
        symptoms = SymptomCheckerEngine.get_available_symptoms()
        return symptoms
    except ImportError as e:
        logger.warning(f"Failed to import symptom engine: {e}")
        return {
            "emergency": [],
            "groups": {},
            "message": "Symptom checker engine not available."
        }
