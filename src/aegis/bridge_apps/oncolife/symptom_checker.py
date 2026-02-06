"""
Oncolife Symptom Checker Service

Wraps the symptom checker engine from Oncolife repo and integrates with AEGIS.
"""

from typing import Dict, Any, Optional, List
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)

# Import from local files (copied into AEGIS)
try:
    from .symptom_engine import SymptomCheckerEngine, ConversationState
    from .constants import TriageLevel
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
                "message": "Symptom checker not available. Please ensure files are copied.",
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
    
    class ConversationState:
        @classmethod
        def from_dict(cls, data):
            return cls()
    
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
    
    def __init__(
        self,
        patient_id: Optional[str] = None,
        data_moat_tools: Optional[Any] = None,
        oncolife_agent: Optional[Any] = None,
    ):
        self.patient_id = patient_id
        self.data_moat = data_moat_tools
        self.oncolife_agent = oncolife_agent
        self.engine = SymptomCheckerEngine()
        self.patient_context: Dict[str, Any] = {}
    
    async def _load_patient_context(self) -> Dict[str, Any]:
        """
        Load patient's oncology data from Data Moat.
        
        Returns:
            Patient context with chemo regimens, labs, genomic variants, previous symptoms
        """
        if not self.patient_id or not self.data_moat:
            return {}
        
        try:
            # Load patient oncology context
            context = {}
            
            # Get active chemo regimens
            medications = await self.data_moat.list_entities(
                "medication",
                filters={"patient_id": self.patient_id, "status": "active"},
            )
            context["chemo_regimens"] = [
                m for m in medications.get("entities", [])
                if any(keyword in m.get("display", "").lower() 
                      for keyword in ["chemo", "chemotherapy", "cancer", "oncology"])
            ]
            
            # Get recent labs (CBC, CMP, tumor markers)
            labs = await self.data_moat.list_entities(
                "lab_result",
                filters={"patient_id": self.patient_id},
                limit=20,
            )
            context["recent_labs"] = labs.get("entities", [])
            
            # Get genomic variants
            variants = await self.data_moat.list_entities(
                "genomic_variant",
                filters={"patient_id": self.patient_id},
            )
            context["genomic_variants"] = variants.get("entities", [])
            
            # Get previous symptom reports
            observations = await self.data_moat.list_entities(
                "observation",
                filters={"patient_id": self.patient_id},
                limit=20,
            )
            context["previous_symptoms"] = [
                o for o in observations.get("entities", [])
                if o.get("category") == "symptom"
            ]
            
            # Get patient summary for demographics
            patient_summary = await self.data_moat.get_patient_summary(self.patient_id)
            context["patient"] = patient_summary.get("patient", {})
            context["conditions"] = patient_summary.get("conditions", [])
            
            return context
            
        except Exception as e:
            logger.warning(f"Failed to load patient context: {e}")
            return {}
    
    def _prioritize_symptoms_by_regimen(self) -> List[str]:
        """
        Prioritize symptom questions based on patient's chemo regimen.
        
        Returns:
            List of symptom IDs prioritized by regimen
        """
        if not self.patient_context:
            return []
        
        regimens = self.patient_context.get("chemo_regimens", [])
        prioritized = []
        
        # Map common regimens to expected symptoms
        regimen_symptom_map = {
            "folfox": ["neuropathy", "diarrhea", "nausea", "fatigue"],
            "folfiri": ["diarrhea", "nausea", "fatigue", "mouth_sores"],
            "carboplatin": ["nausea", "fatigue", "low_blood_counts"],
            "taxol": ["neuropathy", "hair_loss", "fatigue"],
            "keytruda": ["rash", "fatigue", "diarrhea", "thyroid"],
        }
        
        for regimen in regimens:
            regimen_name = regimen.get("display", "").lower()
            for key, symptoms in regimen_symptom_map.items():
                if key in regimen_name:
                    prioritized.extend(symptoms)
        
        return list(set(prioritized))  # Remove duplicates
    
    def start_session(self, patient_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a new symptom checker session with patient context.
        
        Args:
            patient_id: Patient identifier (optional, can be set in __init__)
        
        Returns:
            Initial engine response with disclaimer
        """
        if patient_id:
            self.patient_id = patient_id
        
        # Note: Patient context loading is async, so we'll load it in process_user_response
        # For now, start the conversation normally
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
    
    async def process_user_response(
        self,
        user_response: Any,
        session_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user response in the symptom checker conversation with real-time agent integration.
        
        Args:
            user_response: User's answer/selection
            session_state: Optional session state to restore
        
        Returns:
            Engine response with next question or summary, enriched with agent insights
        """
        # Load patient context on first response if not already loaded
        if not self.patient_context and self.patient_id and self.data_moat:
            self.patient_context = await self._load_patient_context()
        
        # Restore state if provided
        if session_state and ONCOLIFE_AVAILABLE:
            try:
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
        
        # Real-time agent consultation during conversation
        if self.oncolife_agent and self.patient_id and self.patient_context:
            current_symptom = response.get("current_symptom") or self._extract_current_symptom(response)
            if current_symptom:
                try:
                    agent_insight = await self.oncolife_agent.consult_symptom_context(
                        patient_id=self.patient_id,
                        symptom=current_symptom,
                        patient_context=self.patient_context,
                    )
                    response["agent_insight"] = agent_insight
                except Exception as e:
                    logger.warning(f"Failed to get agent insight: {e}")
        
        # Add patient context
        if self.patient_id:
            response['patient_id'] = self.patient_id
        
        return response
    
    def _extract_current_symptom(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract current symptom being discussed from response."""
        # Try to extract from message or state
        message = response.get("message", "").lower()
        state = response.get("state")
        
        # Common symptom keywords
        symptom_keywords = [
            "nausea", "vomiting", "diarrhea", "constipation", "fatigue",
            "pain", "fever", "rash", "shortness", "breath", "cough",
            "neuropathy", "numbness", "tingling", "mouth", "sores",
        ]
        
        for keyword in symptom_keywords:
            if keyword in message:
                return keyword
        
        return None
    
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
