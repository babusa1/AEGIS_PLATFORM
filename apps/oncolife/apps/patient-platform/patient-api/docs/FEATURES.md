# OncoLife Patient API - Complete Feature Documentation

## Overview

The OncoLife Patient API is a FastAPI-based backend service that provides:
- **Rule-Based Symptom Checker**: 27 symptom modules with clinical triage logic
- **Patient Management**: Authentication, profile, diary entries
- **Treatment Tracking**: Chemotherapy dates, conversation summaries
- **Real-Time Chat**: WebSocket-based symptom checker conversations

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          API Layer                                   │
│                    apps/.../api/v1/endpoints/                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │  auth    │ │   chat   │ │  chemo   │ │  diary   │ │ summaries  │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                        Service Layer                                 │
│                       apps/.../services/                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │
│  │ auth_service │ │ chat_service │ │chemo_service │ │diary_service│ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └─────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                       Repository Layer                               │
│                    apps/.../db/repositories/                         │
│  ┌────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐ │
│  │ patient_repo   │ │conversation_repo│ │ chemo/diary/summary_repo│ │
│  └────────────────┘ └─────────────────┘ └─────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                        Database Layer                                │
│                    PostgreSQL (Patient DB)                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Symptom Checker Feature (COMPLETE)

The core feature - a rule-based symptom checker with 27 clinically-validated modules.

### File Locations

| File | Description |
|------|-------------|
| `routers/chat/symptom_checker/symptom_definitions.py` | **27 symptom module definitions** with screening questions, follow-up questions, and triage logic |
| `routers/chat/symptom_checker/symptom_engine.py` | **State machine engine** that manages conversation flow, processes responses, determines next questions |
| `routers/chat/symptom_checker/constants.py` | Shared constants, triage levels, message types |
| `routers/chat/symptom_checker/__init__.py` | Package exports |
| `routers/chat/symptom_checker_service.py` | Service wrapper for the symptom engine |
| `services/chat_service.py` | **Modular service** for chat operations |
| `api/v1/endpoints/chat.py` | **REST + WebSocket endpoints** |

### Symptom Modules (27 Total)

#### Emergency Symptoms (5 Modules)
| ID | Name | Triage Level |
|----|------|--------------|
| URG-101 | Trouble Breathing | call_911 |
| URG-102 | Chest Pain | call_911 |
| URG-103 | Bleeding/Bruising | call_911 / notify_care_team |
| URG-107 | Fainting/Syncope | call_911 |
| URG-108 | Altered Mental Status | call_911 |

#### Common Side Effects (5 Modules)
| ID | Name | Description |
|----|------|-------------|
| FEV-202 | Fever | Temperature tracking, associated symptoms, ADL assessment |
| DEH-201 | Dehydration | Urine color, thirst, vitals, cross-references |
| NAU-203 | Nausea | Duration, intake, medications, severity |
| VOM-204 | Vomiting | Episodes, dehydration assessment, ADL |
| DIA-205 | Diarrhea | Stool count, blood/mucus, abdominal pain |

#### Pain Modules (7 Modules)
| ID | Name | Risk Level |
|----|------|------------|
| PAI-213 | Pain Router | Routes to specific pain modules |
| URG-114 | Port/IV Site Pain | HIGH (Infection) |
| HEA-210 | Headache | HIGH (CNS) |
| ABD-211 | Abdominal Pain | GI Risk |
| LEG-208 | Leg/Calf Pain | HIGH (DVT) |
| JMP-212 | Joint/Muscle Pain | MSK |
| NEU-216 | Neuropathy | Chemo-induced |

#### Other Symptoms (10 Modules)
| ID | Name | Description |
|----|------|-------------|
| CON-210 | Constipation | Bowel movement tracking |
| FAT-206 | Fatigue/Weakness | ADL impact assessment |
| EYE-207 | Eye Complaints | Vision, discharge, pain |
| MSO-208 | Mouth Sores | Oral intake, remedies |
| APP-209 | No Appetite | Weight loss, meal intake |
| URI-211 | Urinary Problems | Output, burning, blood |
| SKI-212 | Skin Rash | Location, coverage, breathing |
| SWE-214 | Swelling | Location, onset, associated symptoms |
| COU-215 | Cough | Duration, mucus, O2 saturation |
| NEU-304 | Falls & Balance | Fall history, neuro signs |

### Triage Levels
- **call_911**: Emergency - requires immediate attention
- **notify_care_team**: Alert - care team notification needed
- **none**: Monitor - continue observation

