"""
Workflow Engine

Dynamically builds and executes LangGraph workflows from definitions.
This is the core of the AEGIS orchestration platform.
"""

from typing import Any
from datetime import datetime
import json

import structlog
from langgraph.graph import StateGraph, END

from aegis.orchestrator.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowEdge,
    WorkflowExecution,
    NodeExecution,
    ExecutionStatus,
    NodeType,
)
from aegis.orchestrator.tools import ToolRegistry

logger = structlog.get_logger(__name__)


class WorkflowEngine:
    """
    Dynamic Workflow Engine
    
    Takes a WorkflowDefinition and:
    1. Builds a LangGraph StateGraph
    2. Executes it with given inputs
    3. Returns execution trace and results
    
    This is your own orchestration engine - no need for n8n!
    """
    
    def __init__(self, pool=None, tenant_id: str = "default"):
        self.pool = pool
        self.tenant_id = tenant_id
        self.tool_registry = ToolRegistry(pool, tenant_id)
    
    async def execute(
        self,
        workflow: WorkflowDefinition,
        inputs: dict,
        user_id: str | None = None,
    ) -> WorkflowExecution:
        """
        Execute a workflow with given inputs.
        
        Args:
            workflow: The workflow definition to execute
            inputs: Input data for the workflow
            user_id: Optional user ID for tracking
            
        Returns:
            WorkflowExecution with results and trace
        """
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            input_data=inputs,
            tenant_id=self.tenant_id,
            user_id=user_id,
            status=ExecutionStatus.RUNNING,
        )
        
        logger.info(
            "Starting workflow execution",
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            execution_id=execution.id,
        )
        
        try:
            # Build the LangGraph from definition
            graph = self._build_graph(workflow, execution)
            compiled = graph.compile()
            
            # Create initial state
            initial_state = {
                "inputs": inputs,
                "outputs": {},
                "current_node": None,
                "execution_id": execution.id,
            }
            
            # Execute
            final_state = await compiled.ainvoke(initial_state)
            
            # Update execution
            execution.status = ExecutionStatus.COMPLETED
            execution.output_data = final_state.get("outputs", {})
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )
            
            logger.info(
                "Workflow completed",
                execution_id=execution.id,
                duration_ms=execution.duration_ms,
            )
            
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )
            
            logger.error(
                "Workflow failed",
                execution_id=execution.id,
                error=str(e),
            )
        
        return execution
    
    def _build_graph(self, workflow: WorkflowDefinition, execution: WorkflowExecution) -> StateGraph:
        """
        Build a LangGraph from workflow definition.
        """
        # Create state graph
        graph = StateGraph(dict)
        
        # Build node lookup
        nodes_by_id = {node.id: node for node in workflow.nodes}
        
        # Find start and end nodes
        start_node = None
        end_nodes = []
        
        for node in workflow.nodes:
            if node.type == NodeType.START:
                start_node = node
            elif node.type == NodeType.END:
                end_nodes.append(node)
        
        if not start_node:
            raise ValueError("Workflow must have a START node")
        
        # Add nodes to graph
        for node in workflow.nodes:
            if node.type not in [NodeType.START, NodeType.END]:
                # Create node function
                node_func = self._create_node_function(node, execution)
                graph.add_node(node.id, node_func)
        
        # Set entry point (first node after START)
        start_edges = [e for e in workflow.edges if e.source == start_node.id]
        if start_edges:
            entry_node = start_edges[0].target
            graph.set_entry_point(entry_node)
        
        # Add edges
        for edge in workflow.edges:
            if edge.source == start_node.id:
                continue  # Entry point already set
            
            source_node = nodes_by_id.get(edge.source)
            target_node = nodes_by_id.get(edge.target)
            
            if not source_node or not target_node:
                continue
            
            # Check if source is a router node
            if source_node.type == NodeType.ROUTER:
                # Add conditional edge
                # For now, add all routes
                routes = source_node.config.routes or []
                if routes:
                    route_map = {}
                    for route in routes:
                        route_map[route.get("condition", "default")] = route.get("target")
                    
                    def router_func(state, routes=routes):
                        # Simple routing based on state
                        for route in routes:
                            condition = route.get("condition", "")
                            if condition == "default" or self._evaluate_condition(condition, state):
                                return route.get("target")
                        return routes[0].get("target") if routes else END
                    
                    graph.add_conditional_edges(source_node.id, router_func, route_map)
                else:
                    # No routes defined, go to target
                    if target_node.type == NodeType.END:
                        graph.add_edge(source_node.id, END)
                    else:
                        graph.add_edge(source_node.id, target_node.id)
            else:
                # Regular edge
                if target_node.type == NodeType.END:
                    graph.add_edge(source_node.id, END)
                else:
                    graph.add_edge(source_node.id, target_node.id)
        
        return graph
    
    def _create_node_function(self, node: WorkflowNode, execution: WorkflowExecution):
        """
        Create an async function for a workflow node.
        """
        async def node_func(state: dict) -> dict:
            start_time = datetime.utcnow()
            
            node_execution = NodeExecution(
                node_id=node.id,
                node_name=node.name,
                node_type=node.type,
                status=ExecutionStatus.RUNNING,
                started_at=start_time,
                input_data=state.get("outputs", {}),
            )
            
            try:
                # Execute based on node type
                result = await self._execute_node(node, state)
                
                # Update state
                outputs = state.get("outputs", {})
                outputs[node.id] = result
                
                # Update node execution
                node_execution.status = ExecutionStatus.COMPLETED
                node_execution.output_data = result
                node_execution.completed_at = datetime.utcnow()
                node_execution.duration_ms = int(
                    (node_execution.completed_at - start_time).total_seconds() * 1000
                )
                
                # Add to execution trace
                execution.node_executions.append(node_execution)
                execution.execution_path.append(node.id)
                
                return {"outputs": outputs, "current_node": node.id}
                
            except Exception as e:
                node_execution.status = ExecutionStatus.FAILED
                node_execution.error = str(e)
                node_execution.completed_at = datetime.utcnow()
                execution.node_executions.append(node_execution)
                raise
        
        return node_func
    
    async def _execute_node(self, node: WorkflowNode, state: dict) -> dict:
        """
        Execute a single node based on its type.
        """
        inputs = state.get("inputs", {})
        outputs = state.get("outputs", {})
        
        # Merge previous outputs into inputs
        merged_inputs = {**inputs}
        for node_id, node_output in outputs.items():
            if isinstance(node_output, dict):
                merged_inputs.update(node_output)
        
        # Execute based on type
        if node.type == NodeType.AGENT:
            agent_type = node.config.agent_type
            tool = self.tool_registry.get_tool(agent_type)
            if tool:
                return await tool(**merged_inputs)
            return {"error": f"Unknown agent: {agent_type}"}
        
        elif node.type == NodeType.LLM:
            tool = self.tool_registry.get_tool("llm_generate")
            prompt = self._render_template(node.config.prompt_template or "", merged_inputs)
            return await tool(
                prompt=prompt,
                system_prompt=node.config.system_prompt,
                temperature=node.config.temperature,
            )
        
        elif node.type in [NodeType.QUERY_PATIENTS, NodeType.QUERY_CLAIMS, 
                          NodeType.QUERY_DENIALS, NodeType.QUERY_VITALS, NodeType.QUERY_LABS]:
            tool_id = node.type.value
            tool = self.tool_registry.get_tool(tool_id)
            if tool:
                return await tool(**merged_inputs, **(node.config.filters or {}))
            return {"error": f"Tool not found: {tool_id}"}
        
        elif node.type == NodeType.GENERATE_APPEAL:
            tool = self.tool_registry.get_tool("generate_appeal")
            if tool:
                return await tool(**merged_inputs)
            return {"error": "Appeal tool not found"}
        
        elif node.type == NodeType.SEND_ALERT:
            tool = self.tool_registry.get_tool("send_alert")
            if tool:
                return await tool(**merged_inputs)
            return {"error": "Alert tool not found"}
        
        elif node.type == NodeType.CALL_API:
            tool = self.tool_registry.get_tool("call_api")
            if tool:
                url = self._render_template(node.config.url or "", merged_inputs)
                body = json.loads(self._render_template(
                    json.dumps(node.config.body_template or {}), merged_inputs
                )) if node.config.body_template else None
                return await tool(
                    url=url,
                    method=node.config.method,
                    body=body,
                    headers=node.config.headers,
                )
            return {"error": "API tool not found"}
        
        elif node.type == NodeType.TRANSFORM:
            # Execute transform code (safely)
            try:
                result = self._render_template(node.config.transform_code or "", merged_inputs)
                return {"transformed": result}
            except Exception as e:
                return {"error": str(e)}
        
        elif node.type == NodeType.FILTER:
            tool = self.tool_registry.get_tool("filter_data")
            if tool:
                return await tool(**merged_inputs)
            return {"error": "Filter tool not found"}
        
        elif node.type == NodeType.AGGREGATE:
            tool = self.tool_registry.get_tool("aggregate_data")
            if tool:
                return await tool(**merged_inputs)
            return {"error": "Aggregate tool not found"}
        
        elif node.type == NodeType.ROUTER:
            # Router just passes through, routing is handled by edges
            return {"routed": True}
        
        elif node.type == NodeType.MERGE:
            # Merge combines all inputs
            return {"merged": merged_inputs}
        
        elif node.type == NodeType.PARALLEL:
            # Parallel would spawn multiple branches - simplified here
            return {"parallel": True}
        
        elif node.type == NodeType.CONDITION:
            # Evaluate condition
            routes = node.config.routes or []
            for route in routes:
                if self._evaluate_condition(route.get("condition", ""), merged_inputs):
                    return {"condition_result": route.get("target")}
            return {"condition_result": "default"}
        
        return {"error": f"Unknown node type: {node.type}"}
    
    def _render_template(self, template: str, data: dict) -> str:
        """
        Simple template rendering (use Jinja2 for production).
        """
        result = template
        for key, value in data.items():
            placeholder = "{{" + key + "}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result
    
    def _evaluate_condition(self, condition: str, data: dict) -> bool:
        """
        Evaluate a condition expression.
        """
        if not condition or condition == "default":
            return True
        
        try:
            # Safe evaluation (in production, use a proper expression evaluator)
            return eval(condition, {"__builtins__": {}}, data)
        except:
            return False
    
    # =========================================================================
    # Workflow Management
    # =========================================================================
    
    async def save_workflow(self, workflow: WorkflowDefinition) -> str:
        """Save workflow definition to database."""
        if not self.pool:
            logger.warning("No database pool, workflow not persisted")
            return workflow.id
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO workflow_definitions 
                (id, name, description, version, nodes, edges, tenant_id, created_by, tags)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (tenant_id, name, version) 
                DO UPDATE SET nodes = $5, edges = $6, updated_at = NOW()
            """,
                workflow.id,
                workflow.name,
                workflow.description,
                workflow.version,
                json.dumps([n.model_dump() for n in workflow.nodes]),
                json.dumps([e.model_dump() for e in workflow.edges]),
                workflow.tenant_id,
                workflow.created_by,
                workflow.tags,
            )
        
        return workflow.id
    
    async def load_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        """Load workflow definition from database."""
        if not self.pool:
            return None
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM workflow_definitions WHERE id = $1
            """, workflow_id)
        
        if not row:
            return None
        
        return WorkflowDefinition(
            id=str(row["id"]),
            name=row["name"],
            description=row["description"],
            version=row["version"],
            nodes=[WorkflowNode(**n) for n in row["nodes"]],
            edges=[WorkflowEdge(**e) for e in row["edges"]],
            tenant_id=row["tenant_id"],
            created_by=row["created_by"],
            tags=row["tags"],
            is_active=row["is_active"],
            is_template=row["is_template"],
        )
    
    async def list_workflows(self, include_templates: bool = True) -> list[dict]:
        """List all workflows."""
        if not self.pool:
            return []
        
        async with self.pool.acquire() as conn:
            if include_templates:
                rows = await conn.fetch("""
                    SELECT id, name, description, version, is_template, tags, created_at
                    FROM workflow_definitions 
                    WHERE tenant_id = $1 AND is_active = true
                    ORDER BY created_at DESC
                """, self.tenant_id)
            else:
                rows = await conn.fetch("""
                    SELECT id, name, description, version, is_template, tags, created_at
                    FROM workflow_definitions 
                    WHERE tenant_id = $1 AND is_active = true AND is_template = false
                    ORDER BY created_at DESC
                """, self.tenant_id)
        
        return [dict(row) for row in rows]
    
    async def save_execution(self, execution: WorkflowExecution) -> str:
        """Save execution record to database."""
        if not self.pool:
            return execution.id
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO workflow_executions 
                (id, workflow_id, workflow_name, status, started_at, completed_at, 
                 duration_ms, input_data, output_data, error, node_executions, 
                 execution_path, tenant_id, user_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
                execution.id,
                execution.workflow_id,
                execution.workflow_name,
                execution.status.value,
                execution.started_at,
                execution.completed_at,
                execution.duration_ms,
                json.dumps(execution.input_data),
                json.dumps(execution.output_data) if execution.output_data else None,
                execution.error,
                json.dumps([ne.model_dump() for ne in execution.node_executions]),
                execution.execution_path,
                execution.tenant_id,
                execution.user_id,
            )
        
        return execution.id
    
    async def get_execution_history(self, workflow_id: str = None, limit: int = 50) -> list[dict]:
        """Get execution history."""
        if not self.pool:
            return []
        
        async with self.pool.acquire() as conn:
            if workflow_id:
                rows = await conn.fetch("""
                    SELECT id, workflow_name, status, started_at, completed_at, duration_ms
                    FROM workflow_executions 
                    WHERE workflow_id = $1 AND tenant_id = $2
                    ORDER BY started_at DESC
                    LIMIT $3
                """, workflow_id, self.tenant_id, limit)
            else:
                rows = await conn.fetch("""
                    SELECT id, workflow_name, status, started_at, completed_at, duration_ms
                    FROM workflow_executions 
                    WHERE tenant_id = $1
                    ORDER BY started_at DESC
                    LIMIT $2
                """, self.tenant_id, limit)
        
        return [dict(row) for row in rows]
