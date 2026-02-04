"""
Orchestrator Tool Registry

All tools available for workflows, built on the Data Moat.
Each tool can be used as a node in visual workflows.
"""

from typing import Any, Callable
from datetime import datetime
from pydantic import BaseModel, Field
import structlog

from aegis.agents.data_tools import DataMoatTools
from aegis.bedrock.client import get_llm_client

logger = structlog.get_logger(__name__)


class ToolDefinition(BaseModel):
    """Definition of a workflow tool."""
    id: str
    name: str
    description: str
    category: str
    icon: str = "tool"
    
    # Input/Output
    inputs: list[dict] = Field(default_factory=list)
    outputs: list[dict] = Field(default_factory=list)
    
    # For UI
    color: str = "#6366f1"


class ToolRegistry:
    """
    Registry of all tools available for workflows.
    
    Tools are organized by category:
    - Data Moat: Query patients, claims, denials, vitals, labs
    - Agents: Patient, Denial, Triage agents
    - LLM: Direct LLM calls with templates
    - Actions: Send alerts, create tasks, call APIs
    - Transforms: Filter, aggregate, transform data
    """
    
    def __init__(self, pool=None, tenant_id: str = "default"):
        self.pool = pool
        self.tenant_id = tenant_id
        self.data_tools = DataMoatTools(pool, tenant_id) if pool else None
        self.llm = get_llm_client()
        self._tools: dict[str, Callable] = {}
        self._definitions: dict[str, ToolDefinition] = {}
        
        # Register all tools
        self._register_data_moat_tools()
        self._register_agent_tools()
        self._register_llm_tools()
        self._register_action_tools()
        self._register_transform_tools()
    
    def _register_data_moat_tools(self):
        """Register Data Moat query tools."""
        
        # Query Patients
        self._definitions["query_patients"] = ToolDefinition(
            id="query_patients",
            name="Query Patients",
            description="Retrieve patient data from PostgreSQL/TimescaleDB",
            category="Data Moat",
            icon="users",
            color="#3b82f6",
            inputs=[
                {"name": "patient_id", "type": "string", "required": False},
                {"name": "mrn", "type": "string", "required": False},
                {"name": "limit", "type": "number", "required": False, "default": 10},
            ],
            outputs=[
                {"name": "patients", "type": "array"},
                {"name": "count", "type": "number"},
            ],
        )
        self._tools["query_patients"] = self._query_patients
        
        # Query Denials
        self._definitions["query_denials"] = ToolDefinition(
            id="query_denials",
            name="Query Denials",
            description="Retrieve denial data and analytics",
            category="Data Moat",
            icon="file-x",
            color="#ef4444",
            inputs=[
                {"name": "status", "type": "string", "required": False},
                {"name": "priority", "type": "string", "required": False},
                {"name": "days_back", "type": "number", "required": False, "default": 90},
            ],
            outputs=[
                {"name": "denials", "type": "array"},
                {"name": "summary", "type": "object"},
            ],
        )
        self._tools["query_denials"] = self._query_denials
        
        # Query Vitals
        self._definitions["query_vitals"] = ToolDefinition(
            id="query_vitals",
            name="Query Vitals",
            description="Retrieve patient vital signs from TimescaleDB",
            category="Data Moat",
            icon="heart-pulse",
            color="#10b981",
            inputs=[
                {"name": "patient_id", "type": "string", "required": False},
                {"name": "abnormal_only", "type": "boolean", "required": False},
                {"name": "hours_back", "type": "number", "required": False, "default": 24},
            ],
            outputs=[
                {"name": "vitals", "type": "array"},
            ],
        )
        self._tools["query_vitals"] = self._query_vitals
        
        # Query Labs
        self._definitions["query_labs"] = ToolDefinition(
            id="query_labs",
            name="Query Labs",
            description="Retrieve lab results from TimescaleDB",
            category="Data Moat",
            icon="flask",
            color="#8b5cf6",
            inputs=[
                {"name": "patient_id", "type": "string", "required": False},
                {"name": "critical_only", "type": "boolean", "required": False},
                {"name": "days_back", "type": "number", "required": False, "default": 30},
            ],
            outputs=[
                {"name": "labs", "type": "array"},
            ],
        )
        self._tools["query_labs"] = self._query_labs
        
        # Query Claims
        self._definitions["query_claims"] = ToolDefinition(
            id="query_claims",
            name="Query Claims",
            description="Retrieve claims data from PostgreSQL",
            category="Data Moat",
            icon="file-text",
            color="#f59e0b",
            inputs=[
                {"name": "patient_id", "type": "string", "required": False},
                {"name": "status", "type": "string", "required": False},
                {"name": "limit", "type": "number", "required": False, "default": 50},
            ],
            outputs=[
                {"name": "claims", "type": "array"},
            ],
        )
        self._tools["query_claims"] = self._query_claims
    
    def _register_agent_tools(self):
        """Register AI agent tools."""
        
        # Patient Agent
        self._definitions["patient_agent"] = ToolDefinition(
            id="patient_agent",
            name="Patient Agent",
            description="AI agent for patient analysis and recommendations",
            category="Agents",
            icon="user-check",
            color="#06b6d4",
            inputs=[
                {"name": "patient_id", "type": "string", "required": True},
                {"name": "query", "type": "string", "required": False},
            ],
            outputs=[
                {"name": "analysis", "type": "string"},
                {"name": "recommendations", "type": "array"},
            ],
        )
        self._tools["patient_agent"] = self._patient_agent
        
        # Denial Agent
        self._definitions["denial_agent"] = ToolDefinition(
            id="denial_agent",
            name="Denial Agent",
            description="AI agent for denial analysis and appeal generation",
            category="Agents",
            icon="file-search",
            color="#ec4899",
            inputs=[
                {"name": "denial_id", "type": "string", "required": False},
                {"name": "claim_id", "type": "string", "required": False},
            ],
            outputs=[
                {"name": "analysis", "type": "string"},
                {"name": "appeal_draft", "type": "string"},
            ],
        )
        self._tools["denial_agent"] = self._denial_agent
        
        # Triage Agent
        self._definitions["triage_agent"] = ToolDefinition(
            id="triage_agent",
            name="Triage Agent",
            description="AI agent for clinical triage and alert prioritization",
            category="Agents",
            icon="activity",
            color="#f43f5e",
            inputs=[
                {"name": "alerts", "type": "array", "required": False},
            ],
            outputs=[
                {"name": "prioritized_alerts", "type": "array"},
                {"name": "recommendations", "type": "array"},
            ],
        )
        self._tools["triage_agent"] = self._triage_agent
    
    def _register_llm_tools(self):
        """Register LLM tools."""
        
        self._definitions["llm_generate"] = ToolDefinition(
            id="llm_generate",
            name="LLM Generate",
            description="Generate text using LLM with custom prompt",
            category="LLM",
            icon="brain",
            color="#a855f7",
            inputs=[
                {"name": "prompt", "type": "string", "required": True},
                {"name": "system_prompt", "type": "string", "required": False},
                {"name": "temperature", "type": "number", "required": False, "default": 0.7},
            ],
            outputs=[
                {"name": "response", "type": "string"},
            ],
        )
        self._tools["llm_generate"] = self._llm_generate
        
        self._definitions["llm_classify"] = ToolDefinition(
            id="llm_classify",
            name="LLM Classify",
            description="Classify text into categories using LLM",
            category="LLM",
            icon="tags",
            color="#a855f7",
            inputs=[
                {"name": "text", "type": "string", "required": True},
                {"name": "categories", "type": "array", "required": True},
            ],
            outputs=[
                {"name": "category", "type": "string"},
                {"name": "confidence", "type": "number"},
            ],
        )
        self._tools["llm_classify"] = self._llm_classify
    
    def _register_action_tools(self):
        """Register action tools."""
        
        self._definitions["generate_appeal"] = ToolDefinition(
            id="generate_appeal",
            name="Generate Appeal",
            description="Generate denial appeal letter with supporting evidence",
            category="Actions",
            icon="file-pen",
            color="#22c55e",
            inputs=[
                {"name": "denial_id", "type": "string", "required": True},
                {"name": "additional_context", "type": "string", "required": False},
            ],
            outputs=[
                {"name": "appeal_letter", "type": "string"},
                {"name": "supporting_evidence", "type": "array"},
            ],
        )
        self._tools["generate_appeal"] = self._generate_appeal
        
        self._definitions["send_alert"] = ToolDefinition(
            id="send_alert",
            name="Send Alert",
            description="Send notification/alert to specified channels",
            category="Actions",
            icon="bell",
            color="#eab308",
            inputs=[
                {"name": "message", "type": "string", "required": True},
                {"name": "priority", "type": "string", "required": False, "default": "normal"},
                {"name": "channels", "type": "array", "required": False},
            ],
            outputs=[
                {"name": "sent", "type": "boolean"},
                {"name": "alert_id", "type": "string"},
            ],
        )
        self._tools["send_alert"] = self._send_alert
        
        self._definitions["call_api"] = ToolDefinition(
            id="call_api",
            name="Call External API",
            description="Make HTTP request to external API",
            category="Actions",
            icon="globe",
            color="#64748b",
            inputs=[
                {"name": "url", "type": "string", "required": True},
                {"name": "method", "type": "string", "required": False, "default": "GET"},
                {"name": "body", "type": "object", "required": False},
                {"name": "headers", "type": "object", "required": False},
            ],
            outputs=[
                {"name": "status_code", "type": "number"},
                {"name": "response", "type": "object"},
            ],
        )
        self._tools["call_api"] = self._call_api
    
    def _register_transform_tools(self):
        """Register data transformation tools."""
        
        self._definitions["filter_data"] = ToolDefinition(
            id="filter_data",
            name="Filter Data",
            description="Filter array data based on conditions",
            category="Transforms",
            icon="filter",
            color="#6b7280",
            inputs=[
                {"name": "data", "type": "array", "required": True},
                {"name": "condition", "type": "string", "required": True},
            ],
            outputs=[
                {"name": "filtered", "type": "array"},
                {"name": "count", "type": "number"},
            ],
        )
        self._tools["filter_data"] = self._filter_data
        
        self._definitions["aggregate_data"] = ToolDefinition(
            id="aggregate_data",
            name="Aggregate Data",
            description="Aggregate data (sum, avg, count, etc.)",
            category="Transforms",
            icon="calculator",
            color="#6b7280",
            inputs=[
                {"name": "data", "type": "array", "required": True},
                {"name": "operation", "type": "string", "required": True},
                {"name": "field", "type": "string", "required": True},
            ],
            outputs=[
                {"name": "result", "type": "number"},
            ],
        )
        self._tools["aggregate_data"] = self._aggregate_data
    
    # =========================================================================
    # Tool Implementations
    # =========================================================================
    
    async def _query_patients(self, patient_id: str = None, mrn: str = None, limit: int = 10, **kwargs) -> dict:
        """Query patient data."""
        if self.data_tools and patient_id:
            return await self.data_tools.get_patient_summary(patient_id)
        if self.data_tools:
            return await self.data_tools.get_high_risk_patients(limit=limit)
        return {"patients": [], "error": "Data tools not available"}
    
    async def _query_denials(self, status: str = None, priority: str = None, days_back: int = 90, **kwargs) -> dict:
        """Query denial data."""
        if self.data_tools:
            return await self.data_tools.get_denial_intelligence(days_back=days_back)
        return {"denials": [], "error": "Data tools not available"}
    
    async def _query_vitals(self, patient_id: str = None, abnormal_only: bool = False, hours_back: int = 24, **kwargs) -> dict:
        """Query vital signs."""
        if self.data_tools:
            attention = await self.data_tools.get_patients_needing_attention()
            return {"vitals": attention.get("patients_with_concerning_vitals", [])}
        return {"vitals": []}
    
    async def _query_labs(self, patient_id: str = None, critical_only: bool = False, days_back: int = 30, **kwargs) -> dict:
        """Query lab results."""
        if self.data_tools:
            attention = await self.data_tools.get_patients_needing_attention()
            return {"labs": attention.get("patients_with_abnormal_labs", [])}
        return {"labs": []}
    
    async def _query_claims(self, patient_id: str = None, status: str = None, limit: int = 50, **kwargs) -> dict:
        """Query claims."""
        # Would query claims table
        return {"claims": [], "message": "Claims query - implement with pool"}
    
    async def _patient_agent(self, patient_id: str, query: str = None, **kwargs) -> dict:
        """Run patient agent."""
        if self.data_tools:
            patient_data = await self.data_tools.get_patient_summary(patient_id)
            analysis = await self.llm.generate(
                prompt=f"Analyze this patient data and provide recommendations:\n{patient_data}",
                system_prompt="You are a clinical analyst providing patient insights."
            )
            return {"analysis": analysis, "patient_data": patient_data}
        return {"error": "Data tools not available"}
    
    async def _denial_agent(self, denial_id: str = None, claim_id: str = None, **kwargs) -> dict:
        """Run denial agent."""
        if self.data_tools and claim_id:
            claim_data = await self.data_tools.get_claim_for_appeal(claim_id)
            analysis = await self.llm.generate(
                prompt=f"Analyze this denied claim and suggest appeal strategy:\n{claim_data}",
                system_prompt="You are a healthcare revenue cycle expert."
            )
            return {"analysis": analysis, "claim_data": claim_data}
        return {"error": "Claim ID required"}
    
    async def _triage_agent(self, alerts: list = None, **kwargs) -> dict:
        """Run triage agent."""
        if self.data_tools:
            attention = await self.data_tools.get_patients_needing_attention()
            high_risk = await self.data_tools.get_high_risk_patients(limit=10)
            
            combined = {
                "alerts": attention,
                "high_risk": high_risk,
            }
            
            analysis = await self.llm.generate(
                prompt=f"Prioritize these clinical alerts and provide recommendations:\n{combined}",
                system_prompt="You are a clinical triage nurse prioritizing patient care."
            )
            return {"analysis": analysis, "data": combined}
        return {"error": "Data tools not available"}
    
    async def _llm_generate(self, prompt: str, system_prompt: str = None, temperature: float = 0.7, **kwargs) -> dict:
        """Generate text with LLM."""
        response = await self.llm.generate(prompt=prompt, system_prompt=system_prompt)
        return {"response": response}
    
    async def _llm_classify(self, text: str, categories: list, **kwargs) -> dict:
        """Classify text."""
        prompt = f"""Classify this text into one of these categories: {', '.join(categories)}

Text: {text}

Return ONLY the category name."""
        response = await self.llm.generate(prompt=prompt)
        return {"category": response.strip(), "confidence": 0.85}
    
    async def _generate_appeal(self, denial_id: str, additional_context: str = None, **kwargs) -> dict:
        """Generate appeal letter."""
        appeal = await self.llm.generate(
            prompt=f"Generate a denial appeal letter for denial ID: {denial_id}. Additional context: {additional_context or 'None'}",
            system_prompt="You are a healthcare appeals specialist writing professional appeal letters."
        )
        return {"appeal_letter": appeal, "supporting_evidence": []}
    
    async def _send_alert(self, message: str, priority: str = "normal", channels: list = None, **kwargs) -> dict:
        """Send alert notification."""
        # Would integrate with notification system
        logger.info("Alert sent", message=message[:100], priority=priority)
        return {"sent": True, "alert_id": f"alert-{datetime.utcnow().timestamp()}"}
    
    async def _call_api(self, url: str, method: str = "GET", body: dict = None, headers: dict = None, **kwargs) -> dict:
        """Call external API."""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, json=body, headers=headers) as resp:
                    return {"status_code": resp.status, "response": await resp.json()}
        except Exception as e:
            return {"error": str(e)}
    
    async def _filter_data(self, data: list, condition: str, **kwargs) -> dict:
        """Filter data based on condition."""
        # Simple filter - in production use safe eval
        filtered = [item for item in data if eval(condition, {"item": item})]
        return {"filtered": filtered, "count": len(filtered)}
    
    async def _aggregate_data(self, data: list, operation: str, field: str, **kwargs) -> dict:
        """Aggregate data."""
        values = [item.get(field, 0) for item in data if isinstance(item, dict)]
        if operation == "sum":
            return {"result": sum(values)}
        elif operation == "avg":
            return {"result": sum(values) / len(values) if values else 0}
        elif operation == "count":
            return {"result": len(values)}
        elif operation == "max":
            return {"result": max(values) if values else 0}
        elif operation == "min":
            return {"result": min(values) if values else 0}
        return {"result": None, "error": f"Unknown operation: {operation}"}
    
    # =========================================================================
    # Registry Methods
    # =========================================================================
    
    def get_tool(self, tool_id: str) -> Callable | None:
        """Get a tool function by ID."""
        return self._tools.get(tool_id)
    
    def get_definition(self, tool_id: str) -> ToolDefinition | None:
        """Get tool definition by ID."""
        return self._definitions.get(tool_id)
    
    def list_tools(self) -> list[ToolDefinition]:
        """List all available tools."""
        return list(self._definitions.values())
    
    def list_tools_by_category(self) -> dict[str, list[ToolDefinition]]:
        """List tools grouped by category."""
        by_category: dict[str, list[ToolDefinition]] = {}
        for tool in self._definitions.values():
            if tool.category not in by_category:
                by_category[tool.category] = []
            by_category[tool.category].append(tool)
        return by_category
    
    async def execute_tool(self, tool_id: str, inputs: dict) -> dict:
        """Execute a tool with given inputs."""
        tool = self.get_tool(tool_id)
        if not tool:
            return {"error": f"Unknown tool: {tool_id}"}
        
        try:
            result = await tool(**inputs)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Tool {tool_id} failed", error=str(e))
            return {"success": False, "error": str(e)}