### API Endpoints

```
GET  /api/v1/chat/session/today     - Get or create today's session
POST /api/v1/chat/session/new       - Force create new session
GET  /api/v1/chat/{uuid}/full       - Get full chat history
GET  /api/v1/chat/{uuid}/state      - Get chat state
POST /api/v1/chat/{uuid}/feeling    - Update overall feeling
DELETE /api/v1/chat/{uuid}          - Delete chat
WS   /api/v1/chat/ws/{uuid}         - WebSocket for real-time chat
```

---

## 2. Authentication Feature (COMPLETE)

AWS Cognito integration for secure authentication.

### File Locations

| File | Description |
|------|-------------|
| `services/auth_service.py` | Complete Cognito integration service |
| `api/v1/endpoints/auth.py` | Authentication endpoints |
| `routers/auth/dependencies.py` | JWT validation, current user extraction |
| `routers/auth/models.py` | Pydantic request/response models |

### Features
- User signup with Cognito
- Login with JWT token generation
- Password change flow (temporary → permanent)
- Account deletion (soft delete)
- Physician-patient association on signup

### API Endpoints

```
POST /api/v1/auth/signup                - Register new user
POST /api/v1/auth/login                 - Authenticate user
POST /api/v1/auth/complete-new-password - Complete password setup
POST /api/v1/auth/logout                - Logout
DELETE /api/v1/auth/delete-patient      - Delete account
```

---

## 3. Chemotherapy Tracking Feature (COMPLETE)

Track chemotherapy treatment dates.

### File Locations

| File | Description |
|------|-------------|
| `services/chemo_service.py` | Chemo business logic |
| `db/repositories/chemo_repository.py` | Database operations |
| `api/v1/endpoints/chemo.py` | REST endpoints |

### Features
- Log chemotherapy dates
- Get chemo history
- Filter by month
- Get upcoming treatments

### API Endpoints

```
POST /api/v1/chemo/log              - Log new chemo date
GET  /api/v1/chemo/history          - Get all chemo dates
GET  /api/v1/chemo/month/{y}/{m}    - Get by month
GET  /api/v1/chemo/upcoming         - Get upcoming dates
DELETE /api/v1/chemo/{date}         - Delete chemo date
```

---

## 4. Patient Diary Feature (COMPLETE)

Patient journal for daily health tracking.

### File Locations

| File | Description |
|------|-------------|
| `services/diary_service.py` | Diary business logic |
| `db/repositories/diary_repository.py` | Database operations |
| `api/v1/endpoints/diary.py` | REST endpoints |

### Features
- Create diary entries
- Mark entries for doctor review
- Filter by month
- Soft delete entries

### API Endpoints

```
GET  /api/v1/diary/                  - Get all entries
GET  /api/v1/diary/{year}/{month}    - Get by month
POST /api/v1/diary/                  - Create entry
PATCH /api/v1/diary/{uuid}           - Update entry
PATCH /api/v1/diary/{uuid}/delete    - Soft delete
GET  /api/v1/diary/for-doctor        - Entries for doctor
```

---

## 5. Conversation Summaries Feature (COMPLETE)

View and retrieve conversation summaries.

### File Locations

| File | Description |
|------|-------------|
| `services/summary_service.py` | Summary business logic |
| `db/repositories/summary_repository.py` | Database operations |
| `api/v1/endpoints/summaries.py` | REST endpoints |

### Features
- Get summaries by month
- Get detailed summary
- Count conversations

### API Endpoints

```
GET /api/v1/summaries/{year}/{month}      - Get by month
GET /api/v1/summaries/detail/{uuid}       - Get details
GET /api/v1/summaries/recent              - Get recent
GET /api/v1/summaries/count               - Count total
```

---

## 6. Patient Profile Feature (COMPLETE)

Patient profile and configuration management.

### File Locations

| File | Description |
|------|-------------|
| `services/profile_service.py` | Profile business logic |
| `db/repositories/profile_repository.py` | Database operations |
| `api/v1/endpoints/profile.py` | REST endpoints |

### Features
- Get complete profile (with doctor/clinic info)
- Update configuration
- Update consent status

### API Endpoints

```
GET   /api/v1/profile/           - Get complete profile
GET   /api/v1/profile/info       - Get patient info
PATCH /api/v1/profile/config     - Update configuration
PATCH /api/v1/profile/consent    - Update consent
```

---

## 7. Core Infrastructure (COMPLETE)

### File Locations

