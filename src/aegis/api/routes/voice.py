"""
Voice API Routes

REST API endpoints for voice-based patient interactions.
Handles inbound/outbound calls, IVR menus, and voice workflows.
"""

from typing import Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Header
from fastapi.responses import Response
from pydantic import BaseModel, Field
import structlog

from aegis.api.auth import TenantContext, get_tenant_context, get_current_user, User

logger = structlog.get_logger(__name__)
from aegis.voice.gateway import VoiceGateway, CallState, CallDirection
from aegis.voice.agent import VoiceAgent
from aegis.voice.workflows import (
    VoiceWorkflows,
    AppointmentBookingRequest,
    FollowUpCallRequest,
    InsuranceCheckRequest,
)

router = APIRouter(prefix="/voice", tags=["Voice"])


# =============================================================================
# Request/Response Models
# =============================================================================

class OutboundCallRequest(BaseModel):
    """Request to initiate outbound call."""
    to_number: str
    from_number: Optional[str] = None
    patient_id: Optional[str] = None
    workflow_id: Optional[str] = None
    message_template: Optional[str] = None


class CallResponse(BaseModel):
    """Response for call operations."""
    call_id: str
    call_sid: str
    status: str
    direction: str
    message: Optional[str] = None


class IVRMenuResponse(BaseModel):
    """Response for IVR menu generation."""
    twiml: Optional[str] = None
    message: str


# =============================================================================
# Helper Functions
# =============================================================================

def get_voice_gateway(request: Request) -> VoiceGateway:
    """Get VoiceGateway instance from app state or create new one."""
    if hasattr(request.app.state, "voice_gateway") and request.app.state.voice_gateway:
        return request.app.state.voice_gateway
    
    # Get config from settings
    from aegis.config import get_settings
    settings = get_settings()
    
    config = {
        "account_sid": getattr(settings, "twilio_account_sid", None),
        "auth_token": getattr(settings, "twilio_auth_token", None),
        "from_number": getattr(settings, "twilio_from_number", None),
        "webhook_url": getattr(settings, "voice_webhook_url", None),
    }
    
    gateway = VoiceGateway(provider="twilio", config=config)
    
    # Cache in app state
    if not hasattr(request.app.state, "voice_gateway"):
        request.app.state.voice_gateway = gateway
    
    return gateway


def get_voice_agent(request: Request, tenant_id: str) -> VoiceAgent:
    """Get VoiceAgent instance."""
    gateway = get_voice_gateway(request)
    
    if not hasattr(request.app.state, "voice_agents"):
        request.app.state.voice_agents = {}
    
    agent_key = f"{tenant_id}"
    if agent_key not in request.app.state.voice_agents:
        agent = VoiceAgent(
            tenant_id=tenant_id,
            voice_gateway=gateway,
        )
        request.app.state.voice_agents[agent_key] = agent
    
    return request.app.state.voice_agents[agent_key]


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/calls/outbound", response_model=CallResponse)
async def initiate_outbound_call(
    request: OutboundCallRequest,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
):
    """
    Initiate an outbound call to a patient.
    
    Used for:
    - Appointment reminders
    - Follow-up calls
    - Medication adherence checks
    - Post-procedure check-ins
    """
    try:
        gateway = get_voice_gateway(req)
        
        call_state = await gateway.initiate_outbound_call(
            to_number=request.to_number,
            from_number=request.from_number or gateway.config.get("from_number"),
            patient_id=request.patient_id,
            workflow_id=request.workflow_id,
        )
        
        return CallResponse(
            call_id=call_state.call_id,
            call_sid=call_state.call_sid,
            status=call_state.status.value,
            direction=call_state.direction.value,
            message="Outbound call initiated",
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate call: {str(e)}",
        )


