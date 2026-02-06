"""
Oncolife Symptom Checker Service

Wraps the symptom checker engine from Oncolife repo and integrates with AEGIS.
"""

from typing import Dict, Any, Optional
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)

# Try to import from Oncolife repo if available
ONCOLIFE_AVAILABLE = False
try:
    # Attempt to import from the Oncolife repo structure
    import sys
    oncolife_path = Path(__file__).parent.parent.parent.parent.parent.parent / "oncolife_temp" / "apps" / "patient-platform" / "patient-api" / "src"
    if oncolife_path.exists():
        sys.path.insert(0, str(oncolife_path))
    
    from routers.chat.symptom_checker.symptom_engine import SymptomCheckerEngine
    from routers.chat.symptom_checker.constants import TriageLevel
    ONCOLIFE_AVAILABLE = True
except (ImportError, AttributeError) as e:
    logger.warning(f"Oncolife symptom checker engine not found: {e}. Using mock implementation.")
    ONCOLIFE_AVAILABLE = False
    
    # Mock implementation
    class SymptomCheckerEngine:
        def __init__(self, state=None):
            self.state = state or {}
        
        def start_conversation(self):
            return {
                "message": "Symptom checker not available. Please ensure Oncolife repo is integrated.",
                "message_type": "error"
            }
        
        def process_response(self, user_response):
            return {
                "message": "Symptom checker not available.",
                "message_type": "error"
            }
        
        def get_state(self):
            return type('State', (), {'to_dict': lambda: {}})()
        
        def set_state(self, state):
            self.state = state
    
    class TriageLevel:
        NONE = "none"
        NOTIFY_CARE_TEAM = "notify_care_team"
        URGENT = "urgent"
        CALL_911 = "call_911"


class SymptomCheckerService:
    """
    Service wrapper for Oncolife symptom checker.
    
    Integrates with:
    - AEGIS Data Moat (patient data)
    - OncolifeAgent (care recommendations)
    - Patient timeline (symptom history)
    """
    
    def __init__(self, patient_id: Optional[str] = None):
        self.patient_id = patient_id
        self.engine = SymptomCheckerEngine()
    
    def start_session(self, patient_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a new symptom checker session.
        
        Args:
            patient_id: Patient identifier (optional, can be set in __init__)
        
        Returns:
            Initial engine response with disclaimer
        """
        if patient_id:
            self.patient_id = patient_id
        
        response = self.engine.start_conversation()
        
        # Convert EngineResponse to dict if needed
        if hasattr(response, 'message'):
            response = {
                'message': response.message,
                'message_type': response.message_type,
                'options': getattr(response, 'options', []),
                'triage_level': getattr(response, 'triage_level', None),
                'state': getattr(response, 'state', None)
            }
        
        # Enrich with patient context from Data Moat if available
        if self.patient_id:
            response['patient_id'] = self.patient_id
        
        return response
    
    def process_user_response(
        self,
        user_response: Any,
        session_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user response in the symptom checker conversation.
        
        Args:
            user_response: User's answer/selection
            session_state: Optional session state to restore
        
        Returns:
            Engine response with next question or summary
        """
        # Restore state if provided
        if session_state and ONCOLIFE_AVAILABLE:
            try:
                from routers.chat.symptom_checker.symptom_engine import ConversationState
                self.engine.set_state(ConversationState.from_dict(session_state))
            except Exception as e:
                logger.warning(f"Failed to restore session state: {e}")
        
        response = self.engine.process_response(user_response)
        
        # Convert EngineResponse to dict if needed
        if hasattr(response, 'message'):
            response = {
                'message': response.message,
                'message_type': response.message_type,
                'options': getattr(response, 'options', []),
                'triage_level': getattr(response, 'triage_level', None),
                'is_complete': getattr(response, 'is_complete', False),
                'state': getattr(response, 'state', None)
            }
        
        # Add patient context
        if self.patient_id:
            response['patient_id'] = self.patient_id
        
        return response
    
    def get_session_state(self) -> Dict[str, Any]:
        """Get current session state for persistence."""
        try:
            state = self.engine.get_state()
            if hasattr(state, 'to_dict'):
                return state.to_dict()
            return {}
        except Exception:
            return {}
    
    def get_triage_level(self) -> str:
        """Get the highest triage level from current session."""
        try:
            state = self.engine.get_state()
            if hasattr(state, 'highest_triage_level'):
                return state.highest_triage_level.value if hasattr(state.highest_triage_level, 'value') else str(state.highest_triage_level)
        except Exception:
            pass
        return TriageLevel.NONE
    
    def get_summary(self) -> Dict[str, Any]:
        """Get session summary data."""
        try:
            state = self.engine.get_state()
            return {
                'symptoms_assessed': getattr(state, 'completed_symptoms', []),
                'triage_results': getattr(state, 'triage_results', []),
                'highest_level': self.get_triage_level(),
                'chat_history': getattr(state, 'chat_history', []),
                'personal_notes': getattr(state, 'personal_notes', None)
            }
        except Exception:
            return {
                'symptoms_assessed': [],
                'triage_results': [],
                'highest_level': TriageLevel.NONE,
                'chat_history': [],
                'personal_notes': None
            }