| File | Description |
|------|-------------|
| `core/config.py` | Centralized settings (Pydantic) |
| `core/logging.py` | Structured logging setup |
| `core/exceptions.py` | Custom exception classes |
| `core/middleware/` | Request logging, error handling, correlation IDs |
| `db/base.py` | SQLAlchemy base, timestamp mixin |
| `db/session.py` | Database session management |
| `db/repositories/base.py` | Generic CRUD repository |

---

## Database Models

### Patient Database Tables

| Table | Model File | Description |
|-------|------------|-------------|
| `patient_info` | `db/patient_models.py` | Patient profiles |
| `patient_configurations` | `db/patient_models.py` | Patient settings |
| `patient_diary_entries` | `db/patient_models.py` | Diary entries |
| `patient_chemo_dates` | `db/patient_models.py` | Chemo dates |
| `patient_physician_associations` | `db/patient_models.py` | Doctor links |
| `conversations` | `db/patient_models.py` | Chat sessions |
| `messages` | `db/patient_models.py` | Chat messages |

---

## Entry Points

| File | Description |
|------|-------------|
| `main.py` | FastAPI application entry point |
| `api/v1/router.py` | Main API v1 router |

### Running the API

```bash
# Development
uvicorn main:app --reload --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Environment Variables Required

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=oncolife
POSTGRES_PASSWORD=password
POSTGRES_PATIENT_DB=oncolife_patient
POSTGRES_DOCTOR_DB=oncolife_doctor

# AWS Cognito
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
COGNITO_USER_POOL_ID=us-west-2_xxxxx
COGNITO_CLIENT_ID=xxxxx
COGNITO_CLIENT_SECRET=xxxxx

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## Feature Status Summary

| Feature | Status | API Ready | WebSocket |
|---------|--------|-----------|-----------|
| **Patient Education (NEW)** | ✅ Complete | ✅ | - |
| **Patient Onboarding** | ✅ Complete | ✅ | - |
| Symptom Checker (27 modules) | ✅ Complete | ✅ | ✅ |
| Authentication (Cognito) | ✅ Complete | ✅ | - |
| Chemo Tracking | ✅ Complete | ✅ | - |
| Patient Diary | ✅ Complete | ✅ | - |
| Conversation Summaries | ✅ Complete | ✅ | - |
| Patient Profile | ✅ Complete | ✅ | - |
| Health Checks | ✅ Complete | ✅ | - |

---

## 8. Patient Onboarding Feature (COMPLETE)

Complete end-to-end patient onboarding from clinic referral to active user.

### File Locations

| File | Description |
|------|-------------|
| `services/ocr_service.py` | AWS Textract OCR integration |
| `services/notification_service.py` | AWS SES/SNS for email/SMS |
| `services/onboarding_service.py` | Main orchestration service |
| `db/models/referral.py` | Referral and onboarding models |
| `api/v1/endpoints/onboarding.py` | REST endpoints |

### Flow

```
Clinic Fax → OCR (Textract) → Parse → Create Account (Cognito) 
→ Send Welcome Email → Patient Logs In → Password Reset 
→ Acknowledgement → Terms/Privacy → Reminders → Active User
```

### AWS Services Used

| Service | Purpose |
|---------|---------|
| **Cognito** | Patient authentication & temp passwords |
| **Textract** | OCR for referral documents |
| **SES** | Welcome emails & reminders |
| **SNS** | SMS notifications |
| **S3** | Referral document storage |

### API Endpoints

```
POST /api/v1/onboarding/webhook/fax          - Receive fax webhook
GET  /api/v1/onboarding/status               - Get onboarding status
POST /api/v1/onboarding/complete/password    - Complete password step
POST /api/v1/onboarding/complete/acknowledgement - Complete acknowledgement
POST /api/v1/onboarding/complete/terms       - Complete terms/privacy
POST /api/v1/onboarding/complete/reminders   - Complete reminder setup
POST /api/v1/onboarding/referral/manual      - Create manual referral (admin)
```

### Data Extracted from Referrals

- **Patient**: Name, DOB, Email, Phone, MRN, Sex
- **Physician**: Name, Clinic, NPI
- **Diagnosis**: Cancer type, Staging, Diagnosis date
- **Treatment**: Chemo regimen, Start/End dates, Cycles
- **History**: Medical, Surgical, Medications, Allergies
- **Vitals**: Height, Weight, BMI, BP, Pulse, SpO2

See [ONBOARDING.md](./ONBOARDING.md) for complete documentation.

---

## 9. Patient Education Feature (NEW - COMPLETE)

Rule-based, non-AI education delivery system that provides clinician-approved content after every symptom session.

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **No AI/LLM** | All content is clinician-approved, copied verbatim |
| **Mandatory Disclaimer** | Cannot be removed, shown every time |
| **Care Team Handout** | Always included in every response |
| **Full Audit Trail** | Every delivery logged for HIPAA |
| **Immutable Summaries** | Patient summaries cannot be modified |

### File Locations

| File | Description |
|------|-------------|
| `db/models/education.py` | 11 database models for education |
| `services/education_service.py` | Education delivery logic |
| `api/v1/endpoints/education.py` | REST endpoints |
| `scripts/seed_education.py` | Database seeding script |

### Database Schema

```sql
-- Core Tables
symptoms                 -- Symptom catalog
education_documents      -- Clinician-approved content
disclaimers              -- Mandatory disclaimer
care_team_handouts       -- Always-included handout

