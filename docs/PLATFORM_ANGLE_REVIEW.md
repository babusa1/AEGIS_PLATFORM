# AEGIS Platform Review: Data Moat → Ingestion → Chunking → RAG → LLM → Agentic Framework

**Review Date:** February 6, 2026  
**Angle:** Platform-as-a-whole, 30+ data sources, agentic framework (beyond n8n/Kogo), therapeutic-specific agents

---

## 1. INTENDED VISION (What You Wanted)

- **First step:** Platform as a whole — Data Moat → Ingestion → Chunking → RAG → LLM as the foundation.
- **Data Moat:** Single unified layer over 30+ healthcare data sources.
- **Data Ingestion:** Connect to 30+ sources; normalize and load into the Moat.
- **Chunking:** Document/semantic chunking for RAG.
- **RAG:** Retrieval Augmented Generation over clinical/knowledge content.
- **LLM:** Central LLM gateway powering agents and generation.
- **Agentic Framework:** Better than n8n or Kogo.AI — healthcare-native, Data-Moat–driven, durable, multi-agent.
- **Therapeutic-Specific Agents:** Use the data to build agents by specialty (e.g. Oncolife, Chaperone CKM, and beyond).

---

## 2. DATA MOAT — Status vs Vision

### Intended
- One logical “Data Moat” over **30+ data sources**.
- Agents and workflows query the Moat, not individual systems.

### Implemented

| Layer | Status | Details |
|-------|--------|--------|
| **Concept & API** | ✅ Done | `DataMoatTools` + “Data Moat” in UI/docs. |
| **Unified access** | ✅ Done | Single tool set: patient summary, high-risk, denials, claim-for-appeal, patients-needing-attention. |
| **Backing stores** | ✅ Done | PostgreSQL, TimescaleDB, JanusGraph, OpenSearch, Redis, Kafka, DynamoDB (7 DBs). |
| **Entity coverage** | 🟡 Partial | ~30+ **entities/tables** in spec (patients, conditions, claims, vitals, etc.). **Not** 30+ **ingested source systems** yet. |
| **Query all 30+ entities** | 🔴 Missing | ORCHESTRATION_ENGINE_SPEC: “Data Moat: Query all 30+ entities” — **not implemented**. Tools today cover ~5–6 logical areas (patient, risk, denials, claim, attention). |
| **Graph + Vector + Relational** | 🟡 Partial | DataMoatTools use mainly **PostgreSQL** (pool). Graph/vector used elsewhere but not fully unified in one “query 30+ entities” surface. |

**Gap:**  
- Data Moat **concept and first slice** (patient, risk, denials, claim, attention) are in place.  
- **“Data Moat = query all 30+ entities”** is not: no single registry of 30+ entity types with generic query/read operations exposed to the agentic layer.

**Recommendation:**  
- Define a **Data Moat entity registry** (list of 30+ entities).  
- Extend `DataMoatTools` (or a new service) with generic “get by entity type + id” / “list by entity type + filters” so workflows/agents can query any Moat entity, not only the 5 current tools.

---

## 3. DATA INGESTION — 30+ Sources

### Intended
- Ingest from **30+ data sources** into the Data Moat.

### Connector Inventory (aegis-connectors)

**Declared (31 sources in `__init__.py`):**  
Tier 1: FHIR R4, HL7v2, CDA/CCDA.  
Tier 2: X12 837/835, 270/271, 276/277, 278.  
Tier 3: Apple HealthKit, Google Fit, Fitbit, Garmin, Withings.  
Tier 4: Genomics (VCF, GA4GH), Imaging (DICOM, DICOMweb), SDOH, PRO, Messaging.  
Tier 5: Scheduling, Workflow, Analytics, Guidelines, Drug Labels, Consent.

**Implemented (have parse/transform or connector class):**

