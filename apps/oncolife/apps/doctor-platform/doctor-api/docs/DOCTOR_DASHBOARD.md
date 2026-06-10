# Doctor Dashboard - Complete Implementation Guide

## Overview

The Doctor Dashboard is an **analytics-driven clinical monitoring platform** for oncology care teams managing chemotherapy patients remotely.

---

## 1. Clinical Goals

- **Continuously monitor** patient symptoms over time
- **Identify early deterioration** trends before emergencies
- **Correlate symptoms** with chemotherapy timelines
- **Reduce avoidable ER visits** and hospitalizations
- **Enable efficient triage** by physicians and nurse navigators

---

## 2. User Roles & Access Model

### 2.1 Roles

| Role | Description | Key Capabilities |
|------|-------------|------------------|
| **Physician** | Primary clinical decision-maker | Full access to own patients |
| **Staff (Nurse/MA/Navigator)** | Daily monitoring support | View-only, can flag concerns |
| **Admin** | System administrator | Create physicians, manage clinics |

### 2.2 Access Rules (STRICT ENFORCEMENT)

```
Physician
├── Patients (many) - directly assigned
└── Staff (many) - can view physician's patients only
```

**Security Rules:**
- ✅ All access control enforced at **database query level**
- ✅ `physician_id` is **mandatory** in every dashboard query
- ❌ No frontend filtering for security
- ❌ No client-side hiding of data
- ❌ No shared dashboards across physicians

This is a **HIPAA boundary**, not a UI preference.

### 2.3 Staff Permissions Matrix

| Action | Physician | Staff (Nurse/MA/Navigator) |
|--------|-----------|---------------------------|
| View Dashboard | ✅ | ✅ |
| View Patients (own physician) | ✅ | ✅ |
| Flag Concerning Trends | ✅ | ✅ |
| Review Shared Questions | ✅ | ✅ |
| Reassign Patients | ✅ | ❌ |
| See Other Physicians' Patients | ❌ | ❌ |
| Modify Patient Records | ✅ | ❌ |
| Create Staff | ✅ | ❌ |
| Generate Reports | ✅ | ❌ |

---

## 3. Physician & Staff Registration

### 3.1 Physician Registration (Admin-Initiated)

**❗ Physicians are NOT self-sign-up users**

**Flow:**
1. Clinic Admin creates physician account
2. Physician receives secure invite email
3. Physician sets password (+ MFA recommended)
4. Physician profile activated
5. Physician can now add staff

**API Endpoint:**
```bash
POST /api/v1/registration/physician
Authorization: Bearer <admin_token>

{
  "email": "john.doe@clinic.com",
  "first_name": "John",
  "last_name": "Doe",
  "npi_number": "1234567890",
  "clinic_uuid": "uuid-of-clinic"
}
```

**Database Record:**
```sql
INSERT INTO physicians (
  id, first_name, last_name, email
) VALUES (
  gen_random_uuid(),
  'John',
  'Doe',
  'john.doe@clinic.com'
);
```

**Cognito Attributes:**
```json
{
  "email": "john.doe@clinic.com",
  "role": "physician",
  "physician_id": "UUID",
  "clinic_id": "UUID"
}
```

**Security:**
- MFA required (recommended)
- IP logging enabled
- Password rotation policy
- Account lockout after failed attempts

### 3.2 Staff Registration (Physician-Controlled)

**Flow:**
1. Physician logs into dashboard
2. Navigates to "Manage Staff"
3. Enters: Name, Email, Role
4. System sends invite
5. Staff sets password
6. Staff restricted to physician scope

**API Endpoint:**
```bash
POST /api/v1/registration/staff
Authorization: Bearer <physician_token>

{
  "email": "jane.smith@clinic.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "role": "navigator"
}
```

**Cognito Attributes:**
```json
{
  "email": "jane.smith@clinic.com",
  "role": "staff",
  "physician_id": "UUID-of-physician",
  "staff_role": "navigator"
}
```

