# AEGIS Platform: High Level Design Document

**Version**: 2.0  
**Last Updated**: February 6, 2026  
**Status**: Production-Ready (100% Complete)

---

## 1. SYSTEM CONTEXT (C4 Level 1)

### System Purpose

**AEGIS (Autonomous Evidence-based Guardian & Interoperability System)** is the **Agentic Operating System for Healthcare**—a composable health OS that orchestrates the EHR rather than replacing it.

### External Actors

```
┌─────────────────────────────────────────────────────────────────┐
│                        AEGIS Platform                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐      │
│   │  Hospital   │     │   Payer     │     │  Analytics  │      │
│   │  Users      │     │   Portals   │     │   Team      │      │
│   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘      │
│          │                   │                   │              │
│          ▼                   ▼                   ▼              │
│   ┌─────────────────────────────────────────────────────┐      │
│   │              AEGIS Platform                          │      │
│   │  • Patient 360  • RCM  • Care Gaps  • Agents        │      │
│   └─────────────────────────────────────────────────────┘      │
│          │                   │                   │              │
│          ▼                   ▼                   ▼              │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐      │
│   │   EHR       │     │   Claims    │     │  Wearables  │      │
│   │  (Epic)     │     │   Systems   │     │   (Fitbit)  │      │
│   └─────────────┘     └─────────────┘     └─────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

**Actors**:
- **Hospital Users**: Clinicians, nurses, administrators
- **Payer Portals**: Insurance companies, managed care organizations
- **Analytics Teams**: Data scientists, quality teams
- **EHR Systems**: Epic, Cerner (via FHIR/SMART-on-FHIR)
- **Claims Systems**: Payer systems (via X12 EDI)
- **Wearables**: Patient devices (via HealthKit, Fitbit APIs)

---

## 2. CONTAINER DIAGRAM (C4 Level 2)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AEGIS PLATFORM                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  PRESENTATION LAYER                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │  │
│  │  │ Provider    │  │ Patient     │  │ API         │          │  │
│  │  │ Dashboard   │  │ Mobile App  │  │ Gateway     │          │  │
│  │  │ (Next.js)   │  │ (React)     │  │ (FastAPI)   │          │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  AGENT LAYER                                                   │  │
│  │  ┌──────────────────────────────────────────────────────────┐ │  │
│  │  │  LangGraph Orchestration                                  │ │  │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │ │  │
│  │  │  │ Librarian│ │ Guardian│ │  Scribe │ │  Scout  │      │ │  │
│  │  │  │ Agent    │ │ Agent   │ │ Agent   │ │ Agent   │      │ │  │
│  │  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘      │ │  │
│  │  └──────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  LLM GATEWAY                                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │  │
│  │  │ AWS Bedrock │  │ OpenAI      │  │ Anthropic    │          │  │
│  │  │ (Primary)   │  │ (Fallback)  │  │ (Fallback)   │          │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  DATA LAYER                                                    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │  │
│  │  │ Graph DB     │  │ Vector DB    │  │ Relational   │        │  │
│  │  │ (Neptune)    │  │ (OpenSearch) │  │ (PostgreSQL) │        │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │  │
│  │  │ Time-Series │  │ Cache        │  │ Event Stream │        │  │
│  │  │ (TimescaleDB)│ │ (Redis)      │  │ (Kafka)      │        │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  INTEGRATION LAYER                                             │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │  │
│  │  │ FHIR    │ │ HL7v2   │ │ Claims  │ │ Devices │            │  │
│  │  │ Adapter │ │ Adapter │ │ Adapter │ │ Gateway │            │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Containers

1. **Provider Dashboard** (Next.js)
   - React-based UI for clinicians
   - Cowork workspace (3-pane layout)
   - Patient 360 views
   - Agent management

2. **Patient Mobile App** (React Native)
   - Symptom checker (Oncolife)
   - Vital logging (CKM)
   - Appointment scheduling

3. **API Gateway** (FastAPI)
   - REST API endpoints
   - WebSocket endpoints (Cowork)
   - Authentication (JWT)
   - Rate limiting

4. **Agent Layer** (LangGraph)
   - Supervisor-Worker architecture
   - Librarian, Guardian, Scribe, Scout agents
   - Workflow orchestration

5. **LLM Gateway**
   - Multi-provider support (Bedrock, OpenAI, Anthropic)
   - Failover logic
   - Cost tracking

6. **Data Layer** (7 Databases)
   - PostgreSQL: Operational data
   - TimescaleDB: Time-series
   - Neptune: Knowledge graph
   - OpenSearch: Vector search
   - Redis: Cache/sessions
   - Kafka: Event streaming
   - DynamoDB: Execution state

7. **Integration Layer**
   - FHIR connectors (Epic, Cerner)
   - HL7v2 parsers
   - X12 EDI (claims)
   - Wearable APIs

---

## 3. THE FIVE PILLARS ARCHITECTURE

### Pillar 1: The Data Moat (Sovereign Clinical Data Layer)

**Purpose**: Unified data model for 30+ entity types across 7 databases

**Components**:
- **Structural**: Canonical FHIR Graph (Neptune)
- **Semantic**: Medical Rosetta Stone (LLM-enriched mapping)
- **Temporal**: Vectorized Timelines (TimescaleDB + OpenSearch)

**Key Features**:
- 30+ entity types (Patient, Condition, Medication, Claim, Denial, etc.)
- Unified query API (`get_entity_by_id`, `list_entities`)
- Entity registry for type discovery

### Pillar 2: Agentic Framework (The Cognitive Layer)

**Purpose**: Multi-agent orchestration with healthcare-native workflows

**Components**:
- **Supervisor**: LangGraph-based orchestrator
- **Workers**: Librarian, Guardian, Scribe, Scout
- **Tools**: Data Moat tools, LLM tools, action tools

**Key Features**:
- Visual workflow builder (React Flow)
- Durable execution (checkpointing, replay)
- Human-in-the-loop (3-tier approval)

### Pillar 3: Clinical RAG & Smart Chunking

**Purpose**: Grounded AI with source attribution

**Components**:
- **Chunking**: Encounter-based, headers-first
- **RAG Pipeline**: GraphRAG + Vector Search + Keyword Search
- **Summarization**: Recursive (hierarchical summaries)

**Key Features**:
- Temporal hybrid search
- Graph path-finding
- Source attribution (FHIR resource links)

### Pillar 4: Bridge Apps (Vertical Intelligence)

**Purpose**: Specialized interfaces for disease states

**Components**:
- **Oncolife**: Oncology care (symptom checker, CTCAE grading, infusion optimization)
- **Chaperone CKM**: CKD management (KFRE, eGFR, dialysis planning, transplant readiness)

**Key Features**:
- Data-aware symptom checking
- Real-time agent consultation
- Patient-facing mobile apps

### Pillar 5: Human-in-the-Loop & Governance

**Purpose**: Constrained autonomy with explainability

**Components**:
- **3-Tier Approval**: Automated, Assisted, Clinical
- **Explainability**: Reasoning_Path nodes, evidence links
- **Kill Switch**: Agent pause/resume
- **Audit Logs**: Immutable, append-only

**Key Features**:
- Guideline cross-checking (NCCN, KDIGO)
- Conflict detection (drug-drug, drug-lab)
- Audit attribution (GUIDELINE_ID, SOURCE_LINK)

---

## 4. DATA FLOW DIAGRAMS

### Ingestion Flow

```
External Source → Connector → Parser → Validator → Normalizer → Data Moat
     (FHIR)        (FHIR)      (JSON)    (Schema)    (SNE)      (Graph+DB)
