# Patient Diary & Doctor Dashboard Module

## Overview

This module implements enhanced patient diary functionality and a comprehensive doctor dashboard for clinical monitoring.

---

## Features Implemented

### 1. Patient Diary Enhancements

#### Daily Summary Auto-Population
- Symptom checker sessions automatically create diary entries
- Entries include:
  - Symptoms reported and severity
  - Triage outcome
  - Auto-generated summary
- Marked for doctor if escalation occurred

#### Patient Questions ("Questions to Ask Doctor")
- Patients can create questions they want to ask their doctor
- **Private by default** - patients must explicitly share
- Share toggle: `POST /api/v1/questions/{id}/share?share=true`
- Categories: `symptom`, `medication`, `treatment`, `other`
- Can mark questions as answered

### 2. Doctor Dashboard Module

#### Landing View (Patient Ranking)
- Answers: "Which patients need attention right now?"
- Patients ranked by:
  1. Has urgent escalation (highest priority)
  2. Maximum symptom severity (last 7 days)
  3. Most recent activity

#### Patient Detail View
- **Symptom Timeline**: Multi-line time series chart
  - Each symptom = one colored line
  - Severity: mild(1) → moderate(2) → severe(3) → urgent(4)
- **Treatment Overlay**: Chemo dates as vertical markers
- **Shared Questions**: Only questions patient chose to share

#### Weekly Physician Reports
- Auto-generated weekly summaries
- Includes:
  - Patient demographics
  - Weekly symptom trends
  - Escalation events
  - Shared questions

#### Audit Logging (HIPAA)
- Tracks all access to patient data
- Logged actions:
  - Dashboard views
  - Patient record access
  - Report downloads
- No PHI in logs

---

## API Endpoints

### Patient API (`/api/v1/questions/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/questions` | List patient's questions |
| POST | `/questions` | Create a new question |
| PATCH | `/questions/{id}` | Update question |
| DELETE | `/questions/{id}` | Soft delete question |
| POST | `/questions/{id}/share` | Toggle share with doctor |

**Example: Create Question**
```json
POST /api/v1/questions
{
  "question_text": "Should I take my medication with food?",
  "share_with_physician": true,
  "category": "medication"
}
```

### Doctor API (`/api/v1/dashboard/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard` | Landing view with ranked patients |
| GET | `/dashboard/patient/{uuid}` | Patient symptom timeline |
| GET | `/dashboard/patient/{uuid}/questions` | Shared questions |
| GET | `/dashboard/reports/weekly` | Weekly report data |

**Example: Dashboard Landing**
```json
GET /api/v1/dashboard?days=7&limit=50

Response:
{
  "patients": [
    {
      "patient_uuid": "...",
      "first_name": "John",
      "last_name": "Doe",
      "last_checkin": "2026-01-03T14:30:00Z",
      "max_severity": "severe",
      "has_escalation": true,
      "severity_badge": "orange"
    }
  ],
  "total_patients": 25,
  "period_days": 7
}
```

**Example: Patient Timeline**
```json
GET /api/v1/dashboard/patient/{uuid}?days=30

Response:
{
  "patient_uuid": "...",
  "period_days": 30,
  "symptom_series": {
    "nausea": [
      {"date": "2026-01-01", "severity": "moderate", "severity_numeric": 2},
      {"date": "2026-01-03", "severity": "mild", "severity_numeric": 1}
    ],
    "fatigue": [
      {"date": "2026-01-02", "severity": "severe", "severity_numeric": 3}
    ]
  },
  "treatment_events": [
    {"event_type": "chemo_date", "event_date": "2026-01-01", "metadata": {}}
  ]
}
```

---

## Database Schema

### Patient Questions
```sql
CREATE TABLE patient_questions (
    id UUID PRIMARY KEY,
    patient_uuid UUID NOT NULL,
    question_text TEXT NOT NULL,
    share_with_physician BOOLEAN DEFAULT false,
    is_answered BOOLEAN DEFAULT false,
    category VARCHAR(50) DEFAULT 'other',
    is_deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Symptom Time Series
```sql
CREATE TABLE symptom_time_series (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL,
    symptom_id VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    recorded_at TIMESTAMP NOT NULL,
    source_session_id UUID,
    created_at TIMESTAMP
);
```

### Treatment Events
```sql
CREATE TABLE treatment_events (
    id UUID PRIMARY KEY,
    patient_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_date DATE NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP
);
```

### Audit Logs
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    user_role VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    ip_address VARCHAR(50),
    accessed_at TIMESTAMP
);
```

---

## Access Control

### Security Rules

1. **Physician-Scoped Queries**
   - All dashboard queries include `physician_id`
   - No cross-physician data access
   - Enforced at database query level

2. **Patient Question Privacy**
   - Questions are private by default
   - Only `share_with_physician = true` visible to doctors
   - No backdoor access to private questions

3. **Audit Logging**
   - All patient data access logged
   - Immutable logs (no update/delete)
   - No PHI in log metadata

### Access Model
```
Physician
├── Patients (many) - via patient_physician_associations
└── Staff (many) - via staff_associations

Staff inherits visibility through their physician only
```

---

## Deployment

### 1. Run Database Migration
```bash
# Patient database
psql -h $RDS_HOST -U $DB_USER -d oncolife_patient \
  -f scripts/db/schema_patient_diary_doctor_dashboard.sql

# Doctor database  
psql -h $RDS_HOST -U $DB_USER -d oncolife_doctor \
  -f scripts/db/schema_patient_diary_doctor_dashboard.sql
```

### 2. Verify Tables
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_name IN (
  'patient_questions', 
  'symptom_time_series', 
  'treatment_events',
  'audit_logs'
);
```

### 3. Backfill Data (Optional)
See migration script in `schema_patient_diary_doctor_dashboard.sql` for backfilling symptom time series from existing conversations.

---

## Frontend Integration

### Severity Colors
| Severity | Color | Hex |
|----------|-------|-----|
| mild | Green | #22c55e |
| moderate | Yellow | #eab308 |
| severe | Orange | #f97316 |
| urgent | Red | #ef4444 |

### Timeline Chart
Recommended: Use [Recharts](https://recharts.org/) or [Chart.js](https://www.chartjs.org/)

```jsx
// Example with Recharts
import { LineChart, Line, XAxis, YAxis } from 'recharts';

const SymptomTimeline = ({ data }) => (
  <LineChart data={data}>
    <XAxis dataKey="date" />
    <YAxis domain={[0, 4]} ticks={[1,2,3,4]} />
    {Object.keys(data.symptom_series).map(symptom => (
      <Line 
        key={symptom}
        dataKey={`symptom_series.${symptom}`}
        name={symptom}
      />
    ))}
  </LineChart>
);
```

---

## Acceptance Criteria

| Feature | Status | Notes |
|---------|--------|-------|
| Dashboard Landing | ✅ | Severity-ranked patient list |
| Patient Timeline | ✅ | Multi-symptom, zigzag chart data |
| Treatment Overlay | ✅ | Uses chemo_dates table |
| Questions (Patient) | ✅ | Create, update, share toggle |
| Questions (Doctor) | ✅ | Shared-only visibility |
| Weekly Reports | ✅ | JSON data (PDF generation TODO) |
| Audit Logging | ✅ | All access logged |
| Diary Auto-Populate | ✅ | From symptom checker sessions |

---

*Last Updated: January 2026*



