"""
Symptom Checker Service.
Provides the main interface for the symptom checker conversation flow.
Replaces the LLM-based chat service with a rule-based approach.

Integrates with Education Service to deliver education after session completion.
"""
from typing import Dict, Any, List, Tuple, Optional, AsyncGenerator
from uuid import UUID
from datetime import datetime, time
from sqlalchemy.orm import Session
import pytz
import json
import logging

from .symptom_checker import SymptomCheckerEngine, TriageLevel
from .symptom_checker.symptom_engine import ConversationState, EngineResponse
from .models import (
    WebSocketMessageIn, WebSocketMessageOut,
    ConnectionEstablished, Message
)
from db.patient_models import Conversations as ChatModel, Messages as MessageModel

logger = logging.getLogger(__name__)


# Diary auto-populate helper
async def _trigger_diary_auto_populate(
    db: Session,
    chat: ChatModel,
    state: ConversationState,
    triage_level: TriageLevel,
) -> None:
    """
    Auto-populate patient diary with symptom session summary.
    
    Creates a diary entry when symptom checker completes, allowing
    patients to reference their check-in history.
    """
    try:
        from services.diary_service import DiaryService
        
        diary_service = DiaryService(db)
        
        # Build symptoms list
        symptoms = []
        for result in state.triage_results:
            symptoms.append({
                "code": result.get('symptom_id', 'unknown'),
                "name": result.get('symptom_id', 'Unknown').replace('-', ' ').title(),
                "severity": result.get('severity', 'mild'),
            })
        
        # Map triage level to string
        triage_str = "none"
        if triage_level == TriageLevel.CALL_911:
            triage_str = "call_911"
        elif triage_level in [TriageLevel.URGENT, TriageLevel.NOTIFY_CARE_TEAM]:
            triage_str = "notify_care_team"
        
        # Create diary entry
        diary_service.create_from_symptom_session(
            patient_uuid=chat.patient_uuid,
            conversation_uuid=chat.uuid,
            symptoms=symptoms,
            triage_level=triage_str,
            overall_feeling=getattr(chat, 'overall_feeling', None),
            summary_text=getattr(chat, 'bulleted_summary', None),
        )
        
        logger.info(f"Diary entry auto-populated for session: {chat.uuid}")
        
    except ImportError:
        logger.warning("Diary service not available - skipping auto-populate")
    except Exception as e:
        logger.error(f"Diary auto-populate failed: {e}")


# Education integration helper
async def _trigger_education_delivery(
    db: Session,
    chat: ChatModel,
    state: ConversationState,
    triage_level: TriageLevel,
) -> Optional[Dict[str, Any]]:
    """
    Trigger education delivery after symptom checker completion.
    
    This is called when the rule engine marks the conversation as complete.
    Returns education payload or None if education service is not available.
    """
    try:
        from services.education_service import EducationService
        from db.models.education import SymptomSession
        
        education_service = EducationService(db)
        
        # Create a symptom session for tracking
        session = education_service.create_symptom_session(
            patient_id=chat.patient_uuid,
            conversation_uuid=chat.uuid,
        )
        
        # Build symptom codes and severity levels from triage results
        symptom_codes = state.selected_symptoms or []
        severity_levels = {}
        
        for result in state.triage_results:
            symptom_id = result.get('symptom_id')
            severity = result.get('severity', 'mild')
            if symptom_id:
                severity_levels[symptom_id] = severity
                
                # Record rule evaluation for audit
                education_service.record_rule_evaluation(
                    session_id=session.id,
                    symptom_code=symptom_id,
                    rule_id=result.get('rule_id', 'UNKNOWN'),
                    condition_met=True,
                    severity=severity,
                    escalation=result.get('escalation', False),
                    triage_message=result.get('message', ''),
                )
        
        # Determine if escalation occurred
        escalation = triage_level in [TriageLevel.CALL_911, TriageLevel.URGENT]
        
        # Deliver education content
        education_payload = await education_service.deliver_post_session_education(
            session_id=session.id,
            symptom_codes=symptom_codes,
            severity_levels=severity_levels,
            escalation=escalation,
        )
        
        # Generate patient summary
        symptoms_for_summary = [
            {
                "code": code,
                "name": code.replace("-", " ").title(),
                "severity": severity_levels.get(code, "mild"),
            }
            for code in symptom_codes
        ]
        
        education_service.generate_patient_summary(
            session_id=session.id,
            patient_id=chat.patient_uuid,
            symptoms=symptoms_for_summary,
            medications_tried=[],  # Will be populated from screening questions
            escalation=escalation,
        )
        
        logger.info(f"Education delivered for session: {session.id}")
        return education_payload
        
    except ImportError:
        logger.warning("Education service not available - skipping education delivery")
        return None
    except Exception as e:
        logger.error(f"Education delivery failed: {e}")
        return None