| Connector / Area | Status | Notes |
|------------------|--------|--------|
| **FHIR R4** | ✅ | Connector + parser + transformer; Synthea ingest. |
| **HL7v2** | ✅ | Connector + parser + transformer. |
| **X12** | ✅ | Connector, parser, transformer; eligibility, claim status, prior auth. |
| **Genomics** | ✅ | Connector + parser + transformer; VCF, GA4GH. |
| **Imaging** | ✅ | Connector + parser + transformer; DICOM, DICOMweb. |
| **SDOH** | ✅ | Connector. |
| **PRO** | ✅ | Connector + parser. |
| **Documents** | ✅ | Connector; PDF, CDA parser, NLP. |
| **Messaging** | ✅ | Connector. |
| **Scheduling** | ✅ | Connector. |
| **Analytics** | ✅ | Connector. |
| **Workflow** | ✅ | Connector. |
| **Devices** | ✅ | Base + Fitbit, HealthKit, Google Fit, Garmin, Withings (parse_response). |
| **Compliance/Consent** | ✅ | Consent connector. |
| **Knowledge** | ✅ | Drug labels, Guidelines (parse/transform). |

So: **connector/parse/transform coverage is broad** (well over 15–20 distinct source types).  
What’s **not** done end-to-end for all of them:

- **Wiring into the live Data Moat:** Many connectors output vertices/edges or DTOs; not every path is wired into PostgreSQL + Graph + Kafka in one standard pipeline.
- **30+ “production connections”:** The number 30+ is closer to “30+ **types** of data we can parse” rather than “30+ **deployed integrations** (e.g. 30+ EHRs/payers/devices) with live credentials and sync.”

**Recommendation:**  
- Keep “30+ data **sources**” as “30+ **source types**” in messaging; clarify “30+ connectors/parsers” vs “30+ live tenant connections.”  
- Add a single **ingestion pipeline** that: receives a payload + source type → picks connector → parses → validates → writes to Moat (PostgreSQL + Graph + Kafka as needed).  
- Then add a **source registry** (e.g. in `data_sources` table) so “connected sources” are explicit and countable.

---

## 4. CHUNKING — For RAG

### Intended
- Chunk documents/content for RAG (and downstream embedding/retrieval).

### Implemented

| Component | Status | Location |
|-----------|--------|----------|
| **Chunk model** | ✅ | `Chunk` (id, content, document_id, chunk_index, start/end, parent_id, level, metadata, embedding). |
| **Sliding window** | ✅ | `SlidingWindowChunker` (size, overlap, separator). |
| **Semantic chunking** | ✅ | `SemanticChunker` (by meaning). |
| **Hierarchical** | ✅ | `HierarchicalChunker` (parent-child). |
| **Configurable** | ✅ | `RAGConfig.chunker_type`: semantic, sliding, hierarchical. |

Chunking is **in place** and integrated into the RAG pipeline.  
No major gap for “chunking” as a platform capability.

---

## 5. RAG PIPELINE

### Intended
- End-to-end RAG: ingest → chunk → embed → store → retrieve → generate (with citations).

### Implemented

| Step | Status | Notes |
|------|--------|--------|
| **1. Document ingestion** | ✅ | Loaders (PDF, DOCX, Text, HL7, FHIR); `RAGPipeline.ingest_document()`. |
| **2. Chunking** | ✅ | As above; configurable chunker type. |
| **3. Embedding** | ✅ | `EmbeddingModelFactory` (bedrock, openai, local). |
| **4. Storage** | ✅ | `VectorStore`; `InMemoryVectorStore`; OpenSearch-backed store used elsewhere. |
| **5. Retrieval** | ✅ | `RAGRetriever`; top_k, hybrid search, rerank, citations. |
| **6. Generation** | ✅ | LLM + context; `RAGResponse` with citations. |
| **Evaluation** | ✅ | `RAGEvaluator` (e.g. in `rag/evaluation.py`). |
| **API** | ✅ | RAG routes (e.g. ingest, query). |

RAG is **implemented end-to-end**. Remaining work is operational: wiring to OpenSearch in production, indexing strategies, and evaluation runs — not “missing pipeline.”

---

## 6. LLM LAYER

### Intended
- Single LLM gateway for the platform; multi-provider; used by agents and RAG.

### Implemented

- **Multi-provider:** Bedrock, OpenAI, Anthropic, Ollama (and mock).
- **Registry / gateway** in code; agents and RAG use it.
- **Config-driven** (e.g. env) for provider/model.

No structural gap; optional improvements: cost tracking, A/B testing, prompt versioning (as in ROADMAP).

---

## 7. PLATFORM AS A WHOLE (First Step)

**First step** = Data Moat → Ingestion → Chunking → RAG → LLM as one coherent platform.

