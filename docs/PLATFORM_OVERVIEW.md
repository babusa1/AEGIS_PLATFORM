# AEGIS Platform: One-Page Overview

**The Agentic Operating System for Healthcare**

---

## Platform Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AEGIS PLATFORM                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  DATA MOAT → INGESTION → CHUNKING → RAG → LLM → AGENTS     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1. Data Moat (Unified Data Layer)

**30+ Entity Types** accessible via unified API:
- **Clinical**: Patients, Conditions, Medications, Encounters, Procedures, Observations
- **Financial**: Claims, Denials, Appeals, Payments, Authorizations
- **Time-Series**: Vitals, Lab Results, Wearable Metrics
- **Genomics**: Genomic Variants, Genomic Reports
- **Workflow**: Workflow Definitions, Executions
- **Security**: Consents, Break-the-Glass Sessions

**7 Databases**:
- PostgreSQL (operational data)
- TimescaleDB (time-series)
- JanusGraph/Neptune (knowledge graph)
- OpenSearch (vector search)
- Redis (cache)
- Kafka (events)
- DynamoDB (state)

**Generic Query API**: `get_entity_by_id()`, `list_entities()` for all 30+ types

---

### 2. Data Ingestion (30+ Sources)

**Unified Pipeline**: `source_type + payload → connector → parse → validate → write to Moat`

**Supported Sources**:
- **Tier 1**: FHIR R4, HL7v2, CDA/CCDA
- **Tier 2**: X12 (837/835, 270/271, 276/277, 278)
- **Tier 3**: Apple HealthKit, Google Fit, Fitbit, Garmin, Withings
- **Tier 4**: Genomics (VCF, GA4GH), Imaging (DICOM, DICOMweb), SDOH, PRO
- **Tier 5**: Messaging, Scheduling, Workflow, Analytics, Guidelines, Drug Labels

**Source Registry**: Track 30+ live connections per tenant

---

### 3. Chunking & RAG

**Chunking**: Sliding window, semantic, hierarchical  
**RAG Pipeline**: Ingest → Chunk → Embed → Store → Retrieve → Generate (with citations)  
**Embeddings**: Bedrock, OpenAI, local  
**Vector Store**: OpenSearch-backed semantic search

---

### 4. LLM Gateway

**Multi-Provider**: Bedrock (primary), OpenAI, Anthropic, Ollama  
**Unified API**: Single interface for all providers  
**Failover**: Automatic provider switching

---

### 5. Agentic Framework

**Better than n8n/Kogo**:
- ✅ Healthcare-native (Data Moat, clinical workflows)
- ✅ Multi-agent orchestration
- ✅ Human-in-the-loop (approvals)
- ✅ Therapeutic-specific agents (Oncolife, Chaperone CKM)
- ✅ Visual builder (React Flow)
- ✅ Durable execution (checkpointing, replay)

**Agents**:
- **UnifiedViewAgent**: Patient 360
- **ActionAgent**: Denial appeals
- **InsightAgent**: Pattern discovery
- **TriageAgent**: Clinical monitoring
- **OncolifeAgent**: Oncology care (genomics, chemo, toxicity)
- **ChaperoneCKMAgent**: CKD management (KFRE, eGFR, dialysis planning)

**Workflow Builder**: React Flow-based visual editor with Data Moat entity nodes

**Durable Execution**: Checkpointing, replay, crash recovery

---

## Key Differentiators

| Feature | AEGIS | n8n | Kogo |
|---------|-------|-----|------|
| Healthcare Focus | ✅ Native | ❌ General | ❌ General |
| Data Moat | ✅ 30+ entities | ❌ | ❌ |
| Therapeutic Agents | ✅ Oncolife, CKM | ❌ | ❌ |
| Multi-Agent | ✅ | ❌ | ⚠️ Limited |
| Human-in-Loop | ✅ | ⚠️ Basic | ✅ |
| Visual Builder | ✅ React Flow | ✅ | ⚠️ Limited |
| Durable Execution | ✅ Checkpointing | ⚠️ Basic | ✅ |
| 30+ Data Sources | ✅ | ⚠️ Generic | ⚠️ Generic |

---

## Use Cases

### Oncolife (Oncology)
- Genomic variant analysis
- Chemotherapy tracking
- Toxicity monitoring
- Care gap alerts

### Chaperone CKM (Nephrology)
- KFRE risk calculation
- eGFR trending
- Dialysis planning
- Care gap tracking

### Revenue Cycle
- Denial management
- Appeal generation
- Claim analysis

### Clinical Operations
- Patient 360 views
- Risk stratification
- Care coordination

---

## Technology Stack

- **Backend**: Python, FastAPI, LangGraph
- **Databases**: PostgreSQL, TimescaleDB, JanusGraph, OpenSearch, Redis, Kafka
- **AI/ML**: AWS Bedrock, OpenAI, Anthropic, Ollama
- **Frontend**: Next.js, React, React Flow, TailwindCSS
- **Infrastructure**: Docker, AWS (planned)

---

## Status

✅ **Complete**: Data Moat entity registry, unified ingestion, therapeutic agents, React Flow builder, durable execution  
🔄 **In Progress**: Production deployment, scaling  
📋 **Planned**: Advanced analytics, federated learning

---

**Last Updated**: February 2026  
**Platform Version**: 1.0
