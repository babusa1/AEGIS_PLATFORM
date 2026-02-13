# AEGIS Platform: Low Level Design Document

**Version**: 2.0  
**Last Updated**: February 6, 2026  
**Status**: Production-Ready (100% Complete)

---

## 1. MODULE STRUCTURE

### Core Modules

```
aegis/
├── agents/              # Agent framework
│   ├── base.py         # BaseAgent, AgentState
│   ├── personas/       # Librarian, Guardian, Scribe, Scout
│   ├── unified_view.py # UnifiedViewAgent
│   ├── action.py       # ActionAgent
│   └── tools.py        # AgentTools
├── cowork/             # Cowork framework
│   ├── engine.py       # CoworkEngine (OODA loop)
│   └── models.py       # CoworkState, CoworkSession
├── orchestrator/       # Workflow orchestration
│   ├── engine.py       # WorkflowEngine
│   ├── tools.py        # ToolRegistry
│   └── core/           # Memory, checkpoints
├── ingestion/          # Data ingestion
│   ├── unified_pipeline.py
│   ├── normalization.py # SNE
│   └── streaming.py    # Kafka integration
├── graph/              # Knowledge graph
│   ├── client.py       # Graph client (Neptune/JanusGraph)
│   └── query.py        # Graph queries
├── rag/                # RAG pipeline
│   ├── retriever.py    # RAGRetriever (GraphRAG)
│   ├── summarization.py # RecursiveSummarizer
│   └── chunking.py     # Smart chunking
├── llm/                # LLM gateway
│   ├── gateway.py      # Multi-provider LLM
│   └── retry.py        # HallucinationRetryHandler
├── guidelines/         # Clinical guidelines
│   ├── nccn.py         # NCCN guidelines
│   ├── kdigo.py        # KDIGO guidelines
│   └── cross_check.py  # GuidelineCrossChecker
├── ehr/                # EHR integration
│   ├── writeback.py    # EHRWriteBackService
│   └── request_group.py # RequestGroupBuilder
└── api/                # API layer
    ├── main.py         # FastAPI app
    ├── routes/         # API routes
    └── websocket.py    # WebSocket handler
```

---

## 2. API SPECIFICATIONS

### REST API Endpoints

#### Cowork Sessions

```
POST   /api/v1/cowork/sessions
GET    /api/v1/cowork/sessions
GET    /api/v1/cowork/sessions/{session_id}
PUT    /api/v1/cowork/sessions/{session_id}
DELETE /api/v1/cowork/sessions/{session_id}
```

#### Agents

```
POST   /api/v1/agents/{agent_type}/execute
GET    /api/v1/agents/{agent_type}/status
POST   /api/v1/agents/{agent_type}/tools/register
```

#### Patients

```
GET    /api/v1/patients/{patient_id}
GET    /api/v1/patients/{patient_id}/timeline
GET    /api/v1/patients/{patient_id}/360
```

#### Workflows

```
POST   /api/v1/workflows/execute
GET    /api/v1/workflows/{workflow_id}/status
GET    /api/v1/workflows/{workflow_id}/checkpoint
POST   /api/v1/workflows/{workflow_id}/replay
```

### WebSocket API

```
WS     /api/v1/cowork/sessions/{session_id}/ws
```

**Message Types**:
- `message`: Chat message
- `artifact_update`: Artifact modification
- `state_sync`: State synchronization
- `typing`: Typing indicator
- `presence`: User presence

---

## 3. DATA MODELS

### Core Models

#### CoworkSession

```python
class CoworkSession(BaseModel):
    id: str
    patient_id: str
    status: SessionStatus  # active, pending, completed
    participants: List[CoworkParticipant]
    artifacts: List[CoworkArtifact]
    state: CoworkState
    created_at: datetime
    updated_at: datetime
```

#### CoworkState

```python
class CoworkState(BaseModel):
    patient_id: str
    clinical_context: Dict[str, Any]
    active_artifacts: Dict[str, CoworkArtifact]
    safety_audit: List[str]
    evidence_links: List[str]
    messages: List[Dict[str, Any]]
    status: str  # scanning, verifying, drafting, approval_required
```

#### AgentState

```python
class AgentState(TypedDict):
    messages: Annotated[List[Dict], operator.add]
    patient_id: str
    context: Dict[str, Any]
    tools_used: List[str]
    reasoning_path: List[str]
```

### FHIR Models

#### Patient (FHIR R4)

```python
class Patient(BaseVertex):
    id: str
    name: List[HumanName]
    birth_date: date
    gender: str
    identifiers: List[Identifier]
    addresses: List[Address]
```

#### Observation (FHIR R4)

```python
class Observation(BaseVertex):
    id: str
    patient_id: str
    code: CodeableConcept  # LOINC code
    value: Union[Quantity, CodeableConcept, str]
    effective_date_time: datetime
    status: str
```

### Graph Schema

#### Nodes

- `Patient`, `Provider`, `Organization`, `Location`
- `Encounter`, `Condition`, `Procedure`, `Observation`
- `Medication`, `MedicationRequest`
- `Claim`, `Denial`, `Authorization`
- `GeneticVariant`, `GenomicReport`
- `WorkflowDefinition`, `WorkflowExecution`

#### Edges

- `HAS_ENCOUNTER`: Patient → Encounter
- `HAS_CONDITION`: Patient → Condition
- `HAS_MEDICATION`: Patient → MedicationRequest
- `TREATED_BY`: Encounter → Provider
- `INDICATED_FOR`: Medication → Condition
- `RESULTED_FROM`: Observation → Procedure
- `CONTRAINDICATED_WITH`: Medication → Medication

---

## 4. AGENT ARCHITECTURE

### BaseAgent

```python
class BaseAgent:
    def __init__(self, llm_client, tools: List[Tool]):
        self.llm_client = llm_client
        self.tools = tools
        self.graph = GraphClient()
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow"""
        pass
    
    def execute(self, state: AgentState) -> AgentState:
        """Execute agent workflow"""
        pass
```

### LibrarianAgent

**Purpose**: Contextual retrieval (GraphRAG, temporal delta, recursive summarization)

**Methods**:
- `traverse_graph_path(patient_id, query)`: Graph traversal
- `calculate_temporal_delta(patient_id, metric, time_window)`: Temporal analysis
- `create_recursive_summary(patient_id, depth)`: Hierarchical summarization
- `get_patient_context(patient_id)`: Unified patient view

**Tools**:
- `get_patient_data`: Query patient from Data Moat
- `traverse_graph`: Graph path-finding
- `search_vector_db`: Vector search
- `get_timeline`: Patient timeline

### GuardianAgent

**Purpose**: Governance & safety (guidelines, conflicts, safety blocks)

**Methods**:
- `check_guidelines(action, specialty)`: Guideline cross-check
- `check_conflicts(medications, labs)`: Conflict detection
- `block_unsafe_action(action, rationale)`: Safety block
- `add_audit_attribution(recommendation, guideline_id)`: Audit trail

**Tools**:
- `check_nccn_guidelines`: NCCN oncology guidelines
- `check_kdigo_guidelines`: KDIGO nephrology guidelines
- `check_drug_interactions`: Drug-drug interactions
- `check_lab_contraindications`: Drug-lab interactions

### ScribeAgent

**Purpose**: Action execution (SOAP notes, referrals, orders, translation)

**Methods**:
- `generate_soap_note(patient_id, encounter_id)`: SOAP note generation
- `generate_referral_letter(patient_id, specialty)`: Referral letter
- `generate_prior_auth(patient_id, procedure)`: Prior authorization
- `draft_orders(patient_id, order_set)`: FHIR RequestGroup
- `translate_patient_instructions(text, language, literacy_level)`: Translation

**Tools**:
- `generate_document`: Document generation
- `build_request_group`: FHIR RequestGroup builder
- `translate_text`: Multilingual translation

### ScoutAgent

**Purpose**: Continuous monitoring (events, trends, triage)

**Methods**:
- `listen_for_events(topic, callback)`: Kafka event listening
- `predict_trend(patient_id, metric)`: Trend prediction
- `detect_no_shows(patient_id)`: No-show detection
- `detect_medication_gaps(patient_id)`: Medication adherence

**Tools**:
- `consume_kafka_events`: Kafka consumer
- `analyze_trends`: Trend analysis
- `match_appointments`: Appointment matching

---

## 5. WORKFLOW ENGINE DESIGN

### WorkflowEngine

```python
class WorkflowEngine:
    def __init__(self, graph_client, llm_client):
        self.graph_client = graph_client
        self.llm_client = llm_client
        self.memory = MemoryStore()
    
    def build_workflow(self, definition: WorkflowDefinition) -> StateGraph:
        """Build LangGraph from workflow definition"""
        builder = StateGraph(AgentState)
        
        for node in definition.nodes:
            builder.add_node(node.name, node.function)
        
        for edge in definition.edges:
            builder.add_edge(edge.source, edge.target)
        
        return builder.compile()
    
    def execute(self, workflow_id: str, initial_state: Dict) -> WorkflowExecution:
        """Execute workflow with checkpointing"""
        workflow = self.load_workflow(workflow_id)
        checkpoint = self.memory.get_checkpoint(workflow_id)
        
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            state=initial_state,
            checkpoint=checkpoint
        )
        
        for step in workflow.stream(initial_state, checkpoint=checkpoint):
            execution.add_step(step)
            self.memory.save_checkpoint(workflow_id, step)
        
        return execution
```

### WorkflowDefinition

```python
class WorkflowDefinition(BaseModel):
    id: str
    name: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    triggers: List[Trigger]
    retry_policy: RetryPolicy
```

### Checkpointing

- **State Persistence**: Redis/DynamoDB
- **Checkpoint Frequency**: After each node execution
- **Replay**: Load checkpoint, resume from last step
- **Crash Recovery**: Automatic recovery from last checkpoint

---

## 6. RAG PIPELINE DESIGN

### RAGRetriever

```python
class RAGRetriever:
    def __init__(self, graph_client, vector_client):
        self.graph = graph_client
        self.vector = vector_client
    
    def retrieve(self, query: str, patient_id: str) -> List[Chunk]:
        """Hybrid retrieval: Graph + Vector + Keyword"""
        # 1. Graph traversal
        graph_results = self._traverse_graph(patient_id, query)
        
        # 2. Vector search
        vector_results = self.vector.search(query, patient_id)
        
        # 3. Keyword search
        keyword_results = self._keyword_search(query, patient_id)
        
        # 4. Merge and rank
        return self._merge_and_rank(graph_results, vector_results, keyword_results)
    
    def _traverse_graph(self, patient_id: str, query: str) -> List[Chunk]:
        """Graph path-finding"""
        paths = self.graph.traverse(
            start=patient_id,
            pattern=self._extract_pattern(query),
            max_depth=3
        )
        return [self._path_to_chunk(path) for path in paths]
```

### RecursiveSummarizer

```python
class RecursiveSummarizer:
    def summarize(self, patient_id: str, depth: int = 3) -> Dict[str, str]:
        """Hierarchical summarization"""
        summaries = {}
        
        # Level 1: Daily summaries
        daily = self._summarize_days(patient_id)
        summaries['daily'] = daily
        
        # Level 2: Weekly summaries
        weekly = self._summarize_weeks(daily)
        summaries['weekly'] = weekly
        
        # Level 3: Monthly summaries
        monthly = self._summarize_months(weekly)
        summaries['monthly'] = monthly
        
        return summaries
```

---

## 7. GUIDELINE SYSTEM DESIGN

### BaseGuideline

```python
class BaseGuideline:
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.sections: List[GuidelineSection] = []
    
    def add_section(self, section: GuidelineSection):
        self.sections.append(section)
    
    def search(self, query: str) -> List[GuidelineSection]:
        """Search guideline sections"""
        return [s for s in self.sections if query.lower() in s.content.lower()]
```

### NCCNGuideline

```python
class NCCNGuideline(BaseGuideline):
    def check_dose_hold_criteria(self, lab_values: Dict[str, float]) -> Dict[str, Any]:
        """Check NCCN dose hold criteria"""
        violations = []
        
        # Anemia: Hgb < 8.0 → Hold
        if lab_values.get('hemoglobin', 0) < 8.0:
            violations.append({
                'type': 'anemia',
                'severity': 'high',
                'action': 'hold_dose',
                'citation': 'NCCN Anemia Management'
            })
        
        # Neutropenia: ANC < 500 → Hold
        if lab_values.get('anc', 0) < 500:
            violations.append({
                'type': 'neutropenia',
                'severity': 'high',
                'action': 'hold_dose',
                'citation': 'NCCN Neutropenia Management'
            })
        
        return {'violations': violations, 'recommendations': self._get_recommendations(violations)}
```

### GuidelineCrossChecker

```python
class GuidelineCrossChecker:
    def check_against_guidelines(self, action: Dict, specialty: str) -> Dict[str, Any]:
        """Cross-check agent action against guidelines"""
        if specialty == 'oncology':
            return self._check_nccn(action)
        elif specialty == 'nephrology':
            return self._check_kdigo(action)
        else:
            return {'status': 'no_guidelines', 'violations': []}
```

---

## 8. DATABASE SCHEMAS

### PostgreSQL Schema

#### patients

```sql
CREATE TABLE patients (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    mrn VARCHAR(255),
    name JSONB,
    birth_date DATE,
    gender VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### workflow_executions

```sql
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    status VARCHAR(50),
    state JSONB,
    checkpoint JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### Graph Schema (Gremlin)

```groovy
// Vertex Labels
g.addV('Patient').property('id', 'patient-123').property('name', 'John Doe')
g.addV('Condition').property('id', 'condition-456').property('code', 'E11.9')
g.addV('Medication').property('id', 'med-789').property('name', 'Metformin')

// Edges
g.V('patient-123').addE('HAS_CONDITION').to(g.V('condition-456'))
g.V('patient-123').addE('HAS_MEDICATION').to(g.V('med-789'))
```

---

## 9. ERROR HANDLING

### Error Types

```python
class AEGISError(Exception):
    """Base exception"""
    pass

class AgentExecutionError(AEGISError):
    """Agent execution failed"""
    pass

class DataMoatError(AEGISError):
    """Data Moat query failed"""
    pass

class LLMError(AEGISError):
    """LLM call failed"""
    pass
```

### Retry Logic

```python
@retry(max_attempts=3, backoff=exponential_backoff)
def call_llm(prompt: str) -> str:
    try:
        return llm_client.generate(prompt)
    except LLMError as e:
        logger.error(f"LLM call failed: {e}")
        raise
```

---

## 10. TESTING STRATEGY

### Unit Tests

- Agent methods
- Data model validation
- API endpoint handlers

### Integration Tests

- End-to-end workflows
- Database operations
- External API calls (mocked)

### E2E Tests

- Complete Cowork sessions
- Agent orchestration
- EHR write-back

---

**Last Updated**: February 6, 2026  
**Document Owner**: Engineering Team
