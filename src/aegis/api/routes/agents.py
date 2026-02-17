"""
Agent Routes

Endpoints for invoking VeritOS AI agents.
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from aegis.api.auth import User, TenantContext, get_current_active_user, get_tenant_context
from aegis.bedrock.client import get_llm_client
from aegis.agents.unified_view import UnifiedViewAgent
from aegis.agents.action import ActionAgent
from aegis.agents.insight import InsightAgent

router = APIRouter(prefix="/agents", tags=["AI Agents"])


# =============================================================================
# Request/Response Models
# =============================================================================

class AgentInvokeRequest(BaseModel):
    """Request to invoke an agent."""
    query: str = Field(..., description="User query or instruction")
    context: dict = Field(default_factory=dict, description="Additional context")


class UnifiedViewRequest(BaseModel):
    """Request for unified patient view."""
    patient_id: str | None = Field(default=None, description="Patient vertex ID")
    mrn: str | None = Field(default=None, description="Patient MRN")
    include_risk_scores: bool = Field(default=True)
    include_financial: bool = Field(default=True)


class AppealRequest(BaseModel):
    """Request to generate denial appeal."""
    claim_id: str = Field(..., description="Claim ID to appeal")
    denial_id: str | None = Field(default=None, description="Specific denial ID")
    additional_context: str | None = Field(default=None, description="Additional notes for appeal")


class InsightRequest(BaseModel):
    """Request for insight discovery."""
    query: str = Field(..., description="What insights to discover")
    scope: Literal["denials", "readmissions", "revenue", "all"] = Field(default="all")
    time_period_days: int = Field(default=90, ge=7, le=365)


class AgentResponse(BaseModel):
    """Response from an agent."""
    agent: str
    status: str
    result: dict
    reasoning: str | None = None
    confidence_score: float | None = None
    execution_time_ms: int | None = None


class AppealResponse(BaseModel):
    """Response from appeal generation."""
    claim_id: str
    denial_reason: str
    appeal_letter: str
    evidence_summary: str
    recommended_actions: list[str]
    confidence_score: float
    similar_successful_appeals: int


class InsightResponse(BaseModel):
    """Response from insight discovery."""
    insights: list[dict]
    summary: str
    recommended_actions: list[str]
    data_points_analyzed: int


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/invoke", response_model=AgentResponse)
async def invoke_agent(
    request: AgentInvokeRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    user: User = Depends(get_current_active_user),
):
    """
    Invoke a general-purpose AEGIS agent.
    
    The agent will analyze the query and execute appropriate actions
    using the knowledge graph and available tools.
    """
    import time
    start_time = time.time()
    
    try:
        llm_client = get_llm_client()
        
        # Build prompt with context
        system_prompt = """You are VeritOS, an AI assistant for healthcare operations.
You have access to a knowledge graph containing patient, encounter, claim, and denial data.
Help users understand their healthcare data and take action on operational issues.
Always be precise and cite specific data when possible."""
        
        prompt = f"""
User Query: {request.query}

Tenant: {tenant.tenant_id}
User Role: {', '.join(user.roles)}

Additional Context:
{request.context}

