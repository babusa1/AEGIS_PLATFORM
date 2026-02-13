# AEGIS Platform: Functional Specification

**Version**: 2.0  
**Last Updated**: February 6, 2026  
**Status**: Production-Ready (100% Complete)

---

## 1. FEATURE OVERVIEW

### Core Features by Pillar

#### Pillar 1: Data Moat
- **Entity Registry**: 30+ entity types (Patient, Condition, Medication, Claim, Denial, etc.)
- **Unified Query API**: `get_entity_by_id()`, `list_entities()` for all types
- **Graph Traversal**: Path-finding across clinical relationships
- **Semantic Mapping**: LLM-enriched fuzzy matching (local codes → LOINC/SNOMED-CT)
- **Temporal Patterns**: Vectorized timelines with Time_Offset

#### Pillar 2: Agentic Framework
- **Multi-Agent Orchestration**: Supervisor-Worker architecture
- **Visual Workflow Builder**: React Flow-based drag-and-drop
- **Durable Execution**: Checkpointing, replay, crash recovery
- **Human-in-the-Loop**: 3-tier approval workflow

#### Pillar 3: Clinical RAG
- **GraphRAG**: Path-finding across knowledge graph
- **Temporal Hybrid Search**: Vector + Keyword + Graph search
- **Recursive Summarization**: Hierarchical summaries (Daily → Weekly → Monthly)
- **Source Attribution**: Every claim linked to FHIR resource

#### Pillar 4: Bridge Apps
- **Oncolife**: Oncology symptom checker, CTCAE grading, infusion optimization
- **Chaperone CKM**: CKD management, KFRE, dialysis planning, transplant readiness

#### Pillar 5: HITL & Governance
- **3-Tier Approval**: Automated, Assisted, Clinical
- **Guideline Cross-Check**: NCCN, KDIGO guidelines
- **Conflict Detection**: Drug-drug, drug-lab interactions
- **Audit Attribution**: GUIDELINE_ID, SOURCE_LINK

---

## 2. USE CASES

### UC-1: Patient 360 View

**Actor**: Clinician  
**Precondition**: Patient exists in Data Moat  
**Flow**:
1. Clinician requests patient 360 view
2. LibrarianAgent retrieves patient data from Data Moat
3. LibrarianAgent traverses graph (Patient → Encounters → Conditions → Medications)
4. LibrarianAgent creates recursive summary (recent → monthly → yearly)
5. System displays unified patient view with timeline, labs, meds, conditions

**Postcondition**: Clinician sees complete patient context

---

### UC-2: Cowork Session - Abnormal Lab Alert

**Actor**: ScoutAgent (triggered), Clinician  
**Precondition**: Patient has active Cowork session  
**Flow**:
1. ScoutAgent detects critical lab result (K+ > 6.0) via Kafka event
2. ScoutAgent triggers Cowork session
3. LibrarianAgent retrieves patient context (medications, labs, conditions)
4. GuardianAgent checks guidelines (KDIGO: ACE inhibitor contraindicated with K+ > 5.5)
5. GuardianAgent blocks unsafe action (continuing ACE inhibitor)
6. ScribeAgent drafts intervention (Hold ACE inhibitor, re-check BMP in 24h)
7. System presents case to Clinician in Cowork sidebar
8. Clinician reviews, edits, approves
9. ScribeAgent writes order to EHR via FHIR RequestGroup

**Postcondition**: Order written to EHR, patient notified

---

### UC-3: Denial Appeal Generation

**Actor**: Revenue Cycle Manager  
**Precondition**: Denial exists in Data Moat  
**Flow**:
1. RCM requests denial appeal
2. ActionAgent retrieves denial details (claim, denial reason, patient context)
3. ActionAgent queries Data Moat for supporting evidence
4. ActionAgent generates appeal letter with citations
5. ActionAgent (Critic) reviews and improves appeal
6. System presents draft to RCM
7. RCM reviews, edits, approves
8. System sends appeal to payer

**Postcondition**: Appeal letter generated and sent

---

### UC-4: Oncolife Symptom Checker

**Actor**: Patient  
**Precondition**: Patient has active Oncolife account  
**Flow**:
1. Patient logs symptom ("Severe Fatigue") in mobile app
2. SymptomCheckerService grades symptom (CTCAE Grade 3)
3. System loads patient context (current chemo cycle, labs, meds)
4. LibrarianAgent retrieves relevant history (previous cycles, reactions)
5. GuardianAgent checks NCCN guidelines (anemia management)
6. System provides personalized recommendation:
   - Low Risk: "Stay hydrated, we've updated your diary"
   - High Risk: "Red Alert" → Triggers Cowork session with oncologist
7. If high risk, ScoutAgent triggers Cowork session
8. Oncologist reviews in Cowork sidebar, approves intervention