@router.post("/calls/inbound/webhook")
async def handle_inbound_call_webhook(
    req: Request,
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    CallStatus: Optional[str] = Form(None),
):
    """
    Webhook endpoint for inbound calls (Twilio).
    
    This endpoint is called by Twilio when a call comes in.
    Returns TwiML for IVR menu or direct routing to voice agent.
    """
    try:
        gateway = get_voice_gateway(req)
        
        # Handle inbound call
        call_state = await gateway.handle_inbound_call(
            call_sid=CallSid,
            from_number=From,
            to_number=To,
            call_data={"status": CallStatus},
        )
        
        # Create IVR menu
        menu = gateway.create_ivr_menu(
            menu_id="main_menu",
            greeting="Welcome to AEGIS Healthcare. Press 1 for appointments, press 2 for questions, press 3 for insurance.",
            options=[
                {"digit": "1", "label": "appointments", "action": "appointment"},
                {"digit": "2", "label": "questions", "action": "query"},
                {"digit": "3", "label": "insurance", "action": "insurance"},
            ],
        )
        
        # Generate TwiML
        action_url = f"{req.base_url}v1/voice/calls/{call_state.call_id}/menu-action"
        twiml = gateway.generate_ivr_twiml(menu, action_url)
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error("Failed to handle inbound call webhook", error=str(e))
        # Return error TwiML (simplified - would use Twilio SDK in production)
        error_twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Say voice="alice">I am sorry, we are experiencing technical difficulties. Please try again later.</Say></Response>'
        return Response(content=error_twiml, media_type="application/xml")


@router.post("/calls/{call_id}/menu-action")
async def handle_menu_action(
    call_id: str,
    req: Request,
    Digits: str = Form(...),
):
    """
    Handle IVR menu selection.
    
    Routes to appropriate workflow based on menu selection.
    """
    try:
        gateway = get_voice_gateway(req)
        call_state = gateway.get_call_state(call_id)
        
        if not call_state:
            raise HTTPException(status_code=404, detail="Call not found")
        
        # Route based on menu selection
        if Digits == "1":
            # Appointment workflow
            action = "appointment"
        elif Digits == "2":
            # Query workflow
            action = "query"
        elif Digits == "3":
            # Insurance workflow
            action = "insurance"
        else:
            action = "query"  # Default
        
        # Update call state
        gateway.update_call_state(call_id, {"current_menu": action})
        
        # Get voice agent
        tenant_id = "default"  # Would come from call context
        agent = get_voice_agent(req, tenant_id)
        
        # Start conversation
        conversation = await agent.start_conversation(call_state)
        
        # Generate TwiML response (simplified - would use Twilio SDK in production)
        action_url = f"{req.base_url}v1/voice/calls/{call_id}/message"
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">{conversation["greeting"]}</Say>
    <Gather input="speech" action="{action_url}" method="POST" />
</Response>'''
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle menu action: {str(e)}",
        )


@router.post("/calls/{call_id}/message")
async def handle_voice_message(
    call_id: str,
    req: Request,
    SpeechResult: Optional[str] = Form(None),
    Digits: Optional[str] = Form(None),
):
    """
    Handle voice message from user (speech or DTMF).
    
    Processes transcribed speech and returns voice response.
    """
    try:
        gateway = get_voice_gateway(req)
        call_state = gateway.get_call_state(call_id)
        
        if not call_state:
            raise HTTPException(status_code=404, detail="Call not found")
        
        # Get transcribed text
        user_message = SpeechResult or (f"Pressed {Digits}" if Digits else "Hello")
        
        # Get voice agent
        tenant_id = "default"
        agent = get_voice_agent(req, tenant_id)
        
        # Process message
        session_id = call_state.session_id or f"session-{call_id}"
        response = await agent.process_message(
            session_id=session_id,
            user_message=user_message,
            call_state=call_state,
        )
        
        # Generate TwiML response (simplified - would use Twilio SDK in production)
        action_url = f"{req.base_url}v1/voice/calls/{call_id}/message"
        response_text = response["response_text"].replace('"', '&quot;')
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">{response_text}</Say>
    <Gather input="speech" action="{action_url}" method="POST" />
    <Say voice="alice">Press 9 to end the call.</Say>
</Response>'''
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process voice message: {str(e)}",
        )


