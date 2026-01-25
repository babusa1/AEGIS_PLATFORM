"""Data Lineage Tracker - HITRUST 09.b"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid
import structlog

logger = structlog.get_logger(__name__)


class NodeType(str, Enum):
    SOURCE = "source"
    TRANSFORM = "transform"
    DESTINATION = "destination"
    DATASET = "dataset"


class OperationType(str, Enum):
    INGEST = "ingest"
    TRANSFORM = "transform"
    NORMALIZE = "normalize"
    MERGE = "merge"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    EXPORT = "export"


@dataclass
class LineageNode:
    id: str
    name: str
    node_type: NodeType
    system: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LineageEdge:
    id: str
    source_id: str
    target_id: str
    operation: OperationType
    timestamp: datetime
    record_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LineageGraph:
    nodes: dict[str, LineageNode]
    edges: list[LineageEdge]


class LineageTracker:
    """
    Track data lineage from source to destination.
    
    HITRUST 09.b: Information labeling and handling
    SOC 2 Processing Integrity: Data flow documentation
    """
    
    def __init__(self):
        self._nodes: dict[str, LineageNode] = {}
        self._edges: list[LineageEdge] = []
    
    def register_source(self, source_id: str, name: str, system: str, 
                       metadata: dict | None = None) -> LineageNode:
        """Register a data source."""
        node = LineageNode(
            id=source_id,
            name=name,
            node_type=NodeType.SOURCE,
            system=system,
            metadata=metadata or {}
        )
        self._nodes[source_id] = node
        return node
    
    def register_transform(self, transform_id: str, name: str,
                          metadata: dict | None = None) -> LineageNode:
        """Register a transformation step."""
        node = LineageNode(
            id=transform_id,
            name=name,
            node_type=NodeType.TRANSFORM,
            system="aegis",
            metadata=metadata or {}
        )
        self._nodes[transform_id] = node
        return node
    
    def register_destination(self, dest_id: str, name: str, system: str,
                            metadata: dict | None = None) -> LineageNode:
        """Register a data destination."""
        node = LineageNode(
            id=dest_id,
            name=name,
            node_type=NodeType.DESTINATION,
            system=system,
            metadata=metadata or {}
        )
        self._nodes[dest_id] = node
        return node
    
    def record_flow(self, source_id: str, target_id: str, operation: OperationType,
                   record_count: int | None = None, metadata: dict | None = None) -> LineageEdge:
        """Record data flow between nodes."""
        edge = LineageEdge(
            id=f"edge-{uuid.uuid4().hex[:8]}",
            source_id=source_id,
            target_id=target_id,
            operation=operation,
            timestamp=datetime.utcnow(),
            record_count=record_count,
            metadata=metadata or {}
        )
        self._edges.append(edge)
        
        logger.debug("Lineage recorded", source=source_id, target=target_id, op=operation.value)
        return edge
    
    def get_upstream(self, node_id: str) -> list[LineageNode]:
        """Get all upstream nodes (data sources)."""
        upstream = []
        visited = set()
        
        def traverse(nid):
            if nid in visited:
                return
            visited.add(nid)
            
            for edge in self._edges:
                if edge.target_id == nid:
                    source = self._nodes.get(edge.source_id)
                    if source:
                        upstream.append(source)
                        traverse(edge.source_id)
        
        traverse(node_id)
        return upstream
    
    def get_downstream(self, node_id: str) -> list[LineageNode]:
        """Get all downstream nodes (data consumers)."""
        downstream = []
        visited = set()
        
        def traverse(nid):
            if nid in visited:
                return
            visited.add(nid)
            
            for edge in self._edges:
                if edge.source_id == nid:
                    target = self._nodes.get(edge.target_id)
                    if target:
                        downstream.append(target)
                        traverse(edge.target_id)
        
        traverse(node_id)
        return downstream
    
    def get_lineage_path(self, source_id: str, target_id: str) -> list[LineageEdge]:
        """Get the lineage path between two nodes."""
        # Simple BFS to find path
        from collections import deque
        
        queue = deque([(source_id, [])])
        visited = set()
        
        while queue:
            current, path = queue.popleft()
            if current == target_id:
                return path
            
            if current in visited:
                continue
            visited.add(current)
            
            for edge in self._edges:
                if edge.source_id == current:
                    queue.append((edge.target_id, path + [edge]))
        
        return []  # No path found
    
    def get_impact_analysis(self, node_id: str) -> dict:
        """Analyze impact of changes to a node."""
        downstream = self.get_downstream(node_id)
        
        return {
            "node_id": node_id,
            "affected_nodes": len(downstream),
            "affected_systems": list(set(n.system for n in downstream)),
            "downstream": [{"id": n.id, "name": n.name, "system": n.system} for n in downstream]
        }
    
    def export_graph(self) -> LineageGraph:
        """Export the full lineage graph."""
        return LineageGraph(nodes=self._nodes, edges=self._edges)
