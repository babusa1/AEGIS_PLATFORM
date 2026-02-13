"""
Voice Agent

Extends BaseAgent for voice-based patient interactions.
Handles voice-specific context, conversation state, and integrates
with UnifiedViewAgent for query resolution.
"""

from typing import Optional, Dict, Any
from datetime import datetime

import structlog
from langgraph.graph import StateGraph, END

from aegis.agents.base import BaseAgent, AgentState
from aegis.agents.tools import AgentTools
from aegis.agents.unified_view import UnifiedViewAgent
from aegis.bedrock.client import LLMClient
from aegis.voice.gateway import VoiceGateway, CallState

logger = structlog.get_logger(__name__)


class VoiceAgent(BaseAgent):
    """
    Voice Agent - Voice-Based Patient Assistant
    
    Handles voice conversations with patients for:
    - Appointment scheduling/rescheduling/cancellation
    - Query resolution (leverages UnifiedViewAgent)
    - Patient instructions and reminders
    - Insurance and claim status inquiries
    
    Features:
    - Voice-specific prompts (concise, natural speech)
    - Conversation state management
    - Multilingual support
    - Integration with existing agents
    """
    
    def __init__(
        self,
        tenant_id: str,
        voice_gateway: VoiceGateway,
        llm_client: LLMClient | None = None,
        language: str = "en-US",
    ):
        """
        Initialize Voice Agent.
        
        Args:
            tenant_id: Tenant ID
            voice_gateway: VoiceGateway instance
            llm_client: Optional LLM client
            language: Language code (en-US, es-ES, etc.)
        """
        self.tenant_id = tenant_id
        self.voice_gateway = voice_gateway
        self.language = language
        
        # Initialize UnifiedViewAgent for query resolution
        self.unified_view_agent = UnifiedViewAgent(tenant_id=tenant_id, llm_client=llm_client)
        
        # Get relevant tools
        self.agent_tools = AgentTools(tenant_id)
        all_tools = self.agent_tools.get_all_tools()
        
        tools = {
            "get_patient": all_tools.get("get_patient"),
            "get_appointments": all_tools.get("get_appointments"),
            "get_claim_status": all_tools.get("get_claim_status"),
            "check_insurance_eligibility": all_tools.get("check_insurance_eligibility"),
        }
        
        # Filter out None tools
        tools = {k: v for k, v in tools.items() if v is not None}
        
        super().__init__(
            name="voice_agent",
            llm_client=llm_client,
            max_iterations=5,  # Voice conversations should be concise
            tools=tools,
        )
        
        # Conversation sessions (in production, use Redis)
        self._conversations: Dict[str, Dict[str, Any]] = {}
    
    def _get_system_prompt(self) -> str:
        return f"""You are ROVA, a friendly and empathetic AI voice assistant for healthcare.

You are speaking with patients over the phone. Your role is to:
1. Help patients schedule, reschedule, or cancel appointments
2. Answer questions about their care, appointments, and claims
3. Provide patient instructions and reminders
4. Check insurance eligibility and claim status

IMPORTANT VOICE GUIDELINES:
- Keep responses SHORT and CONVERSATIONAL (2-3 sentences max)
- Speak naturally, as if talking to a friend
- Use simple language - avoid medical jargon
- Be empathetic and patient
- Confirm understanding before proceeding
- If you need to look up information, say "Let me check that for you"

When scheduling appointments:
- Confirm patient name and date of birth for verification
- Ask for preferred date and time
- Confirm appointment details before booking
- Provide confirmation number

When answering queries:
- Use the patient's data from the Data Moat
- Be specific and accurate
- If you don't know something, say so and offer to connect them to a human

Language: {self.language}
"""
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for voice conversations."""
        
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("understand_intent", self._understand_intent)
        workflow.add_node("route_to_handler", self._route_to_handler)
        workflow.add_node("handle_appointment", self._handle_appointment)
        workflow.add_node("handle_query", self._handle_query)
        workflow.add_node("handle_insurance", self._handle_insurance)
        workflow.add_node("generate_response", self._generate_voice_response)
        
        # Define edges
        workflow.set_entry_point("understand_intent")
        workflow.add_edge("understand_intent", "route_to_handler")
        
        # Conditional routing based on intent
        workflow.add_conditional_edges(
            "route_to_handler",
            self._route_condition,
            {
                "appointment": "handle_appointment",
                "query": "handle_query",
                "insurance": "handle_insurance",
                "other": "generate_response",
            }
        )
        
        workflow.add_edge("handle_appointment", "generate_response")
        workflow.add_edge("handle_query", "generate_response")
        workflow.add_edge("handle_insurance", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow
    
    async def _understand_intent(self, state: AgentState) -> AgentState:
        """Understand user intent from voice input."""
        user_message = state["current_input"]
        
        # Use LLM to classify intent
        intent_prompt = f"""Classify this patient request into one category:

Categories:
- appointment: Scheduling, rescheduling, canceling appointments
- query: Questions about care, medications, test results
- insurance: Insurance eligibility, claim status, coverage questions
- other: Everything else

Request: "{user_message}"

Respond with ONLY the category name."""
        
        intent = await self._call_llm(
            [{"role": "user", "content": intent_prompt}],
            system_prompt="You are an intent classifier. Respond with only the category name.",
        )
        
        intent = intent.strip().lower()
        state["metadata"] = state.get("metadata", {})
        state["metadata"]["intent"] = intent
        
        logger.debug("Intent classified", intent=intent, message=user_message[:50])
        return state
    
    def _route_condition(self, state: AgentState) -> str:
        """Route to appropriate handler based on intent."""
        intent = state.get("metadata", {}).get("intent", "other")
        return intent if intent in ["appointment", "query", "insurance"] else "other"
    
    async def _handle_appointment(self, state: AgentState) -> AgentState:
        """Handle appointment-related requests."""
        user_message = state["current_input"]
        call_state = state.get("call_state")
        patient_id = call_state.patient_id if call_state else None
        
        # Extract appointment details from conversation
        appointment_prompt = f"""Extract appointment details from this conversation:

Patient request: "{user_message}"
Conversation history: {state.get('messages', [])[-3:]}

Extract:
- action: "schedule", "reschedule", "cancel", or "query"
- date: Preferred date (if mentioned)
- time: Preferred time (if mentioned)
- appointment_type: Type of appointment (if mentioned)
- appointment_id: Existing appointment ID (if rescheduling/canceling)

Respond in JSON format."""
        
        details_json = await self._call_llm(
            [{"role": "user", "content": appointment_prompt}],
            system_prompt="Extract appointment details. Respond in valid JSON only.",
        )
        
        # Parse JSON (simplified - would use proper JSON parsing)
        import json
        try:
            details = json.loads(details_json)
        except:
            details = {"action": "schedule"}
        
        state["metadata"]["appointment_details"] = details
        
        # In production, would call scheduling API
        # For now, generate response
        action = details.get("action", "schedule")
        if action == "schedule":
            response = "I'd be happy to help you schedule an appointment. Let me check available times for you."
        elif action == "reschedule":
            response = "I can help you reschedule your appointment. What date and time would work better for you?"
        elif action == "cancel":
            response = "I understand you'd like to cancel. Let me process that cancellation for you."
        else:
            response = "I can help you with your appointment. What would you like to do?"
        
        state["messages"].append({
            "role": "assistant",
            "content": response,
        })
        
        return state
    
    async def _handle_query(self, state: AgentState) -> AgentState:
        """Handle patient queries using UnifiedViewAgent."""
        user_message = state["current_input"]
        call_state = state.get("call_state")
        patient_id = call_state.patient_id if call_state else None
        
        # Use UnifiedViewAgent for query resolution
        if patient_id:
            # Get patient context
            query_result = await self.unified_view_agent.generate_patient_summary(
                patient_id=patient_id,
            )
            
            # Generate voice-friendly response
            voice_prompt = f"""Patient asked: "{user_message}"

Patient context: {query_result.get('answer', '')[:500]}

Generate a SHORT, CONVERSATIONAL response (2-3 sentences max) that:
- Answers their question directly
- Uses simple language
- Sounds natural when spoken aloud

Response:"""
            
            response = await self._call_llm(
                [{"role": "user", "content": voice_prompt}],
                system_prompt="Generate conversational voice responses. Keep it short and natural.",
            )
        else:
            # No patient context - general response
            response = "I'd be happy to help. Could you please provide your name or patient ID so I can look up your information?"
        
        state["messages"].append({
            "role": "assistant",
            "content": response,
        })
        
        return state
    
    async def _handle_insurance(self, state: AgentState) -> AgentState:
        """Handle insurance and claim status inquiries."""
        user_message = state["current_input"]
        call_state = state.get("call_state")
        patient_id = call_state.patient_id if call_state else None
        
        # Check if asking about eligibility or claim status
        if "eligibility" in user_message.lower() or "covered" in user_message.lower():
            response = "Let me check your insurance eligibility for you. This will just take a moment."
        elif "claim" in user_message.lower() or "status" in user_message.lower():
            response = "I can check the status of your claim. Do you have a claim number, or would you like me to look it up?"
        else:
            response = "I can help you with insurance questions. What specifically would you like to know?"
        
        state["messages"].append({
            "role": "assistant",
            "content": response,
        })
        
        return state
    
    async def _generate_voice_response(self, state: AgentState) -> AgentState:
        """Generate final voice-friendly response."""
        # Get last assistant message
        messages = state.get("messages", [])
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        
        if assistant_messages:
            final_response = assistant_messages[-1].get("content", "I'm here to help. How can I assist you today?")
        else:
            final_response = "I'm here to help. How can I assist you today?"
        
        # Ensure response is voice-friendly (short, natural)
        if len(final_response) > 200:
            # Summarize if too long
            summarize_prompt = f"""Make this response shorter and more conversational for voice:

