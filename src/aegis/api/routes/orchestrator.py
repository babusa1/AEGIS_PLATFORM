"""
Orchestrator API Routes

Endpoints for the AEGIS workflow orchestration platform.
Your own n8n-like system built on the Data Moat.
"""

from typing import Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from aegis.api.auth import TenantContext, get_tenant_context

router = APIRouter(prefix="/orchestrator", tags=["Orchestrator"])


# =============================================================================
# Models
# =============================================================================

class NodeConfig(BaseModel):
    """Node configuration."""
    agent_type: str | None = None
    prompt_template: str | None = None
    system_prompt: str | None = None
    query_template: str | None = None
    filters: dict | None = None
    routes: list[dict] | None = None
    url: str | None = None
    method: str = "POST"


class WorkflowNode(BaseModel):
    """A node in a workflow."""
    id: str
    type: str
    name: str
    description: str | None = None
    config: NodeConfig = Field(default_factory=NodeConfig)
    position_x: int = 0
    position_y: int = 0


class WorkflowEdge(BaseModel):
    """An edge connecting nodes."""
    id: str | None = None
    source: str
    target: str
    label: str | None = None


class CreateWorkflowRequest(BaseModel):
    """Request to create a workflow."""
    name: str
    description: str | None = None
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    tags: list[str] = Field(default_factory=list)


class ExecuteWorkflowRequest(BaseModel):
    """Request to execute a workflow."""
    workflow_id: str
    inputs: dict = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    """Workflow response."""
    id: str
    name: str
    description: str | None
    nodes: list[dict]
    edges: list[dict]
    is_template: bool = False
    tags: list[str] = Field(default_factory=list)


class ExecutionResponse(BaseModel):
    """Execution response."""
    execution_id: str
    workflow_id: str
    workflow_name: str
    status: str
    duration_ms: int
    output: dict | None
    error: str | None
    trace: list[dict]
    execution_path: list[str]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/tools")
async def list_tools():
    """
    List all available tools for building workflows.
    
    Tools are organized by category:
    - **Data Moat**: Query patients, claims, denials, vitals, labs
    - **Agents**: AI agents for patient analysis, denial management, triage
    - **LLM**: Direct LLM calls with custom prompts
    - **Actions**: Send alerts, generate appeals, call APIs
    - **Transforms**: Filter, aggregate, transform data
    """
    from aegis.orchestrator.tools import ToolRegistry
    
    registry = ToolRegistry()
    tools_by_category = registry.list_tools_by_category()
    
    return {
        "categories": list(tools_by_category.keys()),
        "tools": {
            category: [tool.model_dump() for tool in tools]
            for category, tools in tools_by_category.items()
        },
        "total_tools": sum(len(tools) for tools in tools_by_category.values()),
    }


@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(
    request: CreateWorkflowRequest,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Create a new workflow.
    
    **Example:**
    ```json
    {
        "name": "My Workflow",
        "description": "Analyzes patient risk",
        "nodes": [
            {"id": "start", "type": "start", "name": "Start"},
            {"id": "query", "type": "query_patients", "name": "Get Patients"},
            {"id": "analyze", "type": "patient_agent", "name": "Analyze"},
            {"id": "end", "type": "end", "name": "End"}
        ],
        "edges": [
            {"source": "start", "target": "query"},
            {"source": "query", "target": "analyze"},
            {"source": "analyze", "target": "end"}
        ]
    }
    ```
    """
    from aegis.orchestrator.engine import WorkflowEngine
    from aegis.orchestrator.models import WorkflowDefinition, WorkflowNode as WFNode, WorkflowEdge as WFEdge, NodeConfig as NC
    
    # Get pool
    pool = None
    if hasattr(req.app.state, 'db') and req.app.state.db:
        pool = req.app.state.db.postgres
    
    # Convert to internal models
    nodes = [
        WFNode(
            id=n.id,
            type=n.type,
            name=n.name,
            description=n.description,
            config=NC(**n.config.model_dump()) if n.config else NC(),
            position_x=n.position_x,
            position_y=n.position_y,
        )
        for n in request.nodes
    ]
    
    edges = [
        WFEdge(
            id=e.id or f"edge-{e.source}-{e.target}",
            source=e.source,
            target=e.target,
            label=e.label,
        )
        for e in request.edges
    ]
    
    workflow = WorkflowDefinition(
        name=request.name,
        description=request.description,
        nodes=nodes,
        edges=edges,
        tags=request.tags,
        tenant_id=tenant.tenant_id,
        created_by=tenant.user_id,
    )
    
    # Save
    engine = WorkflowEngine(pool, tenant.tenant_id)
    await engine.save_workflow(workflow)
    
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        nodes=[n.model_dump() for n in workflow.nodes],
        edges=[e.model_dump() for e in workflow.edges],
        tags=workflow.tags,
    )


@router.get("/workflows")
async def list_workflows(
    req: Request,
    include_templates: bool = True,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    List all workflows.
    
    Use `include_templates=false` to exclude pre-built templates.
    """
    from aegis.orchestrator.engine import WorkflowEngine
    
    pool = None
    if hasattr(req.app.state, 'db') and req.app.state.db:
        pool = req.app.state.db.postgres
    
    engine = WorkflowEngine(pool, tenant.tenant_id)
    workflows = await engine.list_workflows(include_templates=include_templates)
    
    return {
        "workflows": workflows,
        "total": len(workflows),
    }


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """Get a specific workflow by ID."""
    from aegis.orchestrator.engine import WorkflowEngine
    
    pool = None
    if hasattr(req.app.state, 'db') and req.app.state.db:
        pool = req.app.state.db.postgres
    
    engine = WorkflowEngine(pool, tenant.tenant_id)
    workflow = await engine.load_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        nodes=[n.model_dump() for n in workflow.nodes],
        edges=[e.model_dump() for e in workflow.edges],
        is_template=workflow.is_template,
        tags=workflow.tags,
    )


