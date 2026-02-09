# AEGIS Cowork Implementation Plan: Options 1 & 2

**Date**: February 6, 2026  
**Goal**: Implement 100% of missing and partially-done features  
**Approach**: Production-ready, best UX, good architecture, no stubs

---

## 🎯 OVERVIEW

This plan implements:
- **Option 1**: Rename to match spec (Cowork branding + explicit personas)
- **Option 2**: Complete all missing features

**Total Tasks**: 17 major features  
**Estimated Timeline**: 8-10 weeks (done properly, production-ready)

---

## 📋 PHASE 1: OPTION 1 - BRANDING & PERSONAS (Week 1-2)

### 1.1 CoworkEngine Wrapper ✅
**Goal**: Create `CoworkEngine` that wraps `WorkflowEngine` with "Cowork" branding

**Implementation**:
- Create `src/aegis/cowork/engine.py`
- Wrap `WorkflowEngine` functionality
- Add Cowork-specific state management
- Add session persistence (Redis)
- Add multi-user support foundation

**Files**:
- `src/aegis/cowork/engine.py` (new)
- `src/aegis/cowork/__init__.py` (new)
- `src/aegis/cowork/models.py` (new) - CoworkState, CoworkSession

**Dependencies**: None (uses existing WorkflowEngine)

---

### 1.2 LibrarianAgent Wrapper ✅
**Goal**: Create explicit `LibrarianAgent` that wraps `UnifiedViewAgent` + `RAGRetriever`

**Implementation**:
- Create `src/aegis/agents/personas/librarian.py`
- Wrap `UnifiedViewAgent` functionality
- Add GraphRAG path-finding methods
- Add temporal delta analysis
- Add recursive summarization interface

**Files**:
- `src/aegis/agents/personas/librarian.py` (new)
- `src/aegis/agents/personas/__init__.py` (new)

**Dependencies**: UnifiedViewAgent, RAGRetriever (existing)

---

### 1.3 GuardianAgent Wrapper ✅
**Goal**: Create explicit `GuardianAgent` that wraps `TriageAgent` + `GuardrailsEngine`

**Implementation**:
- Create `src/aegis/agents/personas/guardian.py`
- Wrap `TriageAgent` functionality
- Add guideline cross-check methods
- Add conflict detection (drug-drug, drug-lab)
- Add explanation engine (citation links)

**Files**:
- `src/aegis/agents/personas/guardian.py` (new)

**Dependencies**: TriageAgent, GuardrailsEngine (existing)

---

### 1.4 ScribeAgent Wrapper ✅
**Goal**: Create explicit `ScribeAgent` that wraps `ActionAgent` with SOAP/Referral/PriorAuth focus

**Implementation**:
- Create `src/aegis/agents/personas/scribe.py`
- Wrap `ActionAgent` functionality
- Add SOAP note generation
- Add referral letter generation
- Add prior authorization generation
- Add order pre-population (FHIR RequestGroup) - will be completed in 2.2

**Files**:
- `src/aegis/agents/personas/scribe.py` (new)

**Dependencies**: ActionAgent (existing)

---

### 1.5 ScoutAgent Wrapper ✅
**Goal**: Create explicit `ScoutAgent` that wraps `KafkaEventConsumer` + `TriageEventHandler`

**Implementation**:
- Create `src/aegis/agents/personas/scout.py`
- Wrap `KafkaEventConsumer` functionality
- Add proactive triage methods
- Add event-triggered Cowork session creation
- Add trend prediction (slow-burn risks)

**Files**:
- `src/aegis/agents/personas/scout.py` (new)

**Dependencies**: KafkaEventConsumer, TriageEventHandler (existing)

---

### 1.6 Cowork UI Branding ✅
**Goal**: Add "Cowork" branding to React UI

**Implementation**:
- Update `demo/src/app/` components
- Add `/cowork` routes
- Add Cowork branding (logos, colors, naming)
- Update navigation
- Add Cowork session UI

**Files**:
- `demo/src/app/cowork/` (new directory)
- `demo/src/app/cowork/page.tsx` (new)
- `demo/src/app/cowork/[sessionId]/page.tsx` (new)
- Update existing components with Cowork branding

**Dependencies**: Next.js, React (existing)

---

## 📋 PHASE 2: OPTION 2 - MISSING FEATURES (Week 3-10)

### 2.1 NCCN/KDIGO Guideline Databases ✅
**Goal**: Implement specialty-specific guideline databases with vectorized storage

**Implementation**:
- Create `src/aegis/guidelines/nccn.py` - NCCN oncology guidelines
- Create `src/aegis/guidelines/kdigo.py` - KDIGO nephrology guidelines
- Create `src/aegis/guidelines/loader.py` - Guideline loader from PDF/structured data
- Create `src/aegis/guidelines/vectorizer.py` - Vectorize guidelines for RAG
- Create `src/aegis/guidelines/retriever.py` - Retrieve relevant guidelines
- Create `src/aegis/guidelines/cross_check.py` - Cross-check agent outputs against guidelines