| Pillar | Done | Missing / Partial |
|--------|------|-------------------|
| **Data Moat** | Concept, 7 DBs, first tools (patient, risk, denials, claim, attention) | “Query all 30+ entities” not exposed; no single entity registry. |
| **Ingestion** | 15+ connector types; FHIR/HL7/X12/genomics/imaging/SDOH/pro/docs/devices/… | End-to-end wiring into Moat for every type; 30+ “live” connections. |
| **Chunking** | Sliding, semantic, hierarchical | — |
| **RAG** | Full pipeline + API + eval | Production vector store and indexing strategy. |
| **LLM** | Gateway, multi-provider | Cost, A/B, versioning (nice-to-have). |

So: **platform “first step” is largely built**; the main gaps are (1) Data Moat = full 30+ entity query surface, and (2) ingestion = one standard path from each connector into the Moat and optionally into RAG when applicable.

---

## 8. AGENTIC FRAMEWORK vs n8n / Kogo.AI

### Spec (ORCHESTRATION_ENGINE_SPEC)

- **n8n:** Visual builder, 400+ integrations, triggers.  
- **LangGraph:** State, multi-agent.  
- **Temporal:** Durable execution, retries, history.  
- **Kogo:** Agent persistence, tracing, complex workflows.  
- **AEGIS:** All of the above **plus** healthcare focus, Data Moat, 30+ integrations (health), human-in-the-loop.

Comparison matrix in spec:

| Feature | n8n | LangGraph | Temporal | AEGIS |
|---------|-----|-----------|----------|-------|
| Visual Builder | ✅ | ❌ | ❌ | ✅ (target) |
| State Management | ⚠️ | ✅ | ✅ | ✅ (target) |
| Multi-Agent | ❌ | ✅ | ❌ | ✅ (target) |
| Durable Execution | ⚠️ | ⚠️ | ✅ | ✅ (target) |
| Healthcare Focus | ❌ | ❌ | ❌ | ✅ |
| Data Moat | ❌ | ❌ | ❌ | ✅ |
| Human-in-Loop | ⚠️ | ✅ | ⚠️ | ✅ |

### Implemented vs “Better than n8n/Kogo”

| Capability | Status | Notes |
|------------|--------|--------|
| **Visual workflow builder** | 🟡 Partial | Custom canvas in `demo/src/app/studio/page.tsx` and builder; drag/drop, nodes, edges. **Not** React Flow yet; no minimap, versioning, or full n8n-style palette. |
| **State management** | ✅ | LangGraph state; state in workflow runs. |
| **Multi-agent** | ✅ | OrchestratorAgent, UnifiedView, Action, Insight, Triage; coordination pattern. |
| **Data Moat integration** | ✅ | Agents use DataMoatTools. |
| **Human-in-the-loop** | ✅ | Approval workflows (e.g. packages/aegis-ai HITL). |
| **Durable execution** | 🟡 Partial | Workflow definitions and executions in DB; no Temporal-style durable replay yet. |
| **Triggers** | 🟡 Partial | Webhook, schedule, event (Kafka) in spec; not all wired in UI. |
| **Tool registry** | ✅ | Data Moat, agents, LLM, actions, transforms. |
| **Healthcare nodes** | 🟡 Partial | Data Moat and agent nodes exist; “Query all 30+ entities” and specialty-specific nodes not yet. |

So: **agentic framework is “better than n8n/Kogo” on:**  
- Healthcare + Data Moat + multi-agent + HITL + tool registry.  
**Not yet at par on:**  
- Full visual builder (React Flow, versioning, full trigger set), and Temporal-grade durability.

**Recommendation:**  
- Document “AEGIS vs n8n/Kogo” in a short comparison (product/architecture).  
- Prioritize: (1) Data Moat “30+ entity” query, (2) React Flow visual builder, (3) durable execution (e.g. checkpointing or Temporal).

---

## 9. THERAPEUTIC-SPECIFIC AGENTS (Oncolife, Chaperone CKM, etc.)

### Intended
- Use the data in the Moat to build **therapeutic-specific** agents (e.g. oncology, nephrology).

### Implemented

