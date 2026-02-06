"""
Oncolife Bridge App API Endpoints

REST API for symptom checker and integration with OncolifeAgent.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import structlog

from aegis.api.auth import get_current_user
from aegis.agents.oncolife import OncolifeAgent
from aegis.agents.data_tools import DataMoatTools
from .symptom_checker import SymptomCheckerService

logger = structlog.get_logger(__name__)

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
    Start a new symptom checker session.
    
    Returns the initial disclaimer and emergency check screen.
    """
    try:
        service = SymptomCheckerService(patient_id=request.patient_id)
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
    Process a user response in the symptom checker conversation.
    
    Returns the next question, summary, or triage recommendation.
    """
    try:
        service = SymptomCheckerService()
        response = service.process_user_response(
            user_response=request.user_response,
            session_state=request.session_state
        )
        
        # If session is complete, integrate with OncolifeAgent for recommendations
        if response.get("is_complete"):
            triage_level = service.get_triage_level()
            summary = service.get_summary()
            
            # Get patient_id from session state if available
            patient_id = None
            if request.session_state:
                patient_id = request.session_state.get("patient_id")
            
            if patient_id and triage_level != "none":
                # Integrate with OncolifeAgent for care recommendations
                try:
                    data_moat_tools = DataMoatTools(tenant_id=current_user.get("tenant_id", "default"))
                    agent = OncolifeAgent(
                        tenant_id=current_user.get("tenant_id", "default"),
                        data_moat_tools=data_moat_tools
                    )
                    
                    # Get agent recommendations based on symptoms
                    recommendations = await agent.analyze_patient_oncology_status(patient_id)
                    response["agent_recommendations"] = recommendations
                except Exception as e:
                    logger.warning("Failed to get agent recommendations", error=str(e))
        
        return SymptomSessionResponse(
            message=response.get("message", ""),
            message_type=response.get("message_type", "text"),
            options=response.get("options", []),
            triage_level=response.get("triage_level") or service.get_triage_level(),
            session_state=service.get_session_state(),
            patient_id=request.session_state.get("patient_id") if request.session_state else None
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
        from routers.chat.symptom_checker.symptom_engine import SymptomCheckerEngine
        symptoms = SymptomCheckerEngine.get_available_symptoms()
        return symptoms
    except ImportError:
        return {
            "emergency": [],
            "groups": {},
            "message": "Symptom checker engine not available. Ensure Oncolife repo is integrated."
        }
