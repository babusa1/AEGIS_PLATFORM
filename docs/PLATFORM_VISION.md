# AEGIS: The Agentic Operating System for Healthcare

> "Palantir for Healthcare" - A unified operational OS that turns data into action

## Executive Summary

AEGIS is a next-generation healthcare platform that combines:
- **Real-time Digital Twin** of patient populations
- **AI-driven Agents** for autonomous clinical workflows
- **Canonical FHIR+Graph Ontology** unifying 19+ data sources

### Flagship Products
| Product | Domain | Description |
|---------|--------|-------------|
| **Oncolife** | Oncology | Patient mobile app + provider dashboard for chemotherapy support |
| **Chaperone CKM** | Nephrology | Chronic kidney disease management with KFRE risk prediction |

### Target Market
- **Providers**: Health systems, clinics (CIOs, CMIOs, Nurse Navigators)
- **Payers**: Managed care, Medicare/Medicaid plans
- **Pharma**: Real-world evidence (RWE), patient support programs

---

## The Three Pillars

### 1. Agentic AI Infrastructure

AI agents act as "connective tissue between fragmented systems, surfacing insights from siloed data."

```
┌─────────────────────────────────────────────────────────────────┐
│                    AEGIS AGENT ORCHESTRATION                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │
│  │ Unified   │  │  Action   │  │  Insight  │  │  Denial   │    │
│  │   View    │  │  Agent    │  │  Agent    │  │  Manager  │    │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘    │
│        │              │              │              │           │
│        └──────────────┴──────────────┴──────────────┘           │
│                              │                                   │
│                    ┌─────────▼─────────┐                        │
│                    │   LLM Gateway     │                        │
│                    │ (Bedrock/Gemini)  │                        │
│                    └─────────┬─────────┘                        │
│                              │                                   │
│                    ┌─────────▼─────────┐                        │
│                    │  Knowledge Graph  │                        │
│                    │ (FHIR + OMOP)     │                        │
│                    └───────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

**Agent Types:**
| Agent | Purpose | Actions |
|-------|---------|---------|
| Unified View | Patient 360 synthesis | Query graph, summarize, present |
| Action | Execute clinical tasks | Orders, referrals, messages |
| Insight | Discover patterns | Risk scores, care gaps, predictions |
| Denial Writer | Draft appeals | Generate appeal letters |
| Denial Auditor | Review appeals | Validate, critique, improve |
| Care Navigator | Patient engagement | Education, reminders, coaching |
| Symptom Checker | Triage symptoms | Assess urgency, recommend action |

### 2. Canonical Ontology (FHIR + Graph)

**19+ Data Sources Unified:**

| Category | Data Sources | Models |
|----------|--------------|--------|
| **Clinical Core** | EHRs (Epic, Cerner), ADT | Patient, Provider, Organization, Location, Encounter |
| **Diagnostics** | Labs, Pathology | Observation, DiagnosticReport |
| **Medications** | Pharmacy, MAR | Medication, MedicationRequest |
| **Procedures** | OR, Cath Lab | Procedure, ServiceRequest |
| **Genomics** | NGS Panels, Tumor Profiling | GeneticVariant, GenomicReport, MolecularSequence |
| **Imaging** | PACS, Radiology | ImagingStudy, ImagingReport |
| **Devices** | Wearables, IoMT, Implants | Device, DeviceMetric, WearableData |
| **Financial** | Claims, Billing, Denials | Claim, ClaimLine, Denial, Authorization, Coverage |
| **Care Coordination** | Care Plans, Referrals | CarePlan, Goal, CareTeam, Task, Referral |
| **SDOH** | Social Determinants | SocialHistory, SDOHAssessment, CommunityResource |
| **Engagement** | Portal, App, Messages | Communication, Appointment, PatientEngagement |
| **Documents** | Notes, Consent, PROs | DocumentReference, Consent, QuestionnaireResponse |
| **Analytics** | Risk Models, Quality | RiskScore, CareGap, AIRecommendation, Cohort |

**Graph Relationships:**
```
Patient ──HAS_ENCOUNTER──► Encounter ──HAS_DIAGNOSIS──► Diagnosis
    │                          │
    ├──HAS_COVERAGE──► Coverage │──HAS_PROCEDURE──► Procedure
    │                          │
    ├──HAS_OBSERVATION──► Observation (labs, vitals)
    │                          │
    └──HAS_CARE_TEAM──► CareTeam ──HAS_MEMBER──► Provider
                               │
