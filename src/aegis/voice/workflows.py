"""
Voice Workflows

Pre-built workflows for voice-based patient interactions:
- Appointment booking workflow
- Follow-up call workflow
- Insurance check workflow
"""

from typing import Any, Dict, Optional
from datetime import datetime, timedelta

import structlog
from pydantic import BaseModel

from aegis.orchestrator.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowEdge,
    NodeType,
    NodeConfig,
)
from aegis.voice.gateway import VoiceGateway, CallDirection
from aegis.voice.agent import VoiceAgent

logger = structlog.get_logger(__name__)


# =============================================================================
# Workflow Models
# =============================================================================

class AppointmentBookingRequest(BaseModel):
    """Request to book appointment via voice."""
    patient_id: str
    appointment_type: str
    preferred_date: Optional[str] = None
    preferred_time: Optional[str] = None
    reason: Optional[str] = None


class FollowUpCallRequest(BaseModel):
    """Request for follow-up call."""
    patient_id: str
    call_reason: str  # "appointment_reminder", "medication_adherence", "post_procedure"
    scheduled_time: datetime
    message_template: Optional[str] = None


class InsuranceCheckRequest(BaseModel):
    """Request for insurance eligibility check."""
    patient_id: str
    service_code: Optional[str] = None
    procedure_code: Optional[str] = None
    date_of_service: Optional[str] = None


# =============================================================================
# Voice Workflows
# =============================================================================

