"""
Workflow Routes

LangGraph workflow execution and visualization endpoints.
Compatible with n8n and other workflow orchestrators.
"""

from typing import Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from aegis.api.auth import TenantContext, get_tenant_context

router = APIRouter(prefix="/workflows", tags=["Workflows"])


# =============================================================================
# Request/Response Models
# =============================================================================

class WorkflowRunRequest(BaseModel):
    """Request to run a workflow."""
    query: str = Field(..., description="Natural language query")
    workflow_id: str = Field(default="healthcare_orchestrator", description="Workflow to run")


class WorkflowStep(BaseModel):
    """A step in workflow execution."""
    node: str
    timestamp: str
    input_data: dict | None = None
    output_data: dict | None = None
    duration_ms: int = 0
    status: str = "completed"


class WorkflowNode(BaseModel):
    """A node in the workflow graph."""
    id: str
    label: str
    type: str  # entry, router, agent, processor, exit


class WorkflowEdge(BaseModel):
    """An edge in the workflow graph."""
    source: str = Field(alias="from")
    target: str = Field(alias="to")
    label: str | None = None
    
    class Config:
        populate_by_name = True


class WorkflowDefinition(BaseModel):
    """Workflow graph definition."""
    name: str
    framework: str
    nodes: list[dict]
    edges: list[dict]
    data_moat_connections: list[dict]


class WorkflowRunResponse(BaseModel):
    """Response from workflow execution."""
    success: bool
    execution_id: str
    workflow_id: str
    result: dict | None = None
    error: str | None = None
    trace: list[WorkflowStep] = Field(default_factory=list)
    workflow: WorkflowDefinition | None = None
    execution_time_ms: int = 0


