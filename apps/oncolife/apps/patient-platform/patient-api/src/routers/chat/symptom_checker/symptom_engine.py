"""
================================================================================
Symptom Checker Engine - Patient API
================================================================================

Module:         symptom_engine.py
Description:    Rule-based conversation engine for oncology symptom triage.
                Manages the multi-phase symptom checker flow with clinically
                validated questions and severity assessments.

Created:        2025-12-14
Modified:       2026-01-16
Author:         Naveen Babu S A
Version:        2.1.0

Conversation Flow:
    1. DISCLAIMER       - Medical disclaimer with "I Understand" button
    2. EMERGENCY_CHECK  - Urgent safety check (5 emergency symptoms)
    3. SYMPTOM_SELECTION- Grouped symptom selection (7 categories)
    4. SCREENING        - Per-symptom questions (Ruby chat persona)
    5. SUMMARY          - Session summary with recommended actions

Severity Levels:
    - NONE      - No symptoms reported
    - MILD      - Monitor at home
    - MODERATE  - Contact care team within 24h
    - SEVERE    - Contact care team today
    - URGENT    - Seek immediate care / 911

Note: Patient context (chemo dates, physician visits) is stored in
the Patient Profile page, not collected during symptom check.

Copyright:
    (c) 2026 OncoLife Health Technologies. All rights reserved.
================================================================================
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .constants import (
    TriageLevel, InputType, ConversationPhase,
    MEDICAL_DISCLAIMER, EMERGENCY_CHECK_MESSAGE, RUBY_GREETING,
    EMERGENCY_SYMPTOMS, SYMPTOM_GROUPS, SUMMARY_ACTIONS,
    PATIENT_CONTEXT_MESSAGE, LAST_CHEMO_OPTIONS, PHYSICIAN_VISIT_OPTIONS,
    validate_temperature, validate_text_input, TEMP_FEVER_THRESHOLD,
    validate_blood_pressure, validate_heart_rate, validate_oxygen_saturation,
    validate_days, validate_times_per_day, validate_blood_sugar, validate_weight,
    INPUT_HINTS
)
from .symptom_definitions import (
    SYMPTOMS, SymptomDef, Question, LogicResult,
    get_visible_symptoms, get_symptom_by_id
)

logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    """Tracks the current state of the symptom checker conversation."""
    phase: ConversationPhase = ConversationPhase.DISCLAIMER
    current_symptom_id: Optional[str] = None
    current_question_index: int = 0
    is_follow_up: bool = False
    answers: Dict[str, Any] = field(default_factory=dict)
    selected_symptoms: List[str] = field(default_factory=list)
    emergency_symptoms: List[str] = field(default_factory=list)
    completed_symptoms: List[str] = field(default_factory=list)
    triage_results: List[Dict[str, Any]] = field(default_factory=list)
    branch_stack: List[str] = field(default_factory=list)
    highest_triage_level: TriageLevel = TriageLevel.NONE
    chat_history: List[Dict[str, Any]] = field(default_factory=list)
    session_start: Optional[str] = None
    personal_notes: Optional[str] = None  # Patient's additional notes
    # Patient context (critical physician data)
    last_chemo_date: Optional[str] = None  # When was last chemotherapy
    next_physician_visit: Optional[str] = None  # Scheduled physician visit
    patient_context_step: int = 0  # 0=chemo, 1=physician visit
    # Cross-symptom dehydration tracking (per spec DEH-201)
    # Prevents asking same dehydration questions multiple times in one session
    dehydration_questions_asked: bool = False
    dehydration_signs_present: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dictionary."""
        return {
            'phase': self.phase.value,
            'current_symptom_id': self.current_symptom_id,
            'current_question_index': self.current_question_index,
            'is_follow_up': self.is_follow_up,
            'answers': self.answers,
            'selected_symptoms': self.selected_symptoms,
            'emergency_symptoms': self.emergency_symptoms,
            'completed_symptoms': self.completed_symptoms,
            'triage_results': self.triage_results,
            'branch_stack': self.branch_stack,
            'highest_triage_level': self.highest_triage_level.value,
            'chat_history': self.chat_history,
            'session_start': self.session_start,
            'personal_notes': self.personal_notes,
            'last_chemo_date': self.last_chemo_date,
            'next_physician_visit': self.next_physician_visit,
            'patient_context_step': self.patient_context_step,
            'dehydration_questions_asked': self.dehydration_questions_asked,
            'dehydration_signs_present': self.dehydration_signs_present
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """Deserialize state from dictionary."""
        return cls(
            phase=ConversationPhase(data.get('phase', 'disclaimer')),
            current_symptom_id=data.get('current_symptom_id'),
            current_question_index=data.get('current_question_index', 0),
            is_follow_up=data.get('is_follow_up', False),
            answers=data.get('answers', {}),
            selected_symptoms=data.get('selected_symptoms', []),
            emergency_symptoms=data.get('emergency_symptoms', []),
            completed_symptoms=data.get('completed_symptoms', []),
            triage_results=data.get('triage_results', []),
            branch_stack=data.get('branch_stack', []),
            highest_triage_level=TriageLevel(data.get('highest_triage_level', 'none')),
            chat_history=data.get('chat_history', []),
            session_start=data.get('session_start'),
            personal_notes=data.get('personal_notes'),
            last_chemo_date=data.get('last_chemo_date'),
            next_physician_visit=data.get('next_physician_visit'),
            patient_context_step=data.get('patient_context_step', 0),
            dehydration_questions_asked=data.get('dehydration_questions_asked', False),
            dehydration_signs_present=data.get('dehydration_signs_present', False)
        )


@dataclass
class EngineResponse:
    """Response from the symptom checker engine."""
    message: str
    message_type: str  # 'disclaimer', 'emergency_check', 'symptom_select', 'text', 'yes_no', 'choice', 'multiselect', 'number', 'summary', 'patient_context'
    options: List[Dict[str, Any]] = field(default_factory=list)
    triage_level: Optional[TriageLevel] = None
    triage_message: Optional[str] = None
    is_complete: bool = False
    state: Optional[ConversationState] = None
    # Chat-specific fields
    sender: str = "ruby"  # 'ruby' or 'system'
    avatar: Optional[str] = None
    timestamp: Optional[str] = None
    # Symptom groups for grouped selection
    symptom_groups: Optional[Dict[str, Any]] = None
    # Summary data
    summary_data: Optional[Dict[str, Any]] = None
    # Input type hint for frontend (optional)
    input_type: Optional[str] = None  # 'date_picker', 'number', 'text', etc.


class SymptomCheckerEngine:
    """
    Rule-based symptom checker engine - Version 2.0
    
    Implements the improved UX flow:
    1. Medical disclaimer (legal requirement)
    2. Emergency safety check (rule out 911 situations first)
    3. Grouped symptom selection (user-friendly categories)
    4. Ruby chat (WhatsApp-style conversation)
    5. Summary with actions (download, diary, report another)
    """

    def __init__(self, state: Optional[ConversationState] = None):
        """Initialize the engine with optional existing state."""
        self.state = state or ConversationState()

    def start_conversation(self) -> EngineResponse:
        """Start a new symptom checker conversation with the disclaimer."""
        self.state = ConversationState(
            phase=ConversationPhase.DISCLAIMER,
            session_start=datetime.utcnow().isoformat()
        )
        
        return EngineResponse(
            message=MEDICAL_DISCLAIMER,
            message_type='disclaimer',
            options=[
                {
                    'label': '✓ I Understand - Start Triage',
                    'value': 'accept',
                    'style': 'primary'
                }
            ],
            sender='system',
            state=self.state
        )

    def process_response(self, user_response: Any) -> EngineResponse:
        """
        Process a user's response and return the next step.
        
        Args:
            user_response: The user's answer
        
        Returns:
            EngineResponse with the next screen or question
        """
        logger.info(f"Processing response: {user_response}, Phase: {self.state.phase}")

        # Add to chat history for WhatsApp-style display
        self._add_to_chat_history('user', user_response)

        if self.state.phase == ConversationPhase.DISCLAIMER:
            return self._handle_disclaimer(user_response)
        
        # DEPRECATED: Patient context is now in Profile page, not symptom checker
        # Kept for backwards compatibility with old sessions
        elif self.state.phase == ConversationPhase.PATIENT_CONTEXT:
            # Redirect to emergency check for any legacy sessions
            self.state.phase = ConversationPhase.EMERGENCY_CHECK
            return self._show_emergency_check()
        
        elif self.state.phase == ConversationPhase.EMERGENCY_CHECK:
            return self._handle_emergency_check(user_response)
        
        elif self.state.phase == ConversationPhase.SYMPTOM_SELECTION:
            return self._handle_symptom_selection(user_response)
        
        elif self.state.phase == ConversationPhase.SCREENING:
            return self._handle_screening_response(user_response)
        
        elif self.state.phase == ConversationPhase.FOLLOW_UP:
            return self._handle_followup_response(user_response)
        
        elif self.state.phase == ConversationPhase.SUMMARY:
            return self._handle_summary_action(user_response)
        
        elif self.state.phase == ConversationPhase.ADDING_NOTES:
            return self._handle_notes_input(user_response)
        
        elif self.state.phase == ConversationPhase.EMERGENCY:
            return self._handle_emergency_action(user_response)
        
        elif self.state.phase == ConversationPhase.COMPLETED:
            return self._handle_completed_action(user_response)
        
        else:
            return self.start_conversation()

    def _add_to_chat_history(self, sender: str, message: Any):
        """Add a message to the chat history."""
        self.state.chat_history.append({
            'sender': sender,
            'message': str(message) if not isinstance(message, (list, dict)) else message,
            'timestamp': datetime.utcnow().isoformat()
        })

    # =========================================================================
    # PHASE 1: DISCLAIMER
    # =========================================================================
    def _handle_disclaimer(self, user_response: Any) -> EngineResponse:
        """Handle the disclaimer acceptance."""
        if user_response == 'accept':
            # Skip patient context - now stored in Profile page
            # Go directly to emergency check
            self.state.phase = ConversationPhase.EMERGENCY_CHECK
            return self._show_emergency_check()
        else:
            # User must accept to continue
            return EngineResponse(
                message="Please accept the medical disclaimer to continue.",
                message_type='disclaimer',
                options=[
                    {
                        'label': '✓ I Understand - Start Triage',
                        'value': 'accept',
                        'style': 'primary'
                    }
                ],
                sender='system',
                state=self.state
            )

    # =========================================================================
    # PHASE 2: PATIENT CONTEXT (Critical Physician Data)
    # =========================================================================
    def _show_patient_context_question(self) -> EngineResponse:
        """Show patient context questions (last chemo, physician visit)."""
        step = self.state.patient_context_step
        
        if step == 0:
            # Question 1: When was your last chemotherapy?
            return EngineResponse(
                message=f"{PATIENT_CONTEXT_MESSAGE}\n\n"
                        "📅 **When was your last chemotherapy session?**\n\n"
                        "*This helps us understand your treatment timeline.*",
                message_type='patient_context',
                options=LAST_CHEMO_OPTIONS,
                input_type='date_picker',  # Hint for frontend to show calendar
                sender='ruby',
                avatar='💎',
                state=self.state
            )
        else:
            # Question 2: When is your next scheduled physician visit?
            return EngineResponse(
                message="📅 **When is your next scheduled physician visit?**\n\n"
                        "*This helps us prioritize any concerns for your upcoming appointment.*",
                message_type='patient_context',
                options=PHYSICIAN_VISIT_OPTIONS,
                input_type='date_picker',  # Hint for frontend to show calendar
                sender='ruby',
                avatar='💎',
                state=self.state
            )

    def _handle_patient_context(self, user_response: Any) -> EngineResponse:
        """Handle patient context responses."""
        step = self.state.patient_context_step
        
        if step == 0:
            # Save last chemo date
            self.state.last_chemo_date = user_response
            self.state.answers['last_chemo_date'] = user_response
            
            # Move to next question
            self.state.patient_context_step = 1
            return self._show_patient_context_question()
        else:
            # Save physician visit
            self.state.next_physician_visit = user_response
            self.state.answers['next_physician_visit'] = user_response
            
            # Move to emergency check
            self.state.phase = ConversationPhase.EMERGENCY_CHECK
            return self._show_emergency_check()

    # =========================================================================
    # PHASE 3: EMERGENCY CHECK
    # =========================================================================
    def _show_emergency_check(self) -> EngineResponse:
        """Show the emergency safety check screen."""
        emergency_options = []
        
        for symptom in EMERGENCY_SYMPTOMS:
            emergency_options.append({
                'label': f"{symptom['icon']} {symptom['name']}",
                'value': symptom['id'],
                'is_emergency': True
            })
        
        emergency_options.append({
            'label': '✓ None of these - I\'m not experiencing any emergency symptoms',
            'value': 'none',
            'style': 'secondary'
        })

        return EngineResponse(
            message=EMERGENCY_CHECK_MESSAGE,
            message_type='emergency_check',
            options=emergency_options,
            sender='system',
            state=self.state
        )

    def _handle_emergency_check(self, user_response: Any) -> EngineResponse:
        """Handle the emergency check response."""
        if isinstance(user_response, str):
            if user_response == 'none':
                # No emergencies, continue to symptom selection
                self.state.phase = ConversationPhase.SYMPTOM_SELECTION
                return self._show_symptom_selection()
            selected = [user_response]
        elif isinstance(user_response, list):
            selected = [s for s in user_response if s != 'none']
        else:
            selected = []

        if not selected or selected == ['none']:
            self.state.phase = ConversationPhase.SYMPTOM_SELECTION
            return self._show_symptom_selection()

        # Emergency symptoms selected - go to emergency path
        self.state.emergency_symptoms = selected
        self.state.selected_symptoms = selected
        self.state.phase = ConversationPhase.SCREENING
        
        # Start with the first emergency symptom
        return self._start_ruby_chat()

    # =========================================================================
    # PHASE 3: SYMPTOM SELECTION (Grouped)
    # =========================================================================
    def _show_symptom_selection(self) -> EngineResponse:
        """Show the grouped symptom selection screen."""
        groups = {}
        
        for group_id, group_data in SYMPTOM_GROUPS.items():
            groups[group_id] = {
                'name': group_data['name'],
                'icon': group_data['icon'],
                'symptoms': []
            }
            
            for symptom in group_data['symptoms']:
                # Verify symptom exists in definitions
                symptom_def = get_symptom_by_id(symptom['id'])
                if symptom_def:
                    groups[group_id]['symptoms'].append({
                        'id': symptom['id'],
                        'name': symptom['name'],
                        'available': True
                    })

        return EngineResponse(
            message="What symptoms are you experiencing today?\n\n*Select all that apply, then tap Continue.*",
            message_type='symptom_select',
            options=[
                {
                    'label': 'Continue',
                    'value': 'continue',
                    'style': 'primary',
                    'disabled_until_selection': True
                },
                {
                    'label': "I'm feeling fine today",
                    'value': 'none',
                    'style': 'secondary'
                }
            ],
            symptom_groups=groups,
            sender='system',
            state=self.state
        )

    def _handle_symptom_selection(self, user_response: Any) -> EngineResponse:
        """Handle symptom selection from the grouped view."""
        if isinstance(user_response, str):
            if user_response in ['none', 'continue']:
                if user_response == 'none' or not self.state.selected_symptoms:
                    return self._complete_feeling_fine()
            else:
                self.state.selected_symptoms.append(user_response)
        elif isinstance(user_response, list):
            self.state.selected_symptoms = [s for s in user_response if s not in ['none', 'continue']]
        elif isinstance(user_response, dict) and 'symptoms' in user_response:
            # Handle structured response from grouped selection
            self.state.selected_symptoms = user_response['symptoms']

        if not self.state.selected_symptoms:
            return self._complete_feeling_fine()

        # Start the Ruby chat for symptom assessment
        self.state.phase = ConversationPhase.SCREENING
        return self._start_ruby_chat()

    def _complete_feeling_fine(self) -> EngineResponse:
        """Complete the session when patient is feeling fine."""
        self.state.phase = ConversationPhase.COMPLETED
        
        return EngineResponse(
            message="Great to hear you're feeling fine today! 😊\n\n"
                    "Remember, you can always come back if you start experiencing any symptoms.\n\n"
                    "Take care!",
            message_type='text',
            options=SUMMARY_ACTIONS[2:],  # Report another, Done for today
            is_complete=True,
            sender='ruby',
            avatar='👋',
            state=self.state
        )

    # =========================================================================
    # PHASE 4: RUBY CHAT (Per-Symptom Questions)
    # =========================================================================
    def _start_ruby_chat(self) -> EngineResponse:
        """Start the Ruby chat interface with greeting."""
        # Get symptom names for the greeting
        selected_names = []
        for symptom_id in self.state.selected_symptoms:
            symptom = get_symptom_by_id(symptom_id)
            if symptom:
                selected_names.append(symptom.name)
        
        symptoms_text = ", ".join(selected_names)
        
        greeting = f"{RUBY_GREETING}\n\n📋 **You selected:** {symptoms_text}\n\nLet's start with your first symptom."
        
        self._add_to_chat_history('ruby', greeting)
        
        # Start first symptom
        return self._start_next_symptom(greeting_message=greeting)

    def _start_next_symptom(self, greeting_message: Optional[str] = None) -> EngineResponse:
        """Start processing the next symptom in the queue."""
        # Check if there are branched symptoms to process first
        if self.state.branch_stack:
            next_symptom_id = self.state.branch_stack.pop(0)
        else:
            # Get next unprocessed symptom
            remaining = [s for s in self.state.selected_symptoms 
                        if s not in self.state.completed_symptoms]
            if not remaining:
                return self._generate_summary()
            next_symptom_id = remaining[0]

        symptom = get_symptom_by_id(next_symptom_id)
        if not symptom:
            logger.error(f"Symptom not found: {next_symptom_id}")
            self.state.completed_symptoms.append(next_symptom_id)
            return self._start_next_symptom()

        self.state.current_symptom_id = next_symptom_id
        self.state.current_question_index = 0
        self.state.is_follow_up = False
        self.state.answers = {}
        self.state.phase = ConversationPhase.SCREENING

        return self._get_next_question(symptom, greeting_message)

    def _is_dehydration_question(self, question_id: str) -> bool:
        """Check if a question is a dehydration-related question (per DEH-201 cross-symptom tracking)."""
        dehydration_patterns = [
            'dehydration_signs', 'dehydration',
            'urine_dark', 'urine_less', 'urine_amt', 'urine_color',
            'thirsty', 'lightheaded', 'vitals_known',
            # Module-specific prefixes
            'mso_urine', 'mso_thirsty', 'mso_lightheaded', 'mso_vitals',
            'vom_urine', 'vom_thirsty', 'vom_lightheaded', 'vom_vitals',
            'dia_urine', 'dia_thirsty', 'dia_lightheaded', 'dia_vitals',
        ]
        return any(pattern in question_id for pattern in dehydration_patterns)

    def _get_next_question(self, symptom: SymptomDef, prefix_message: Optional[str] = None) -> EngineResponse:
        """Get the next applicable question for the current symptom."""
        questions = symptom.follow_up_questions if self.state.is_follow_up else symptom.screening_questions
        
        while self.state.current_question_index < len(questions):
            question = questions[self.state.current_question_index]
            
            # DEH-201: Skip dehydration questions if already asked in this session
            if self._is_dehydration_question(question.id) and self.state.dehydration_questions_asked:
                logger.info(f"Skipping dehydration question {question.id} - already asked in session")
                self.state.current_question_index += 1
                continue
            
            # Check if question condition is met
            if question.condition is None or question.condition(self.state.answers):
                # Mark dehydration questions as asked
                if self._is_dehydration_question(question.id):
                    self.state.dehydration_questions_asked = True
                return self._format_question(question, symptom, prefix_message)
            
            # Skip this question if condition not met
            self.state.current_question_index += 1

        # No more questions in current phase
        return self._evaluate_current_phase(symptom)

    def _format_question(self, question: Question, symptom: SymptomDef, prefix: Optional[str] = None) -> EngineResponse:
        """Format a question into an EngineResponse with WhatsApp-style formatting."""
        options = []
        
        if question.input_type == InputType.YES_NO:
            options = [
                {'label': 'Yes', 'value': True, 'style': 'choice'},
                {'label': 'No', 'value': False, 'style': 'choice'}
            ]
            message_type = 'yes_no'
        
        elif question.input_type == InputType.CHOICE:
            options = [{'label': o.label, 'value': o.value, 'style': 'choice'} for o in question.options]
            message_type = 'choice'
        
        elif question.input_type == InputType.MULTISELECT:
            options = [{'label': o.label, 'value': o.value, 'style': 'choice'} for o in question.options]
            message_type = 'multiselect'
        
        elif question.input_type == InputType.NUMBER:
            message_type = 'number'
        
        else:  # TEXT
            message_type = 'text'

        # Build the message with symptom context for first question
        message_parts = []
        
        if prefix:
            message_parts.append(prefix)
        
        if self.state.current_question_index == 0 and not self.state.is_follow_up:
            # Large, prominent symptom header
            message_parts.append(f"\n\n━━━━━━━━━━━━━━━━━━━━\n\n🔍 **Now let's talk about:**\n## 💊 {symptom.name}\n\n━━━━━━━━━━━━━━━━━━━━\n")
        
        message_parts.append(question.text)
        
        # Add input hints for NUMBER inputs
        if question.input_type == InputType.NUMBER:
            hint = self._get_input_hint(question.id)
            if hint:
                message_parts.append(f"\n\n{hint}")
        
        full_message = "\n".join(message_parts)
        
        self._add_to_chat_history('ruby', question.text)

        return EngineResponse(
            message=full_message,
            message_type=message_type,
            options=options,
            sender='ruby',
            avatar='💬',
            timestamp=datetime.utcnow().isoformat(),
            state=self.state
        )

    def _get_input_hint(self, question_id: str) -> Optional[str]:
        """Get the input hint/format for a question based on its ID."""
        q_id = question_id.lower()
        
        if 'temp' in q_id:
            return INPUT_HINTS.get('temperature', '')
        if 'bp' in q_id or 'blood_pressure' in q_id or 'pressure' in q_id:
            return INPUT_HINTS.get('blood_pressure', '')
        if 'hr' in q_id or 'heart_rate' in q_id or 'pulse' in q_id:
            return INPUT_HINTS.get('heart_rate', '')
        if 'o2' in q_id or 'oxygen' in q_id or 'spo2' in q_id or 'sat' in q_id:
            return INPUT_HINTS.get('oxygen', '')
        if 'sugar' in q_id or 'glucose' in q_id:
            return INPUT_HINTS.get('blood_sugar', '')
        if 'days' in q_id or 'day' in q_id or 'duration' in q_id:
            return INPUT_HINTS.get('days', '')
        if 'times' in q_id or 'episodes' in q_id or 'frequency' in q_id:
            return INPUT_HINTS.get('times', '')
        if 'weight' in q_id:
            return INPUT_HINTS.get('weight', '')
        
        return None

    def _validate_numeric_input(self, question: Any, user_response: Any) -> tuple[bool, Any, Optional[str]]:
        """
        Validate numeric inputs based on question ID patterns.
        
        Returns:
            (is_valid, validated_value, error_message_or_None)
        """
        q_id = question.id.lower()
        response_str = str(user_response).strip()
        
        # Temperature validation (with Celsius auto-conversion)
        if 'temp' in q_id:
            is_valid, value, msg = validate_temperature(response_str)
            if not is_valid:
                return False, None, msg
            # Log if Celsius was converted
            if msg:
                logger.info(f"Temperature conversion: {msg}")
            return True, value, None
        
        # Blood pressure validation (format: 120/80)
        if 'bp' in q_id or 'blood_pressure' in q_id or 'pressure' in q_id:
            is_valid, value, msg = validate_blood_pressure(response_str)
            if not is_valid:
                return False, None, msg
            return True, value, None
        
        # Heart rate validation
        if 'hr' in q_id or 'heart_rate' in q_id or 'pulse' in q_id:
            is_valid, value, msg = validate_heart_rate(response_str)
            if not is_valid:
                return False, None, msg
            return True, value, None
        
        # Oxygen saturation validation
        if 'o2' in q_id or 'oxygen' in q_id or 'spo2' in q_id or 'sat' in q_id:
            is_valid, value, msg = validate_oxygen_saturation(response_str)
            if not is_valid:
                return False, None, msg
            return True, value, None
        
        # Blood sugar validation
        if 'sugar' in q_id or 'glucose' in q_id or 'blood_sugar' in q_id:
            is_valid, value, msg = validate_blood_sugar(response_str)
            if not is_valid:
                return False, None, msg
            return True, value, None
        
        # Days validation
        if 'days' in q_id or 'day' in q_id or 'duration' in q_id:
            is_valid, value, msg = validate_days(response_str)
            if not is_valid:
                return False, None, msg
            return True, value, None
        
        # Times/frequency validation
        if 'times' in q_id or 'episodes' in q_id or 'frequency' in q_id or 'count' in q_id:
            is_valid, value, msg = validate_times_per_day(response_str)
            if not is_valid:
                return False, None, msg
            return True, value, None
        
        # Weight validation
        if 'weight' in q_id or 'lbs' in q_id:
            is_valid, value, msg = validate_weight(response_str)
            if not is_valid:
                return False, None, msg
            return True, value, None
        
        # Generic number - just ensure it's a valid number
        try:
            value = float(response_str)
            return True, value, None
        except (ValueError, TypeError):
            return False, None, "📝 Please enter a valid number."

    def _handle_screening_response(self, user_response: Any) -> EngineResponse:
        """Handle a response during the screening phase."""
        symptom = get_symptom_by_id(self.state.current_symptom_id)
        if not symptom:
            return self._start_next_symptom()

        questions = symptom.screening_questions
        if self.state.current_question_index < len(questions):
            question = questions[self.state.current_question_index]
            
            # Validate NUMBER inputs
            if question.input_type == InputType.NUMBER:
                is_valid, validated_value, error_msg = self._validate_numeric_input(question, user_response)
                if not is_valid:
                    return EngineResponse(
                        message=f"{error_msg}\n\n{question.text}",
                        message_type='number',
                        options=[],
                        sender='ruby',
                        avatar='⚠️',
                        state=self.state
                    )
                self.state.answers[question.id] = validated_value
                logger.info(f"Stored validated {question.id}: {validated_value}")
            
            # Validate TEXT inputs
            elif question.input_type == InputType.TEXT:
                is_valid, error_msg = validate_text_input(str(user_response))
                if not is_valid:
                    return EngineResponse(
                        message=f"{error_msg}\n\n{question.text}",
                        message_type='text',
                        options=[],
                        sender='ruby',
                        avatar='⚠️',
                        state=self.state
                    )
                self.state.answers[question.id] = user_response
                logger.info(f"Stored answer for {question.id}: {user_response}")
            
            # Other input types (CHOICE, YES_NO, MULTISELECT) - no validation needed
            else:
                self.state.answers[question.id] = user_response
                logger.info(f"Stored answer for {question.id}: {user_response}")

        self.state.current_question_index += 1
        return self._get_next_question(symptom)

    def _handle_followup_response(self, user_response: Any) -> EngineResponse:
        """Handle a response during the follow-up phase."""
        symptom = get_symptom_by_id(self.state.current_symptom_id)
        if not symptom:
            return self._start_next_symptom()

        questions = symptom.follow_up_questions
        if self.state.current_question_index < len(questions):
            question = questions[self.state.current_question_index]
            
            # Validate NUMBER inputs
            if question.input_type == InputType.NUMBER:
                is_valid, validated_value, error_msg = self._validate_numeric_input(question, user_response)
                if not is_valid:
                    return EngineResponse(
                        message=f"{error_msg}\n\n{question.text}",
                        message_type='number',
                        options=[],
                        sender='ruby',
                        avatar='⚠️',
                        state=self.state
                    )
                self.state.answers[question.id] = validated_value
                logger.info(f"Stored validated {question.id}: {validated_value}")
            
            # Validate TEXT inputs
            elif question.input_type == InputType.TEXT:
                is_valid, error_msg = validate_text_input(str(user_response))
                if not is_valid:
                    return EngineResponse(
                        message=f"{error_msg}\n\n{question.text}",
                        message_type='text',
                        options=[],
                        sender='ruby',
                        avatar='⚠️',
                        state=self.state
                    )
                self.state.answers[question.id] = user_response
                logger.info(f"Stored follow-up answer for {question.id}: {user_response}")
            
            # Other input types - no validation needed
            else:
                self.state.answers[question.id] = user_response
                logger.info(f"Stored follow-up answer for {question.id}: {user_response}")

        self.state.current_question_index += 1
        return self._get_next_question(symptom)

    def _evaluate_current_phase(self, symptom: SymptomDef) -> EngineResponse:
        """Evaluate the current phase and determine next steps."""
        if self.state.is_follow_up:
            # Evaluate follow-up
            if symptom.evaluate_follow_up:
                result = symptom.evaluate_follow_up(self.state.answers)
                return self._handle_logic_result(result, symptom)
            else:
                return self._complete_symptom(symptom)
        else:
            # Evaluate screening
            result = symptom.evaluate_screening(self.state.answers)
            return self._handle_logic_result(result, symptom)

    def _handle_logic_result(self, result: LogicResult, symptom: SymptomDef) -> EngineResponse:
        """Handle the result of a logic evaluation."""
        # Record triage result if any
        if result.triage_level != TriageLevel.NONE:
            self._record_triage_result(symptom.id, symptom.name, result)

        if result.action == 'stop':
            # Check for emergency
            if result.triage_level == TriageLevel.CALL_911:
                self.state.phase = ConversationPhase.EMERGENCY
                return self._generate_emergency_response(result.triage_message)
            
            return self._complete_symptom(symptom, result.triage_message)

        elif result.action == 'branch':
            # Add branched symptom to stack
            if result.branch_to_symptom_id and result.branch_to_symptom_id not in self.state.completed_symptoms:
                self.state.branch_stack.insert(0, result.branch_to_symptom_id)
            
            return self._complete_symptom(symptom)

        elif result.action == 'continue':
            # Check if there are follow-up questions
            if not self.state.is_follow_up and symptom.follow_up_questions:
                self.state.is_follow_up = True
                self.state.current_question_index = 0
                self.state.phase = ConversationPhase.FOLLOW_UP
                return self._get_next_question(symptom)
            else:
                return self._complete_symptom(symptom)

        return self._complete_symptom(symptom)

    def _record_triage_result(self, symptom_id: str, symptom_name: str, result: LogicResult):
        """Record a triage result."""
        self.state.triage_results.append({
            'symptom_id': symptom_id,
            'symptom_name': symptom_name,
            'level': result.triage_level.value,
            'message': result.triage_message,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Update highest triage level
        levels = [TriageLevel.NONE, TriageLevel.NOTIFY_CARE_TEAM, TriageLevel.URGENT, TriageLevel.CALL_911]
        try:
            if levels.index(result.triage_level) > levels.index(self.state.highest_triage_level):
                self.state.highest_triage_level = result.triage_level
        except ValueError:
            pass

    def _complete_symptom(self, symptom: SymptomDef, message: Optional[str] = None) -> EngineResponse:
        """Complete processing of a symptom and move to the next."""
        self.state.completed_symptoms.append(symptom.id)
        
        # Count remaining
        remaining = len([s for s in self.state.selected_symptoms 
                        if s not in self.state.completed_symptoms])
        
        if message:
            logger.info(f"Symptom {symptom.name} completed with message: {message}")
        
        if remaining > 0:
            # Show transition message
            transition = f"✅ Got it! I've recorded your **{symptom.name}** responses.\n\n"
            if remaining == 1:
                transition += "One more symptom to go..."
            else:
                transition += f"{remaining} more symptoms to go..."
            
            return self._start_next_symptom(greeting_message=transition)
        
        return self._start_next_symptom()

    # =========================================================================
    # PHASE 5: EMERGENCY RESPONSE
    # =========================================================================
    def _generate_emergency_response(self, message: Optional[str] = None) -> EngineResponse:
        """Generate emergency response for 911 situations."""
        emergency_text = (
            "🚨 **EMERGENCY - IMMEDIATE ACTION REQUIRED** 🚨\n\n"
            f"{message or 'Based on your responses, you need immediate medical attention.'}\n\n"
            "---\n\n"
            "**📞 Please call 911 immediately**\n"
            "or go to your nearest emergency room.\n\n"
            "If you cannot call yourself, please ask someone nearby to help you.\n\n"
            "---\n\n"
            "*Your care team has also been notified of this emergency.*"
        )
        
        self._add_to_chat_history('ruby', emergency_text)
        
        return EngineResponse(
            message=emergency_text,
            message_type='emergency',
            triage_level=TriageLevel.CALL_911,
            triage_message=message,
            options=[
                {'label': '📞 Call 911', 'value': 'call_911', 'style': 'emergency', 'action': 'tel:911'},
                {'label': '📱 Call Care Team', 'value': 'call_care_team', 'style': 'warning', 'action': 'call_care_team'},
                {'label': 'I Understand', 'value': 'acknowledge', 'style': 'secondary'}
            ],
            is_complete=True,
            sender='ruby',
            state=self.state
        )

    def _handle_emergency_action(self, user_response: Any) -> EngineResponse:
        """Handle user action on emergency screen."""
        if user_response == 'acknowledge':
            # User acknowledged the emergency - complete the session
            self.state.phase = ConversationPhase.COMPLETED
            return EngineResponse(
                message="✅ **Acknowledged**\n\n"
                        "Your care team has been notified of this emergency.\n\n"
                        "**Please seek immediate medical attention.**\n\n"
                        "If your condition worsens, call 911 immediately.",
                message_type='text',
                is_complete=True,
                triage_level=TriageLevel.CALL_911,
                sender='system',
                state=self.state
            )
        elif user_response == 'call_911':
            # User clicked Call 911 - confirm and complete
            self.state.phase = ConversationPhase.COMPLETED
            return EngineResponse(
                message="📞 **Calling 911...**\n\n"
                        "Stay on the line and follow their instructions.\n\n"
                        "Your care team has also been notified.",
                message_type='text',
                is_complete=True,
                triage_level=TriageLevel.CALL_911,
                sender='system',
                state=self.state
            )
        elif user_response == 'call_care_team':
            # User wants to call care team
            self.state.phase = ConversationPhase.COMPLETED
            return EngineResponse(
                message="📱 **Contacting Care Team...**\n\n"
                        "Your care team has been notified of this emergency.\n\n"
                        "They will contact you shortly. If your condition worsens before they call, "
                        "please call 911 immediately.",
                message_type='text',
                options=[
                    {'label': '📞 Call Care Team Now', 'value': 'dial_care_team', 'style': 'primary', 'action': 'tel:care_team'},
                ],
                is_complete=True,
                triage_level=TriageLevel.CALL_911,
                sender='system',
                state=self.state
            )
        else:
            # Re-show emergency for any other response
            return self._generate_emergency_response()

    def _handle_completed_action(self, user_response: Any) -> EngineResponse:
        """Handle actions after session is completed."""
        return EngineResponse(
            message="This session has ended. Start a new session to continue symptom checking.",
            message_type='text',
            is_complete=True,
            sender='system',
            state=self.state
        )

    # =========================================================================
    # PHASE 6: SUMMARY
    # =========================================================================
    def _generate_summary(self) -> EngineResponse:
        """Generate the final summary of the symptom check."""
        self.state.phase = ConversationPhase.SUMMARY
        
        # Build summary data
        summary_data = {
            'session_start': self.state.session_start,
            'session_end': datetime.utcnow().isoformat(),
            'symptoms_assessed': [],
            'triage_results': self.state.triage_results,
            'highest_level': self.state.highest_triage_level.value,
            'chat_history': self.state.chat_history
        }
        
        # Get symptom details
        for symptom_id in self.state.completed_symptoms:
            symptom = get_symptom_by_id(symptom_id)
            if symptom:
                summary_data['symptoms_assessed'].append({
                    'id': symptom_id,
                    'name': symptom.name
                })

        # Build concise summary (2-3 sentences as requested)
        symptoms_list = ", ".join([s['name'] for s in summary_data['symptoms_assessed']])
        
        if self.state.highest_triage_level == TriageLevel.CALL_911:
            return self._generate_emergency_response()
        
        elif self.state.highest_triage_level in [TriageLevel.NOTIFY_CARE_TEAM, TriageLevel.URGENT]:
            alerts = [r for r in self.state.triage_results 
                     if r['level'] in ['notify_care_team', 'urgent']]
            
            # Generate concise 2-3 sentence summary
            concise_summary = f"You reported {symptoms_list}. "
            if alerts:
                alert_names = [r['symptom_name'] for r in alerts]
                concise_summary += f"Your care team has been notified about: {', '.join(alert_names)}. "
            concise_summary += "They will follow up with you soon."
            
            summary_message = (
                "📋 **Assessment Complete**\n\n"
                f"**Summary:** {concise_summary}\n\n"
                "---\n\n"
                "⚠️ **Care team notified** - they will review and follow up.\n\n"
                "📔 **Saved to your diary** automatically for your records.\n\n"
                "💬 **Want to add anything?** You can add personal notes.\n\n"
                "What would you like to do?"
            )
            triage_level = TriageLevel.NOTIFY_CARE_TEAM
        
        else:
            # Generate concise 2-3 sentence summary for no concerns
            concise_summary = f"You reported {symptoms_list}. "
            concise_summary += "No urgent concerns were identified. "
            concise_summary += "Continue monitoring and reach out if symptoms change."
            
            summary_message = (
                "📋 **Assessment Complete**\n\n"
                f"**Summary:** {concise_summary}\n\n"
                "---\n\n"
                "✅ **Good news!** No urgent concerns identified.\n\n"
                "📔 **Saved to your diary** automatically for your records.\n\n"
                "💬 **Want to add anything?** You can add personal notes.\n\n"
                "What would you like to do?"
            )
            triage_level = TriageLevel.NONE
        
        # Store the concise summary for later use
        summary_data['concise_summary'] = concise_summary

        self._add_to_chat_history('ruby', summary_message)

        return EngineResponse(
            message=summary_message,
            message_type='summary',
            options=SUMMARY_ACTIONS,
            triage_level=triage_level,
            is_complete=True,  # Mark as complete so bulleted_summary is saved
            summary_data=summary_data,
            sender='ruby',
            avatar='📋',
            state=self.state
        )

    def _handle_summary_action(self, user_response: Any) -> EngineResponse:
        """Handle user's action selection on the summary screen."""
        if user_response == 'add_notes':
            # Prompt user for personal notes
            self.state.phase = ConversationPhase.ADDING_NOTES
            return EngineResponse(
                message="✏️ **Add Personal Notes**\n\n"
                        "Type any additional information you'd like to include with this symptom check:\n\n"
                        "• How you're feeling overall\n"
                        "• Any other symptoms you noticed\n"
                        "• Questions for your doctor\n"
                        "• Notes about medications or treatments",
                message_type='text_input',
                options=[
                    {'label': '💾 Save Notes & Continue', 'value': 'submit_notes', 'style': 'primary'},
                    {'label': '← Back to Summary', 'value': 'back_to_summary', 'style': 'secondary'}
                ],
                sender='ruby',
                state=self.state
            )
        
        elif user_response == 'download':
            # Return summary data for download
            return EngineResponse(
                message="📥 Your summary is ready for download.",
                message_type='download',
                summary_data=self._get_download_summary(),
                state=self.state
            )
        
        elif user_response in ['save_diary', 'view_diary']:
            # Diary is auto-saved, this just navigates to view it
            return EngineResponse(
                message="📔 **Your symptom check is in your diary.**\n\n"
                        "It was automatically saved when the assessment completed.\n\n"
                        "You can view and add notes to it anytime in **My Diary**.",
                message_type='text',
                options=[
                    {'label': '📔 Go to Diary', 'value': 'go_diary', 'action': 'navigate:diary'},
                    {'label': '🔄 Report Another Symptom', 'value': 'report_another'},
                    {'label': '✅ Done', 'value': 'done'}
                ],
                is_complete=True,
                sender='ruby',
                state=self.state
            )
        
        elif user_response == 'report_another':
            # Reset and start again from emergency check
            self.state.selected_symptoms = []
            self.state.completed_symptoms = []
            self.state.triage_results = []
            self.state.answers = {}
            self.state.highest_triage_level = TriageLevel.NONE
            self.state.phase = ConversationPhase.EMERGENCY_CHECK
            return self._show_emergency_check()
        
        elif user_response == 'done':
            self.state.phase = ConversationPhase.COMPLETED
            return EngineResponse(
                message="Thank you for checking in! Take care. 💙",
                message_type='text',
                is_complete=True,
                sender='ruby',
                state=self.state
            )
        
        # Default: show summary again
        return self._generate_summary()

    def _handle_notes_input(self, user_response: Any) -> EngineResponse:
        """Handle the patient's personal notes input."""
        if user_response == 'back_to_summary':
            # Go back to summary without saving notes
            self.state.phase = ConversationPhase.SUMMARY
            return self._generate_summary()
        
        # Check if it's a "submit notes" action with notes data
        if isinstance(user_response, dict) and 'notes' in user_response:
            notes_text = user_response.get('notes', '').strip()
        elif isinstance(user_response, str) and user_response not in ['submit_notes', 'back_to_summary']:
            # The user typed their notes directly
            notes_text = user_response.strip()
        else:
            notes_text = ''
        
        if notes_text:
            # Save the notes to state
            self.state.personal_notes = notes_text
            
            # Show confirmation and return to summary options
            self.state.phase = ConversationPhase.SUMMARY
            return EngineResponse(
                message=f"✅ **Notes saved!**\n\n"
                        f"Your notes:\n> {notes_text}\n\n"
                        "---\n\n"
                        "What would you like to do next?",
                message_type='text',
                options=[
                    {"label": "📥 Download Summary", "value": "download", "icon": "download"},
                    {"label": "📔 Save to My Diary", "value": "save_diary", "icon": "diary"},
                    {"label": "✏️ Edit Notes", "value": "add_notes", "icon": "edit"},
                    {"label": "✅ Done for Today", "value": "done", "icon": "check"},
                ],
                sender='ruby',
                state=self.state
            )
        else:
            # No notes provided, return to summary
            self.state.phase = ConversationPhase.SUMMARY
            return self._generate_summary()

    def _get_download_summary(self) -> Dict[str, Any]:
        """Generate summary data for PDF/download."""
        symptoms_assessed = []
        for symptom_id in self.state.completed_symptoms:
            symptom = get_symptom_by_id(symptom_id)
            if symptom:
                symptoms_assessed.append({
                    'name': symptom.name,
                    'id': symptom_id
                })
        
        return {
            'title': 'Symptom Check Summary',
            'date': datetime.utcnow().strftime('%B %d, %Y at %I:%M %p'),
            'session_id': self.state.session_start,
            'symptoms': symptoms_assessed,
            'triage_level': self.state.highest_triage_level.value,
            'triage_results': self.state.triage_results,
            'personal_notes': self.state.personal_notes,
            'disclaimer': (
                "This symptom check was conducted using Oncolife's automated triage system. "
                "It does not replace professional medical advice. Always follow your care team's instructions."
            )
        }

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    def get_state(self) -> ConversationState:
        """Get the current conversation state."""
        return self.state

    def set_state(self, state: ConversationState):
        """Set the conversation state."""
        self.state = state

    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Get the chat history for WhatsApp-style display."""
        return self.state.chat_history

    @staticmethod
    def get_available_symptoms() -> Dict[str, Any]:
        """Get grouped symptoms for selection."""
        return {
            'emergency': EMERGENCY_SYMPTOMS,
            'groups': SYMPTOM_GROUPS
        }

    @staticmethod
    def get_symptom_groups() -> Dict[str, Any]:
        """Get symptom groups with full details."""
        return SYMPTOM_GROUPS