Encounter ──HAS_CLAIM──► Claim ──HAS_DENIAL──► Denial
                               │
Patient ──HAS_VARIANT──► GeneticVariant ──ACTIONABLE_FOR──► Medication
```

### 3. Live Digital Twin

Real-time perception-to-action loop:

```
┌────────────────────────────────────────────────────────────────┐
│                     DIGITAL TWIN LOOP                          │
│                                                                │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐ │
│   │  INGEST  │───►│  ANALYZE │───►│  DECIDE  │───►│  ACT   │ │
│   └──────────┘    └──────────┘    └──────────┘    └────────┘ │
│        ▲                                              │       │
│        │                                              │       │
│        └──────────────────────────────────────────────┘       │
│                      FEEDBACK LOOP                             │
│                                                                │
│   Data Sources:          Analytics:           Actions:         │
│   - EHR events          - Risk scores        - Alerts         │
│   - Wearable streams    - Care gaps          - Orders         │
│   - Lab results         - Predictions        - Messages       │
│   - Claims adjudication - Anomaly detection  - Referrals      │
│   - Patient messages    - Cohort matching    - Care plans     │
└────────────────────────────────────────────────────────────────┘
```

---

## Product Lines

### Oncolife (Oncology Care Companion)

**Patient App Features:**
- Conversational AI for symptom triage
- Medication reminders with chemo protocols
- Side effect management (nausea, fatigue, etc.)
- Diet/nutrition coaching
- Appointment scheduling

**Provider Dashboard:**
- Real-time patient status
- Risk flags (infection, dehydration, etc.)
- Adherence metrics
- Genomic variant actionability
- Care gap alerts (tumor boards, scans)

**Key Data Models:**
- GeneticVariant (BRCA, EGFR, etc.)
- GenomicReport (FoundationOne, Tempus)
- Medication (chemo regimens)
- Observation (toxicity grades)
- Communication (patient coaching)

### Chaperone CKM (Chronic Kidney Management)

**Risk Stratification:**
- Kidney Failure Risk Equation (KFRE)
- 2-year and 5-year progression probability
- Real-time eGFR trending

**Patient App Features:**
- Daily BP, weight, symptom logging
- Wearable/device integration
- Diet coaching (sodium, potassium, protein)
- Medication adherence tracking
- Education modules

**Provider Dashboard:**
- CKD cohort overview
- High-risk patient prioritization
- Care gap tracking (ACR, A1C, BP control)
- Dialysis planning triggers
- Referral management

**Key Data Models:**
- Observation (eGFR, creatinine, albumin)
- RiskScore (KFRE model)
- CareGap (screening, vaccinations)
- WearableData (BP, weight)
- CarePlan (CKD pathway)

---

## Technology Stack

### Current Implementation Status

| Component | Technology | Status |
|-----------|------------|--------|
| **Graph Database** | JanusGraph (dev) / Neptune (prod) | ✅ Abstraction layer built |
| **Ontology** | FHIR R4 + OMOP CDM Pydantic models | ✅ 40+ models, 19+ sources |
| **API Layer** | FastAPI + JWT auth | ✅ Demo working |
| **OIDC Auth** | Cognito / Auth0 / Okta | ✅ Provider abstraction |
| **PBAC** | Purpose-Based Access Control | ✅ HIPAA-compliant |
| **Multi-tenancy** | Schema-per-tenant + TenantContext | ✅ Isolation built |
| **Audit Logging** | PHI access tracking | ✅ HIPAA compliance |
| **LLM Gateway** | Bedrock (primary) + OpenAI fallback | ✅ Multi-provider with failover |
| **Agent Framework** | ReAct agents with tool use | ✅ Patient360, CareGap, Denial agents |
| **Tool Registry** | Healthcare tools (graph, clinical, RCM) | ✅ 10+ tools registered |
| **Human-in-the-Loop** | Approval workflows | ✅ Built for sensitive actions |
| **Event Streaming** | Kafka/MSK | 📋 Planned |
| **CI/CD** | GitHub Actions | ✅ Demo verification |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AEGIS PLATFORM                               │
├─────────────────────────────────────────────────────────────────────┤
│  PRESENTATION LAYER                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ Provider    │  │ Patient     │  │ API         │                 │
│  │ Dashboard   │  │ Mobile App  │  │ Gateway     │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
├─────────────────────────────────────────────────────────────────────┤
│  AGENT LAYER                                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  LangGraph Orchestration                                      │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │  │
│  │  │ View    │ │ Action  │ │ Insight │ │ Denial  │            │  │
│  │  │ Agent   │ │ Agent   │ │ Agent   │ │ Agents  │            │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘            │  │
│  └──────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│  LLM GATEWAY                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ AWS Bedrock │  │ Google      │  │ OpenAI      │                 │
│  │ (Primary)   │  │ Gemini      │  │ (Fallback)  │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
├─────────────────────────────────────────────────────────────────────┤
│  DATA LAYER                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Graph DB     │  │ Vector DB    │  │ Relational   │              │
│  │ (Neptune)    │  │ (OpenSearch) │  │ (PostgreSQL) │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
├─────────────────────────────────────────────────────────────────────┤
│  INTEGRATION LAYER                                                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │ FHIR    │ │ HL7v2   │ │ Claims  │ │ Devices │ │ Wearable│      │
│  │ Adapter │ │ Adapter │ │ Adapter │ │ Gateway │ │ SDK     │      │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Roadmap

### Phase 0-1: Foundation ✅ COMPLETE
- [x] Demo stabilization
- [x] CI/CD pipeline
- [x] Git repository setup
- [x] Basic API with auth

### Phase 2: Data Spine ✅ COMPLETE
- [x] Graph DB abstraction (JanusGraph/Neptune)
- [x] Ontology package (40+ FHIR/OMOP models)
- [x] 19+ data source coverage
- [x] Monorepo structure

### Phase 3: Auth & Multi-tenancy ✅ COMPLETE
- [x] OIDC provider abstraction (Cognito/Auth0/Okta)
- [x] Purpose-Based Access Control (PBAC)
- [x] Schema-per-tenant isolation
- [x] Audit logging

### Phase 4: AI/Agent Layer ✅ COMPLETE
- [x] LLM Gateway (Bedrock + OpenAI failover)
- [x] Agent framework (ReAct-style)
- [x] Tool registry (10+ healthcare tools)
- [x] Human-in-the-loop workflows

### Phase 5: Use Cases 🔄 NEXT
- [ ] Patient 360 (unified view)
- [ ] RCM/Denial Management
- [ ] Care Gaps identification
- [ ] Oncolife MVP
- [ ] Chaperone CKM MVP

### Phase 6+: Scale
- [ ] Event streaming (Kafka)
- [ ] Real-time pipelines
- [ ] Federated learning
- [ ] Network effects

---

## Business Model

| Offering | Pricing Model | Target |
|----------|--------------|--------|
| Oncolife | PPPM ($15-30/patient/month) | Cancer centers |
| Chaperone CKM | PPPM ($10-25/patient/month) | Nephrology practices |
| Platform License | Enterprise annual | Health systems |
| RWE/Analytics | Data access fees | Pharma |

**Outcomes-based incentives:** Portion of fees tied to quality metrics (reduced admissions, improved labs).

---

## Competitive Differentiation

| Competitor | Gap | AEGIS Advantage |
|------------|-----|-----------------|
| Palantir Foundry | General-purpose, no clinical workflows | Healthcare-native ontology + agents |
| Epic/Cerner | Closed ecosystem, batch analytics | Open, real-time, multi-source |
| Point solutions | Single domain (RCM OR engagement OR analytics) | Unified platform |
| Generic AI | No healthcare context | FHIR-native, HIPAA-compliant |

---

## Key Metrics to Track

| Category | Metric |
|----------|--------|
| **Engagement** | App DAU/MAU, session duration |
| **Clinical** | Care gaps closed, risk score accuracy |
| **Operational** | Denial overturn rate, time-to-action |
| **Financial** | Cost avoided per patient, ROI |

---

## Next Steps

1. **Complete Phase 3** - Auth & Multi-tenancy
2. **Build Phase 4** - LLM Gateway & Agent Framework
3. **MVP for Oncolife or CKM** - Pick one vertical to go deep
4. **Pilot with 1-2 health systems** - Validate value proposition
5. **Iterate based on feedback** - Refine agents, ontology, UX

---

*"The time to transform healthcare operations is now."*
