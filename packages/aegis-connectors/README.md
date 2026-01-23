# AEGIS Data Connectors

Production connectors for 19+ healthcare data sources.

## Supported Formats

| Connector | Format | Status |
|-----------|--------|--------|
| FHIR R4 | JSON Bundles, Resources | Ready |
| HL7v2 | ADT, ORU, ORM messages | Planned |
| X12 EDI | 837/835 Claims | Planned |
| Genomics | VCF Variants | Planned |
| DICOM | Imaging metadata | Planned |
| Devices | Wearable APIs | Planned |

## Installation

```bash
pip install aegis-connectors

# With HL7v2 support
pip install aegis-connectors[hl7]

# All connectors
pip install aegis-connectors[all]
```

## FHIR Connector

### Parse a Bundle

```python
from aegis_connectors.fhir import FHIRConnector

connector = FHIRConnector(tenant_id="hospital-a")

# Parse FHIR bundle
result = await connector.parse(fhir_bundle_json)

print(f"Vertices: {result.vertex_count}")
print(f"Edges: {result.edge_count}")

# Write to graph
for vertex in result.vertices:
    await graph.create_vertex(vertex["label"], vertex)

for edge in result.edges:
    await graph.create_edge(...)
```

### Ingest Synthea Data

```python
from aegis_connectors.fhir.connector import ingest_synthea_data

summary = await ingest_synthea_data(
    directory="./synthea/output/fhir",
    tenant_id="hospital-a",
    graph_writer=graph_writer,
)

print(f"Processed {summary['files_processed']} files")
print(f"Created {summary['total_vertices']} vertices")
```

### Supported FHIR Resources

| Resource | Graph Vertex | Edges Created |
|----------|-------------|---------------|
| Patient | Patient | - |
| Encounter | Encounter | HAS_ENCOUNTER |
| Condition | Condition | HAS_CONDITION |
| Observation | Observation | HAS_OBSERVATION |
| MedicationRequest | MedicationRequest | HAS_MEDICATION |
| Procedure | Procedure | HAS_PROCEDURE |
| Claim | Claim | HAS_CLAIM |
| Coverage | Coverage | HAS_COVERAGE |
| Practitioner | Provider | - |
| Organization | Organization | - |
| CarePlan | CarePlan | HAS_CARE_PLAN |
| CareTeam | CareTeam | HAS_CARE_TEAM |

## License

MIT