Original: {final_response}

Generate a 2-3 sentence version that sounds natural when spoken."""
            
            final_response = await self._call_llm(
                [{"role": "user", "content": summarize_prompt}],
                system_prompt="Summarize for voice. Keep it conversational and short.",
            )
        
        state["final_answer"] = final_response
        return state
    
    # =========================================================================
    # Conversation Management
    # =========================================================================
    
    async def start_conversation(
        self,
        call_state: CallState,
        initial_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Start a new voice conversation.
        
        Args:
            call_state: Call state from VoiceGateway
            initial_message: Optional initial message
            
        Returns:
            Conversation session data
        """
        session_id = f"voice-{call_state.call_id}"
        
        conversation = {
            "session_id": session_id,
            "call_id": call_state.call_id,
            "patient_id": call_state.patient_id,
            "language": self.language,
            "messages": [],
            "started_at": datetime.utcnow(),
        }
        
        self._conversations[session_id] = conversation
        
        # Initial greeting
        greeting = self._get_greeting()
        
        logger.info("Voice conversation started", session_id=session_id, call_id=call_state.call_id)
        
        return {
            "session_id": session_id,
            "greeting": greeting,
            "conversation": conversation,
        }
    
    async def process_message(
        self,
        session_id: str,
        user_message: str,
        call_state: CallState,
    ) -> Dict[str, Any]:
        """
        Process a user message in voice conversation.
        
        Args:
            session_id: Conversation session ID
            user_message: Transcribed user speech
            call_state: Current call state
            
        Returns:
            Response data with text and audio
        """
        conversation = self._conversations.get(session_id)
        if not conversation:
            conversation = await self.start_conversation(call_state)
            session_id = conversation["session_id"]
            conversation = conversation["conversation"]
        
        # Add user message
        conversation["messages"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Create agent state
        initial_state: AgentState = {
            "messages": conversation["messages"],
            "current_input": user_message,
            "tenant_id": self.tenant_id,
            "user_id": call_state.patient_id,
            "tool_calls": [],
            "tool_results": [],
            "reasoning": [],
            "plan": [],
            "final_answer": None,
            "confidence": 0.0,
            "iteration": 0,
            "max_iterations": self.max_iterations,
            "error": None,
            "call_state": call_state,
            "metadata": {},
        }
        
        # Run agent
        try:
            final_state = await self.compiled_graph.ainvoke(initial_state)
            response_text = final_state.get("final_answer", "I'm here to help. How can I assist you?")
        except Exception as e:
            logger.error("Voice agent execution failed", error=str(e), session_id=session_id)
            response_text = "I apologize, I'm having trouble processing that. Could you please repeat?"
        
        # Add assistant response
        conversation["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Generate audio (TTS)
        audio_data = await self.voice_gateway.text_to_speech(
            text=response_text,
            language=self.language,
        )
        
        # Update call state
        self.voice_gateway.update_call_state(
            call_state.call_id,
            {
                "session_id": session_id,
                "conversation_history": conversation["messages"],
            }
        )
        
        return {
            "session_id": session_id,
            "response_text": response_text,
            "audio_data": audio_data,
            "conversation": conversation,
        }
    
    def _get_greeting(self) -> str:
        """Get language-appropriate greeting."""
        greetings = {
            "en-US": "Hello! This is ROVA, your healthcare assistant. How can I help you today?",
            "es-ES": "¡Hola! Soy ROVA, su asistente de salud. ¿Cómo puedo ayudarle hoy?",
            "hi-IN": "नमस्ते! मैं ROVA हूं, आपका स्वास्थ्य सहायक। आज मैं आपकी कैसे मदद कर सकता हूं?",
        }
        return greetings.get(self.language, greetings["en-US"])
