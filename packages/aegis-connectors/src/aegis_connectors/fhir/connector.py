"""
FHIR Connector

Main connector class that combines parser and transformer.
"""

from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult
from aegis_connectors.fhir.parser import FHIRParser
from aegis_connectors.fhir.transformer import FHIRTransformer

logger = structlog.get_logger(__name__)


class FHIRConnector(BaseConnector):
    """
    FHIR R4 Connector.
    
    Parses FHIR bundles/resources and transforms to graph vertices.
    
    Usage:
        connector = FHIRConnector(tenant_id="hospital-a")
        result = await connector.parse(fhir_bundle_json)
        
        for vertex in result.vertices:
            await graph.create_vertex(vertex["label"], vertex)
        
        for edge in result.edges:
            await graph.create_edge(...)
    """
    
    def __init__(
        self,
        tenant_id: str,
        source_system: str = "fhir",
    ):
        super().__init__(tenant_id, source_system)
        self.parser = FHIRParser()
        self.transformer = FHIRTransformer(tenant_id, source_system)
    
    @property
    def connector_type(self) -> str:
        return "fhir"
    
    async def parse(self, data: Any) -> ConnectorResult:
        """
        Parse FHIR data and transform to graph vertices/edges.
        
        Args:
            data: FHIR Bundle JSON (string or dict) or single resource
            
        Returns:
            ConnectorResult with vertices and edges
        """
        all_vertices = []
        all_edges = []
        errors = []
        warnings = []
        
        # Determine if bundle or single resource
        if isinstance(data, str):
            import json
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                return ConnectorResult(
                    success=False,
                    errors=[f"Invalid JSON: {e}"]
                )
        
        resource_type = data.get("resourceType", "")
        
        if resource_type == "Bundle":
            resources, parse_errors = self.parser.parse_bundle(data)
            errors.extend(parse_errors)
        else:
            resource, parse_errors = self.parser.parse_resource(data)
            errors.extend(parse_errors)
            resources = [resource] if resource else []
        
        # Transform each resource
        for resource in resources:
            try:
                vertices, edges = self.transformer.transform(resource)
                all_vertices.extend(vertices)
                all_edges.extend(edges)
            except Exception as e:
                resource_type = getattr(resource, "resource_type", "Unknown")
                resource_id = getattr(resource, "id", "unknown")
                errors.append(f"Transform error for {resource_type}/{resource_id}: {e}")
        
        logger.info(
            "FHIR parse complete",
            vertices=len(all_vertices),
            edges=len(all_edges),
            errors=len(errors),
            tenant=self.tenant_id,
        )
        
        return ConnectorResult(
            success=len(errors) == 0,
            vertices=all_vertices,
            edges=all_edges,
            errors=errors,
            warnings=warnings,
            metadata={
                "resource_count": len(resources),
                "connector_type": self.connector_type,
            }
        )
    
    async def validate(self, data: Any) -> list[str]:
        """Validate FHIR data without full parsing."""
        if isinstance(data, str):
            import json
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                return [f"Invalid JSON: {e}"]
        
        resource_type = data.get("resourceType", "")
        
        if resource_type == "Bundle":
            _, errors = self.parser.parse_bundle(data)
            return errors
        else:
            return self.parser.validate_resource(data)
    
    async def parse_synthea_bundle(self, file_path: str) -> ConnectorResult:
        """
        Parse a Synthea-generated FHIR bundle file.
        
        Convenience method for loading Synthea test data.
        """
        with open(file_path, "r") as f:
            data = f.read()
        
        return await self.parse(data)


async def ingest_synthea_data(
    directory: str,
    tenant_id: str,
    graph_writer: Any,
) -> dict:
    """
    Ingest all Synthea FHIR bundles from a directory.
    
    Args:
        directory: Path to Synthea output/fhir directory
        tenant_id: Tenant ID for data isolation
        graph_writer: Graph writer instance
        
    Returns:
        Summary dict with counts
    """
    import os
    
    connector = FHIRConnector(tenant_id=tenant_id, source_system="synthea")
    
    total_vertices = 0
    total_edges = 0
    total_errors = 0
    files_processed = 0
    
    for filename in os.listdir(directory):
        if not filename.endswith(".json"):
            continue
        
        file_path = os.path.join(directory, filename)
        
        try:
            result = await connector.parse_synthea_bundle(file_path)
            
            # Write to graph
            for vertex in result.vertices:
                await graph_writer.upsert_vertex(
                    label=vertex["label"],
                    id_value=vertex["id"],
                    tenant_id=tenant_id,
                    properties=vertex,
                )
            
            for edge in result.edges:
                await graph_writer.create_edge(
                    from_label=edge["from_label"],
                    from_id=edge["from_id"],
                    edge_label=edge["label"],
                    to_label=edge["to_label"],
                    to_id=edge["to_id"],
                    tenant_id=tenant_id,
                )
            
            total_vertices += result.vertex_count
            total_edges += result.edge_count
            total_errors += len(result.errors)
            files_processed += 1
            
        except Exception as e:
            logger.error(f"Failed to process {filename}", error=str(e))
            total_errors += 1
    
    return {
        "files_processed": files_processed,
        "total_vertices": total_vertices,
        "total_edges": total_edges,
        "total_errors": total_errors,
    }
