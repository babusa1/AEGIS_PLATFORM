# AEGIS Data Layer

Unified data access layer. All agents use DataService for data access.

## Usage

```python
from aegis_data import DataService

service = DataService(tenant_id="tenant-123", clients=clients)

# Get complete patient view
patient_360 = await service.get_patient_360("patient-456")

# Get patient summary for LLM
summary = await service.get_patient_summary("patient-456")

# Get vital trends
bp_trend = await service.get_vital_trend("patient-456", "bp_systolic", days=30)
```

## Architecture

- DataService: Single interface for all data access
- Repositories: Patient, Condition, Medication, Encounter, Observation
- Databases: Graph (Neptune), Postgres, TimescaleDB, Vector (Pinecone)