```

### Agent Execution Flow

```
User Request → API Gateway → Supervisor → Worker Agent → Tools → Data Moat
                                                              ↓
                                                         LLM Gateway
                                                              ↓
                                                         Response → User
```

### Cowork Workflow Flow

```
Event (Kafka) → Scout → Supervisor → Librarian → Guardian → Scribe → Human Review → EHR Write-Back
```

---

## 5. INTEGRATION ARCHITECTURE

### EHR Integration (SMART-on-FHIR)

```
AEGIS Platform ←→ SMART-on-FHIR ←→ Epic/Cerner EHR
     (CDS Hooks)      (OAuth 2.0)      (FHIR R4)
```

### Claims Integration (X12 EDI)

```
AEGIS Platform ←→ X12 Parser ←→ Payer Systems
   (837/835)      (270/271)      (276/277)
```

### Wearable Integration

```
AEGIS Platform ←→ HealthKit/Fitbit SDK ←→ Patient Devices
   (REST API)        (OAuth)              (iOS/Android)
```

---

## 6. DEPLOYMENT ARCHITECTURE

### Hybrid Deployment Model

```
┌─────────────────────────────────────────────────────────────┐
│  Control Plane (AWS/Azure VPC)                             │
│  - API Gateway                                              │
│  - Agent Orchestration                                      │
│  - LLM Gateway                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Data Plane (On-Premises/Private Cloud)                    │
│  - Data Moat (7 Databases)                                  │
│  - PHI Storage (never traverses open web)                  │
│  - EHR Integration                                         │
└─────────────────────────────────────────────────────────────┘
```

### Scalability

- **Horizontal Scaling**: API Gateway, Agent Workers (stateless)
- **Vertical Scaling**: Databases (PostgreSQL, Neptune)
- **Caching**: Redis for session state, query results
- **Load Balancing**: API Gateway → Multiple agent instances

---

## 7. SECURITY ARCHITECTURE

### Authentication & Authorization

- **OAuth 2.0 / OIDC**: Cognito, Auth0, Okta
- **JWT Tokens**: API authentication
- **Purpose-Based Access Control (PBAC)**: HIPAA-compliant
- **Multi-Tenancy**: Schema-per-tenant isolation

### Data Protection

- **PHI Detection**: Presidio (spaCy)
- **PHI Redaction**: Auto-redact before logging
- **Encryption**: TLS in transit, encryption at rest
- **Audit Logs**: Immutable, append-only

---

## 8. TECHNOLOGY STACK

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Orchestration**: LangGraph
- **Graph**: Neptune/JanusGraph
- **Vector DB**: OpenSearch

### Frontend
- **Framework**: Next.js 14
- **UI Library**: React, TailwindCSS
- **Workflow Builder**: React Flow
- **Mobile**: React Native

### Infrastructure
- **Containers**: Docker
- **Orchestration**: Kubernetes (planned)
- **CI/CD**: GitHub Actions
- **Monitoring**: OpenTelemetry

---

**Last Updated**: February 6, 2026  
**Document Owner**: Architecture Team
