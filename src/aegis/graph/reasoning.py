"""
Reasoning_Path Nodes in Graph

Stores agent reasoning chains as graph nodes for explainability.
Every recommendation includes a Reasoning_Path node linking to evidence.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ReasoningStep:
    """A single step in a reasoning chain."""
    step_id: str
    step_type: str  # "query", "analysis", "inference", "decision"
    description: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    confidence: float
    timestamp: datetime


@dataclass
class ReasoningPath:
    """
    A reasoning path storing agent decision-making process.
    
    Links recommendations to evidence nodes in the graph.
    """
    id: str
    agent_id: str
    agent_name: str
    recommendation_id: str
    recommendation_type: str  # "medication", "procedure", "alert", etc.
    recommendation_text: str
    
    # Reasoning chain
    steps: List[ReasoningStep]
    
    # Evidence links (FHIR resource IDs)
    evidence_nodes: List[str]  # Graph node IDs
    evidence_types: List[str]  # e.g., "Observation", "Condition", "Guideline"
    
    # Conflict checks
    conflicts_checked: List[str]
    conflicts_found: List[str]
    
    # Metadata
    created_at: datetime
    tenant_id: str
    patient_id: Optional[str] = None


class ReasoningPathManager:
    """
    Manages Reasoning_Path nodes in the knowledge graph.
    
    Stores agent reasoning chains for explainability and audit trails.
    """
    
    def __init__(self, graph_client=None):
        """
        Initialize reasoning path manager.
        
        Args:
            graph_client: Graph database client
        """
        self.graph_client = graph_client
    
    async def create_reasoning_path(
        self,
        agent_id: str,
        agent_name: str,
        recommendation_id: str,
        recommendation_type: str,
        recommendation_text: str,
        steps: List[ReasoningStep],
        evidence_nodes: List[str],
        evidence_types: List[str],
        conflicts_checked: List[str],
        conflicts_found: List[str],
        tenant_id: str,
        patient_id: Optional[str] = None,
    ) -> ReasoningPath:
        """
        Create a Reasoning_Path node in the graph.
        
        Args:
            agent_id: Agent identifier
            agent_name: Agent name
            recommendation_id: Unique recommendation ID
            recommendation_type: Type of recommendation
            recommendation_text: Recommendation text
            steps: Reasoning steps
            evidence_nodes: Graph node IDs providing evidence
            evidence_types: Types of evidence (FHIR resource types)
            conflicts_checked: What conflicts were checked
            conflicts_found: Conflicts found
            tenant_id: Tenant ID
            patient_id: Patient ID (if applicable)
            
        Returns:
            ReasoningPath created
        """
        reasoning_path = ReasoningPath(
            id=f"reasoning_path:{recommendation_id}",
            agent_id=agent_id,
            agent_name=agent_name,
            recommendation_id=recommendation_id,
            recommendation_type=recommendation_type,
            recommendation_text=recommendation_text,
            steps=steps,
            evidence_nodes=evidence_nodes,
            evidence_types=evidence_types,
            conflicts_checked=conflicts_checked,
            conflicts_found=conflicts_found,
            created_at=datetime.utcnow(),
            tenant_id=tenant_id,
            patient_id=patient_id,
        )
        
        # Store in graph if available
        if self.graph_client:
            await self._store_in_graph(reasoning_path)
        
        return reasoning_path
    
    async def _store_in_graph(self, reasoning_path: ReasoningPath):
        """Store reasoning path as graph node with edges to evidence."""
        try:
            # Create Reasoning_Path vertex
            vertex_properties = {
                "id": reasoning_path.id,
                "agent_id": reasoning_path.agent_id,
                "agent_name": reasoning_path.agent_name,
                "recommendation_id": reasoning_path.recommendation_id,
                "recommendation_type": reasoning_path.recommendation_type,
                "recommendation_text": reasoning_path.recommendation_text,
                "steps": [step.__dict__ for step in reasoning_path.steps],
                "evidence_types": reasoning_path.evidence_types,
                "conflicts_checked": reasoning_path.conflicts_checked,
                "conflicts_found": reasoning_path.conflicts_found,
                "created_at": reasoning_path.created_at.isoformat(),
                "tenant_id": reasoning_path.tenant_id,
            }
            
            if hasattr(self.graph_client, 'add_vertex'):
                await self.graph_client.add_vertex(
                    label="Reasoning_Path",
                    id=reasoning_path.id,
                    properties=vertex_properties,
                )
            elif isinstance(self.graph_client, dict) and 'g' in self.graph_client:
                g = self.graph_client['g']
                g.addV("Reasoning_Path").property("id", reasoning_path.id).property(
                    "agent_name", reasoning_path.agent_name
                ).property("recommendation_text", reasoning_path.recommendation_text).iterate()
            
            # Create edges to evidence nodes
            for evidence_node_id in reasoning_path.evidence_nodes:
                if hasattr(self.graph_client, 'add_edge'):
                    await self.graph_client.add_edge(
                        from_label="Reasoning_Path",
                        from_id=reasoning_path.id,
                        to_label="Evidence",  # Generic evidence label
                        to_id=evidence_node_id,
                        edge_label="HAS_EVIDENCE",
                    )
            
            logger.info("Stored reasoning path in graph", reasoning_path_id=reasoning_path.id)
            
        except Exception as e:
            logger.error("Failed to store reasoning path in graph", error=str(e))
    
    async def get_reasoning_path(self, recommendation_id: str) -> Optional[ReasoningPath]:
        """Retrieve a reasoning path by recommendation ID."""
        if not self.graph_client:
            return None
        
        try:
            reasoning_path_id = f"reasoning_path:{recommendation_id}"
            
            if hasattr(self.graph_client, 'query'):
                results = await self.graph_client.query(
                    f"g.V().hasLabel('Reasoning_Path').has('id', '{reasoning_path_id}').valueMap(true)"
                )
                if results:
                    return self._parse_reasoning_path(results[0])
            elif isinstance(self.graph_client, dict) and 'g' in self.graph_client:
                g = self.graph_client['g']
                vertices = g.V().hasLabel("Reasoning_Path").has("id", reasoning_path_id).valueMap(True).toList()
                if vertices:
                    return self._parse_reasoning_path(dict(vertices[0]))
            
        except Exception as e:
            logger.error("Failed to retrieve reasoning path", error=str(e))
        
        return None
    
    def _parse_reasoning_path(self, vertex_data: Dict[str, Any]) -> ReasoningPath:
        """Parse graph vertex data into ReasoningPath."""
        # Simplified parsing - in production would handle all fields
        return ReasoningPath(
            id=vertex_data.get("id", ""),
            agent_id=vertex_data.get("agent_id", ""),
            agent_name=vertex_data.get("agent_name", ""),
            recommendation_id=vertex_data.get("recommendation_id", ""),
            recommendation_type=vertex_data.get("recommendation_type", ""),
            recommendation_text=vertex_data.get("recommendation_text", ""),
            steps=[],  # Would parse from vertex_data
            evidence_nodes=[],
            evidence_types=vertex_data.get("evidence_types", []),
            conflicts_checked=vertex_data.get("conflicts_checked", []),
            conflicts_found=vertex_data.get("conflicts_found", []),
            created_at=datetime.fromisoformat(vertex_data.get("created_at", datetime.utcnow().isoformat())),
            tenant_id=vertex_data.get("tenant_id", ""),
        )
    
    async def query_by_evidence(self, evidence_node_id: str) -> List[ReasoningPath]:
        """Find all reasoning paths that reference a specific evidence node."""
        if not self.graph_client:
            return []
        
        # Query graph for Reasoning_Path nodes connected to evidence
        # Implementation would traverse HAS_EVIDENCE edges
        return []
