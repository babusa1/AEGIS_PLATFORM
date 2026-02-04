"""
Orchestrator Models

Data models for workflow definitions, nodes, and executions.
These are stored in PostgreSQL as part of the Data Moat.
"""

from enum import Enum
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
import uuid


class NodeType(str, Enum):
    """Types of nodes in a workflow."""
    # Control Flow
    START = "start"
    END = "end"
    ROUTER = "router"  # LLM-based routing
    CONDITION = "condition"  # Rule-based branching
    PARALLEL = "parallel"  # Run multiple branches
    MERGE = "merge"  # Combine parallel branches
    
    # Agents
    AGENT = "agent"  # LangGraph agent
    LLM = "llm"  # Direct LLM call
    
    # Data Moat Tools
    QUERY_PATIENTS = "query_patients"
    QUERY_CLAIMS = "query_claims"
    QUERY_DENIALS = "query_denials"
    QUERY_VITALS = "query_vitals"
    QUERY_LABS = "query_labs"
    
    # Actions
    GENERATE_APPEAL = "generate_appeal"
    SEND_ALERT = "send_alert"
    CREATE_TASK = "create_task"
    CALL_API = "call_api"
    
    # Transforms
    TRANSFORM = "transform"  # Data transformation
    FILTER = "filter"  # Filter data
    AGGREGATE = "aggregate"  # Aggregate data


class NodeConfig(BaseModel):
    """Configuration for a workflow node."""
    # For AGENT nodes
    agent_type: str | None = None  # patient_agent, denial_agent, triage_agent
    
    # For LLM nodes
    prompt_template: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    temperature: float = 0.7
    
    # For QUERY nodes
    query_template: str | None = None
    filters: dict | None = None
    limit: int | None = None
    
    # For ROUTER/CONDITION nodes
    routes: list[dict] | None = None  # [{condition: "...", target: "node_id"}]
    
    # For CALL_API nodes
    url: str | None = None
    method: str = "POST"
    headers: dict | None = None
    body_template: str | None = None
    
    # For TRANSFORM nodes
    transform_code: str | None = None  # Python code or Jinja template
    
    # General
    timeout_seconds: int = 60
    retry_count: int = 0


class WorkflowNode(BaseModel):
    """A node in a workflow."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: NodeType
    name: str
    description: str | None = None
    config: NodeConfig = Field(default_factory=NodeConfig)
    
    # Position for visual editor
    position_x: int = 0
    position_y: int = 0
    
    class Config:
        use_enum_values = True


class WorkflowEdge(BaseModel):
    """An edge connecting two nodes."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str  # Source node ID
    target: str  # Target node ID
    label: str | None = None  # For conditional edges
    condition: str | None = None  # Expression for conditional routing


class WorkflowDefinition(BaseModel):
    """A complete workflow definition."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str | None = None
    version: int = 1
    
    # Graph structure
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = None
    tenant_id: str = "default"
    
    # Settings
    is_active: bool = True
    is_template: bool = False
    tags: list[str] = Field(default_factory=list)
    
    # Input/Output schema
    input_schema: dict | None = None
    output_schema: dict | None = None


class ExecutionStatus(str, Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeExecution(BaseModel):
    """Execution record for a single node."""
    node_id: str
    node_name: str
    node_type: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0
    
    input_data: dict | None = None
    output_data: dict | None = None
    error: str | None = None


class WorkflowExecution(BaseModel):
    """A single execution of a workflow."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    workflow_name: str
    
    status: ExecutionStatus = ExecutionStatus.PENDING
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    duration_ms: int = 0
    
    # Input/Output
    input_data: dict = Field(default_factory=dict)
    output_data: dict | None = None
    error: str | None = None
    
    # Trace
    node_executions: list[NodeExecution] = Field(default_factory=list)
    
    # Context
    tenant_id: str = "default"
    user_id: str | None = None
    
    # The execution path taken
    execution_path: list[str] = Field(default_factory=list)


# =============================================================================
# SQL Schema for PostgreSQL
# =============================================================================

