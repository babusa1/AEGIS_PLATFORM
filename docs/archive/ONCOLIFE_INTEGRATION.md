# Oncolife Symptom Checker Integration

**Date**: February 6, 2026  
**Status**: ✅ Integrated

## Overview

The Oncolife symptom checker has been integrated into AEGIS as a bridge app, providing oncology-specific symptom triage capabilities integrated with the AEGIS Data Moat and Agentic Framework.

## What Was Integrated

### 1. Bridge App Structure
- **Location**: `src/aegis/bridge_apps/oncolife/`
- **Components**:
  - `symptom_checker.py`: Service wrapper for the symptom checker engine
  - `api.py`: REST API endpoints for symptom checker
  - `__init__.py`: Package exports

### 2. Symptom Checker Engine
- **Source**: Oncolife Monolith repo (`oncolife_temp/apps/patient-platform/patient-api/src/routers/chat/symptom_checker/`)
- **Features**:
  - 27 symptom modules (emergency, digestive, pain/nerve, systemic, skin)
  - Rule-based triage engine
  - Emergency safety checks (5 emergency symptoms)
  - CTCAE-graded toxicity monitoring
  - Multi-phase conversation flow (disclaimer → emergency check → symptom selection → screening → summary)

### 3. API Endpoints
- **Base Path**: `/v1/bridge/oncolife/`
- **Endpoints**:
  - `POST /symptom-checker/start`: Start a new symptom checker session
  - `POST /symptom-checker/respond`: Process user responses
  - `GET /symptom-checker/summary/{session_id}`: Get session summary
  - `GET /symptom-checker/symptoms`: Get available symptoms list

### 4. Integration Points
- **OncolifeAgent**: Symptom checker results trigger agent recommendations
- **Data Moat**: Patient context from Data Moat enriches symptom sessions
- **Patient Timeline**: Symptom history tracked in patient timeline

## Architecture

```
┌─────────────────────────────────────────┐
│   Patient/Frontend                      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   AEGIS API                             │
│   /v1/bridge/oncolife/*                 │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   SymptomCheckerService                  │
│   (bridge_apps/oncolife/)               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   Oncolife Symptom Checker Engine       │
│   (from oncolife_temp repo)            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   OncolifeAgent                         │
│   (Care recommendations)                │
└─────────────────────────────────────────┘
```

## Usage

### Starting a Session
```python
POST /v1/bridge/oncolife/symptom-checker/start
{
  "patient_id": "patient-123"
}

Response:
{
  "message": "⚠️ IMPORTANT MEDICAL DISCLAIMER...",
  "message_type": "disclaimer",
  "options": [...],
  "session_state": {...},
  "patient_id": "patient-123"
}
```

### Processing Responses
```python
POST /v1/bridge/oncolife/symptom-checker/respond
{
  "user_response": "accept",
  "session_state": {...}
}

Response:
{
  "message": "🚨 Urgent Safety Check...",
  "message_type": "emergency_check",
  "options": [...],
  "session_state": {...}
}
```

## Integration Notes

### Oncolife Repo Dependency
The symptom checker engine is imported from the Oncolife Monolith repo located at:
- `oncolife_temp/apps/patient-platform/patient-api/src/routers/chat/symptom_checker/`

If the Oncolife repo is not available, the bridge app falls back to a mock implementation with appropriate warnings.

### Future Enhancements
1. **Mobile UI**: React Native app for symptom checker (P2)
2. **Session Persistence**: Store sessions in Data Moat
3. **Analytics**: Track symptom patterns across patients
4. **ML Integration**: Use symptom data for predictive models

## Files Created/Modified

### New Files
- `src/aegis/bridge_apps/__init__.py`
- `src/aegis/bridge_apps/oncolife/__init__.py`
- `src/aegis/bridge_apps/oncolife/symptom_checker.py`
- `src/aegis/bridge_apps/oncolife/api.py`
- `docs/ONCOLIFE_INTEGRATION.md` (this file)

### Modified Files
- `src/aegis/api/main.py`: Added Oncolife router
- `docs/MASTER_PLAN.md`: Updated Bridge Apps status

## CI/CD Notes

The AEGIS CI workflow (`aegis/.github/workflows/ci.yml`) should handle the bridge app integration. The Oncolife symptom checker engine is imported dynamically, so if the Oncolife repo is not present, the bridge app gracefully degrades to mock mode.

## Testing

To test the integration:
1. Ensure the Oncolife repo is available at `oncolife_temp/`
2. Start the AEGIS API: `python -m uvicorn aegis.api.main:app`
3. Test endpoints: `curl http://localhost:8000/v1/bridge/oncolife/symptom-checker/symptoms`

## References

- Oncolife Monolith Repo: `https://github.com/nbsaKanasu/Oncolife_Monolith`
- AEGIS OncolifeAgent: `src/aegis/agents/oncolife.py`
- MASTER_PLAN.md: Bridge Apps section