**Postcondition**: Patient receives appropriate care, high-risk cases escalated

---

### UC-5: Transplant Readiness Checklist

**Actor**: Transplant Coordinator  
**Precondition**: Patient in transplant queue  
**Flow**:
1. Coordinator requests transplant readiness assessment
2. TransplantReadinessAgent retrieves patient data
3. Agent checks 50+ required documents/tests:
   - Lab results (eGFR, A1C, etc.)
   - Imaging (chest X-ray, EKG)
   - Consents (living will, advance directive)
   - Evaluations (cardiac, pulmonary, psych)
4. Agent identifies missing items, expiring items
5. Agent generates checklist with priorities
6. System alerts coordinator when patient "falls out" of queue

**Postcondition**: Complete transplant readiness status, actionable checklist

---

## 3. USER STORIES

### Epic: Data Moat

**US-1**: As a developer, I want to query any entity type using a unified API, so I don't need to know the underlying database structure.

**US-2**: As a clinician, I want to see all patient data in one view, so I can make informed decisions quickly.

**US-3**: As a data engineer, I want to map local lab codes to LOINC automatically, so terminology is standardized.

### Epic: Agentic Framework

**US-4**: As a clinician, I want agents to collaborate like a clinical team, so I can focus on patient care instead of documentation.

**US-5**: As a workflow builder, I want to visually design workflows using drag-and-drop, so I can create complex automations without coding.

**US-6**: As a system administrator, I want workflows to survive crashes, so critical processes aren't lost.

### Epic: Clinical RAG

**US-7**: As a clinician, I want AI responses to cite sources, so I can verify recommendations.

**US-8**: As a researcher, I want to search patient histories temporally, so I can find patterns across time.

**US-9**: As a clinician, I want summaries of long patient histories, so I can quickly understand context.

### Epic: Bridge Apps

**US-10**: As a cancer patient, I want to log symptoms and get immediate feedback, so I know when to seek help.

**US-11**: As a nephrologist, I want to see CKD patients ranked by risk, so I can prioritize care.

**US-12**: As a transplant coordinator, I want automated tracking of transplant requirements, so patients don't fall out of queue.

---

## 4. API ENDPOINTS

### Cowork API

```
POST   /api/v1/cowork/sessions
       Create new Cowork session
       
GET    /api/v1/cowork/sessions
       List all Cowork sessions
       
GET    /api/v1/cowork/sessions/{session_id}
       Get session details
       
PUT    /api/v1/cowork/sessions/{session_id}
       Update session
       
DELETE /api/v1/cowork/sessions/{session_id}
       Delete session
       
WS     /api/v1/cowork/sessions/{session_id}/ws
       WebSocket connection for real-time updates
```

### Agent API

```
POST   /api/v1/agents/{agent_type}/execute
       Execute agent (librarian, guardian, scribe, scout)
       
GET    /api/v1/agents/{agent_type}/status
       Get agent status
       
POST   /api/v1/agents/{agent_type}/tools/register
       Register custom tool
```

### Patient API

```
GET    /api/v1/patients/{patient_id}
       Get patient details
       
GET    /api/v1/patients/{patient_id}/timeline
       Get patient timeline
       
GET    /api/v1/patients/{patient_id}/360
       Get patient 360 view
```

### Workflow API

```
POST   /api/v1/workflows/execute
       Execute workflow
       
GET    /api/v1/workflows/{workflow_id}/status
       Get workflow execution status
       
GET    /api/v1/workflows/{workflow_id}/checkpoint
       Get workflow checkpoint
       
POST   /api/v1/workflows/{workflow_id}/replay
       Replay workflow from checkpoint
```

---

## 5. BRIDGE APPS SPECIFICATIONS

### Oncolife

**Features**:
- **Symptom Checker**: Conversational AI for symptom triage
- **CTCAE Grading**: Automatic toxicity grading (Grade 1-4)
- **Infusion Optimization**: Predicts reactions, pre-populates pre-meds
- **Regimen Adherence**: Tracks chemo cycles, detects missed doses
- **Real-Time Agent Consultation**: Triggers Cowork session for high-risk symptoms

**Data Models**:
- `GeneticVariant`: BRCA, EGFR, etc.
- `GenomicReport`: FoundationOne, Tempus
- `Medication`: Chemo regimens
- `Observation`: Toxicity grades

### Chaperone CKM

**Features**:
- **KFRE Calculation**: Kidney Failure Risk Equation (2-year, 5-year)
- **eGFR Trending**: Real-time eGFR monitoring
- **Dialysis Planning**: Triggers for Stage 4 CKD
- **Transplant Readiness**: Manages 50+ documents/tests
- **Organ Conflict Detection**: Heart vs Kidney interventions

**Data Models**:
- `Observation`: eGFR, creatinine, albumin
- `RiskScore`: KFRE model
- `CareGap`: Screening, vaccinations
- `WearableData`: BP, weight