---

## 4. Dashboard UX (API Behavior)

### 4.1 Landing View - Ranked Patient List

**Clinical Purpose:** Answer "Which patients need attention right now?"

**Patient List Ranking Logic:**
1. Has urgent escalation (highest priority)
2. Maximum symptom severity in last 7 days
3. Most recent check-in

**API Endpoint:**
```bash
GET /api/v1/dashboard?days=7&limit=50
Authorization: Bearer <token>
```

**Response:**
```json
{
  "patients": [
    {
      "patient_uuid": "uuid",
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

**Patient Row Contents:**
| Field | Description |
|-------|-------------|
| Name | Clickable → patient detail view |
| Last Check-in | Timestamp of most recent entry |
| Severity Badge | Color-coded based on max severity |
| Escalation Icon | Visible if any urgent rule triggered |

**Severity Color Logic:**
| Severity | Color | Hex |
|----------|-------|-----|
| Mild | Green | #22c55e |
| Moderate | Yellow | #eab308 |
| Severe | Orange | #f97316 |
| Urgent | Red | #ef4444 |

**Backend Query:**
```sql
SELECT
  p.uuid,
  p.first_name,
  p.last_name,
  MAX(c.created_at) AS last_checkin,
  MAX(CASE 
    WHEN c.conversation_state = 'EMERGENCY' THEN 'urgent'
    WHEN c.severity_list::text LIKE '%severe%' THEN 'severe'
    WHEN c.severity_list::text LIKE '%moderate%' THEN 'moderate'
    ELSE 'mild'
  END) AS max_severity,
  BOOL_OR(c.conversation_state = 'EMERGENCY') AS has_escalation