WORKFLOW_SCHEMA_SQL = """
-- Workflow Definitions
CREATE TABLE IF NOT EXISTS workflow_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version INT DEFAULT 1,
    
    -- Graph structure stored as JSONB
    nodes JSONB NOT NULL DEFAULT '[]',
    edges JSONB NOT NULL DEFAULT '[]',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    tenant_id VARCHAR(100) DEFAULT 'default',
    
    -- Settings
    is_active BOOLEAN DEFAULT true,
    is_template BOOLEAN DEFAULT false,
    tags TEXT[] DEFAULT '{}',
    
    -- Schema
    input_schema JSONB,
    output_schema JSONB,
    
    -- Indexes
    UNIQUE(tenant_id, name, version)
);

CREATE INDEX idx_workflow_tenant ON workflow_definitions(tenant_id);
CREATE INDEX idx_workflow_active ON workflow_definitions(is_active);
CREATE INDEX idx_workflow_template ON workflow_definitions(is_template);

-- Workflow Executions
CREATE TABLE IF NOT EXISTS workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflow_definitions(id),
    workflow_name VARCHAR(255) NOT NULL,
    
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    
    -- Timing
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_ms INT DEFAULT 0,
    
    -- Input/Output
    input_data JSONB DEFAULT '{}',
    output_data JSONB,
    error TEXT,
    
    -- Trace
    node_executions JSONB DEFAULT '[]',
    execution_path TEXT[] DEFAULT '{}',
    
    -- Context
    tenant_id VARCHAR(100) DEFAULT 'default',
    user_id VARCHAR(255)
);

CREATE INDEX idx_execution_workflow ON workflow_executions(workflow_id);
CREATE INDEX idx_execution_status ON workflow_executions(status);
CREATE INDEX idx_execution_tenant ON workflow_executions(tenant_id);
CREATE INDEX idx_execution_started ON workflow_executions(started_at DESC);

-- Workflow Templates (pre-built workflows)
INSERT INTO workflow_definitions (name, description, is_template, tags, nodes, edges)
VALUES 
(
    'Patient Risk Assessment',
    'Analyze patient data and generate risk score with recommendations',
    true,
    ARRAY['patient', 'risk', 'clinical'],
    '[
        {"id": "start", "type": "start", "name": "Start", "position_x": 100, "position_y": 100},
        {"id": "get_patient", "type": "query_patients", "name": "Get Patient Data", "config": {"query_template": "patient_360"}, "position_x": 100, "position_y": 200},
        {"id": "analyze_risk", "type": "llm", "name": "Analyze Risk Factors", "config": {"prompt_template": "Analyze risk factors for this patient: {{patient_data}}"}, "position_x": 100, "position_y": 300},
        {"id": "generate_recs", "type": "agent", "name": "Generate Recommendations", "config": {"agent_type": "patient_agent"}, "position_x": 100, "position_y": 400},
        {"id": "end", "type": "end", "name": "End", "position_x": 100, "position_y": 500}
    ]',
    '[
        {"source": "start", "target": "get_patient"},
        {"source": "get_patient", "target": "analyze_risk"},
        {"source": "analyze_risk", "target": "generate_recs"},
        {"source": "generate_recs", "target": "end"}
    ]'
),
(
    'Denial Appeal Workflow',
    'Analyze denied claim and generate appeal letter with supporting evidence',
    true,
    ARRAY['denial', 'appeal', 'revenue'],
    '[
        {"id": "start", "type": "start", "name": "Start", "position_x": 100, "position_y": 100},
        {"id": "get_denial", "type": "query_denials", "name": "Get Denial Details", "position_x": 100, "position_y": 200},
        {"id": "get_patient", "type": "query_patients", "name": "Get Patient Clinical Data", "position_x": 100, "position_y": 300},
        {"id": "analyze", "type": "llm", "name": "Analyze Denial Reason", "config": {"prompt_template": "Analyze why this claim was denied and identify appeal strategy"}, "position_x": 100, "position_y": 400},
        {"id": "generate_appeal", "type": "generate_appeal", "name": "Generate Appeal Letter", "position_x": 100, "position_y": 500},
        {"id": "end", "type": "end", "name": "End", "position_x": 100, "position_y": 600}
    ]',
    '[
        {"source": "start", "target": "get_denial"},
        {"source": "get_denial", "target": "get_patient"},
        {"source": "get_patient", "target": "analyze"},
        {"source": "analyze", "target": "generate_appeal"},
        {"source": "generate_appeal", "target": "end"}
    ]'
),
(
    'Clinical Triage Alert',
    'Monitor patients and generate alerts for those needing attention',
    true,
    ARRAY['triage', 'alert', 'clinical'],
    '[
        {"id": "start", "type": "start", "name": "Start", "position_x": 100, "position_y": 100},
        {"id": "scan_vitals", "type": "query_vitals", "name": "Scan Recent Vitals", "config": {"filters": {"abnormal": true}}, "position_x": 100, "position_y": 200},
        {"id": "scan_labs", "type": "query_labs", "name": "Scan Recent Labs", "config": {"filters": {"critical": true}}, "position_x": 300, "position_y": 200},
        {"id": "merge", "type": "merge", "name": "Combine Alerts", "position_x": 200, "position_y": 300},
        {"id": "prioritize", "type": "agent", "name": "Prioritize Alerts", "config": {"agent_type": "triage_agent"}, "position_x": 200, "position_y": 400},
        {"id": "send_alerts", "type": "send_alert", "name": "Send Notifications", "position_x": 200, "position_y": 500},
        {"id": "end", "type": "end", "name": "End", "position_x": 200, "position_y": 600}
    ]',
    '[
        {"source": "start", "target": "scan_vitals"},
        {"source": "start", "target": "scan_labs"},
        {"source": "scan_vitals", "target": "merge"},
        {"source": "scan_labs", "target": "merge"},
        {"source": "merge", "target": "prioritize"},
        {"source": "prioritize", "target": "send_alerts"},
        {"source": "send_alerts", "target": "end"}
    ]'
)
ON CONFLICT DO NOTHING;
"""
