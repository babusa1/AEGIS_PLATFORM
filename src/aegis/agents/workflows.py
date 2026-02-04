"""
LangGraph Multi-Agent Workflows

Proper LangGraph orchestration with:
- Supervisor pattern for agent coordination
- Visual workflow representation
- Execution traces
- n8n-compatible webhooks
"""

from typing import Literal, Annotated, Any
from datetime import datetime
from enum import Enum
import operator
import json

import structlog
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from aegis.bedrock.client import get_llm_client, LLMClient
from aegis.agents.data_tools import DataMoatTools

logger = structlog.get_logger(__name__)


# =============================================================================
# Workflow State
# =============================================================================

class WorkflowStep(BaseModel):
    """A step in the workflow execution."""
    node: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    input_data: dict | None = None
    output_data: dict | None = None
    duration_ms: int = 0
    status: str = "pending"  # pending, running, completed, failed


class WorkflowState(BaseModel):
    """State passed through the LangGraph workflow."""
    # Input
    query: str
    tenant_id: str = "default"
    
    # Routing
    intent: str | None = None
    selected_agent: str | None = None
    
    # Execution trace
    steps: list[WorkflowStep] = Field(default_factory=list)
    current_node: str = "start"
    
    # Agent outputs
    patient_data: dict | None = None
    denial_data: dict | None = None
    triage_data: dict | None = None
    
    # Final output
    result: dict | None = None
    error: str | None = None
    
    class Config:
        arbitrary_types_allowed = True


# For LangGraph TypedDict compatibility
class WorkflowStateDict(dict):
    """TypedDict-compatible state for LangGraph."""
    pass


# =============================================================================
# Supervisor Agent (Routes to Specialized Agents)
# =============================================================================