FROM patient_info p
JOIN conversations c ON p.uuid = c.patient_uuid
WHERE p.uuid IN (
  SELECT patient_uuid FROM patient_physician_associations
  WHERE physician_uuid = :physician_id
)
AND c.created_at >= now() - interval '7 days'
GROUP BY p.uuid
ORDER BY has_escalation DESC, max_severity DESC, last_checkin DESC;
```

### 4.2 Patient Detail View - Symptom Timeline

**API Endpoint:**
```bash
GET /api/v1/dashboard/patient/{patient_uuid}?days=30
Authorization: Bearer <token>
```

**Response:**
```json
{
  "patient_uuid": "uuid",
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

**Chart Structure:**
- **Chart Type:** Multi-line time series (zigzag style)
- **X-axis:** Time (days)
- **Y-axis:** Severity (ordinal: mild=1, moderate=2, severe=3, urgent=4)
- **Lines:** One colored line per symptom type
- **Treatment Markers:** Vertical dashed lines for chemo events

**Interactive Features:**
- Toggle symptoms on/off (checkbox list)
- Hover tooltips: Date, Symptom, Severity, Source
- Zoom by time range

---

## 5. Patient Questions (Physician View)

**What Physicians See:**
- ✅ Questions with `share_with_physician = true`
- ✅ Sorted newest → oldest
- ✅ Highlighted if unanswered

**What Physicians Never See:**
- ❌ Private patient notes
- ❌ Draft questions
- ❌ Unshared content

**API Endpoint:**
```bash
GET /api/v1/dashboard/patient/{patient_uuid}/questions
Authorization: Bearer <token>
```

**Backend Query:**
```sql
SELECT id, question_text, category, is_answered, created_at
FROM patient_questions
WHERE patient_uuid = :patient_uuid
AND share_with_physician = true
AND is_deleted = false
ORDER BY created_at DESC;
```

---

## 6. Weekly Physician Reports

### 6.1 Report Contents

- Patient demographics
- Weekly symptom severity trends
- Escalation events
- Shared questions
- Treatment overlays

### 6.2 Generation Trigger

- Weekly cron job (AWS EventBridge)
- Or manual admin trigger

**API Endpoint:**
```bash
GET /api/v1/dashboard/reports/weekly?week_start=2026-01-01
Authorization: Bearer <token>
```

**Response:**
```json
{
  "physician_id": "uuid",
  "report_week_start": "2026-01-01",
  "report_week_end": "2026-01-07",
  "generated_at": "2026-01-08T00:00:00Z",
  "patient_count": 25,
  "total_alerts": 3,
  "total_questions": 12,
  "patients": [
    {
      "patient": {"uuid": "...", "first_name": "John", "last_name": "Doe"},
      "symptoms": {"symptom_count": 5, "max_severity": "moderate"},
      "alerts": [],
      "questions": []
    }
  ]
}
```

---

## 7. Audit Logging (HIPAA Requirement)

All patient data access is logged.

**Logged Actions:**
- Dashboard views
- Patient record access
- Report downloads
- Question views

**Audit Table:**
```sql
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  user_role VARCHAR(50) NOT NULL,
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(50),
  entity_id UUID,
  ip_address VARCHAR(50),
  accessed_at TIMESTAMP DEFAULT NOW()
);
```

---

## 8. Database Schema

### Core Tables (Doctor Database)

```sql
-- Symptom Time Series (powers timeline)
CREATE TABLE symptom_time_series (
  id UUID PRIMARY KEY,
  patient_id UUID NOT NULL,
  symptom_id VARCHAR(100) NOT NULL,
  severity VARCHAR(20) NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  source_session_id UUID
);

-- Treatment Events (timeline overlay)
CREATE TABLE treatment_events (
  id UUID PRIMARY KEY,
  patient_id UUID NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  event_date DATE NOT NULL,
  metadata JSONB
);

-- Weekly Reports
CREATE TABLE physician_reports (
  id UUID PRIMARY KEY,
  physician_id UUID NOT NULL,
  report_week_start DATE NOT NULL,
  report_week_end DATE NOT NULL,
  generated_at TIMESTAMP DEFAULT NOW(),
  report_s3_path TEXT NOT NULL
);

-- Audit Logs
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  user_role VARCHAR(50) NOT NULL,
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(50),
  entity_id UUID,
  accessed_at TIMESTAMP DEFAULT NOW()
);
```

---

## 9. Security Model

### Authentication
- AWS Cognito
- Separate user pools: Patients vs Physicians+Staff

### Authorization
- Physician ID enforced in **every** query
- Staff inherit physician scope
- No frontend filtering for security

### Audit
- Every patient view logged
- Every report download logged
- IP addresses captured
- No PHI in logs

---

## 10. API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard` | Ranked patient list |
| GET | `/dashboard/patient/{uuid}` | Patient symptom timeline |
| GET | `/dashboard/patient/{uuid}/questions` | Shared questions |
| GET | `/dashboard/reports/weekly` | Weekly report data |
| POST | `/registration/physician` | Admin: Create physician |
| POST | `/registration/staff` | Physician: Create staff |
| GET | `/registration/permissions` | Get staff permissions |

---

## 11. Deployment Checklist

### Infrastructure
- [ ] Cognito User Pool for Physicians/Staff
- [ ] Database tables created
- [ ] IAM roles configured
- [ ] CloudWatch alarms set

### Security
- [ ] Physician-scoped queries verified
- [ ] Audit logging active
- [ ] MFA enabled for physicians
- [ ] IP logging enabled

### Testing
- [ ] Dashboard loads with correct patients
- [ ] Timeline data accurate
- [ ] Only shared questions visible
- [ ] Audit logs populated

---

## 12. Acceptance Criteria

| Feature | Done When |
|---------|-----------|
| Physician onboarding | Admin-controlled, MFA |
| Staff access | Scoped to physician |
| Dashboard | Severity-ranked, matches spec |
| Timeline | Multi-symptom, accurate |
| Questions | Opt-in only visible |
| Reports | Weekly data generated |
| Security | No cross-physician access |
| Audit | All access logged |

---

*Last Updated: January 2026*



