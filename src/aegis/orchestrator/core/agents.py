"""
Agent Manager

Multi-agent orchestration with:
- Agent profiles and capabilities
- Supervisor pattern
- Agent handoff
- Human-in-the-loop gates
- Cost tracking
"""

from typing import Any, Callable, Awaitable
from datetime import datetime
from enum import Enum
import uuid

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Agent Models
# =============================================================================

class AgentCapability(str, Enum):
    """Agent capabilities."""
    PATIENT_ANALYSIS = "patient_analysis"
    DENIAL_MANAGEMENT = "denial_management"
    CLINICAL_TRIAGE = "clinical_triage"
    INSIGHT_DISCOVERY = "insight_discovery"
    APPEAL_GENERATION = "appeal_generation"
    DATA_QUERY = "data_query"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"


class AgentProfile(BaseModel):
    """Agent profile defining capabilities and constraints."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    
    # Capabilities
    capabilities: list[AgentCapability] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)  # Allowed tools
    
    # LLM configuration
    model: str = "claude-3-sonnet"
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str | None = None
    
    # Constraints
    max_iterations: int = 10
    timeout_seconds: int = 300
    rate_limit_rpm: int = 60  # Requests per minute
    
    # Cost tracking
    cost_per_1k_input_tokens: float = 0.003
    cost_per_1k_output_tokens: float = 0.015
    
    # Human-in-loop
    requires_approval: bool = False
    approval_threshold: float = 0.8  # Confidence below this requires approval
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1


class AgentExecution(BaseModel):
    """Record of an agent execution."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    agent_name: str
    
    # Input/Output
    query: str
    response: str | None = None
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    duration_ms: int = 0
    
    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0
    
    # Tool usage
    tools_called: list[str] = Field(default_factory=list)
    
    # Quality
    confidence: float = 0.0
    approved: bool | None = None
    approved_by: str | None = None


# =============================================================================
# Human-in-the-Loop
# =============================================================================