| Area | Status | Notes |
|------|--------|--------|
| **Oncolife (oncology)** | 🟡 Vision + ontology only | PLATFORM_VISION: Oncolife described. Ontology: genomics (e.g. GeneticVariant, GenomicReport) for oncology. **No dedicated OncolifeAgent** that uses genomics + chemo + toxicity. |
| **Chaperone CKM (nephrology)** | 🟡 Vision + data only | PLATFORM_VISION: CKM, KFRE. Readmission model has N18 (CKD). **No dedicated CKMAgent** (KFRE, eGFR trends, care gaps, dialysis planning). |
| **Generic clinical agents** | ✅ | TriageAgent (labs, vitals, risk); UnifiedView (360); Action (denials); Insight (patterns). |
| **Specialty in ontology** | ✅ | Provider specialty; genomics models for oncology; N18 in readmission. |

So: **therapeutic-specific agents are not yet built.** You have:

- Data and ontology support (oncology, CKD).  
- Generic agents that could be specialized.  
- No **OncolifeAgent** or **ChaperoneCKMAgent** that encapsulate specialty workflows (e.g. KFRE, tumor board, toxicity triage).

**Recommendation:**  
- Add **OncolifeAgent**: inputs from Data Moat (demographics, conditions, meds, genomics, labs, encounters); tools for chemo regimens, toxicity, guidelines; outputs for patient app + provider dashboard.  
- Add **ChaperoneCKMAgent**: inputs (eGFR, ACR, BP, meds, encounters); KFRE (or wrapper); tools for care gaps, dialysis planning; outputs for CKM dashboard and outreach.  
- Both should use the same Data Moat + RAG (guidelines) + LLM gateway so “use the data we have to build agents” is explicit.

---

## 10. SUMMARY: What’s Done vs What’s Pending

### Done (Platform Angle)

- **Data Moat concept and first tools** (patient, risk, denials, claim, attention) over 7 DBs.  
- **Ingestion:** 15+ connector types (FHIR, HL7, X12, genomics, imaging, SDOH, PRO, documents, devices, scheduling, messaging, knowledge, compliance).  
- **Chunking:** Sliding, semantic, hierarchical; integrated in RAG.  
- **RAG:** End-to-end pipeline (load → chunk → embed → store → retrieve → generate) + API + evaluation.  
- **LLM:** Multi-provider gateway used by agents and RAG.  
- **Agentic framework:** Multi-agent (Orchestrator, View, Action, Insight, Triage), Data Moat tools, HITL, tool registry; custom workflow builder (non–React Flow).  
- **Orchestration spec** and comparison to n8n/Temporal/Kogo.  
- **Ontology** and **connectors** that support oncology and nephrology.

### Pending (Platform Angle)

1. **Data Moat = “query all 30+ entities”**  
   - Single registry and generic read/list per entity type for workflows/agents.

2. **30+ sources**  
   - Clarify: 30+ **source types** (connectors) vs 30+ **live connections**.  
   - One standard **ingestion path** from each connector into the Moat (and RAG where applicable).

3. **Agentic framework**  
   - React Flow visual builder; full trigger set; durable execution (e.g. checkpointing/Temporal).

4. **Therapeutic-specific agents**  
   - **OncolifeAgent** and **ChaperoneCKMAgent** (and optionally others) built on Data Moat + RAG + LLM.

5. **Production hardening**  
   - RAG: OpenSearch indexing, evaluation.  
   - Ingestion: lineage, DLQ, and monitoring for all source types.

---

## 11. RECOMMENDED NEXT STEPS (Platform Order)

1. **Data Moat entity registry**  
   - List 30+ entities; add generic “get/list by entity type” to Data Moat (or DataService) so the agentic layer can “query all 30+ entities.”

2. **Unified ingestion path**  
   - One pipeline: source type + payload → connector → validate → write to Moat (and optionally to RAG).  
   - Register “connected sources” (e.g. in `data_sources`).

3. **Therapeutic agents**  
   - Implement **OncolifeAgent** and **ChaperoneCKMAgent** on top of Data Moat + RAG (guidelines) + LLM; document as the model for “use the data we have to build agents.”

4. **Visual builder**  
   - Move to React Flow; add Data Moat “entity” nodes (per type or per tool); add triggers (schedule, webhook, Kafka).

5. **Durable execution**  
   - Introduce checkpointing and replay (or Temporal) so the framework is clearly “better than n8n/Kogo” on durability.

6. **Documentation**  
   - One-page “AEGIS platform: Data Moat → Ingestion → Chunking → RAG → LLM” and “AEGIS vs n8n/Kogo” for investors and partners.

---

**Last Updated:** February 6, 2026  
**Next Review:** After Data Moat entity registry and first therapeutic agent (Oncolife or CKM) are implemented.