class SymptomCheckerService:
    """
    Service for managing symptom checker conversations.
    Uses a rule-based engine instead of LLM.
    """

    def __init__(self, db: Session):
        self.db = db
        self.engine = None

    def create_chat(self, patient_uuid: UUID, commit: bool = True) -> Tuple[ChatModel, Dict[str, Any]]:
        """
        Creates a new symptom checker chat session.
        """
        # Create the conversation record
        new_chat = ChatModel(
            patient_uuid=patient_uuid,
            conversation_state="symptom_selection",
            symptom_list=[]
        )
        self.db.add(new_chat)
        
        if commit:
            self.db.commit()
            self.db.refresh(new_chat)

        # Initialize the engine and get the greeting
        engine = SymptomCheckerEngine()
        response = engine.start_conversation()

        # Store engine state in chat metadata
        new_chat.engine_state = response.state.to_dict() if response.state else {}
        new_chat.conversation_state = "disclaimer"  # New initial phase
        self.db.commit()

        initial_message = {
            "text": response.message,
            "type": self._map_message_type(response.message_type),
            "frontend_type": response.message_type,
            "options": [opt['label'] for opt in response.options] if response.options else [],
            "options_data": response.options,
            "symptom_groups": response.symptom_groups,  # For grouped selection
            "summary_data": response.summary_data,  # For summary screen
            "sender": response.sender,  # ruby or system
        }

        return new_chat, initial_message

    def delete_chat(self, chat_uuid: UUID, patient_uuid: UUID):
        """Deletes a chat conversation after verifying ownership."""
        chat = self.db.query(ChatModel).filter(
            ChatModel.uuid == chat_uuid,
            ChatModel.patient_uuid == patient_uuid
        ).first()

        if not chat:
            raise ValueError("Chat not found or access denied.")
        
        self.db.delete(chat)
        self.db.commit()

    def get_or_create_today_session(
        self, 
        patient_uuid: UUID, 
        user_timezone: str = "America/Los_Angeles"
    ) -> Tuple[ChatModel, List[MessageModel], bool]:
        """
        Gets the most recent chat for today, or creates a new one if none exists.
        """
        # Get today's date in user's timezone
        user_tz = pytz.timezone(user_timezone)
        user_now = datetime.now(user_tz)
        today_start = datetime.combine(user_now.date(), time.min)
        today_end = datetime.combine(user_now.date(), time.max)
        
        # Convert to UTC for database query
        utc_today_start = user_tz.localize(today_start).astimezone(pytz.UTC)
        utc_today_end = user_tz.localize(today_end).astimezone(pytz.UTC)
        
        # Query for today's chat
        today_chat = self.db.query(ChatModel).filter(
            ChatModel.patient_uuid == patient_uuid,
            ChatModel.created_at >= utc_today_start,
            ChatModel.created_at <= utc_today_end
        ).order_by(ChatModel.created_at.desc()).first()
        
        if today_chat:
            messages = self.db.query(MessageModel).filter(
                MessageModel.chat_uuid == today_chat.uuid
            ).order_by(MessageModel.created_at).all()
            return today_chat, messages, False
        else:
            # Create new chat
            new_chat, initial_question = self.create_chat(patient_uuid, commit=True)
            
            # Create the first assistant message
            first_message = MessageModel(
                chat_uuid=new_chat.uuid,
                sender="assistant",
                message_type=initial_question["type"],
                content=initial_question["text"],
                structured_data={
                    "options": initial_question.get("options", []),
                    "options_data": initial_question.get("options_data", []),
                    "frontend_type": initial_question.get("frontend_type", "text")
                }
            )
            
            self.db.add(first_message)
            self.db.commit()
            self.db.refresh(first_message)
            
            return new_chat, [first_message], True

    async def process_message_stream(
        self, 
        chat_uuid: UUID, 
        message: WebSocketMessageIn
    ) -> AsyncGenerator[Any, None]:
        """
        Processes a message using the rule-based symptom checker engine.
        """
        logger.info(f"Processing symptom checker message for chat {chat_uuid}: {message.content}")
        
        chat = self.db.query(ChatModel).filter(ChatModel.uuid == chat_uuid).first()
        if not chat:
            logger.error(f"Chat {chat_uuid} not found")
            return

        # 1. Save the user's message
        user_msg = MessageModel(
            chat_uuid=chat_uuid,
            sender="user",
            message_type=message.message_type,
            content=message.content
        )
        self.db.add(user_msg)
        self.db.commit()
        self.db.refresh(user_msg)
        yield Message.from_orm(user_msg)

        # 2. Load or create the engine with saved state
        engine_state_data = getattr(chat, 'engine_state', None) or {}
        if engine_state_data:
            state = ConversationState.from_dict(engine_state_data)
            engine = SymptomCheckerEngine(state=state)
        else:
            engine = SymptomCheckerEngine()

        # 3. Parse the user's response
        user_response = self._parse_user_response(message)

        # 4. Process the response through the engine
        try:
            engine_response = engine.process_response(user_response)
        except Exception as e:
            logger.error(f"Engine processing error: {e}")
            error_msg = MessageModel(
                chat_uuid=chat_uuid,
                sender="assistant",
                message_type="text",
                content="I'm sorry, I encountered an error. Please try again."
            )
            self.db.add(error_msg)
            self.db.commit()
            self.db.refresh(error_msg)
            yield Message.from_orm(error_msg)
            return

        # 5. Save the engine state
        if engine_response.state:
            chat.engine_state = engine_response.state.to_dict()
            
            # Update chat fields based on state
            chat.symptom_list = engine_response.state.selected_symptoms
            
            if engine_response.is_complete:
                if engine_response.triage_level == TriageLevel.CALL_911:
                    chat.conversation_state = "EMERGENCY"
                else:
                    chat.conversation_state = "COMPLETED"
            else:
                chat.conversation_state = engine_response.state.phase.value
        
        self.db.commit()

        # 6. Create and save the assistant message
        assistant_msg = MessageModel(
            chat_uuid=chat_uuid,
            sender="assistant",
            message_type=self._map_message_type(engine_response.message_type),
            content=engine_response.message,
            structured_data={
                "options": [opt['label'] for opt in engine_response.options] if engine_response.options else None,
                "options_data": engine_response.options,
                "frontend_type": engine_response.message_type,
                "triage_level": engine_response.triage_level.value if engine_response.triage_level else None,
                "is_complete": engine_response.is_complete,
                # New fields for updated UX
                "symptom_groups": engine_response.symptom_groups,
                "summary_data": engine_response.summary_data,
                "sender": engine_response.sender,
                "avatar": engine_response.avatar,
                "timestamp": engine_response.timestamp,
            }
        )
        self.db.add(assistant_msg)
        self.db.commit()
        self.db.refresh(assistant_msg)

        # Convert for frontend
        frontend_message = Message.from_orm(assistant_msg)
        frontend_message.message_type = self._map_frontend_type(engine_response.message_type)
        
        yield frontend_message
        
        # 7. Trigger education delivery if conversation is complete
        if engine_response.is_complete and engine_response.state:
            education_payload = await _trigger_education_delivery(
                db=self.db,
                chat=chat,
                state=engine_response.state,
                triage_level=engine_response.triage_level or TriageLevel.NONE,
            )
            
            if education_payload:
                # Create education message
                education_msg = MessageModel(
                    chat_uuid=chat_uuid,
                    sender="assistant",
                    message_type="education",
                    content="Here is some helpful information about your symptoms:",
                    structured_data={
                        "frontend_type": "education",
                        "education_blocks": education_payload.get("educationBlocks", []),
                        "disclaimer": education_payload.get("disclaimer", {}),
                        "session_id": education_payload.get("session_id"),
                    }
                )
                self.db.add(education_msg)
                self.db.commit()
                self.db.refresh(education_msg)
                
                education_frontend = Message.from_orm(education_msg)
                education_frontend.message_type = "education"
                yield education_frontend
            
            # 8. Auto-populate diary entry from session
            await _trigger_diary_auto_populate(
                db=self.db,
                chat=chat,
                state=engine_response.state,
                triage_level=engine_response.triage_level or TriageLevel.NONE,
            )

    def _parse_user_response(self, message: WebSocketMessageIn) -> Any:
        """Parse the user's response based on message type."""
        content = message.content
        msg_type = message.message_type

        # Handle disclaimer acceptance
        if msg_type == 'disclaimer_response':
            return 'accept' if content.lower() in ['accept', 'i understand', 'ok'] else content

        # Handle summary action buttons
        if msg_type == 'summary_action':
            return content  # download, save_diary, report_another, done

        # Handle emergency check response
        if msg_type == 'emergency_check_response':
            if message.structured_data and 'selected_values' in message.structured_data:
                return message.structured_data['selected_values']
            if content.lower() in ['none', 'no emergency']:
                return 'none'
            return content

        # Handle grouped symptom selection
        if msg_type == 'symptom_select_response':
            if message.structured_data:
                if 'selected_symptoms' in message.structured_data:
                    return {'symptoms': message.structured_data['selected_symptoms']}
                if 'selected_values' in message.structured_data:
                    return {'symptoms': message.structured_data['selected_values']}
            # Handle comma-separated symptom IDs
            if content:
                symptoms = [s.strip() for s in content.split(',') if s.strip()]
                return {'symptoms': symptoms}
            return 'none'

        # Handle yes/no responses
        if msg_type == 'button_response':
            if content.lower() in ['yes', 'true']:
                return True
            elif content.lower() in ['no', 'false']:
                return False
            return content

        # Handle multi-select responses (comma-separated)
        if msg_type == 'multi_select_response':
            # Parse comma-separated values
            values = [v.strip() for v in content.split(',') if v.strip()]
            
            # Try to get the actual values from structured_data
            if message.structured_data and 'selected_values' in message.structured_data:
                return message.structured_data['selected_values']
            
            return values

        # Handle number responses
        try:
            return float(content)
        except (ValueError, TypeError):
            pass

        return content

    def _map_message_type(self, engine_type: str) -> str:
        """Map engine message types to database message types."""
        mapping = {
            'text': 'text',
            'yes_no': 'single_select',
            'choice': 'single_select',
            'multiselect': 'multi_select',
            'number': 'text',
            'symptom_select': 'multi_select',
            'triage_result': 'text',
            # New message types for updated UX flow
            'disclaimer': 'text',
            'emergency_check': 'multi_select',
            'summary': 'text',
            'emergency': 'text',
            'download': 'text',
        }
        return mapping.get(engine_type, 'text')

    def _map_frontend_type(self, engine_type: str) -> str:
        """Map engine message types to frontend message types."""
        mapping = {
            'text': 'text',
            'yes_no': 'single-select',
            'choice': 'single-select',
            'multiselect': 'multi-select',
            'number': 'text',
            'symptom_select': 'symptom-select',
            'triage_result': 'text',
            # New message types for updated UX flow
            'disclaimer': 'disclaimer',
            'emergency_check': 'emergency-check',
            'summary': 'summary',
            'emergency': 'emergency',
            'download': 'download',
        }
        return mapping.get(engine_type, 'text')

    def get_connection_ack(self, chat_uuid: UUID) -> ConnectionEstablished:
        """Returns a connection acknowledgment message."""
        return ConnectionEstablished(
            content="Connection established successfully.",
            chat_state={
                "chat_uuid": str(chat_uuid),
                "status": "connected"
            }
        )



