"""
AEGIS Voice Module

Voice-based patient interaction layer built on top of AEGIS platform.
Provides ROVA-like capabilities for voice-based healthcare assistance.

Components:
- VoiceGateway: Telephony integration (Twilio/Amazon Connect)
- VoiceAgent: Voice conversation agent extending BaseAgent
- VoiceWorkflows: Pre-built workflows for appointments, follow-ups, insurance
"""

from aegis.voice.gateway import VoiceGateway, CallState, CallDirection, CallStatus
from aegis.voice.agent import VoiceAgent
from aegis.voice.workflows import (
    VoiceWorkflows,
    AppointmentBookingRequest,
    FollowUpCallRequest,
    InsuranceCheckRequest,
)

__all__ = [
    "VoiceGateway",
    "VoiceAgent",
    "VoiceWorkflows",
    "CallState",
    "CallDirection",
    "CallStatus",
    "AppointmentBookingRequest",
    "FollowUpCallRequest",
    "InsuranceCheckRequest",
]