-- Session Tracking
symptom_sessions         -- Session management
rule_evaluations         -- Audit of which rules fired

-- Patient Data
patient_summaries        -- Immutable summaries
medications_tried        -- Medication effectiveness

-- Audit Tables
education_delivery_log   -- What patient saw
education_access_log     -- Tab access analytics
```

### API Endpoints

```
POST /api/v1/education/deliver              - Deliver post-session education
POST /api/v1/education/summary              - Generate patient summary
POST /api/v1/education/summary/{id}/note    - Add patient note (max 300 chars)
GET  /api/v1/education/summary/{session}    - Get summary for session
GET  /api/v1/education/tab                  - Education library
GET  /api/v1/education/search?q=nausea      - Simple ILIKE search
GET  /api/v1/education/document/{id}        - Get specific document
GET  /api/v1/education/symptoms             - Get symptom catalog
POST /api/v1/education/session              - Create symptom session
GET  /api/v1/education/disclaimer           - Get mandatory disclaimer
```

### Education Delivery Flow

```
Symptom Session Completes
         │
         ▼
┌─────────────────────────┐
│  Fetch Education Docs   │
│  for each symptom       │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Add Care Team Handout  │
│  (always included)      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Append Mandatory       │
│  Disclaimer             │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Log Delivery           │
│  (audit trail)          │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Generate Patient       │
│  Summary (template)     │
└───────────┬─────────────┘
            │
            ▼
      Return to UI
```

### Content Rules

| Rule | Requirement |
|------|-------------|
| Inline Text | 4-6 bullets max, Grade 6-8 reading level |
| No Generation | Content copied verbatim from approved docs |
| source_document_id | Required on all documents (audit) |
| Pre-signed URLs | 30 min expiry, HTTPS only |
| status = 'active' | Only active documents rendered |

### Summary Templates (No AI)

```python
SUMMARY_TEMPLATES = {
    "default": (
        "You reported {symptom_list} with {severity_list} severity. "
        "{medication_sentence}"
        "{escalation_sentence}"
    ),
    "single_symptom": (
        "You reported {symptom_name} ({severity}). "
        "{medication_sentence}"
        "{escalation_sentence}"
    ),
}
```

**Example Output:**
```
You reported nausea (moderate) and fatigue (mild).
You tried ondansetron with partial relief.
No urgent symptoms were detected.
```

### AWS Integration

| Service | Purpose |
|---------|---------|
| **S3** | Education PDFs (KMS encrypted) |
| **Pre-signed URLs** | Secure document access (30 min) |
| **CloudTrail** | Access audit logging |

### S3 Bucket Structure

```
s3://oncolife-education/
├── symptoms/
│   ├── fever/
│   │   ├── fever_v1.pdf
│   │   └── fever_v1.txt
│   ├── nausea/
│   │   ├── nausea_v1.pdf
│   │   └── nausea_v1.txt
│   └── ...
└── care-team/
    ├── care_team_handout_v1.pdf
    └── care_team_handout_v1.txt
```

### Anti-Hallucination Safeguards

| Allowed | Forbidden |
|---------|-----------|
| Copy-paste from approved docs | Paraphrasing |
| Light truncation | Sentence recombination |
| | Multi-document merging |
| | Any AI/LLM generation |

**Engineering Control:**
```python
# Every education block must reference:
education_documents.source_document_id
# If missing → block rendering FAILS
```

See [EDUCATION.md](./EDUCATION.md) for complete documentation.

---

*Last Updated: January 2026*

