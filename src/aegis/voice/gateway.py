"""
Voice Gateway Service

Handles telephony integration (Twilio/Amazon Connect) for voice-based
patient interactions. Provides speech-to-text, text-to-speech, IVR menus,
and call state management.
"""

from typing import Any, Dict, Optional, Callable, Awaitable
from datetime import datetime
from enum import Enum
import json

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Models
# =============================================================================

class CallDirection(str, Enum):
    """Call direction."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(str, Enum):
    """Call status."""
    INITIATING = "initiating"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    NO_ANSWER = "no_answer"


class IVRMenuOption(BaseModel):
    """IVR menu option."""
    digit: str  # "1", "2", etc.
    label: str  # "Press 1 for appointments"
    action: str  # Route to agent/workflow


class CallState(BaseModel):
    """State of an active call."""
    call_id: str
    call_sid: str  # Provider-specific call ID
    direction: CallDirection
    status: CallStatus
    from_number: str
    to_number: str
    patient_id: Optional[str] = None
    session_id: Optional[str] = None  # VoiceAgent session
    current_menu: Optional[str] = None  # Current IVR menu
    conversation_history: list[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None


# =============================================================================
# Voice Gateway Interface
# =============================================================================

class VoiceGateway:
    """
    Voice Gateway - Telephony Integration Layer
    
    Supports:
    - Twilio (primary)
    - Amazon Connect (alternative)
    
    Features:
    - Inbound/outbound call handling
    - Speech-to-text (STT)
    - Text-to-speech (TTS)
    - IVR menu system
    - Call state management
    """
    
    def __init__(
        self,
        provider: str = "twilio",  # "twilio" or "amazon_connect"
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize Voice Gateway.
        
        Args:
            provider: Telephony provider ("twilio" or "amazon_connect")
            config: Provider-specific configuration
        """
        self.provider = provider
        self.config = config or {}
        
        # Call state storage (in production, use Redis)
        self._active_calls: Dict[str, CallState] = {}
        
        # Initialize provider-specific client
        if provider == "twilio":
            self._init_twilio()
        elif provider == "amazon_connect":
            self._init_amazon_connect()
        else:
            logger.warning(f"Unknown provider: {provider}, using mock mode")
            self.provider = "mock"
        
        logger.info("VoiceGateway initialized", provider=provider)
    
    def _init_twilio(self):
        """Initialize Twilio client."""
        try:
            from twilio.rest import Client
            from twilio.twiml.voice_response import VoiceResponse, Gather
            
            account_sid = self.config.get("account_sid") or self.config.get("TWILIO_ACCOUNT_SID")
            auth_token = self.config.get("auth_token") or self.config.get("TWILIO_AUTH_TOKEN")
            
            if account_sid and auth_token:
                self.twilio_client = Client(account_sid, auth_token)
                self.twilio_gather = Gather
                self.twilio_response = VoiceResponse
                logger.info("Twilio client initialized")
            else:
                logger.warning("Twilio credentials not found, using mock mode")
                self.provider = "mock"
        except ImportError:
            logger.warning("Twilio SDK not installed, using mock mode")
            self.provider = "mock"
    
    def _init_amazon_connect(self):
        """Initialize Amazon Connect client."""
        try:
            import boto3
            self.connect_client = boto3.client("connect", region_name=self.config.get("region", "us-east-1"))
            logger.info("Amazon Connect client initialized")
        except ImportError:
            logger.warning("boto3 not installed, using mock mode")
            self.provider = "mock"
    
    # =========================================================================
    # Call Management
    # =========================================================================
    
    async def handle_inbound_call(
        self,
        call_sid: str,
        from_number: str,
        to_number: str,
        call_data: Optional[Dict[str, Any]] = None,
    ) -> CallState:
        """
        Handle an inbound call.
        
        Args:
            call_sid: Provider-specific call ID
            from_number: Caller's phone number
            to_number: Called number
            call_data: Additional call metadata
            
        Returns:
            CallState for the new call
        """
        call_state = CallState(
            call_id=f"call-{call_sid}",
            call_sid=call_sid,
            direction=CallDirection.INBOUND,
            status=CallStatus.IN_PROGRESS,
            from_number=from_number,
            to_number=to_number,
            metadata=call_data or {},
        )
        
        self._active_calls[call_state.call_id] = call_state
        
        logger.info(
            "Inbound call received",
            call_id=call_state.call_id,
            from_number=from_number,
        )
        
        return call_state
    
    async def initiate_outbound_call(
        self,
        to_number: str,
        from_number: str,
        patient_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> CallState:
        """
        Initiate an outbound call.
        
        Args:
            to_number: Phone number to call
            from_number: Caller ID number
            patient_id: Optional patient ID
            workflow_id: Optional workflow to execute during call
            
        Returns:
            CallState for the new call
        """
        call_sid = f"outbound-{datetime.utcnow().timestamp()}"
        
        call_state = CallState(
            call_id=f"call-{call_sid}",
            call_sid=call_sid,
            direction=CallDirection.OUTBOUND,
            status=CallStatus.INITIATING,
            from_number=from_number,
            to_number=to_number,
            patient_id=patient_id,
            metadata={"workflow_id": workflow_id} if workflow_id else {},
        )
        
        self._active_calls[call_state.call_id] = call_state
        
        # Initiate call via provider
        if self.provider == "twilio":
            await self._twilio_outbound_call(call_state)
        elif self.provider == "amazon_connect":
            await self._amazon_connect_outbound_call(call_state)
        else:
            # Mock mode - simulate call initiation
            call_state.status = CallStatus.IN_PROGRESS
            logger.info("Mock outbound call initiated", call_id=call_state.call_id)
        
        return call_state
    
    async def _twilio_outbound_call(self, call_state: CallState):
        """Initiate outbound call via Twilio."""
        if self.provider != "twilio" or not hasattr(self, "twilio_client"):
            return
        
        try:
            call = self.twilio_client.calls.create(
                to=call_state.to_number,
                from_=call_state.from_number,
                url=self.config.get("webhook_url", "https://your-api.com/voice/webhook"),
                method="POST",
            )
            call_state.call_sid = call.sid
            call_state.status = CallStatus.RINGING
            logger.info("Twilio outbound call initiated", call_sid=call.sid)
        except Exception as e:
            logger.error("Failed to initiate Twilio call", error=str(e))
            call_state.status = CallStatus.FAILED
    
    async def _amazon_connect_outbound_call(self, call_state: CallState):
        """Initiate outbound call via Amazon Connect."""
        if self.provider != "amazon_connect" or not hasattr(self, "connect_client"):
            return
        
        try:
            # Amazon Connect outbound call logic
            # This would use StartOutboundVoiceContact API
            logger.info("Amazon Connect outbound call initiated", call_id=call_state.call_id)
            call_state.status = CallStatus.RINGING
        except Exception as e:
            logger.error("Failed to initiate Amazon Connect call", error=str(e))
            call_state.status = CallStatus.FAILED
    
    # =========================================================================
    # Speech Processing
    # =========================================================================
    
    async def speech_to_text(
        self,
        audio_data: bytes,
        language: str = "en-US",
        call_id: Optional[str] = None,
    ) -> str:
        """
        Convert speech to text.
        
        Args:
            audio_data: Audio bytes (WAV, MP3, etc.)
            language: Language code (en-US, es-ES, etc.)
            call_id: Optional call ID for context
            
        Returns:
            Transcribed text
        """
        if self.provider == "twilio":
            # Twilio provides transcription via webhook
            # For real-time, would use streaming STT
            return await self._twilio_stt(audio_data, language)
        elif self.provider == "amazon_connect":
            return await self._amazon_connect_stt(audio_data, language)
        else:
            # Mock mode
            return "Hello, I need help with my appointment"
    
    async def text_to_speech(
        self,
        text: str,
        language: str = "en-US",
        voice: Optional[str] = None,
    ) -> bytes:
        """
        Convert text to speech.
        
        Args:
            text: Text to convert
            language: Language code
            voice: Voice ID (optional)
            
        Returns:
            Audio bytes (MP3, WAV, etc.)
        """
        if self.provider == "twilio":
            # Twilio uses SSML in TwiML
            # Return TwiML response instead of audio bytes
            return await self._twilio_tts(text, language, voice)
        elif self.provider == "amazon_connect":
            return await self._amazon_connect_tts(text, language, voice)
        else:
            # Mock mode - return empty bytes (would be SSML/TwiML in real implementation)
            return b""
    
    async def _twilio_stt(self, audio_data: bytes, language: str) -> str:
        """Twilio speech-to-text (mock for now)."""
        # In production, would use Twilio Media Streams or external STT service
        return "transcribed text"
    
    async def _twilio_tts(self, text: str, language: str, voice: Optional[str]) -> bytes:
        """Twilio text-to-speech (returns TwiML)."""
        if not hasattr(self, "twilio_response"):
            return b""
        
        response = self.twilio_response()
        response.say(text, voice=voice or "alice", language=language[:2])
        return response.to_xml().encode()
    
    async def _amazon_connect_stt(self, audio_data: bytes, language: str) -> str:
        """Amazon Connect speech-to-text."""
        # Would use Amazon Transcribe
        return "transcribed text"
    
    async def _amazon_connect_tts(self, text: str, language: str, voice: Optional[str]) -> bytes:
        """Amazon Connect text-to-speech."""
        # Would use Amazon Polly
        return b""
    
    # =========================================================================
    # IVR Menus
    # =========================================================================
    
    def create_ivr_menu(
        self,
        menu_id: str,
        greeting: str,
        options: list[IVRMenuOption],
        timeout_seconds: int = 10,
    ) -> Dict[str, Any]:
        """
        Create an IVR menu.
        
        Args:
            menu_id: Unique menu identifier
            greeting: Greeting message
            options: Menu options
            timeout_seconds: Timeout for input
            
        Returns:
            Menu configuration
        """
        menu = {
            "menu_id": menu_id,
            "greeting": greeting,
            "options": [opt.model_dump() for opt in options],
            "timeout_seconds": timeout_seconds,
        }
        
        logger.info("IVR menu created", menu_id=menu_id, options_count=len(options))
        return menu
    
    def generate_ivr_twiml(
        self,
        menu: Dict[str, Any],
        action_url: str,
    ) -> str:
        """
        Generate TwiML for IVR menu.
        
        Args:
            menu: Menu configuration
            action_url: URL to handle menu selection
            
        Returns:
            TwiML XML string
        """
        if not hasattr(self, "twilio_response"):
            return ""
        
        response = self.twilio_response()
        response.say(menu["greeting"], voice="alice")
        
        gather = self.twilio_gather(
            num_digits=1,
            action=action_url,
            method="POST",
            timeout=menu["timeout_seconds"],
        )
        
        for option in menu["options"]:
            gather.say(f"Press {option['digit']} for {option['label']}")
        
        response.append(gather)
        response.say("I didn't receive your selection. Goodbye.")
        
        return response.to_xml()
    
    # =========================================================================
    # Call State Management
    # =========================================================================
    
    def get_call_state(self, call_id: str) -> Optional[CallState]:
        """Get call state by call ID."""
        return self._active_calls.get(call_id)
    
    def update_call_state(
        self,
        call_id: str,
        updates: Dict[str, Any],
    ) -> Optional[CallState]:
        """Update call state."""
        call_state = self._active_calls.get(call_id)
        if not call_state:
            return None
        
        # Update fields
        for key, value in updates.items():
            if hasattr(call_state, key):
                setattr(call_state, key, value)
        
        call_state.metadata.update(updates.get("metadata", {}))
        
        logger.debug("Call state updated", call_id=call_id, updates=list(updates.keys()))
        return call_state
    
    def end_call(self, call_id: str) -> Optional[CallState]:
        """End a call."""
        call_state = self._active_calls.get(call_id)
        if not call_state:
            return None
        
        call_state.status = CallStatus.COMPLETED
        call_state.ended_at = datetime.utcnow()
        
        logger.info("Call ended", call_id=call_id, duration_seconds=(
            (call_state.ended_at - call_state.started_at).total_seconds()
        ))
        
        return call_state
    
    def get_active_calls(self) -> list[CallState]:
        """Get all active calls."""
        return [
            call for call in self._active_calls.values()
            if call.status == CallStatus.IN_PROGRESS
        ]
