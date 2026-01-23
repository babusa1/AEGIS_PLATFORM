# AEGIS Graph

Graph database abstraction layer for the AEGIS Healthcare Platform.

## Features

- **Provider Abstraction**: Unified interface for multiple graph databases
- **Supported Backends**:
  - JanusGraph (local development, on-premise)
  - AWS Neptune (production cloud)
  - Neo4j (coming soon)
- **Multi-tenant**: Built-in tenant isolation via `tenant_id` property
- **Retry Logic**: Automatic retry with exponential backoff

## Installation

```bash
pip install aegis-graph
```

## Quick Start

```python
from aegis_graph import GraphProvider, get_graph_provider

# Create provider explicitly
provider = GraphProvider.create(
    provider_type="janusgraph",
    connection_url="ws://localhost:8182/gremlin"
)

# Or from config
provider = GraphProvider.from_config(settings)

# Use as context manager
async with provider as graph:
    # Create a patient vertex
    patient_id = await graph.create_vertex(
        label="Patient",
        properties={
            "mrn": "12345",
            "given_name": "John",
            "family_name": "Doe"
        },
        tenant_id="hospital-a"
    )
    
    # Create an encounter
    encounter_id = await graph.create_vertex(
        label="Encounter",
        properties={"type": "inpatient", "status": "in-progress"},
        tenant_id="hospital-a"
    )
    
    # Link patient to encounter
    await graph.create_edge(
        from_vertex_id=patient_id,
        to_vertex_id=encounter_id,
        label="HAS_ENCOUNTER"
    )
    
    # Traverse the graph
    encounters = await graph.traverse(
        start_vertex_id=patient_id,
        path_pattern=["HAS_ENCOUNTER"]
    )
```

## Configuration

### JanusGraph (Local Development)

```python
provider = GraphProvider.create(
    provider_type="janusgraph",
    connection_url="ws://localhost:8182/gremlin"
)
```

### AWS Neptune (Production)

```python
provider = GraphProvider.create(
    provider_type="neptune",
    connection_url="wss://my-cluster.us-east-1.neptune.amazonaws.com:8182/gremlin",
    region="us-east-1",
    use_iam=True
)
```

## API Reference

### BaseGraphProvider Interface

All providers implement these methods:

#### Vertex Operations
- `create_vertex(label, properties, tenant_id)` → vertex_id
- `get_vertex(vertex_id)` → dict | None
- `update_vertex(vertex_id, properties)` → bool
- `delete_vertex(vertex_id)` → bool
- `find_vertices(label, filters, tenant_id, limit)` → list[dict]

#### Edge Operations
- `create_edge(from_id, to_id, label, properties)` → edge_id
- `get_edges(vertex_id, direction, edge_label)` → list[dict]
- `delete_edge(edge_id)` → bool

#### Traversal
- `traverse(start_id, path_pattern, max_depth)` → list[dict]
- `execute_query(query, bindings)` → list[Any]

#### Health
- `health_check()` → bool
- `get_stats()` → dict

## License

MIT
