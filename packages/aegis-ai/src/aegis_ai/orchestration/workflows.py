"""Pre-built Clinical Workflows"""
from dataclasses import dataclass
from enum import Enum
from typing import Any
import structlog

from aegis_ai.orchestration.graph import AgentGraph, AgentState, NodeType

logger = structlog.get_logger(__name__)


class WorkflowType(str, Enum):
    PATIENT_SUMMARY = "patient_summary"
    CARE_GAP_REVIEW = "care_gap_review"
    DENIAL_APPEAL = "denial_appeal"
    SYMPTOM_TRIAGE = "symptom_triage"
    LAB_INTERPRETATION = "lab_interpretation"


@dataclass
class WorkflowResult:
    workflow_type: WorkflowType
    success: bool
    output: dict[str, Any]
    state: AgentState
    steps_executed: int


class ClinicalWorkflow:
    """Pre-built clinical workflows using agent graphs."""
    
    @staticmethod
    def create_patient_summary_workflow() -> AgentGraph:
        """Workflow to generate patient 360 summary."""
        graph = AgentGraph("patient_summary")
        
        async def fetch_demographics(state: AgentState) -> AgentState:
            state.set_context("demographics", {"fetched": True})
            return state
        
        async def fetch_conditions(state: AgentState) -> AgentState:
            state.set_context("conditions", {"fetched": True})
            return state
        
        async def fetch_medications(state: AgentState) -> AgentState:
            state.set_context("medications", {"fetched": True})
            return state
        
        async def generate_summary(state: AgentState) -> AgentState:
            state.add_message("assistant", "Patient summary generated")
            state.set_context("summary", "Complete clinical summary")
            return state
        
        graph.add_node("fetch_demographics", NodeType.TOOL, fetch_demographics)
        graph.add_node("fetch_conditions", NodeType.TOOL, fetch_conditions)
        graph.add_node("fetch_medications", NodeType.TOOL, fetch_medications)
        graph.add_node("generate_summary", NodeType.AGENT, generate_summary)
        
        graph.add_edge("start", "fetch_demographics")
        graph.add_edge("fetch_demographics", "fetch_conditions")
        graph.add_edge("fetch_conditions", "fetch_medications")
        graph.add_edge("fetch_medications", "generate_summary")
        graph.add_edge("generate_summary", "end")
        
        return graph.compile()
    
    @staticmethod
    def create_denial_appeal_workflow() -> AgentGraph:
        """Workflow for claims denial appeal."""
        graph = AgentGraph("denial_appeal")
        
        async def fetch_claim(state: AgentState) -> AgentState:
            state.set_context("claim", {"claim_id": state.context.get("claim_id")})
            return state
        
        async def analyze_denial(state: AgentState) -> AgentState:
            state.set_context("denial_reason", "Medical necessity")
            return state
        
        async def gather_evidence(state: AgentState) -> AgentState:
            state.set_context("evidence", ["Clinical notes", "Lab results"])
            return state
        
        async def draft_appeal(state: AgentState) -> AgentState:
            state.add_message("assistant", "Appeal letter drafted")
            state.set_context("appeal_draft", "Dear Payer, we are appealing...")
            return state
        
        async def human_review(state: AgentState) -> AgentState:
            state.set_context("reviewed", True)
            return state
        
        def route_confidence(state: AgentState) -> str:
            confidence = state.context.get("confidence", 0.5)
            return "human_review" if confidence < 0.8 else "finalize"
        
        async def finalize(state: AgentState) -> AgentState:
            state.add_message("assistant", "Appeal finalized and ready for submission")
            return state
        
        graph.add_node("fetch_claim", NodeType.TOOL, fetch_claim)
        graph.add_node("analyze_denial", NodeType.AGENT, analyze_denial)
        graph.add_node("gather_evidence", NodeType.TOOL, gather_evidence)
        graph.add_node("draft_appeal", NodeType.AGENT, draft_appeal)
        graph.add_node("router", NodeType.ROUTER)
        graph.add_node("human_review", NodeType.HUMAN, human_review)
        graph.add_node("finalize", NodeType.AGENT, finalize)
        
        graph.add_edge("start", "fetch_claim")
        graph.add_edge("fetch_claim", "analyze_denial")
        graph.add_edge("analyze_denial", "gather_evidence")
        graph.add_edge("gather_evidence", "draft_appeal")
        graph.add_edge("draft_appeal", "router")
        graph.add_conditional_edge("router", route_confidence)
        graph.add_edge("human_review", "finalize")
        graph.add_edge("finalize", "end")
        
        return graph.compile()
    
    @staticmethod
    def create_symptom_triage_workflow() -> AgentGraph:
        """Workflow for patient symptom triage."""
        graph = AgentGraph("symptom_triage")
        
        async def collect_symptoms(state: AgentState) -> AgentState:
            state.set_context("symptoms_collected", True)
            return state
        
        async def assess_urgency(state: AgentState) -> AgentState:
            # Mock urgency assessment
            state.set_context("urgency", "moderate")
            return state
        
        def route_urgency(state: AgentState) -> str:
            urgency = state.context.get("urgency", "low")
            if urgency == "emergency":
                return "emergency_protocol"
            elif urgency == "high":
                return "urgent_care"
            return "routine_care"
        
        async def emergency_protocol(state: AgentState) -> AgentState:
            state.add_message("assistant", "EMERGENCY: Call 911 immediately")
            return state
        
        async def urgent_care(state: AgentState) -> AgentState:
            state.add_message("assistant", "Schedule urgent appointment within 24 hours")
            return state
        
        async def routine_care(state: AgentState) -> AgentState:
            state.add_message("assistant", "Schedule routine follow-up")
            return state
        
        graph.add_node("collect_symptoms", NodeType.AGENT, collect_symptoms)
        graph.add_node("assess_urgency", NodeType.AGENT, assess_urgency)
        graph.add_node("router", NodeType.ROUTER)
        graph.add_node("emergency_protocol", NodeType.AGENT, emergency_protocol)
        graph.add_node("urgent_care", NodeType.AGENT, urgent_care)
        graph.add_node("routine_care", NodeType.AGENT, routine_care)
        
        graph.add_edge("start", "collect_symptoms")
        graph.add_edge("collect_symptoms", "assess_urgency")
        graph.add_edge("assess_urgency", "router")
        graph.add_conditional_edge("router", route_urgency)
        graph.add_edge("emergency_protocol", "end")
        graph.add_edge("urgent_care", "end")
        graph.add_edge("routine_care", "end")
        
        return graph.compile()
    
    @classmethod
    async def run_workflow(cls, workflow_type: WorkflowType, initial_context: dict | None = None) -> WorkflowResult:
        """Run a pre-built workflow."""
        workflows = {
            WorkflowType.PATIENT_SUMMARY: cls.create_patient_summary_workflow,
            WorkflowType.DENIAL_APPEAL: cls.create_denial_appeal_workflow,
            WorkflowType.SYMPTOM_TRIAGE: cls.create_symptom_triage_workflow,
        }
        
        factory = workflows.get(workflow_type)
        if not factory:
            raise ValueError(f"Unknown workflow: {workflow_type}")
        
        graph = factory()
        state = AgentState(context=initial_context or {})
        
        result_state = await graph.run(state)
        
        return WorkflowResult(
            workflow_type=workflow_type,
            success=len(result_state.errors) == 0,
            output=result_state.context,
            state=result_state,
            steps_executed=len(result_state.history)
        )