class WebhookRequest(BaseModel):
    """n8n-compatible webhook request."""
    query: str
    workflow_id: str = "healthcare_orchestrator"
    callback_url: str | None = None
    metadata: dict = Field(default_factory=dict)


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/run", response_model=WorkflowRunResponse)
async def run_workflow(
    request: WorkflowRunRequest,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Run a LangGraph workflow.
    
    **Available Workflows:**
    - `healthcare_orchestrator`: Multi-agent workflow that routes to specialized agents
    
    **Example Queries:**
    - "Review patient-001" → Routes to Patient Agent
    - "Analyze denial backlog" → Routes to Denial Agent
    - "Show clinical alerts" → Routes to Triage Agent
    
    **Response includes:**
    - `result`: The synthesized output
    - `trace`: Step-by-step execution trace
    - `workflow`: Graph definition for visualization
    """
    from aegis.agents.workflows import HealthcareWorkflow
    
    start_time = datetime.utcnow()
    
    try:
        # Get database pool from app state
        pool = None
        if hasattr(req.app.state, 'db') and req.app.state.db:
            pool = req.app.state.db.postgres
        
        # Create and run workflow
        workflow = HealthcareWorkflow(pool=pool, tenant_id=tenant.tenant_id)
        result = await workflow.run(request.query)
        
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return WorkflowRunResponse(
            success=result.get("success", False),
            execution_id=datetime.utcnow().isoformat(),
            workflow_id=request.workflow_id,
            result=result.get("result"),
            error=result.get("error"),
            trace=[WorkflowStep(**step) for step in result.get("trace", [])],
            workflow=result.get("workflow"),
            execution_time_ms=execution_time,
        )
        
    except Exception as e:
        return WorkflowRunResponse(
            success=False,
            execution_id=datetime.utcnow().isoformat(),
            workflow_id=request.workflow_id,
            error=str(e),
            execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
        )


@router.get("/definition/{workflow_id}")
async def get_workflow_definition(workflow_id: str):
    """
    Get workflow graph definition for visualization.
    
    Returns nodes, edges, and data source connections that can be
    rendered with tools like:
    - React Flow
    - Mermaid
    - D3.js
    - n8n
    """
    from aegis.agents.workflows import HealthcareWorkflow
    
    if workflow_id != "healthcare_orchestrator":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown workflow: {workflow_id}"
        )
    
    workflow = HealthcareWorkflow()
    definition = workflow.get_workflow_definition()
    
    # Add Mermaid diagram
    mermaid = """graph TD
    START([START]) --> SUPERVISOR{Supervisor<br/>Intent Router}
    SUPERVISOR -->|patient| PATIENT[Patient Agent<br/>360 View]
    SUPERVISOR -->|denial| DENIAL[Denial Agent<br/>Appeals]
    SUPERVISOR -->|triage| TRIAGE[Triage Agent<br/>Monitoring]
    SUPERVISOR -->|direct| SYNTH[Synthesizer]
    PATIENT --> SYNTH
    DENIAL --> SYNTH
    TRIAGE --> SYNTH
    SYNTH --> END([END])
    
    subgraph Data Moat
        PG[(PostgreSQL)]
        TS[(TimescaleDB)]
    end
    
    PATIENT -.-> PG
    PATIENT -.-> TS
    DENIAL -.-> PG
    TRIAGE -.-> PG
    TRIAGE -.-> TS"""
    
    return {
        **definition,
        "mermaid": mermaid,
        "visualization_options": [
            {"name": "Mermaid", "format": "mermaid", "url": "https://mermaid.live"},
            {"name": "React Flow", "format": "react-flow", "url": "https://reactflow.dev"},
            {"name": "n8n", "format": "n8n", "url": "https://n8n.io"},
        ],
    }


@router.post("/webhook")
async def webhook_trigger(
    request: WebhookRequest,
    req: Request,
):
    """
    n8n-compatible webhook endpoint.
    
    **n8n Integration:**
    1. Add HTTP Request node in n8n
    2. Set Method: POST
    3. Set URL: http://your-server/v1/workflows/webhook
    4. Set Body:
       ```json
       {
         "query": "{{ $json.query }}",
         "workflow_id": "healthcare_orchestrator"
       }
       ```
    
    **Callback Support:**
    If `callback_url` is provided, results will be POSTed to that URL
    when the workflow completes (async execution).
    """
    from aegis.agents.workflows import HealthcareWorkflow
    
    start_time = datetime.utcnow()
    
    # Get database pool
    pool = None
    if hasattr(req.app.state, 'db') and req.app.state.db:
        pool = req.app.state.db.postgres
    
    workflow = HealthcareWorkflow(pool=pool)
    result = await workflow.run(request.query)
    
    execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
    response = {
        "webhook_id": request.workflow_id,
        "execution_id": datetime.utcnow().isoformat(),
        "status": "completed" if result.get("success") else "failed",
        "execution_time_ms": execution_time,
        "result": result.get("result"),
        "trace": result.get("trace", []),
        "metadata": request.metadata,
    }
    
    # TODO: If callback_url provided, POST results there asynchronously
    
    return response


@router.get("/list")
async def list_workflows():
    """
    List available workflows.
    """
    return {
        "workflows": [
            {
                "id": "healthcare_orchestrator",
                "name": "Healthcare Multi-Agent Orchestrator",
                "description": "Routes queries to specialized agents (Patient, Denial, Triage) and synthesizes results",
                "framework": "LangGraph",
                "agents": ["supervisor", "patient_agent", "denial_agent", "triage_agent", "synthesizer"],
                "data_sources": ["PostgreSQL", "TimescaleDB"],
                "n8n_compatible": True,
            }
        ],
        "integrations": {
            "n8n": {
                "webhook_url": "/v1/workflows/webhook",
                "supported": True,
            },
            "langchain": {
                "version": "latest",
                "supported": True,
            },
            "langgraph": {
                "version": "latest",
                "supported": True,
            },
        },
    }


@router.get("/trace/{execution_id}")
async def get_execution_trace(execution_id: str):
    """
    Get detailed execution trace for a workflow run.
    
    Note: Currently returns mock data. In production, traces would be
    stored in a database for later retrieval.
    """
    return {
        "execution_id": execution_id,
        "status": "completed",
        "message": "Execution traces are available in the workflow run response. Persistent storage coming soon.",
    }