**Data Sources**:
- NCCN Guidelines (oncology)
- KDIGO Guidelines (nephrology)
- ACC/AHA Guidelines (cardiology) - bonus

**Files**:
- `src/aegis/guidelines/__init__.py` (new)
- `src/aegis/guidelines/base.py` (new) - BaseGuideline class
- `src/aegis/guidelines/nccn.py` (new)
- `src/aegis/guidelines/kdigo.py` (new)
- `src/aegis/guidelines/loader.py` (new)
- `src/aegis/guidelines/vectorizer.py` (new)
- `src/aegis/guidelines/retriever.py` (new)
- `src/aegis/guidelines/cross_check.py` (new)

**Dependencies**: Vector DB (existing), RAG pipeline (existing)

---

### 2.2 EHR Write-Back (FHIR RequestGroup) ✅
**Goal**: Implement order pre-population and write-back to EHR

**Implementation**:
- Create `src/aegis/ehr/writeback.py` - EHR write-back service
- Create `src/aegis/ehr/request_group.py` - FHIR RequestGroup builder
- Create `src/aegis/ehr/orders.py` - Order generation (labs, imaging, meds)
- Integrate with Epic/Cerner via SMART-on-FHIR
- Add approval workflow before write-back

**Files**:
- `src/aegis/ehr/__init__.py` (new)
- `src/aegis/ehr/writeback.py` (new)
- `src/aegis/ehr/request_group.py` (new)
- `src/aegis/ehr/orders.py` (new)
- `src/aegis/ehr/epic.py` (new) - Epic-specific write-back
- `src/aegis/ehr/cerner.py` (new) - Cerner-specific write-back

**Dependencies**: SMART-on-FHIR (existing), FHIR client (existing)

---

### 2.3 3-Pane Workspace UI ✅
**Goal**: Build production-ready 3-pane workspace UI

**Implementation**:
- Left Pane: Patient 360 (Timeline, Labs, Meds, Conditions)
- Middle Pane: Agentic Chat (collaboration thread)
- Right Pane: Artifacts (current document being co-written)
- Real-time updates via WebSocket (2.4)
- Drag-and-drop for artifacts
- Split-pane resizing

**Files**:
- `demo/src/app/cowork/workspace/page.tsx` (new)
- `demo/src/components/cowork/Patient360Pane.tsx` (new)
- `demo/src/components/cowork/ChatPane.tsx` (new)
- `demo/src/components/cowork/ArtifactPane.tsx` (new)
- `demo/src/components/cowork/WorkspaceLayout.tsx` (new)

**Dependencies**: React, WebSocket (2.4), Patient data API (existing)

---

### 2.4 WebSocket Real-Time Communication ✅
**Goal**: Implement WebSocket for real-time Cowork sessions