@router.get("/calls/{call_id}", response_model=CallResponse)
async def get_call_status(
    call_id: str,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """Get status of a call."""
    try:
        gateway = get_voice_gateway(req)
        call_state = gateway.get_call_state(call_id)
        
        if not call_state:
            raise HTTPException(status_code=404, detail="Call not found")
        
        return CallResponse(
            call_id=call_state.call_id,
            call_sid=call_state.call_sid,
            status=call_state.status.value,
            direction=call_state.direction.value,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get call status: {str(e)}",
        )


@router.post("/workflows/appointment-booking")
async def execute_appointment_booking(
    request: AppointmentBookingRequest,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
):
    """
    Execute appointment booking workflow via voice.
    
    This can be triggered by:
    - Inbound call (user requests appointment)
    - Outbound call (agent-initiated booking)
    """
    try:
        gateway = get_voice_gateway(req)
        agent = get_voice_agent(req, tenant.tenant_id)
        workflows = VoiceWorkflows(gateway, agent, tenant.tenant_id)
        
        # Get or create call state
        call_state = gateway.get_call_state(request.patient_id) or CallState(
            call_id=f"appt-{request.patient_id}",
            call_sid=f"appt-{request.patient_id}",
            direction=CallDirection.INBOUND,
            status="in_progress",
            from_number="+1234567890",
            to_number="+1234567890",
            patient_id=request.patient_id,
        )
        
        result = await workflows.execute_appointment_booking(request, call_state)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute appointment booking: {str(e)}",
        )


@router.post("/workflows/followup-call")
async def schedule_followup_call(
    request: FollowUpCallRequest,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
):
    """
    Schedule a follow-up call workflow.
    
    Creates a scheduled workflow that will:
    1. Wait until scheduled time
    2. Initiate outbound call
    3. Deliver message
    4. Collect response
    """
    try:
        gateway = get_voice_gateway(req)
        agent = get_voice_agent(req, tenant.tenant_id)
        workflows = VoiceWorkflows(gateway, agent, tenant.tenant_id)
        
        # In production, would schedule workflow execution
        # For now, execute immediately if time has passed
        if request.scheduled_time <= datetime.utcnow():
            result = await workflows.execute_followup_call(request)
        else:
            # Schedule for later (would use workflow scheduler)
            result = {
                "success": True,
                "scheduled": True,
                "scheduled_time": request.scheduled_time.isoformat(),
                "message": "Follow-up call scheduled",
            }
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule follow-up call: {str(e)}",
        )


@router.post("/workflows/insurance-check")
async def execute_insurance_check(
    request: InsuranceCheckRequest,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
):
    """
    Execute insurance eligibility check workflow via voice.
    """
    try:
        gateway = get_voice_gateway(req)
        agent = get_voice_agent(req, tenant.tenant_id)
        workflows = VoiceWorkflows(gateway, agent, tenant.tenant_id)
        
        # Get or create call state
        call_state = gateway.get_call_state(request.patient_id) or CallState(
            call_id=f"ins-{request.patient_id}",
            call_sid=f"ins-{request.patient_id}",
            direction=CallDirection.INBOUND,
            status="in_progress",
            from_number="+1234567890",
            to_number="+1234567890",
            patient_id=request.patient_id,
        )
        
        result = await workflows.execute_insurance_check(request, call_state)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute insurance check: {str(e)}",
        )


@router.get("/calls")
async def list_active_calls(
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """List all active calls."""
    try:
        gateway = get_voice_gateway(req)
        active_calls = gateway.get_active_calls()
        
        return {
            "calls": [
                {
                    "call_id": call.call_id,
                    "call_sid": call.call_sid,
                    "direction": call.direction.value,
                    "status": call.status.value,
                    "from_number": call.from_number,
                    "to_number": call.to_number,
                    "patient_id": call.patient_id,
                    "started_at": call.started_at.isoformat(),
                }
                for call in active_calls
            ],
            "total": len(active_calls),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list calls: {str(e)}",
        )