@router.post("/execute", response_model=ExecutionResponse)
async def execute_workflow(
    request: ExecuteWorkflowRequest,
    req: Request,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Execute a workflow.
    
    **Example:**
    ```json
    {
        "workflow_id": "uuid-of-workflow",
        "inputs": {
            "patient_id": "patient-001"
        }
    }
    ```
    
    **Returns:**
    - Execution status
    - Output data
    - Execution trace showing each node's execution
    - Execution path taken through the workflow
    """
    from aegis.orchestrator.engine import WorkflowEngine
    
    pool = None
    if hasattr(req.app.state, 'db') and req.app.state.db:
        pool = req.app.state.db.postgres
    
    engine = WorkflowEngine(pool, tenant.tenant_id)
    
    # Load workflow
    workflow = await engine.load_workflow(request.workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Execute
    execution = await engine.execute(
        workflow=workflow,
        inputs=request.inputs,
        user_id=tenant.user_id,
    )
    
    # Save execution record
    await engine.save_execution(execution)
    
    return ExecutionResponse(
        execution_id=execution.id,
        workflow_id=execution.workflow_id,
        workflow_name=execution.workflow_name,
        status=execution.status.value,
        duration_ms=execution.duration_ms,
        output=execution.output_data,
        error=execution.error,
        trace=[ne.model_dump() for ne in execution.node_executions],
        execution_path=execution.execution_path,
    )


@router.get("/executions")
async def list_executions(
    req: Request,
    workflow_id: str | None = None,
    limit: int = 50,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    List execution history.
    
    Filter by `workflow_id` to see executions for a specific workflow.
    """
    from aegis.orchestrator.engine import WorkflowEngine
    
    pool = None
    if hasattr(req.app.state, 'db') and req.app.state.db:
        pool = req.app.state.db.postgres
    
    engine = WorkflowEngine(pool, tenant.tenant_id)
    executions = await engine.get_execution_history(workflow_id=workflow_id, limit=limit)
    
    return {
        "executions": executions,
        "total": len(executions),
    }


@router.get("/templates")
async def list_templates(req: Request):
    """
    List pre-built workflow templates.
    
    Templates provide starting points for common healthcare workflows:
    - Patient Risk Assessment
    - Denial Appeal Workflow
    - Clinical Triage Alert
    """
    from aegis.orchestrator.engine import WorkflowEngine
    
    pool = None
    if hasattr(req.app.state, 'db') and req.app.state.db:
        pool = req.app.state.db.postgres
    
    engine = WorkflowEngine(pool, "default")
    
    # Return hardcoded templates for demo
    templates = [
        {
            "id": "patient-risk-assessment",
            "name": "Patient Risk Assessment",
            "description": "Analyze patient data and generate risk score with recommendations",
            "tags": ["patient", "risk", "clinical"],
            "node_count": 5,
        },
        {
            "id": "denial-appeal-workflow",
            "name": "Denial Appeal Workflow",
            "description": "Analyze denied claim and generate appeal letter with supporting evidence",
            "tags": ["denial", "appeal", "revenue"],
            "node_count": 6,
        },
        {
            "id": "clinical-triage-alert",
            "name": "Clinical Triage Alert",
            "description": "Monitor patients and generate alerts for those needing attention",
            "tags": ["triage", "alert", "clinical"],
            "node_count": 7,
        },
    ]
    
    return {"templates": templates}


@router.post("/execute-quick")
async def execute_quick(
    req: Request,
    query: str,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Quick execution without pre-defined workflow.
    
    Automatically routes to appropriate tools based on query.
    
    **Example queries:**
    - "Get patient-001 summary"
    - "Analyze denials for last 30 days"
    - "Find critical lab results"
    """
    from aegis.orchestrator.tools import ToolRegistry
    from aegis.bedrock.client import get_llm_client
    
    pool = None
    if hasattr(req.app.state, 'db') and req.app.state.db:
        pool = req.app.state.db.postgres
    
    registry = ToolRegistry(pool, tenant.tenant_id)
    llm = get_llm_client()
    
    # Use LLM to determine which tool to use
    tool_list = "\n".join([
        f"- {t.id}: {t.description}"
        for t in registry.list_tools()
    ])
    
    classification = await llm.generate(
        prompt=f"""Given this query, which tool should be used?

Query: {query}

Available tools:
{tool_list}

Return ONLY the tool ID.""",
        system_prompt="You are a tool router. Return only the tool ID, nothing else."
    )
    
    tool_id = classification.strip().lower()
    
    # Extract parameters from query (simplified)
    params = {}
    if "patient" in query.lower():
        import re
        match = re.search(r'patient[-_]?(\d+)', query.lower())
        if match:
            params["patient_id"] = f"patient-{match.group(1).zfill(3)}"
    
    # Execute tool
    result = await registry.execute_tool(tool_id, params)
    
    return {
        "query": query,
        "tool_used": tool_id,
        "parameters": params,
        "result": result,
    }