**Implementation**:
- Create `src/aegis/api/websocket.py` - WebSocket handler
- Create `src/aegis/cowork/realtime.py` - Real-time state sync
- Add message broadcasting
- Add typing indicators
- Add presence (who's in session)
- Add conflict resolution (concurrent edits)

**Files**:
- `src/aegis/api/websocket.py` (new)
- `src/aegis/cowork/realtime.py` (new)
- `demo/src/hooks/useWebSocket.ts` (new) - React hook

**Dependencies**: FastAPI WebSocket, Redis pub/sub (existing)

---

### 2.5 Multi-User Cowork Sessions ✅
**Goal**: Support multiple clinicians in same Cowork session

**Implementation**:
- Extend `CoworkSession` model with `participants` list
- Add user presence tracking
- Add role-based permissions (who can edit/approve)
- Add collaborative editing (operational transform or CRDT)
- Add user avatars/names in UI
- Add activity feed (who did what)

**Files**:
- `src/aegis/cowork/session.py` (new) - Session management
- `src/aegis/cowork/collaboration.py` (new) - Collaborative editing
- Update `CoworkEngine` for multi-user
- Update UI for multi-user

**Dependencies**: Redis (existing), WebSocket (2.4)

---

### 2.6 Patient Translation (Multilingual) ✅
**Goal**: Generate patient instructions in any language at 5th-grade reading level

**Implementation**:
- Create `src/aegis/translation/engine.py` - Translation engine
- Integrate with LLM for translation
- Add health literacy adjustment (5th-grade level)
- Add tone adjustment based on patient's recorded literacy
- Support: Spanish, Chinese, Arabic, Hindi, etc.

**Files**:
- `src/aegis/translation/__init__.py` (new)
- `src/aegis/translation/engine.py` (new)
- `src/aegis/translation/literacy.py` (new) - Literacy adjustment
- `src/aegis/translation/languages.py` (new) - Language support

**Dependencies**: LLM client (existing)

---

### 2.7 Infusion Optimization ✅
**Goal**: Predict infusion reactions and pre-populate pre-medication regimens

**Implementation**:
- Create `src/aegis/oncology/infusion.py` - Infusion optimization
- Analyze patient history (previous cycles, reactions)
- Predict reaction probability
- Generate pre-medication regimen
- Integrate with OncolifeAgent

**Files**:
- `src/aegis/oncology/infusion.py` (new)
- `src/aegis/oncology/reaction_predictor.py` (new)
- Update `OncolifeAgent` to use infusion optimization

**Dependencies**: OncolifeAgent (existing), ML models (new)

---

### 2.8 Transplant Readiness Agent ✅
**Goal**: Manage 50+ documents/tests required for transplant listing

**Implementation**:
- Create `src/aegis/agents/transplant_readiness.py` - Transplant readiness agent
- Track required documents (lab results, imaging, consents, etc.)
- Track required tests (cardiac, pulmonary, etc.)
- Identify missing items
- Generate checklist
- Alert when patient "falls out" of queue

**Files**:
- `src/aegis/agents/transplant_readiness.py` (new)
- `src/aegis/transplant/checklist.py` (new) - Transplant checklist
- `src/aegis/transplant/tracker.py` (new) - Document/test tracking

**Dependencies**: Data Moat (existing), ChaperoneCKMAgent (existing)

---

### 2.9 No-Show Detection ✅
**Goal**: Compare Claims data with EHR schedules to detect no-shows

**Implementation**:
- Create `src/aegis/monitoring/no_show.py` - No-show detection
- Compare scheduled appointments (EHR) vs actual visits (Claims)
- Identify patterns (frequent no-shows)
- Alert Nurse Navigator
- Generate outreach plan

**Files**:
- `src/aegis/monitoring/no_show.py` (new)
- `src/aegis/monitoring/appointment_matcher.py` (new)
- Update `ScoutAgent` to use no-show detection

**Dependencies**: Claims data (existing), EHR integration (existing)

---

### 2.10 Hallucination Retry Logic ✅
**Goal**: Auto-retry with strict search when hallucination detected

**Implementation**:
- Extend `HallucinationDetector` with retry logic
- Create `src/aegis/llm/retry.py` - Retry handler
- On detection: wipe response, retry with strict search
- Add max retry limit
- Log retry attempts

**Files**:
- `src/aegis/llm/retry.py` (new)
- Update `HallucinationDetector` with retry
- Update `BaseAgent` to use retry logic

**Dependencies**: HallucinationDetector (existing), RAG retriever (existing)

---

### 2.11 Formal Agent SDK ✅
**Goal**: Create production-ready Agent SDK for 3rd party developers

**Implementation**:
- Create `packages/aegis-agent-sdk/` - SDK package
- Add `BaseAgent` wrapper for external agents
- Add tool registration system
- Add graph access API
- Add Cowork UI integration hooks
- Create documentation and examples
- Create plugin system

**Files**:
- `packages/aegis-agent-sdk/` (new directory)
- `packages/aegis-agent-sdk/src/aegis_sdk/agent.py` (new)
- `packages/aegis-agent-sdk/src/aegis_sdk/tools.py` (new)
- `packages/aegis-agent-sdk/src/aegis_sdk/graph.py` (new)
- `packages/aegis-agent-sdk/docs/` (new) - Documentation
- `packages/aegis-agent-sdk/examples/` (new) - Example agents

**Dependencies**: BaseAgent (existing), ToolRegistry (existing)

---

## 🏗️ ARCHITECTURE PRINCIPLES

1. **Production-Ready**: No stubs, full error handling, logging, monitoring
2. **Best UX**: Intuitive interfaces, real-time updates, collaborative editing
3. **Good Architecture**: Modular, testable, maintainable, scalable
4. **Backward Compatible**: Existing code continues to work
5. **Incremental**: Each feature can be deployed independently

---

## 📊 IMPLEMENTATION ORDER

### Week 1-2: Option 1 (Branding & Personas)
1. CoworkEngine wrapper
2. LibrarianAgent wrapper
3. GuardianAgent wrapper
4. ScribeAgent wrapper
5. ScoutAgent wrapper
6. UI branding

### Week 3-4: Core Features
1. NCCN/KDIGO guidelines
2. EHR write-back
3. WebSocket real-time

### Week 5-6: UI & Collaboration
1. 3-pane workspace UI
2. Multi-user sessions

### Week 7-8: Advanced Features
1. Patient translation
2. Infusion optimization
3. Transplant readiness

### Week 9-10: Monitoring & SDK
1. No-show detection
2. Hallucination retry
3. Agent SDK

---

## ✅ SUCCESS CRITERIA

- [ ] All 17 tasks completed
- [ ] Production-ready (no stubs)
- [ ] Full test coverage (>80%)
- [ ] Documentation complete
- [ ] Backward compatible
- [ ] Performance benchmarks met
- [ ] Security review passed

---

**Last Updated**: February 6, 2026
