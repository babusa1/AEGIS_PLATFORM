# AEGIS Local Testing Guide

**Complete guide to testing AEGIS locally with all services.**

---

## Quick Start

```bash
# 1. Start all services
docker-compose up -d

# 2. Wait for services to be healthy (30-60 seconds)
docker-compose ps

# 3. Initialize database
psql -h localhost -p 5433 -U aegis -d aegis -f scripts/init-db.sql

# 4. Start backend
cd aegis
pip install -e .
uvicorn src.aegis.api.main:app --reload --port 8000

# 5. Start frontend (new terminal)
cd demo
npm install
npm run dev
```

**Access**:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Demo App: http://localhost:3000

---

## Detailed Setup

### Prerequisites

```bash
# Install Docker & Docker Compose
# Install Python 3.11+
# Install Node.js 18+
# Install PostgreSQL client (optional)
```

### Step 1: Clone & Setup

```bash
git clone <repo>
cd aegis
```

### Step 2: Environment Configuration

**Create `.env`**:
```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=aegis
POSTGRES_USER=aegis
POSTGRES_PASSWORD=aegis

# Graph
JANUSGRAPH_URL=http://localhost:8182

# Vector
OPENSEARCH_URL=http://localhost:9200

# LLM (use mock for local testing)
LLM_PROVIDER=mock

# Redis
REDIS_URL=redis://localhost:6379

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Tenant
TENANT_ID=default
```

### Step 3: Start Infrastructure

```bash
docker-compose up -d
```

**Verify services**:
```bash
docker-compose ps
# All services should show "healthy"
```

**Check logs**:
```bash
docker-compose logs -f postgres
docker-compose logs -f janusgraph
```

### Step 4: Initialize Database

**Option A: Automatic (via Docker init script)**
- Database auto-initializes from `scripts/init-db.sql`

**Option B: Manual**
```bash
psql -h localhost -p 5433 -U aegis -d aegis -f scripts/init-db.sql
```

**Option C: Python script**
```bash
python scripts/load_sample_data.py
```

**Verify data**:
```bash
psql -h localhost -p 5433 -U aegis -d aegis -c "SELECT COUNT(*) FROM patients;"
# Should return 20
```

### Step 5: Install Python Dependencies

```bash
cd aegis
pip install -e ".[dev]"
```

### Step 6: Start Backend API

```bash
uvicorn src.aegis.api.main:app --reload --port 8000
```

**Verify**:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/v1/agents/data-moat/tools
```

### Step 7: Start Frontend

**New terminal**:
```bash
cd demo
npm install
npm run dev
```

**Access**: http://localhost:3000

---

## Testing Key Features

### 1. Data Moat Entity Registry

```bash
# Get all entity types
curl http://localhost:8000/v1/agents/data-moat/entity-registry

# Query specific entity
curl "http://localhost:8000/v1/agents/data-moat/entities/patient?limit=5"
```

### 2. Generic Entity Queries

```bash
# Get patient by ID
curl "http://localhost:8000/v1/agents/data-moat/entities/patient/patient-001"

# List conditions
curl "http://localhost:8000/v1/agents/data-moat/entities/condition?filters[patient_id]=patient-001"
```

### 3. Agent Execution

```bash
# UnifiedViewAgent
curl -X POST http://localhost:8000/v1/agents/unified-view/query \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient-001",
    "query": "Summarize patient status"
  }'

# OncolifeAgent
curl -X POST http://localhost:8000/v1/agents/oncolife/analyze \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "patient-001"}'

# ChaperoneCKMAgent
curl -X POST http://localhost:8000/v1/agents/chaperone-ckm/analyze \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "patient-005"}'
```

### 4. Workflow Builder

1. Navigate to http://localhost:3000/flow
2. Drag nodes from palette:
   - Data Moat entities (patient, condition, etc.)
   - Agents (OncolifeAgent, ChaperoneCKMAgent)
   - Triggers (webhook, schedule)
3. Connect nodes
4. Click "Execute"

### 5. Ingestion Pipeline

```bash
# Ingest FHIR bundle
curl -X POST http://localhost:8000/v1/ingestion/fhir \
  -H "Content-Type: application/json" \
  -d @examples/fhir-bundle.json
```

### 6. RAG Pipeline

```bash
# Ingest document
curl -X POST http://localhost:8000/v1/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "document": "Patient has diabetes and hypertension...",
    "metadata": {"patient_id": "patient-001"}
  }'

# Query RAG
curl -X POST http://localhost:8000/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the patient conditions?"}'
```

---

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs

# Restart specific service
docker-compose restart postgres

# Rebuild containers
docker-compose up -d --build
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check connection
psql -h localhost -p 5433 -U aegis -d aegis -c "SELECT 1;"

# Reset database
docker-compose down -v
docker-compose up -d
```

### Mock Mode Warnings

**Expected in development**: Mock LLM, mock clients are OK for testing.

**To use real services**:
```bash
export LLM_PROVIDER=bedrock  # or openai, anthropic
export AEGIS_MOCK_MODE=false
```

### Port Conflicts

**Change ports in `docker-compose.yml`**:
```yaml
ports:
  - "5434:5432"  # Change 5433 to 5434
```

---

## Production Mode Testing

**To test without mocks**:

1. **Configure real LLM**:
```bash
export LLM_PROVIDER=bedrock
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

2. **Verify no mocks**:
```bash
# Check logs for "using mock" - should be none
uvicorn src.aegis.api.main:app --reload --port 8000 2>&1 | grep -i mock
```

3. **Health check**:
```bash
curl http://localhost:8000/health
# All services should show "up", not "mock"
```

---

## Next Steps

After local testing works:

1. **Replace mocks** with real connections
2. **Add GraphRAG** (graph traversal + RAG)
3. **Implement JWT auth**
4. **Add PHI detection**
5. **Deploy to AWS** (Phase 2)

---

**Last Updated**: February 2026