Please analyze this request and provide a helpful response.
"""
        
        # Get response from LLM
        response = await llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return AgentResponse(
            agent="general",
            status="success",
            result={"response": response},
            reasoning="Processed query using LLM with healthcare context",
            confidence_score=0.85,
            execution_time_ms=execution_time,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent invocation failed: {str(e)}",
        )


@router.post("/unified-view", response_model=AgentResponse)
async def get_unified_patient_view(
    request: UnifiedViewRequest,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Generate a unified 360-degree patient view using the Unified View Agent.
    
    Synthesizes data from multiple sources and provides an AI-generated
    summary with risk assessments and recommended actions.
    """
    import time
    start_time = time.time()
    
    if not request.patient_id and not request.mrn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either patient_id or mrn must be provided",
        )
    
    try:
        # Create and run the Unified View Agent
        agent = UnifiedViewAgent(tenant_id=tenant.tenant_id)
        
        result = await agent.generate_patient_summary(
            patient_id=request.patient_id,
            mrn=request.mrn,
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return AgentResponse(
            agent="unified_view",
            status="success" if result.get("answer") else "error",
            result={
                "patient_summary": result.get("answer"),
                "patient_id": request.patient_id,
                "mrn": request.mrn,
            },
            reasoning="\n".join(result.get("reasoning", [])),
            confidence_score=result.get("confidence", 0.0),
            execution_time_ms=execution_time,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unified view generation failed: {str(e)}",
        )


@router.post("/appeal", response_model=AppealResponse)
async def generate_denial_appeal(
    request: AppealRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    user: User = Depends(get_current_active_user),
):
    """
    Generate a denial appeal using the Action Agent.
    
    Analyzes the denial, gathers clinical evidence, finds similar
    successful appeals, and drafts an appeal letter.
    
    Uses Writer + Critic pattern for quality assurance.
    The appeal requires human approval before submission.
    """
    try:
        # Create and run the Action Agent
        agent = ActionAgent(tenant_id=tenant.tenant_id)
        
        result = await agent.generate_appeal(
            claim_id=request.claim_id,
            additional_context=request.additional_context,
        )
        
        appeal_letter = result.get("answer", "")
        
        return AppealResponse(
            claim_id=request.claim_id,
            denial_reason="Extracted from claim data",  # Would come from tool results
            appeal_letter=appeal_letter,
            evidence_summary="\n".join(result.get("reasoning", [])),
            recommended_actions=[
                "Review generated appeal letter",
                "Attach supporting documentation",
                "Submit to payer within appeal deadline",
            ],
            confidence_score=result.get("confidence", 0.0),
            similar_successful_appeals=3,  # Would come from similarity search
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Appeal generation failed: {str(e)}",
        )


@router.post("/insights", response_model=InsightResponse)
async def discover_insights(
    request: InsightRequest,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Discover insights using the Insight Discovery Agent.
    
    Analyzes patterns in the knowledge graph to find:
    - Denial trends
    - Revenue leakage
    - Operational inefficiencies
    - Clinical patterns
    """
    try:
        # Create and run the Insight Agent
        agent = InsightAgent(tenant_id=tenant.tenant_id)
        
        result = await agent.discover_insights(
            query=request.query,
            scope=request.scope,
            time_period_days=request.time_period_days,
        )
        
        return InsightResponse(
            insights=[
                {
                    "type": request.scope,
                    "title": f"Analysis: {request.query[:50]}",
                    "description": result.get("answer", ""),
                    "impact": "high",
                }
            ],
            summary=result.get("answer", ""),
            recommended_actions=[
                "Review insights report",
                "Validate findings with stakeholders", 
                "Prioritize recommended actions",
            ],
            data_points_analyzed=len(result.get("tool_calls", [])) * 100,  # Estimated
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Insight discovery failed: {str(e)}",
        )


class OrchestratorRequest(BaseModel):
    """Request for orchestrator agent."""
    query: str = Field(..., description="Natural language query for the orchestrator")


class OrchestratorResponse(BaseModel):
    """Response from orchestrator agent."""
    answer: str
    task_type: str | None = None
    activities: list[dict] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    data_sources_used: list[str] = Field(default_factory=list)


class TriageResponse(BaseModel):
    """Response from triage agent."""
    report: str
    alerts: list[dict] = Field(default_factory=list)
    priority_counts: dict = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    generated_at: str | None = None


@router.post("/orchestrate", response_model=OrchestratorResponse)
async def run_orchestrator(
    request: OrchestratorRequest,
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Run the Orchestrator Agent.
    
    The Orchestrator coordinates multiple specialized agents and demonstrates
    how the Data Moat powers intelligent healthcare operations.
    
    **Example Queries:**
    - "Review patient-001" → Patient summary with risk analysis
    - "Handle denial backlog" → Denial intelligence and appeal recommendations
    - "Run clinical triage" → Identify patients needing attention
    
    **Data Sources Accessed:**
    - PostgreSQL (patient demographics, conditions, claims, denials)
    - TimescaleDB (vitals, lab results)
    - Graph DB (clinical relationships)
    """
    from aegis.agents.orchestrator import OrchestratorAgent
    from aegis.db.clients import get_postgres_pool
    
    try:
        pool = get_postgres_pool()
        agent = OrchestratorAgent(pool, tenant.tenant_id)
        
        result = await agent.run(request.query, tenant.user_id)
        
        # Extract data sources from activities
        data_sources = set()
        for activity in result.get("activities", []):
            sources = activity.get("data_sources", [])
            data_sources.update(sources)
        
        return OrchestratorResponse(
            answer=result.get("answer", "Analysis complete"),
            task_type=result.get("task_type"),
            activities=result.get("activities", []),
            insights=result.get("insights", []),
            confidence=result.get("confidence", 0.0),
            data_sources_used=list(data_sources),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Orchestrator failed: {str(e)}",
        )


@router.post("/triage", response_model=TriageResponse)
async def run_triage(
    tenant: TenantContext = Depends(get_tenant_context),
):
    """
    Run the Clinical Triage Agent.
    
    Scans the Data Moat for patients requiring clinical attention:
    - Critical/abnormal lab values
    - Concerning vital signs
    - High-risk patients
    
    **Returns:**
    - Prioritized alert list (Critical → High → Medium → Low)
    - Actionable recommendations
    - Patient-specific findings
    
    **Data Sources:**
    - TimescaleDB: Real-time vitals and lab results
    - PostgreSQL: Patient conditions, medications, encounters
    """
    from aegis.agents.triage import TriageAgent
    from aegis.db.clients import get_postgres_pool
    
    try:
        pool = get_postgres_pool()
        agent = TriageAgent(pool, tenant.tenant_id)
        
        result = await agent.run()
        
        return TriageResponse(
            report=result.get("report", "Triage complete"),
            alerts=result.get("alerts", []),
            priority_counts=result.get("priority_counts", {}),
            recommendations=result.get("recommendations", []),
            generated_at=result.get("generated_at"),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Triage agent failed: {str(e)}",
        )


@router.get("/data-moat/tools")
async def get_data_moat_tools():
    """
    Get available Data Moat tools.
    
    Shows all the tools agents can use to access the unified data layer.
    """
    from aegis.agents.data_tools import DataMoatTools
    
    tools = DataMoatTools(None, "demo")
    all_tools = tools.get_all_tools()
    
    return {
        "description": "Data Moat - Unified Healthcare Data Layer",
        "data_sources": [
            {"name": "PostgreSQL", "type": "relational", "data": "Demographics, conditions, medications, claims, denials"},
            {"name": "TimescaleDB", "type": "timeseries", "data": "Vitals, lab results, wearable metrics"},
            {"name": "Graph DB", "type": "graph", "data": "Clinical relationships, care pathways"},
            {"name": "Vector DB", "type": "vector", "data": "Semantic search, similar patients"},
        ],
        "tools": {
            name: {
                "description": tool["description"],
                "parameters": tool.get("parameters", {}),
            }
            for name, tool in all_tools.items()
        },
    }


@router.get("/status")
async def get_agent_status():
    """
    Get the status of available agents.
    """
    from aegis.config import get_settings
    settings = get_settings()
    
    return {
        "agents": {
            "orchestrator": {"status": "available", "description": "Master coordinator - routes to specialized agents"},
            "triage": {"status": "available", "description": "Clinical monitoring - identifies patients needing attention"},
            "unified_view": {"status": "available", "description": "Patient 360 view agent"},
            "action": {"status": "available", "description": "Denial appeal agent"},
            "insight": {"status": "available", "description": "Insight discovery agent"},
        },
        "data_moat": {
            "postgresql": "connected",
            "timescaledb": "connected", 
            "graph_db": "mock",
            "vector_db": "mock",
        },
        "llm_provider": settings.llm.llm_provider,
        "model": settings.llm.bedrock_model_id if settings.llm.llm_provider == "bedrock" else "mock",
    }