class VoiceWorkflows:
    """
    Pre-built workflows for voice interactions.
    
    These workflows integrate with:
    - VoiceGateway for call management
    - VoiceAgent for conversation handling
    - Scheduling Connector for appointments
    - X12 EDI for insurance checks
    - Data Moat for patient data
    """
    
    def __init__(
        self,
        voice_gateway: VoiceGateway,
        voice_agent: VoiceAgent,
        tenant_id: str = "default",
    ):
        self.voice_gateway = voice_gateway
        self.voice_agent = voice_agent
        self.tenant_id = tenant_id
    
    # =========================================================================
    # Appointment Booking Workflow
    # =========================================================================
    
    def create_appointment_booking_workflow(self) -> WorkflowDefinition:
        """
        Create workflow for voice-based appointment booking.
        
        Flow:
        1. Receive call → Identify patient
        2. Understand appointment request
        3. Check availability
        4. Confirm details
        5. Book appointment
        6. Send confirmation
        """
        nodes = [
            WorkflowNode(
                id="start",
                type=NodeType.START,
                name="Start",
                description="Voice call received",
            ),
            WorkflowNode(
                id="identify_patient",
                type=NodeType.AGENT,
                name="Identify Patient",
                description="Verify patient identity",
                config=NodeConfig(
                    agent_type="voice_agent",
                    prompt_template="Verify patient identity. Ask for name and date of birth.",
                ),
            ),
            WorkflowNode(
                id="understand_request",
                type=NodeType.AGENT,
                name="Understand Request",
                description="Extract appointment details",
                config=NodeConfig(
                    agent_type="voice_agent",
                    prompt_template="Extract: appointment type, preferred date/time, reason.",
                ),
            ),
            WorkflowNode(
                id="check_availability",
                type=NodeType.QUERY_DATA,
                name="Check Availability",
                description="Query available appointment slots",
                config=NodeConfig(
                    query_template="SELECT * FROM slots WHERE date = {preferred_date} AND status = 'free'",
                ),
            ),
            WorkflowNode(
                id="confirm_details",
                type=NodeType.AGENT,
                name="Confirm Details",
                description="Confirm appointment with patient",
                config=NodeConfig(
                    agent_type="voice_agent",
                    prompt_template="Confirm: date, time, type, location. Get patient confirmation.",
                ),
            ),
            WorkflowNode(
                id="book_appointment",
                type=NodeType.CALL_API,
                name="Book Appointment",
                description="Create appointment in system",
                config=NodeConfig(
                    url="/v1/scheduling/appointments",
                    method="POST",
                ),
            ),
            WorkflowNode(
                id="send_confirmation",
                type=NodeType.SEND_NOTIFICATION,
                name="Send Confirmation",
                description="Send SMS/Email confirmation",
                config=NodeConfig(
                    filters={"channel": "sms", "template": "appointment_confirmation"},
                ),
            ),
            WorkflowNode(
                id="end",
                type=NodeType.END,
                name="End",
                description="Workflow complete",
            ),
        ]
        
        edges = [
            WorkflowEdge(source="start", target="identify_patient"),
            WorkflowEdge(source="identify_patient", target="understand_request"),
            WorkflowEdge(source="understand_request", target="check_availability"),
            WorkflowEdge(source="check_availability", target="confirm_details"),
            WorkflowEdge(source="confirm_details", target="book_appointment"),
            WorkflowEdge(source="book_appointment", target="send_confirmation"),
            WorkflowEdge(source="send_confirmation", target="end"),
        ]
        
        return WorkflowDefinition(
            name="Voice Appointment Booking",
            description="Handle appointment booking via voice call",
            nodes=nodes,
            edges=edges,
            tenant_id=self.tenant_id,
            is_template=True,
            tags=["voice", "appointment", "scheduling"],
        )
    
    async def execute_appointment_booking(
        self,
        request: AppointmentBookingRequest,
        call_state: Any,
    ) -> Dict[str, Any]:
        """
        Execute appointment booking workflow.
        
        Args:
            request: Appointment booking request
            call_state: Current call state
            
        Returns:
            Booking result
        """
        logger.info("Executing appointment booking workflow", patient_id=request.patient_id)
        
        # Start conversation
        conversation = await self.voice_agent.start_conversation(call_state)
        session_id = conversation["session_id"]
        
        # Process booking request
        booking_message = f"I'd like to schedule a {request.appointment_type} appointment"
        if request.preferred_date:
            booking_message += f" on {request.preferred_date}"
        if request.preferred_time:
            booking_message += f" at {request.preferred_time}"
        
        # Use voice agent to handle booking
        response = await self.voice_agent.process_message(
            session_id=session_id,
            user_message=booking_message,
            call_state=call_state,
        )
        
        # In production, would integrate with scheduling connector
        # For now, return mock result
        return {
            "success": True,
            "appointment_id": f"APPT-{datetime.utcnow().timestamp()}",
            "appointment_date": request.preferred_date or "TBD",
            "appointment_time": request.preferred_time or "TBD",
            "confirmation_number": f"CONF-{datetime.utcnow().timestamp()}",
            "response": response["response_text"],
        }
    
    # =========================================================================
    # Follow-Up Call Workflow
    # =========================================================================
    
    def create_followup_call_workflow(self) -> WorkflowDefinition:
        """
        Create workflow for automated follow-up calls.
        
        Flow:
        1. Schedule call → Wait for scheduled time
        2. Initiate outbound call
        3. Deliver message (reminder, instructions, etc.)
        4. Collect response (if needed)
        5. Update patient record
        """
        nodes = [
            WorkflowNode(
                id="start",
                type=NodeType.START,
                name="Start",
                description="Follow-up call scheduled",
            ),
            WorkflowNode(
                id="wait_for_time",
                type=NodeType.WAIT,
                name="Wait for Scheduled Time",
                description="Wait until scheduled call time",
            ),
            WorkflowNode(
                id="initiate_call",
                type=NodeType.CALL_API,
                name="Initiate Outbound Call",
                description="Call patient",
                config=NodeConfig(
                    url="/v1/voice/calls/outbound",
                    method="POST",
                ),
            ),
            WorkflowNode(
                id="deliver_message",
                type=NodeType.AGENT,
                name="Deliver Message",
                description="Voice agent delivers message",
                config=NodeConfig(
                    agent_type="voice_agent",
                    prompt_template="Deliver {message_template} in a friendly, conversational way.",
                ),
            ),
            WorkflowNode(
                id="collect_response",
                type=NodeType.AGENT,
                name="Collect Response",
                description="Ask for confirmation/response",
                config=NodeConfig(
                    agent_type="voice_agent",
                    prompt_template="Ask: 'Does this work for you?' or 'Do you have any questions?'",
                ),
            ),
            WorkflowNode(
                id="update_record",
                type=NodeType.UPDATE_DATA,
                name="Update Patient Record",
                description="Record call outcome",
                config=NodeConfig(
                    query_template="UPDATE patients SET last_followup_call = NOW() WHERE id = {patient_id}",
                ),
            ),
            WorkflowNode(
                id="end",
                type=NodeType.END,
                name="End",
                description="Call complete",
            ),
        ]
        
        edges = [
            WorkflowEdge(source="start", target="wait_for_time"),
            WorkflowEdge(source="wait_for_time", target="initiate_call"),
            WorkflowEdge(source="initiate_call", target="deliver_message"),
            WorkflowEdge(source="deliver_message", target="collect_response"),
            WorkflowEdge(source="collect_response", target="update_record"),
            WorkflowEdge(source="update_record", target="end"),
        ]
        
        return WorkflowDefinition(
            name="Voice Follow-Up Call",
            description="Automated follow-up calls for reminders and check-ins",
            nodes=nodes,
            edges=edges,
            tenant_id=self.tenant_id,
            is_template=True,
            tags=["voice", "follow-up", "outbound"],
        )
    
    async def execute_followup_call(
        self,
        request: FollowUpCallRequest,
    ) -> Dict[str, Any]:
        """
        Execute follow-up call workflow.
        
        Args:
            request: Follow-up call request
            
        Returns:
            Call result
        """
        logger.info("Executing follow-up call", patient_id=request.patient_id, reason=request.call_reason)
        
        # Get patient phone number (would query Data Moat)
        # For now, use mock
        patient_phone = "+1234567890"  # Would come from patient record
        
        # Initiate outbound call
        call_state = await self.voice_gateway.initiate_outbound_call(
            to_number=patient_phone,
            from_number=self.voice_gateway.config.get("from_number", "+18005551234"),
            patient_id=request.patient_id,
            workflow_id="followup_call",
        )
        
        # Start conversation
        conversation = await self.voice_agent.start_conversation(call_state)
        session_id = conversation["session_id"]
        
        # Deliver message
        message = request.message_template or self._get_default_message(request.call_reason)
        response = await self.voice_agent.process_message(
            session_id=session_id,
            user_message=message,
            call_state=call_state,
        )
        
        return {
            "success": True,
            "call_id": call_state.call_id,
            "call_status": call_state.status.value,
            "message_delivered": True,
            "response": response["response_text"],
        }
    
    def _get_default_message(self, call_reason: str) -> str:
        """Get default message template for call reason."""
        templates = {
            "appointment_reminder": "This is a reminder about your upcoming appointment. Can you confirm you'll be able to make it?",
            "medication_adherence": "I'm calling to check in on your medication. Are you taking your medications as prescribed?",
            "post_procedure": "I'm calling to see how you're doing after your recent procedure. How are you feeling?",
        }
        return templates.get(call_reason, "I'm calling to check in with you. How are you doing?")
    
    # =========================================================================
    # Insurance Check Workflow
    # =========================================================================
    
    def create_insurance_check_workflow(self) -> WorkflowDefinition:
        """
        Create workflow for insurance eligibility checks via voice.
        
        Flow:
        1. Receive call → Identify patient
        2. Understand service/procedure
        3. Check insurance eligibility (X12 270/271)
        4. Deliver results
        5. Answer questions
        """
        nodes = [
            WorkflowNode(
                id="start",
                type=NodeType.START,
                name="Start",
                description="Insurance check call",
            ),
            WorkflowNode(
                id="identify_patient",
                type=NodeType.AGENT,
                name="Identify Patient",
                description="Verify patient identity",
                config=NodeConfig(
                    agent_type="voice_agent",
                    prompt_template="Verify patient identity for insurance check.",
                ),
            ),
            WorkflowNode(
                id="understand_service",
                type=NodeType.AGENT,
                name="Understand Service",
                description="Extract service/procedure codes",
                config=NodeConfig(
                    agent_type="voice_agent",
                    prompt_template="Extract: service description, procedure code (if mentioned), date of service.",
                ),
            ),
            WorkflowNode(
                id="check_eligibility",
                type=NodeType.CALL_API,
                name="Check Eligibility",
                description="X12 270/271 eligibility check",
                config=NodeConfig(
                    url="/v1/integrations/x12/eligibility",
                    method="POST",
                ),
            ),
            WorkflowNode(
                id="format_results",
                type=NodeType.AGENT,
                name="Format Results",
                description="Convert eligibility results to voice-friendly format",
                config=NodeConfig(
                    agent_type="voice_agent",
                    prompt_template="Convert eligibility results to simple, conversational language.",
                ),
            ),
            WorkflowNode(
                id="deliver_results",
                type=NodeType.AGENT,
                name="Deliver Results",
                description="Voice agent delivers eligibility information",
                config=NodeConfig(
                    agent_type="voice_agent",
                    prompt_template="Deliver eligibility results clearly. Answer any questions.",
                ),
            ),
            WorkflowNode(
                id="end",
                type=NodeType.END,
                name="End",
                description="Call complete",
            ),
        ]
        
        edges = [
            WorkflowEdge(source="start", target="identify_patient"),
            WorkflowEdge(source="identify_patient", target="understand_service"),
            WorkflowEdge(source="understand_service", target="check_eligibility"),
            WorkflowEdge(source="check_eligibility", target="format_results"),
            WorkflowEdge(source="format_results", target="deliver_results"),
            WorkflowEdge(source="deliver_results", target="end"),
        ]
        
        return WorkflowDefinition(
            name="Voice Insurance Check",
            description="Check insurance eligibility via voice call",
            nodes=nodes,
            edges=edges,
            tenant_id=self.tenant_id,
            is_template=True,
            tags=["voice", "insurance", "eligibility"],
        )
    
    async def execute_insurance_check(
        self,
        request: InsuranceCheckRequest,
        call_state: Any,
    ) -> Dict[str, Any]:
        """
        Execute insurance check workflow.
        
        Args:
            request: Insurance check request
            call_state: Current call state
            
        Returns:
            Eligibility check result
        """
        logger.info("Executing insurance check", patient_id=request.patient_id)
        
        # Start conversation
        conversation = await self.voice_agent.start_conversation(call_state)
        session_id = conversation["session_id"]
        
        # Process insurance inquiry
        inquiry_message = "I'd like to check my insurance coverage"
        if request.service_code:
            inquiry_message += f" for {request.service_code}"
        
        response = await self.voice_agent.process_message(
            session_id=session_id,
            user_message=inquiry_message,
            call_state=call_state,
        )
        
        # In production, would integrate with X12 EDI connector
        # For now, return mock result
        return {
            "success": True,
            "eligible": True,
            "coverage_details": "Service is covered under your plan",
            "response": response["response_text"],
        }
