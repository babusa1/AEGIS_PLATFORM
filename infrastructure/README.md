# AEGIS Infrastructure

Local development and production infrastructure for AEGIS platform.

## Local Development (Docker Compose)

### Prerequisites

- Docker Desktop installed and running
- PowerShell (Windows) or Bash (Linux/Mac)

### Quick Start

```powershell
# Start all services
.\scripts\start-local.ps1

# Stop all services
.\scripts\stop-local.ps1
```

### Services

| Service | Port | URL | Credentials |
|---------|------|-----|-------------|
| JanusGraph | 8182 | ws://localhost:8182/gremlin | - |
| Kafka | 9092 | - | - |
| Kafka UI | 8080 | http://localhost:8080 | - |
| PostgreSQL | 5432 | - | aegis / aegis_dev_password |
| Redis | 6379 | - | - |
| MinIO Console | 9001 | http://localhost:9001 | aegis / aegis_dev_password |
| MinIO API | 9000 | - | aegis / aegis_dev_password |

### Kafka Topics

After startup, create topics:

```bash
docker exec aegis-kafka /bin/bash -c "chmod +x /scripts/create-topics.sh && /scripts/create-topics.sh"
```

Topics created:
- `fhir.raw`, `fhir.validated`, `fhir.dlq` - FHIR ingestion
- `hl7.raw`, `hl7.validated`, `hl7.dlq` - HL7v2 ingestion
- `x12.claims.raw`, `x12.claims.validated`, `x12.remit.raw` - Claims
- `devices.raw`, `devices.validated` - Wearables/IoMT
- `graph.events` - Graph CDC events
- `audit.events` - Audit trail

### PostgreSQL Schemas

- `audit` - HIPAA access logs
- `tenants` - Multi-tenant management
- `pipeline` - Ingestion job tracking

### Data Persistence

All data is persisted in Docker volumes:
- `janusgraph-data` - Graph data
- `kafka-data` - Kafka messages
- `postgres-data` - PostgreSQL data
- `redis-data` - Redis cache
- `minio-data` - Object storage

To reset all data:

```powershell
docker-compose down -v
```

## Production (AWS)

See `terraform/` directory for AWS infrastructure:
- Neptune (managed graph)
- MSK (managed Kafka)
- RDS PostgreSQL
- ElastiCache Redis
- S3

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │        Data Sources                 │
                    │  (FHIR, HL7v2, X12, Devices, etc)  │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │           Apache Kafka              │
                    │    (Streaming + Data Quality)       │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────┼───────────────────┐
                    │                 │                   │
                    ▼                 ▼                   ▼
            ┌───────────┐     ┌───────────┐      ┌───────────┐
            │ JanusGraph│     │ PostgreSQL│      │   MinIO   │
            │  (Graph)  │     │  (Audit)  │      │ (Objects) │
            └───────────┘     └───────────┘      └───────────┘
                    │                 │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────────────────────────┐
                    │           FastAPI + PBAC            │
                    │         (API Gateway)               │
                    └─────────────────────────────────────┘
```