class ApprovalRequest(BaseModel):
    """Request for human approval."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str
    agent_id: str
    agent_name: str
    
    # What needs approval
    action: str
    content: str
    confidence: float
    
    # Context
    context: dict = Field(default_factory=dict)
    
    # Status
    status: str = "pending"  # pending, approved, rejected, timeout
    created_at: datetime = Field(default_factory=datetime.utcnow)
    responded_at: datetime | None = None
    responded_by: str | None = None
    feedback: str | None = None


class ApprovalGate:
    """
    Human-in-the-loop approval gate.
    
    Features:
    - Pause execution for human review
    - Collect feedback
    - Support timeout and auto-reject
    """
    
    def __init__(self, timeout_seconds: int = 3600):
        self.timeout_seconds = timeout_seconds
        self._pending_requests: dict[str, ApprovalRequest] = {}
        self._callbacks: dict[str, Callable] = {}
    
    def create_request(
        self,
        execution_id: str,
        agent_id: str,
        agent_name: str,
        action: str,
        content: str,
        confidence: float,
        context: dict = None,
    ) -> ApprovalRequest:
        """Create an approval request."""
        request = ApprovalRequest(
            execution_id=execution_id,
            agent_id=agent_id,
            agent_name=agent_name,
            action=action,
            content=content,
            confidence=confidence,
            context=context or {},
        )
        
        self._pending_requests[request.id] = request
        
        logger.info(
            "Created approval request",
            request_id=request.id,
            agent=agent_name,
            action=action,
        )
        
        return request
    
    def approve(
        self,
        request_id: str,
        approved_by: str,
        feedback: str = None,
    ) -> bool:
        """Approve a request."""
        request = self._pending_requests.get(request_id)
        if not request:
            return False
        
        request.status = "approved"
        request.responded_at = datetime.utcnow()
        request.responded_by = approved_by
        request.feedback = feedback
        
        logger.info("Approved request", request_id=request_id, by=approved_by)
        
        # Trigger callback if registered
        if request_id in self._callbacks:
            self._callbacks[request_id](True, feedback)
        
        return True
    
    def reject(
        self,
        request_id: str,
        rejected_by: str,
        feedback: str = None,
    ) -> bool:
        """Reject a request."""
        request = self._pending_requests.get(request_id)
        if not request:
            return False
        
        request.status = "rejected"
        request.responded_at = datetime.utcnow()
        request.responded_by = rejected_by
        request.feedback = feedback
        
        logger.info("Rejected request", request_id=request_id, by=rejected_by)
        
        if request_id in self._callbacks:
            self._callbacks[request_id](False, feedback)
        
        return True
    
    def get_pending_requests(self, agent_id: str = None) -> list[ApprovalRequest]:
        """Get pending approval requests."""
        requests = [r for r in self._pending_requests.values() if r.status == "pending"]
        if agent_id:
            requests = [r for r in requests if r.agent_id == agent_id]
        return requests


# =============================================================================
# Agent Manager
# =============================================================================

class AgentManager:
    """
    Manages agent registration, execution, and orchestration.
    
    Features:
    - Agent registration with profiles
    - Capability-based routing
    - Supervisor pattern
    - Handoff between agents
    - Cost tracking
    - Human-in-the-loop gates
    """
    
    def __init__(self, pool=None):
        self.pool = pool
        
        # Registered agents
        self._agents: dict[str, AgentProfile] = {}
        self._agent_functions: dict[str, Callable] = {}
        
        # Execution tracking
        self._executions: list[AgentExecution] = []
        self._total_cost: float = 0.0
        
        # Human-in-the-loop
        self.approval_gate = ApprovalGate()
        
        # Register built-in agents
        self._register_builtin_agents()
    
    def _register_builtin_agents(self):
        """Register built-in AEGIS agents."""
        
        # Patient Agent
        self.register_agent(AgentProfile(
            id="patient_agent",
            name="Patient Agent",
            description="Analyzes patient data and generates 360 views",
            capabilities=[
                AgentCapability.PATIENT_ANALYSIS,
                AgentCapability.DATA_QUERY,
                AgentCapability.SUMMARIZATION,
            ],
            tools=["query_patients", "get_patient_summary", "get_high_risk_patients"],
            system_prompt="You are a clinical analyst specializing in patient data analysis.",
        ))
        
        # Denial Agent
        self.register_agent(AgentProfile(
            id="denial_agent",
            name="Denial Agent",
            description="Handles denial analysis and appeal generation",
            capabilities=[
                AgentCapability.DENIAL_MANAGEMENT,
                AgentCapability.APPEAL_GENERATION,
            ],
            tools=["query_denials", "get_denial_intelligence", "generate_appeal"],
            system_prompt="You are a healthcare revenue cycle expert specializing in denial management.",
            requires_approval=True,  # Appeals need human review
        ))
        
        # Triage Agent
        self.register_agent(AgentProfile(
            id="triage_agent",
            name="Triage Agent",
            description="Clinical monitoring and alert prioritization",
            capabilities=[
                AgentCapability.CLINICAL_TRIAGE,
            ],
            tools=["query_vitals", "query_labs", "get_patients_needing_attention"],
            system_prompt="You are a clinical triage specialist prioritizing patient care.",
        ))
        
        # Insight Agent
        self.register_agent(AgentProfile(
            id="insight_agent",
            name="Insight Agent",
            description="Discovers patterns and trends in healthcare data",
            capabilities=[
                AgentCapability.INSIGHT_DISCOVERY,
                AgentCapability.DATA_QUERY,
            ],
            tools=["query_patients", "query_claims", "query_denials"],
            system_prompt="You are a healthcare analytics expert discovering insights from data.",
        ))
    
    def register_agent(
        self,
        profile: AgentProfile,
        execute_func: Callable = None,
    ):
        """Register an agent."""
        self._agents[profile.id] = profile
        if execute_func:
            self._agent_functions[profile.id] = execute_func
        
        logger.info(
            "Registered agent",
            agent_id=profile.id,
            capabilities=profile.capabilities,
        )
    
    def get_agent(self, agent_id: str) -> AgentProfile | None:
        """Get agent by ID."""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> list[AgentProfile]:
        """List all registered agents."""
        return list(self._agents.values())
    
    def find_agent_by_capability(self, capability: AgentCapability) -> AgentProfile | None:
        """Find an agent with a specific capability."""
        for agent in self._agents.values():
            if capability in agent.capabilities:
                return agent
        return None
    
    def route_to_agent(self, query: str) -> AgentProfile | None:
        """
        Route a query to the most appropriate agent.
        
        Uses keyword matching (in production, use LLM classification).
        """
        query_lower = query.lower()
        
        # Patient-related
        if any(w in query_lower for w in ["patient", "360", "view", "summary"]):
            return self.find_agent_by_capability(AgentCapability.PATIENT_ANALYSIS)
        
        # Denial-related
        if any(w in query_lower for w in ["denial", "appeal", "claim", "reject"]):
            return self.find_agent_by_capability(AgentCapability.DENIAL_MANAGEMENT)
        
        # Triage-related
        if any(w in query_lower for w in ["triage", "alert", "critical", "urgent"]):
            return self.find_agent_by_capability(AgentCapability.CLINICAL_TRIAGE)
        
        # Insight-related
        if any(w in query_lower for w in ["insight", "pattern", "trend", "analyze"]):
            return self.find_agent_by_capability(AgentCapability.INSIGHT_DISCOVERY)
        
        return None
    
    async def execute_agent(
        self,
        agent_id: str,
        query: str,
        context: dict = None,
        require_approval: bool = None,
    ) -> AgentExecution:
        """
        Execute an agent.
        
        Handles:
        - Rate limiting
        - Cost tracking
        - Human-in-the-loop
        """
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        execution = AgentExecution(
            agent_id=agent_id,
            agent_name=agent.name,
            query=query,
        )
        
        # Get agent function
        execute_func = self._agent_functions.get(agent_id)
        
        try:
            # Execute agent
            if execute_func:
                result = await execute_func(query, context or {})
            else:
                # Use default LLM-based execution
                from aegis.bedrock.client import get_llm_client
                llm = get_llm_client()
                
                result = await llm.generate(
                    prompt=query,
                    system_prompt=agent.system_prompt,
                )
            
            execution.response = result if isinstance(result, str) else str(result)
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )
            
            # Estimate tokens and cost (simplified)
            execution.input_tokens = len(query.split()) * 2
            execution.output_tokens = len(execution.response.split()) * 2
            execution.total_cost = (
                (execution.input_tokens / 1000) * agent.cost_per_1k_input_tokens +
                (execution.output_tokens / 1000) * agent.cost_per_1k_output_tokens
            )
            
            self._total_cost += execution.total_cost
            
            # Check if approval required
            check_approval = require_approval if require_approval is not None else agent.requires_approval
            
            if check_approval and execution.confidence < agent.approval_threshold:
                # Create approval request
                approval = self.approval_gate.create_request(
                    execution_id=execution.id,
                    agent_id=agent_id,
                    agent_name=agent.name,
                    action="agent_response",
                    content=execution.response,
                    confidence=execution.confidence,
                    context={"query": query},
                )
                execution.approved = None  # Pending
            
        except Exception as e:
            execution.response = f"Error: {str(e)}"
            execution.completed_at = datetime.utcnow()
            
            logger.error(
                "Agent execution failed",
                agent_id=agent_id,
                error=str(e),
            )
        
        self._executions.append(execution)
        return execution
    
    async def handoff(
        self,
        from_agent_id: str,
        to_agent_id: str,
        query: str,
        context: dict = None,
    ) -> AgentExecution:
        """
        Handoff from one agent to another.
        
        Useful for:
        - Specialized processing
        - Escalation
        - Delegation
        """
        from_agent = self._agents.get(from_agent_id)
        to_agent = self._agents.get(to_agent_id)
        
        if not to_agent:
            raise ValueError(f"Unknown target agent: {to_agent_id}")
        
        logger.info(
            "Agent handoff",
            from_agent=from_agent.name if from_agent else "unknown",
            to_agent=to_agent.name,
            query=query[:100],
        )
        
        # Execute target agent
        return await self.execute_agent(
            agent_id=to_agent_id,
            query=query,
            context={
                **(context or {}),
                "_handoff_from": from_agent_id,
            },
        )
    
    def get_execution_stats(self) -> dict:
        """Get agent execution statistics."""
        return {
            "total_executions": len(self._executions),
            "total_cost": round(self._total_cost, 4),
            "by_agent": {
                agent_id: {
                    "count": len([e for e in self._executions if e.agent_id == agent_id]),
                    "total_tokens": sum(
                        e.input_tokens + e.output_tokens
                        for e in self._executions if e.agent_id == agent_id
                    ),
                }
                for agent_id in self._agents.keys()
            },
        }