class HealthcareWorkflow:
    """
    LangGraph Multi-Agent Workflow
    
    Architecture:
    ```
                        ┌─────────────────┐
                        │     START       │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │   SUPERVISOR    │
                        │  (Intent Router)│
                        └────────┬────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
    ┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
    │ PATIENT AGENT │   │ DENIAL AGENT  │   │ TRIAGE AGENT  │
    │ (360 View)    │   │ (Appeals)     │   │ (Monitoring)  │
    └───────┬───────┘   └───────┬───────┘   └───────┬───────┘
            │                    │                    │
            └────────────────────┼────────────────────┘
                                 │
                        ┌────────▼────────┐
                        │   SYNTHESIZER   │
                        │  (Combine Results)
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │      END        │
                        └─────────────────┘
    ```
    """
    
    def __init__(self, pool=None, tenant_id: str = "default"):
        self.pool = pool
        self.tenant_id = tenant_id
        self.data_tools = DataMoatTools(pool, tenant_id) if pool else None
        self.llm = get_llm_client()
        
        # Build the workflow graph
        self.graph = self._build_graph()
        self.compiled = self.graph.compile()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Define the graph with our state
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("patient_agent", self._patient_agent_node)
        workflow.add_node("denial_agent", self._denial_agent_node)
        workflow.add_node("triage_agent", self._triage_agent_node)
        workflow.add_node("synthesizer", self._synthesizer_node)
        
        # Set entry point
        workflow.set_entry_point("supervisor")
        
        # Add conditional routing from supervisor
        workflow.add_conditional_edges(
            "supervisor",
            self._route_to_agent,
            {
                "patient": "patient_agent",
                "denial": "denial_agent",
                "triage": "triage_agent",
                "direct": "synthesizer",
            }
        )
        
        # All agents route to synthesizer
        workflow.add_edge("patient_agent", "synthesizer")
        workflow.add_edge("denial_agent", "synthesizer")
        workflow.add_edge("triage_agent", "synthesizer")
        
        # Synthesizer ends the workflow
        workflow.add_edge("synthesizer", END)
        
        return workflow
    
    def _route_to_agent(self, state: dict) -> str:
        """Route to the appropriate agent based on intent."""
        intent = state.get("intent", "")
        
        if "patient" in intent or "360" in intent:
            return "patient"
        elif "denial" in intent or "appeal" in intent or "claim" in intent:
            return "denial"
        elif "triage" in intent or "alert" in intent or "monitor" in intent:
            return "triage"
        else:
            return "direct"
    
    async def _supervisor_node(self, state: dict) -> dict:
        """
        Supervisor: Analyzes query and determines which agent to call.
        """
        query = state.get("query", "").lower()
        start_time = datetime.utcnow()
        
        # Intent classification
        intent = "general"
        selected_agent = None
        
        # Simple keyword-based classification (in production, use LLM)
        if any(w in query for w in ["patient", "360", "view", "summary", "profile", "review"]):
            intent = "patient_analysis"
            selected_agent = "patient_agent"
        elif any(w in query for w in ["denial", "appeal", "claim", "reject", "revenue"]):
            intent = "denial_management"
            selected_agent = "denial_agent"
        elif any(w in query for w in ["triage", "alert", "critical", "monitor", "urgent", "attention"]):
            intent = "clinical_triage"
            selected_agent = "triage_agent"
        
        # Use LLM for more complex classification
        if intent == "general":
            response = await self.llm.generate(
                prompt=f"""Classify this healthcare query into one category:
                
Query: {query}

Categories:
- patient_analysis: Questions about specific patients, their history, conditions
- denial_management: Questions about claims, denials, appeals, revenue
- clinical_triage: Questions about alerts, monitoring, critical patients
- general: Other questions

Return ONLY the category name.""",
                system_prompt="You are a healthcare query classifier."
            )
            intent = response.strip().lower()
            if "patient" in intent:
                selected_agent = "patient_agent"
            elif "denial" in intent:
                selected_agent = "denial_agent"
            elif "triage" in intent:
                selected_agent = "triage_agent"
        
        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        step = WorkflowStep(
            node="supervisor",
            input_data={"query": query},
            output_data={"intent": intent, "selected_agent": selected_agent},
            duration_ms=duration,
            status="completed"
        )
        
        steps = state.get("steps", [])
        steps.append(step.model_dump())
        
        return {
            **state,
            "intent": intent,
            "selected_agent": selected_agent,
            "current_node": "supervisor",
            "steps": steps,
        }
    
    async def _patient_agent_node(self, state: dict) -> dict:
        """
        Patient Agent: Retrieves and analyzes patient data from Data Moat.
        """
        start_time = datetime.utcnow()
        query = state.get("query", "")
        
        # Extract patient ID from query
        patient_id = None
        import re
        match = re.search(r'patient[-_]?(\d+)', query.lower())
        if match:
            patient_id = f"patient-{match.group(1).zfill(3)}"
        else:
            patient_id = "patient-001"  # Default for demo
        
        patient_data = {}
        
        if self.data_tools:
            # Get comprehensive patient data from Data Moat
            patient_data = await self.data_tools.get_patient_summary(patient_id)
            
            # Also get risk assessment
            high_risk = await self.data_tools.get_high_risk_patients(limit=5)
            patient_data["context"] = {
                "high_risk_patients": high_risk.get("high_risk_patients", []),
            }
        else:
            # Mock data for demo
            patient_data = {
                "patient": {
                    "id": patient_id,
                    "name": "Demo Patient",
                    "age": 65,
                    "status": "active",
                },
                "conditions": [{"display": "Type 2 Diabetes"}, {"display": "Hypertension"}],
                "medications": [{"display": "Metformin"}, {"display": "Lisinopril"}],
                "data_sources": ["mock"],
            }
        
        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        step = WorkflowStep(
            node="patient_agent",
            input_data={"patient_id": patient_id},
            output_data={
                "patient_name": patient_data.get("patient", {}).get("name"),
                "conditions_count": len(patient_data.get("conditions", [])),
                "data_sources": patient_data.get("data_sources", []),
            },
            duration_ms=duration,
            status="completed"
        )
        
        steps = state.get("steps", [])
        steps.append(step.model_dump())
        
        return {
            **state,
            "patient_data": patient_data,
            "current_node": "patient_agent",
            "steps": steps,
        }
    
    async def _denial_agent_node(self, state: dict) -> dict:
        """
        Denial Agent: Analyzes denials and generates appeal recommendations.
        """
        start_time = datetime.utcnow()
        
        denial_data = {}
        
        if self.data_tools:
            # Get denial intelligence from Data Moat
            denial_data = await self.data_tools.get_denial_intelligence()
        else:
            # Mock data
            denial_data = {
                "summary": {
                    "total_denials": 10,
                    "total_denied_amount": 125000,
                    "pending_appeals": 5,
                    "urgent_deadlines": 2,
                },
                "data_sources": ["mock"],
            }
        
        # Generate appeal recommendations using LLM
        if denial_data.get("urgent_denials"):
            urgent = denial_data["urgent_denials"][0]
            appeal_rec = await self.llm.generate(
                prompt=f"""Generate a brief appeal recommendation for this denied claim:
                
Denial Reason: {urgent.get('denial_reason', 'Medical necessity')}
Amount: ${urgent.get('amount', 0):,.0f}
Deadline: {urgent.get('deadline', 'Soon')}

Provide 2-3 key points for the appeal.""",
                system_prompt="You are a healthcare revenue cycle expert."
            )
            denial_data["appeal_recommendation"] = appeal_rec
        
        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        step = WorkflowStep(
            node="denial_agent",
            input_data={"action": "analyze_denials"},
            output_data={
                "total_denials": denial_data.get("summary", {}).get("total_denials"),
                "total_amount": denial_data.get("summary", {}).get("total_denied_amount"),
                "data_sources": denial_data.get("data_sources", []),
            },
            duration_ms=duration,
            status="completed"
        )
        
        steps = state.get("steps", [])
        steps.append(step.model_dump())
        
        return {
            **state,
            "denial_data": denial_data,
            "current_node": "denial_agent",
            "steps": steps,
        }
    
    async def _triage_agent_node(self, state: dict) -> dict:
        """
        Triage Agent: Identifies patients needing clinical attention.
        """
        start_time = datetime.utcnow()
        
        triage_data = {}
        
        if self.data_tools:
            # Get patients needing attention
            attention = await self.data_tools.get_patients_needing_attention()
            high_risk = await self.data_tools.get_high_risk_patients(limit=10)
            
            triage_data = {
                "alerts": attention,
                "high_risk_patients": high_risk.get("high_risk_patients", []),
                "total_alerts": attention.get("total_alerts", 0),
                "data_sources": attention.get("data_sources", []),
            }
        else:
            # Mock data
            triage_data = {
                "alerts": {"total_alerts": 3},
                "high_risk_patients": [
                    {"name": "John Doe", "risk_score": 8, "risk_factors": ["Age 75", "3 conditions"]}
                ],
                "total_alerts": 3,
                "data_sources": ["mock"],
            }
        
        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        step = WorkflowStep(
            node="triage_agent",
            input_data={"action": "scan_patients"},
            output_data={
                "total_alerts": triage_data.get("total_alerts"),
                "high_risk_count": len(triage_data.get("high_risk_patients", [])),
                "data_sources": triage_data.get("data_sources", []),
            },
            duration_ms=duration,
            status="completed"
        )
        
        steps = state.get("steps", [])
        steps.append(step.model_dump())
        
        return {
            **state,
            "triage_data": triage_data,
            "current_node": "triage_agent",
            "steps": steps,
        }
    
    async def _synthesizer_node(self, state: dict) -> dict:
        """
        Synthesizer: Combines agent outputs into a coherent response.
        """
        start_time = datetime.utcnow()
        
        query = state.get("query", "")
        intent = state.get("intent", "general")
        patient_data = state.get("patient_data")
        denial_data = state.get("denial_data")
        triage_data = state.get("triage_data")
        
        # Build synthesis prompt
        context_parts = [f"Original Query: {query}", f"Detected Intent: {intent}"]
        
        if patient_data:
            context_parts.append(f"Patient Data: {json.dumps(patient_data, default=str)[:500]}")
        if denial_data:
            context_parts.append(f"Denial Data: {json.dumps(denial_data, default=str)[:500]}")
        if triage_data:
            context_parts.append(f"Triage Data: {json.dumps(triage_data, default=str)[:500]}")
        
        synthesis = await self.llm.generate(
            prompt=f"""Synthesize a clear, actionable response based on this data:

{chr(10).join(context_parts)}

Provide a structured response with:
1. Summary of findings
2. Key insights
3. Recommended actions""",
            system_prompt="You are a healthcare operations analyst providing clear, actionable insights."
        )
        
        # Build result
        result = {
            "summary": synthesis,
            "intent": intent,
            "data_sources": [],
        }
        
        # Collect data sources
        if patient_data:
            result["data_sources"].extend(patient_data.get("data_sources", []))
            result["patient"] = patient_data.get("patient")
        if denial_data:
            result["data_sources"].extend(denial_data.get("data_sources", []))
            result["denial_summary"] = denial_data.get("summary")
        if triage_data:
            result["data_sources"].extend(triage_data.get("data_sources", []))
            result["alert_count"] = triage_data.get("total_alerts")
        
        result["data_sources"] = list(set(result["data_sources"]))
        
        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        step = WorkflowStep(
            node="synthesizer",
            input_data={"intent": intent},
            output_data={"summary_length": len(synthesis)},
            duration_ms=duration,
            status="completed"
        )
        
        steps = state.get("steps", [])
        steps.append(step.model_dump())
        
        return {
            **state,
            "result": result,
            "current_node": "synthesizer",
            "steps": steps,
        }
    
    async def run(self, query: str) -> dict:
        """
        Execute the workflow.
        
        Returns:
            dict with result, steps (trace), and workflow info
        """
        initial_state = {
            "query": query,
            "tenant_id": self.tenant_id,
            "intent": None,
            "selected_agent": None,
            "steps": [],
            "current_node": "start",
            "patient_data": None,
            "denial_data": None,
            "triage_data": None,
            "result": None,
            "error": None,
        }
        
        try:
            # Execute the workflow
            final_state = await self.compiled.ainvoke(initial_state)
            
            return {
                "success": True,
                "result": final_state.get("result"),
                "trace": final_state.get("steps", []),
                "workflow": self.get_workflow_definition(),
            }
            
        except Exception as e:
            logger.error("Workflow failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "trace": [],
                "workflow": self.get_workflow_definition(),
            }
    
    def get_workflow_definition(self) -> dict:
        """
        Get the workflow graph definition for visualization.
        """
        return {
            "name": "Healthcare Multi-Agent Workflow",
            "framework": "LangGraph",
            "nodes": [
                {"id": "start", "label": "START", "type": "entry"},
                {"id": "supervisor", "label": "Supervisor\n(Intent Router)", "type": "router"},
                {"id": "patient_agent", "label": "Patient Agent\n(360 View)", "type": "agent"},
                {"id": "denial_agent", "label": "Denial Agent\n(Appeals)", "type": "agent"},
                {"id": "triage_agent", "label": "Triage Agent\n(Monitoring)", "type": "agent"},
                {"id": "synthesizer", "label": "Synthesizer\n(Combine)", "type": "processor"},
                {"id": "end", "label": "END", "type": "exit"},
            ],
            "edges": [
                {"from": "start", "to": "supervisor"},
                {"from": "supervisor", "to": "patient_agent", "label": "patient intent"},
                {"from": "supervisor", "to": "denial_agent", "label": "denial intent"},
                {"from": "supervisor", "to": "triage_agent", "label": "triage intent"},
                {"from": "supervisor", "to": "synthesizer", "label": "direct"},
                {"from": "patient_agent", "to": "synthesizer"},
                {"from": "denial_agent", "to": "synthesizer"},
                {"from": "triage_agent", "to": "synthesizer"},
                {"from": "synthesizer", "to": "end"},
            ],
            "data_moat_connections": [
                {"agent": "patient_agent", "sources": ["PostgreSQL", "TimescaleDB"]},
                {"agent": "denial_agent", "sources": ["PostgreSQL"]},
                {"agent": "triage_agent", "sources": ["PostgreSQL", "TimescaleDB"]},
            ],
        }


# =============================================================================
# n8n-Compatible Webhook Handler
# =============================================================================

class WebhookPayload(BaseModel):
    """n8n-style webhook payload."""
    query: str
    workflow_id: str = "healthcare_orchestrator"
    callback_url: str | None = None
    metadata: dict = Field(default_factory=dict)


async def handle_webhook(payload: WebhookPayload, pool=None) -> dict:
    """
    Handle incoming webhook request (n8n compatible).
    
    Can be triggered from n8n using HTTP Request node:
    - Method: POST
    - URL: http://your-server/v1/workflows/webhook
    - Body: {"query": "...", "workflow_id": "healthcare_orchestrator"}
    """
    workflow = HealthcareWorkflow(pool=pool)
    result = await workflow.run(payload.query)
    
    return {
        "webhook_id": payload.workflow_id,
        "execution_id": datetime.utcnow().isoformat(),
        "status": "completed" if result.get("success") else "failed",
        "result": result,
    }