---

## 6. COWORK WORKFLOW SPECIFICATION

### OODA Loop

1. **Perceive** (ScoutAgent)
   - Kafka event listening
   - Detects critical events (labs, vitals, symptoms)
   - Triggers Cowork session

2. **Orient** (LibrarianAgent)
   - Retrieves patient context
   - Traverses graph for related data
   - Creates recursive summary

3. **Decide** (GuardianAgent)
   - Checks guidelines (NCCN, KDIGO)
   - Detects conflicts (drug-drug, drug-lab)
   - Blocks unsafe actions

4. **Collaborate** (Supervisor)
   - Presents case to clinician
   - Shows evidence links
   - Waits for human input

5. **Act** (Human + ScribeAgent)
   - Clinician reviews, edits
   - Approves intervention
   - ScribeAgent writes to EHR

### Session State

```python
{
    "patient_id": "patient-123",
    "clinical_context": {...},
    "active_artifacts": {...},
    "safety_audit": [...],
    "evidence_links": [...],
    "messages": [...],
    "status": "approval_required"
}
```

---

## 7. AGENT BEHAVIORS

### LibrarianAgent

**Input**: Patient ID, query  
**Output**: Patient context, graph paths, summaries

**Behaviors**:
- Graph traversal (follows clinical edges)
- Temporal delta calculation
- Recursive summarization
- Source attribution

### GuardianAgent

**Input**: Proposed action, patient context  
**Output**: Safety check result, violations, recommendations

**Behaviors**:
- Guideline cross-check (NCCN, KDIGO)
- Conflict detection (drug-drug, drug-lab)
- Safety block with rationale
- Audit attribution

### ScribeAgent

**Input**: Patient ID, artifact type, context  
**Output**: Generated artifact (SOAP note, referral, order)

**Behaviors**:
- SOAP note generation
- Referral letter drafting
- Prior authorization requests
- Order pre-population (FHIR RequestGroup)
- Patient translation (multilingual)

### ScoutAgent

**Input**: Kafka events, patient data  
**Output**: Alerts, triage recommendations

**Behaviors**:
- Event listening (Kafka)
- Trend prediction (slow-burn risks)
- No-show detection
- Medication gap detection

---

## 8. DATA INGESTION SPECIFICATIONS

### Supported Sources (30+)

**Tier 1**: FHIR R4, HL7v2, CDA/CCDA  
**Tier 2**: X12 (837/835, 270/271, 276/277, 278)  
**Tier 3**: Apple HealthKit, Google Fit, Fitbit, Garmin, Withings  
**Tier 4**: Genomics (VCF, GA4GH), Imaging (DICOM, DICOMweb), SDOH, PRO  
**Tier 5**: Messaging, Scheduling, Workflow, Analytics, Guidelines, Drug Labels

### Ingestion Pipeline

```
Source → Connector → Parser → Validator → Normalizer → Data Moat
```

**Steps**:
1. **Connector**: Receives payload, identifies source type
2. **Parser**: Parses format (FHIR JSON, HL7v2, X12, etc.)
3. **Validator**: Validates against schema
4. **Normalizer**: Maps to canonical ontology (SNE)
5. **Data Moat**: Writes to PostgreSQL + Graph + Kafka

---

## 9. GUIDELINE SPECIFICATIONS

### NCCN Guidelines

**Sections**:
- Anemia Management (Hgb < 8.0 → Hold dose)
- Neutropenia Management (ANC < 500 → Hold dose)
- CTCAE v5.0 Toxicity Grading

**Methods**:
- `check_dose_hold_criteria(lab_values)`: Returns violations and recommendations

### KDIGO Guidelines

**Sections**:
- CKD-MBD Management
- Dialysis Planning
- Medication Dosing in CKD

**Methods**:
- `check_medication_contraindication(medication, labs)`: Returns contraindications

---

## 10. EHR WRITE-BACK SPECIFICATIONS

### FHIR RequestGroup

**Structure**:
```json
{
  "resourceType": "RequestGroup",
  "action": [
    {
      "resource": {
        "resourceType": "MedicationRequest",
        "medicationCodeableConcept": {...},
        "dosageInstruction": {...}
      }
    }
  ]
}
```

### Supported Orders

- **Lab Orders**: BMP, CBC, CMP, etc.
- **Imaging Orders**: X-ray, CT, MRI
- **Medication Orders**: Prescriptions with dosing

### Write-Back Flow

1. ScribeAgent drafts order (FHIR RequestGroup)
2. System presents to clinician for approval
3. Clinician reviews, edits, approves
4. EHRWriteBackService sends RequestGroup to EHR (Epic/Cerner)
5. EHR pre-populates order entry form
6. Clinician signs order in EHR

---

**Last Updated**: February 6, 2026  
**Document Owner**: Product Team
