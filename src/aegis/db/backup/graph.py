"""
Graph Database Backup Operations

Supports:
- JanusGraph export/import
- Neptune snapshot management
- GraphML, JSON, Gremlin formats
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator
from enum import Enum
import asyncio
import json
import structlog

logger = structlog.get_logger(__name__)


class GraphExportFormat(str, Enum):
    """Supported export formats."""
    GRAPHML = "graphml"
    JSON = "json"
    GREMLIN = "gremlin"  # Gremlin script for replay


@dataclass
class GraphBackupConfig:
    """Configuration for graph database backup."""
    host: str = "localhost"
    port: int = 8182
    use_ssl: bool = False
    backup_dir: str = "./backups/graph"
    batch_size: int = 1000


@dataclass
class GraphBackupResult:
    """Result of a graph backup operation."""
    success: bool
    format: GraphExportFormat
    file_path: str
    vertex_count: int = 0
    edge_count: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


class GraphBackup:
    """
    Graph database backup and restore operations.
    
    Supports JanusGraph and Neptune-compatible operations.
    """
    
    def __init__(self, config: GraphBackupConfig, graph_client: Any = None):
        self.config = config
        self.graph_client = graph_client
        self._ensure_backup_dir()
    
    def _ensure_backup_dir(self):
        """Ensure backup directory exists."""
        Path(self.config.backup_dir).mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, format: GraphExportFormat) -> str:
        """Generate backup filename."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        ext_map = {
            GraphExportFormat.GRAPHML: ".graphml",
            GraphExportFormat.JSON: ".json",
            GraphExportFormat.GREMLIN: ".groovy",
        }
        return f"graph_{timestamp}{ext_map[format]}"
    
    async def _get_traversal(self):
        """Get Gremlin traversal source."""
        if self.graph_client and isinstance(self.graph_client, dict):
            return self.graph_client.get("g")
        return None
    
    async def export_to_json(
        self,
        custom_filename: str | None = None,
        vertex_labels: list[str] | None = None,
    ) -> GraphBackupResult:
        """
        Export graph to JSON format.
        
        Args:
            custom_filename: Optional custom filename
            vertex_labels: Optional filter to specific vertex labels
        
        Returns:
            GraphBackupResult
        """
        start_time = datetime.now(timezone.utc)
        filename = custom_filename or self._generate_filename(GraphExportFormat.JSON)
        file_path = Path(self.config.backup_dir) / filename
        
        result = GraphBackupResult(
            success=False,
            format=GraphExportFormat.JSON,
            file_path=str(file_path),
        )
        
        try:
            g = await self._get_traversal()
            if not g:
                result.errors.append("Graph traversal not available")
                return result
            
            logger.info("Starting graph JSON export")
            
            # Export vertices
            vertices = []
            vertex_query = g.V()
            if vertex_labels:
                vertex_query = vertex_query.hasLabel(*vertex_labels)
            
            vertex_data = vertex_query.valueMap(True).toList()
            for v in vertex_data:
                vertex = {
                    "id": str(v.get("id", [None])[0] if isinstance(v.get("id"), list) else v.get("id")),
                    "label": v.get("label", [""])[0] if isinstance(v.get("label"), list) else v.get("label", ""),
                    "properties": {}
                }
                for key, value in v.items():
                    if key not in ["id", "label"]:
                        vertex["properties"][key] = value[0] if isinstance(value, list) and len(value) == 1 else value
                vertices.append(vertex)
            
            result.vertex_count = len(vertices)
            
            # Export edges
            edges = []
            edge_data = g.E().project("id", "label", "outV", "inV", "properties").by("id").by("label").by(
                "outV").by("inV").by("valueMap").toList()
            
            for e in edge_data:
                edge = {
                    "id": str(e.get("id")),
                    "label": e.get("label", ""),
                    "outV": str(e.get("outV")),
                    "inV": str(e.get("inV")),
                    "properties": e.get("properties", {}),
                }
                edges.append(edge)
            
            result.edge_count = len(edges)
            
            # Write to file
            export_data = {
                "exported_at": start_time.isoformat(),
                "vertex_count": result.vertex_count,
                "edge_count": result.edge_count,
                "vertices": vertices,
                "edges": edges,
            }
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, default=str)
            
            end_time = datetime.now(timezone.utc)
            result.duration_seconds = (end_time - start_time).total_seconds()
            result.success = True
            
            logger.info(
                "Graph JSON export completed",
                vertices=result.vertex_count,
                edges=result.edge_count,
                file=str(file_path),
            )
            
            return result
            
        except Exception as e:
            result.errors.append(str(e))
            logger.error("Graph JSON export failed", error=str(e))
            return result
    
    async def export_to_gremlin(
        self,
        custom_filename: str | None = None,
    ) -> GraphBackupResult:
        """
        Export graph as Gremlin script for replay.
        
        Creates a script that can recreate the graph.
        """
        start_time = datetime.now(timezone.utc)
        filename = custom_filename or self._generate_filename(GraphExportFormat.GREMLIN)
        file_path = Path(self.config.backup_dir) / filename
        
        result = GraphBackupResult(
            success=False,
            format=GraphExportFormat.GREMLIN,
            file_path=str(file_path),
        )
        
        try:
            g = await self._get_traversal()
            if not g:
                result.errors.append("Graph traversal not available")
                return result
            
            logger.info("Starting Gremlin script export")
            
            lines = [
                "// AEGIS Graph Export",
                f"// Exported at: {start_time.isoformat()}",
                "// Run this script to restore the graph",
                "",
                "// Clear existing graph (uncomment if needed)",
                "// g.V().drop().iterate()",
                "",
                "// ===== VERTICES =====",
            ]
            
            # Export vertices
            vertex_data = g.V().valueMap(True).toList()
            for v in vertex_data:
                vid = v.get("id", [None])
                vid = vid[0] if isinstance(vid, list) else vid
                label = v.get("label", ["vertex"])
                label = label[0] if isinstance(label, list) else label
                
                props = []
                for key, value in v.items():
                    if key not in ["id", "label"]:
                        val = value[0] if isinstance(value, list) and len(value) == 1 else value
                        if isinstance(val, str):
                            props.append(f"property('{key}', '{val}')")
                        elif val is not None:
                            props.append(f"property('{key}', {val})")
                
                prop_str = "." + ".".join(props) if props else ""
                lines.append(f"g.addV('{label}').property('id', '{vid}'){prop_str}")
                result.vertex_count += 1
            
            lines.extend(["", "// ===== EDGES ====="])
            
            # Export edges
            edge_data = g.E().project("id", "label", "outV", "inV").by("id").by("label").by("outV").by("inV").toList()
            for e in edge_data:
                out_v = e.get("outV")
                in_v = e.get("inV")
                label = e.get("label", "edge")
                
                lines.append(
                    f"g.V().has('id', '{out_v}').addE('{label}').to(g.V().has('id', '{in_v}'))"
                )
                result.edge_count += 1
            
            # Write script
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            
            end_time = datetime.now(timezone.utc)
            result.duration_seconds = (end_time - start_time).total_seconds()
            result.success = True
            
            logger.info(
                "Gremlin script export completed",
                vertices=result.vertex_count,
                edges=result.edge_count,
            )
            
            return result
            
        except Exception as e:
            result.errors.append(str(e))
            logger.error("Gremlin export failed", error=str(e))
            return result
    
    async def import_from_json(
        self,
        file_path: str,
        clear_existing: bool = False,
    ) -> GraphBackupResult:
        """
        Import graph from JSON export.
        
        Args:
            file_path: Path to JSON export file
            clear_existing: Whether to clear existing graph first
        
        Returns:
            GraphBackupResult
        """
        start_time = datetime.now(timezone.utc)
        
        result = GraphBackupResult(
            success=False,
            format=GraphExportFormat.JSON,
            file_path=file_path,
        )
        
        try:
            g = await self._get_traversal()
            if not g:
                result.errors.append("Graph traversal not available")
                return result
            
            # Load JSON
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            logger.info(
                "Starting graph import",
                vertices=len(data.get("vertices", [])),
                edges=len(data.get("edges", [])),
            )
            
            # Clear if requested
            if clear_existing:
                g.V().drop().iterate()
                logger.info("Cleared existing graph")
            
            # Import vertices
            vertex_id_map = {}  # Map original IDs to new IDs
            for vertex in data.get("vertices", []):
                original_id = vertex["id"]
                label = vertex.get("label", "vertex")
                
                # Add vertex
                traversal = g.addV(label)
                for key, value in vertex.get("properties", {}).items():
                    traversal = traversal.property(key, value)
                
                new_vertex = traversal.next()
                vertex_id_map[original_id] = new_vertex.id
                result.vertex_count += 1
            
            # Import edges
            for edge in data.get("edges", []):
                out_v = vertex_id_map.get(edge["outV"])
                in_v = vertex_id_map.get(edge["inV"])
                
                if out_v and in_v:
                    label = edge.get("label", "edge")
                    traversal = g.V(out_v).addE(label).to(g.V(in_v))
                    
                    for key, value in edge.get("properties", {}).items():
                        traversal = traversal.property(key, value)
                    
                    traversal.iterate()
                    result.edge_count += 1
            
            end_time = datetime.now(timezone.utc)
            result.duration_seconds = (end_time - start_time).total_seconds()
            result.success = True
            
            logger.info(
                "Graph import completed",
                vertices=result.vertex_count,
                edges=result.edge_count,
            )
            
            return result
            
        except Exception as e:
            result.errors.append(str(e))
            logger.error("Graph import failed", error=str(e))
            return result
    
    async def create_neptune_snapshot(
        self,
        cluster_identifier: str,
        snapshot_identifier: str | None = None,
    ) -> tuple[bool, str]:
        """
        Create Neptune cluster snapshot (AWS only).
        
        Args:
            cluster_identifier: Neptune cluster ID
            snapshot_identifier: Optional custom snapshot ID
        
        Returns:
            Tuple of (success, snapshot_arn)
        """
        try:
            import aioboto3
            
            if not snapshot_identifier:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                snapshot_identifier = f"aegis-{cluster_identifier}-{timestamp}"
            
            session = aioboto3.Session()
            async with session.client("neptune") as client:
                response = await client.create_db_cluster_snapshot(
                    DBClusterSnapshotIdentifier=snapshot_identifier,
                    DBClusterIdentifier=cluster_identifier,
                )
                
                snapshot_arn = response["DBClusterSnapshot"]["DBClusterSnapshotArn"]
                logger.info("Neptune snapshot created", arn=snapshot_arn)
                return True, snapshot_arn
                
        except ImportError:
            logger.error("aioboto3 not installed")
            return False, ""
        except Exception as e:
            logger.error("Neptune snapshot failed", error=str(e))
            return False, ""
    
    async def list_neptune_snapshots(
        self,
        cluster_identifier: str,
    ) -> list[dict[str, Any]]:
        """List Neptune snapshots for a cluster."""
        try:
            import aioboto3
            
            session = aioboto3.Session()
            async with session.client("neptune") as client:
                response = await client.describe_db_cluster_snapshots(
                    DBClusterIdentifier=cluster_identifier,
                )
                
                snapshots = []
                for snap in response.get("DBClusterSnapshots", []):
                    snapshots.append({
                        "id": snap["DBClusterSnapshotIdentifier"],
                        "arn": snap["DBClusterSnapshotArn"],
                        "status": snap["Status"],
                        "created_at": snap.get("SnapshotCreateTime"),
                        "engine_version": snap.get("EngineVersion"),
                    })
                
                return snapshots
                
        except Exception as e:
            logger.error("Failed to list Neptune snapshots", error=str(e))
            return []
    
    async def list_backups(self) -> list[dict[str, Any]]:
        """List local graph backup files."""
        backups = []
        backup_dir = Path(self.config.backup_dir)
        
        for file in backup_dir.glob("graph_*.*"):
            stat = file.stat()
            
            # Determine format
            if file.suffix == ".json":
                format_type = GraphExportFormat.JSON
            elif file.suffix == ".graphml":
                format_type = GraphExportFormat.GRAPHML
            elif file.suffix == ".groovy":
                format_type = GraphExportFormat.GREMLIN
            else:
                continue
            
            backups.append({
                "filename": file.name,
                "path": str(file),
                "format": format_type.value,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            })
        
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups
