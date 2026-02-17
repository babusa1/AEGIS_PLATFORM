# Oncolife & CKM Bridge Apps Architecture Discussion

## Current State

### Oncolife Symptom Checker
- **Status**: ✅ Integrated as bridge app
- **Location**: `src/aegis/bridge_apps/oncolife/`
- **Current Integration**:
  - Symptom checker engine (27 symptom modules, rule-based triage)
  - API endpoints (`/bridge/oncolife/symptom-checker/*`)
  - Basic integration with `OncolifeAgent` after symptom session completes
  - **Gap**: Symptom checker doesn't use patient data from VeritOS Data Moat during the conversation

### Chaperone CKM
- **Status**: ✅ Agent implemented
- **Location**: `src/aegis/agents/chaperone_ckm.py`
- **Current Integration**:
  - Uses Data Moat to query patient CKD data
  - Calculates KFRE, eGFR trends, care gaps
  - **Gap**: No patient-facing bridge app UI yet

---

## 🎯 Vision: Data-Driven Bridge Apps

### Core Principle
**"Use the data we have to build agents"** → **"Use the data we have to build intelligent bridge apps"**

Bridge apps should be **data-aware** and **context-aware**, not just standalone symptom checkers.

---

## 💡 Proposed Architecture Enhancements

### 1. **Oncolife: Data-Enriched Symptom Checker**

#### Current Flow (Basic):
```
Patient → Symptom Checker → Triage Level → OncolifeAgent (after completion)
```

#### Proposed Flow (Data-Driven):
```
Patient → Symptom Checker (enriched with patient data) → Real-time Agent Integration → Personalized Recommendations
```

#### Enhancements:

**A. Pre-Session Data Loading**
- Load patient's oncology history from Data Moat:
  - Active chemo regimens
  - Recent lab results (CBC, CMP, tumor markers)
  - Previous symptom reports
  - Genomic variants (if relevant)
  - Current medications

**B. Context-Aware Questioning**
- **Example**: If patient is on FOLFOX, automatically ask about neuropathy, diarrhea, nausea
- **Example**: If recent labs show neutropenia, prioritize fever/infection symptoms
- **Example**: If genomic variant (e.g., BRCA), tailor questions to hereditary cancer risks

**C. Real-Time Agent Integration**
- During symptom session, query `OncolifeAgent` for:
  - **Risk stratification**: "Given this patient's chemo regimen and current symptoms, what's the risk?"
  - **Medication context**: "Is this symptom expected for their current treatment?"
  - **Historical patterns**: "Has this patient reported similar symptoms before?"

**D. Personalized Recommendations**
- After triage, use `OncolifeAgent` to generate:
  - Medication-specific guidance (e.g., "You're on Keytruda, this rash is common")
  - Care team routing (e.g., "Your oncologist Dr. Smith should be notified")
  - Follow-up scheduling (e.g., "Schedule urgent visit within 24h")

#### Implementation Plan:

```python
# Enhanced SymptomCheckerService
class SymptomCheckerService:
    def __init__(self, patient_id: str, data_moat_tools: DataMoatTools):
        self.patient_id = patient_id
        self.data_moat = data_moat_tools
        self.oncolife_agent = OncolifeAgent(tenant_id, data_moat_tools)
        
        # Load patient context
        self.patient_context = await self._load_patient_context()
    
    async def _load_patient_context(self):
        """Load patient's oncology data from Data Moat."""
        return {
            "chemo_regimens": await self.data_moat.list_entities("medication", filters={"patient_id": self.patient_id, "category": "chemotherapy"}),
            "recent_labs": await self.data_moat.list_entities("lab_result", filters={"patient_id": self.patient_id}, limit=10),
            "previous_symptoms": await self.data_moat.list_entities("observation", filters={"patient_id": self.patient_id, "category": "symptom"}),
            "genomic_variants": await self.data_moat.list_entities("genomic_variant", filters={"patient_id": self.patient_id}),
        }
    
    def start_session(self):
        """Start session with patient context."""
        # Get initial questions based on patient's chemo regimen
        prioritized_symptoms = self._prioritize_symptoms_by_regimen()
        
        # Start conversation with context-aware questions
        return self.engine.start_conversation(context=self.patient_context)
    
    async def process_user_response(self, user_response, session_state):
        """Process response with real-time agent integration."""
        # Standard symptom checker processing
        response = self.engine.process_response(user_response)
        
        # Real-time agent consultation
        if response.get("current_symptom"):
            agent_insight = await self.oncolife_agent.consult_symptom_context(
                patient_id=self.patient_id,
                symptom=response["current_symptom"],
                patient_context=self.patient_context
            )
            response["agent_insight"] = agent_insight
        
        return response
```

---

### 2. **Chaperone CKM: Patient-Facing Bridge App**

#### What Can We Build?

**A. Symptom & Vital Logging App**
- **BP Logging**: Patient logs BP → Agent calculates BP control metrics
- **Weight Tracking**: Patient logs weight → Agent detects fluid retention (CKD progression)
- **Symptom Diary**: Fatigue, swelling, shortness of breath → Agent correlates with eGFR trends

**B. Care Gap Tracker**
- **Patient View**: "You're due for ACR test" (based on Data Moat care gap analysis)
- **Medication Adherence**: "You missed 2 doses of Lisinopril this week"
- **Lab Reminders**: "Your eGFR check is due in 2 weeks"

**C. Educational Content**
- **Personalized**: "Your eGFR is 45, here's what that means for you"
- **Diet Coaching**: Based on lab results (potassium, phosphorus)
- **Medication Education**: "Why you're taking SGLT2 inhibitor"

**D. Risk Communication**
- **KFRE Visualization**: "Your 5-year kidney failure risk is 15%"
- **Trend Alerts**: "Your eGFR dropped 10% in 3 months - contact your nephrologist"

#### Implementation Plan:

```python
# New ChaperoneCKM Bridge App
class ChaperoneCKMService:
    def __init__(self, patient_id: str, data_moat_tools: DataMoatTools):
        self.patient_id = patient_id
        self.data_moat = data_moat_tools
        self.ckm_agent = ChaperoneCKMAgent(tenant_id, data_moat_tools)
    
    async def get_patient_dashboard(self):
        """Get personalized CKD dashboard."""
        ckd_status = await self.ckm_agent.analyze_patient_ckd_status(self.patient_id)
        
        return {
            "egfr_trend": ckd_status["egfr_trend"],
            "kfre_risk": ckd_status["kfre_result"],
            "care_gaps": ckd_status["care_gaps"],
            "medication_adherence": await self._get_adherence_metrics(),
            "vital_trends": await self._get_vital_trends(),
            "personalized_recommendations": ckd_status["recommendations"],
        }
    
    async def log_vital(self, vital_type: str, value: float, timestamp: datetime):
        """Patient logs a vital sign."""
        # Store in Data Moat
        await self.data_moat.create_entity("vital", {
            "patient_id": self.patient_id,
            "type": vital_type,
            "value": value,
            "timestamp": timestamp,
        })
        
        # Real-time agent analysis
        alert = await self.ckm_agent.analyze_vital_alert(
            patient_id=self.patient_id,
            vital_type=vital_type,
            value=value
        )
        
        return {"logged": True, "alert": alert}
```

---

## 🔄 Integration Points

### Data Flow:

```
┌─────────────────┐
│   Data Moat     │
│  (FHIR Graph)   │
└────────┬────────┘
         │
         │ Patient Data
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────────┐
│Oncolife │ │ Chaperone CKM │
│  Agent  │ │     Agent     │
└────┬────┘ └──────┬────────┘
     │             │
     │             │
     ▼             ▼
┌─────────────┐ ┌──────────────────┐
│ Oncolife    │ │ Chaperone CKM    │
│ Bridge App  │ │ Bridge App       │
│ (Symptom    │ │ (Vitals, Care    │
│  Checker)   │ │  Gaps, Dashboard) │
└─────────────┘ └──────────────────┘
```

---

## 📋 What Should We Build First?

### Option 1: Enhance Oncolife Symptom Checker (Recommended)
**Priority**: High  
**Impact**: Immediate value - makes symptom checker intelligent  
**Effort**: Medium

**Features**:
1. ✅ Load patient context at session start
2. ✅ Context-aware symptom prioritization
3. ✅ Real-time agent consultation during conversation
4. ✅ Personalized recommendations post-triage

### Option 2: Build Chaperone CKM Bridge App
**Priority**: High  
**Impact**: New patient-facing app  
**Effort**: High

**Features**:
1. ✅ Patient dashboard (eGFR trends, KFRE, care gaps)
2. ✅ Vital logging (BP, weight)
3. ✅ Care gap reminders
4. ✅ Medication adherence tracking

### Option 3: Both (Phased)
**Priority**: Highest  
**Impact**: Complete vertical intelligence  
**Effort**: High

**Phase 1**: Enhance Oncolife (2-3 weeks)  
**Phase 2**: Build CKM Bridge App (3-4 weeks)

---

## 🤔 Discussion Questions

1. **Oncolife Enhancement**: Should we prioritize making the symptom checker data-aware, or is the current integration sufficient?

2. **CKM Bridge App**: What's the MVP? Dashboard? Vital logging? Care gaps?

3. **Data Integration Depth**: How much patient data should we surface in the UI? Full medical history or curated views?

4. **Real-Time vs Batch**: Should agent consultations happen in real-time during symptom sessions, or async after completion?

5. **Mobile Apps**: Should these bridge apps be web-first or mobile-first (React Native)?

---

## 🎯 Recommendation

**Start with Option 1 (Enhance Oncolife)** because:
- ✅ Symptom checker already integrated
- ✅ High impact with medium effort
- ✅ Demonstrates "data-driven bridge apps" vision
- ✅ Can reuse patterns for CKM later

**Then build Option 2 (CKM Bridge App)** because:
- ✅ Completes the vertical intelligence story
- ✅ Different use case (chronic disease management vs acute symptom triage)
- ✅ Reuses Data Moat + Agent patterns

---

## 📝 Next Steps

1. **Fix CI issue** (verify-demo)
2. **Discuss architecture** (this document)
3. **Decide on priority** (Oncolife enhancement vs CKM bridge app)
4. **Implement chosen path**
5. **Document integration patterns** for future bridge apps
