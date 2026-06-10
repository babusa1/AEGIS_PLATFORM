# OncoLife Doctor Application - Test Guide

## Overview

This document provides a complete testing guide for the OncoLife Doctor Dashboard Application. Use this to verify all implemented features are working correctly.

---

## Quick Reference

| Feature | API Endpoint | Status |
|---------|--------------|--------|
| Admin Login | POST /api/v1/auth/login | ✅ Implemented |
| Physician Registration | POST /api/v1/registration/physician | ✅ Implemented |
| Staff Registration | POST /api/v1/registration/staff | ✅ Implemented |
| Dashboard Landing | GET /api/v1/dashboard | ✅ Implemented |
| Patient Timeline | GET /api/v1/dashboard/patient/{uuid} | ✅ Implemented |
| Patient Questions | GET /api/v1/dashboard/patient/{uuid}/questions | ✅ Implemented |
| Weekly Reports | GET /api/v1/dashboard/reports/weekly | ✅ Implemented |
| Patient List | GET /api/v1/patients | ✅ Implemented |
| Patient Alerts | GET /api/v1/patients/{uuid}/alerts | ✅ Implemented |
| Patient Diary | GET /api/v1/patients/{uuid}/diary | ✅ Implemented |

---

## User Roles & Access

| Role | Can Do | Cannot Do |
|------|--------|-----------|
| **Admin** | Create physicians, manage clinics | See patient data directly |
| **Physician** | View own patients, create staff, generate reports | See other physicians' patients |
| **Staff (Nurse/MA/Navigator)** | View dashboard, flag concerns | Modify records, create staff, see other physicians' patients |

---

## Test Scenarios

### 1. Admin Functions

#### 1.1 Admin Login

**Screen Flow:**
```
Login Page → Enter Credentials → Dashboard (Admin View)
```

**What to Test:**
1. Navigate to https://doctor.oncolife.com
2. Enter admin credentials
3. Click "Login"
4. **Expected:** Redirect to Admin Dashboard

**Test Credentials:**
```
Email: admin@oncolife.com
Password: [Admin password]
```

---

#### 1.2 Create Physician (Admin Only)

**Screen Flow:**
```
Admin Dashboard → "Manage Physicians" → "Add Physician" → Form → Submit
```

**What to Test:**

**Step 1: Navigate to Physician Management**
- Click "Manage Physicians" in admin menu
- **Expected:** List of existing physicians displayed

**Step 2: Add New Physician**
1. Click "Add Physician" button
2. Fill form:
   - Email: `dr.smith@clinic.com`
   - First Name: `John`
   - Last Name: `Smith`
   - NPI Number: `1234567890` (10 digits)
   - Clinic: Select from dropdown
3. Click "Create Physician"
4. **Expected:** 
   - Success message displayed
   - Invite email sent to physician

**Step 3: Verify Email Sent**
- Check `dr.smith@clinic.com` inbox
- **Expected:** Welcome email with:
  - Username
  - Temporary password
  - Login link

**API Test:**
```bash
POST /api/v1/registration/physician
Authorization: Bearer <admin_token>

{
  "email": "dr.smith@clinic.com",
  "first_name": "John",
  "last_name": "Smith",
  "npi_number": "1234567890",
  "clinic_uuid": "clinic-uuid-here"
}

Expected Response:
{
  "success": true,
  "message": "Physician account created. Invite sent to dr.smith@clinic.com",
  "user_uuid": "new-physician-uuid",
  "email": "dr.smith@clinic.com",
  "role": "physician",
  "invite_sent": true,
  "status": "FORCE_CHANGE_PASSWORD"
}
```

**Validation Tests:**
- Try with invalid email → Error: "Valid email required"
- Try with duplicate email → Error: "Email already registered"
- Try with invalid NPI (not 10 digits) → Error: "NPI must be 10 digits"
- Try as non-admin user → Error: "Only administrators can create physician accounts"

---

#### 1.3 Create Clinic (Admin Only)

**Screen Flow:**
```
Admin Dashboard → "Manage Clinics" → "Add Clinic" → Form → Submit
```

**What to Test:**
1. Click "Manage Clinics"
2. Click "Add Clinic"
3. Enter clinic details:
   - Clinic Name
   - Address
   - Phone
4. Click "Save"
5. **Expected:** Clinic created and appears in list

**API Test:**
```bash
POST /api/v1/clinics
{
  "clinic_name": "City Cancer Center",
  "address": "123 Medical Drive",
  "phone": "555-0100"
}
```

---

### 2. Physician Functions

#### 2.1 Physician First Login

**Screen Flow:**
```
Login Page → Temp Password → Set New Password → MFA Setup (Optional) → Dashboard
```

**What to Test:**

**Step 1: Login with Temp Password**
1. Enter email from invite
2. Enter temporary password
3. Click "Login"
4. **Expected:** "Password Change Required" screen

**Step 2: Set New Password**
1. Enter new password (requirements shown)
2. Confirm password
3. Click "Update Password"
4. **Expected:** Redirect to MFA setup or Dashboard

**Step 3: MFA Setup (If Enabled)**
1. Scan QR code with authenticator app
2. Enter verification code
3. Click "Verify"
4. **Expected:** MFA enabled, redirect to Dashboard

**API Test:**
```bash
# Login returns challenge
POST /api/v1/auth/login
{
  "email": "dr.smith@clinic.com",
  "password": "TempPassword123!"
}

Response:
{
  "valid": true,
  "message": "Password change required",
  "user_status": "FORCE_CHANGE_PASSWORD",
  "session": "session-token"
}

# Complete password change
POST /api/v1/auth/complete-new-password
{
  "email": "dr.smith@clinic.com",
  "new_password": "NewSecurePass123!",
  "session": "session-token"
}
```

---

#### 2.2 Create Staff Member (Physician Only)

**Screen Flow:**
```
Physician Dashboard → "Manage My Staff" → "Add Staff" → Form → Submit
```

**What to Test:**

**Step 1: Navigate to Staff Management**
- Click "Manage My Staff" in menu
- **Expected:** List of staff associated with this physician

**Step 2: Add New Staff**
1. Click "Add Staff Member"
2. Fill form:
   - Email: `nurse.jane@clinic.com`
   - First Name: `Jane`
   - Last Name: `Doe`
   - Role: Select (Nurse / MA / Navigator)
3. Click "Create Staff"
4. **Expected:**
   - Success message
   - Staff linked to this physician
   - Invite email sent

**Step 3: Verify Staff Scope**
- New staff can only see THIS physician's patients
- Cannot see other physicians' patients

**API Test:**
```bash
POST /api/v1/registration/staff
Authorization: Bearer <physician_token>

{
  "email": "nurse.jane@clinic.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "role": "nurse"
}

Expected Response:
{
  "success": true,
  "user_uuid": "staff-uuid",
  "email": "nurse.jane@clinic.com",
  "role": "nurse",
  "physician_uuid": "physician-uuid",
  "invite_sent": true
}
```

**Validation Tests:**
- Try invalid role → Error: "Invalid role. Must be one of: nurse, ma, navigator"
- Try as staff (not physician) → Error: "Invalid physician"

---

### 3. Dashboard - Landing View

#### 3.1 View Ranked Patient List

**Screen Flow:**
```
Login → Dashboard Landing
```

**What to Test:**

**Expected Display:**
- List of patients sorted by:
  1. Has urgent escalation (red icon) - TOP
  2. Highest severity in last 7 days
  3. Most recent check-in

**Patient Row Should Show:**
| Element | Description |
|---------|-------------|
| Patient Name | Clickable, opens detail view |
| Last Check-In | Date/time of last symptom session |
| Severity Badge | Color-coded (Green/Yellow/Orange/Red) |
| Escalation Icon | ⚠️ Visible if urgent symptoms |

**Severity Colors:**
| Color | Meaning |
|-------|---------|
| 🟢 Green | Mild - Stable |
| 🟡 Yellow | Moderate - Monitor |
| 🟠 Orange | Severe - Needs review |
| 🔴 Red | Urgent - Immediate attention |

**API Test:**
```bash
GET /api/v1/dashboard?days=7&limit=50
Authorization: Bearer <token>

Expected Response:
{
  "patients": [
    {
      "patient_uuid": "uuid-1",
      "first_name": "John",
      "last_name": "Doe",
      "last_checkin": "2026-01-04T14:30:00Z",
      "max_severity": "severe",
      "has_escalation": true,
      "severity_badge": "orange"
    },
    {
      "patient_uuid": "uuid-2",
      "first_name": "Jane",
      "last_name": "Smith",
      "last_checkin": "2026-01-04T10:00:00Z",
      "max_severity": "mild",
      "has_escalation": false,
      "severity_badge": "green"
    }
  ],
  "total_patients": 25,
  "period_days": 7
}
```

---

#### 3.2 Filter and Search

**What to Test:**
1. Change time period (7 days, 14 days, 30 days)
2. Search by patient name
3. **Expected:** List updates accordingly

---

### 4. Patient Detail View

#### 4.1 Symptom Timeline

**Screen Flow:**
```
Dashboard → Click Patient Name → Patient Detail View → Timeline Tab
```

**What to Test:**

**Expected Display:**
- Multi-line chart showing symptoms over time
- X-axis: Days (last 30 days default)
- Y-axis: Severity (1=Mild, 2=Moderate, 3=Severe, 4=Urgent)
- Each symptom = different colored line
- Treatment events shown as vertical dashed lines

**Interactive Features:**
- Hover over point → Tooltip shows: Date, Symptom, Severity
- Toggle symptoms on/off with checkboxes
- Zoom in/out on timeline
- Change time period (7, 14, 30, 90 days)

**API Test:**
```bash
GET /api/v1/dashboard/patient/{patient_uuid}?days=30
Authorization: Bearer <token>

Expected Response:
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

---

#### 4.2 Treatment Overlay

**What to Test:**
1. Chemo dates appear as vertical markers on timeline
2. Hover shows: Event type, Date
3. Can see correlation between treatment and symptoms

---

#### 4.3 Patient Summary

**Screen Flow:**
```
Patient Detail → "Summary" Tab
```

**What to Test:**
- Patient demographics displayed
- Cancer type
- Treatment plan
- Recent symptom trends
- Escalation history

---

### 5. Shared Patient Questions

#### 5.1 View Shared Questions

**Screen Flow:**
```
Patient Detail → "Questions" Tab
```

**What to Test:**

**Expected Display:**
- Only questions where patient chose "Share with Doctor"
- Private questions are NOT visible (verify!)
- Questions sorted newest → oldest
- Unanswered questions highlighted

**Question Card Shows:**
- Question text
- Category (Symptom/Medication/Treatment/Other)
- Date asked
- Answered status

**API Test:**
```bash
GET /api/v1/dashboard/patient/{patient_uuid}/questions
Authorization: Bearer <token>

Expected Response:
{
  "questions": [
    {
      "id": "question-uuid",
      "question_text": "Should I take anti-nausea meds with food?",
      "category": "medication",
      "is_answered": false,
      "created_at": "2026-01-03T15:00:00Z"
    }
  ]
}
```

**Privacy Test:**
1. Have patient create a private question (share_with_physician = false)
2. Verify physician CANNOT see this question
3. Have patient share the question
4. Verify physician CAN now see it

---

### 6. Patient Diary (Physician View)

#### 6.1 View Patient Diary

**Screen Flow:**
```
Patient Detail → "Diary" Tab
```

**What to Test:**

**What Physicians SEE:**
- ✅ System-generated daily summaries
- ✅ Entries marked "Share with Doctor"
- ✅ Symptom severity per day
- ✅ Shared questions

**What Physicians DON'T SEE:**
- ❌ Private patient notes (marked_for_doctor = false)
- ❌ Draft entries
- ❌ Unshared content

**API Test:**
```bash
GET /api/v1/patients/{patient_uuid}/diary?for_doctor_only=true
Authorization: Bearer <token>

Expected Response:
{
  "entries": [
    {
      "id": 1,
      "entry_uuid": "uuid",
      "created_at": "2026-01-04T10:30:00Z",
      "title": "Symptom Check - January 4",
      "diary_entry": "Daily Check-in Summary...",
      "marked_for_doctor": true
    }
  ]
}
```

---

### 7. Alerts & Escalations

#### 7.1 View Patient Alerts

**Screen Flow:**
```
Patient Detail → "Alerts" Tab
```

**What to Test:**
- List of escalation events
- Shows: Date, Triage level, Symptoms involved
- Emergency (Call 911) highlighted in red
- Notify Care Team in orange

**API Test:**
```bash
GET /api/v1/patients/{patient_uuid}/alerts
Authorization: Bearer <token>

Expected Response:
{
  "alerts": [
    {
      "conversation_uuid": "uuid",
      "triage_level": "call_911",
      "symptom_list": ["fever", "confusion"],
      "created_at": "2026-01-02T08:00:00Z"
    }
  ]
}
```

---

### 8. Weekly Reports

#### 8.1 View Weekly Report

**Screen Flow:**
```
Dashboard → "Reports" → Select Week → View Report
```

**What to Test:**
- Select week to view
- Report shows:
  - All patients summary
  - Symptom trends
  - Escalation events
  - Shared questions
  - Treatment correlations

**API Test:**
```bash
GET /api/v1/dashboard/reports/weekly?week_start=2026-01-01
Authorization: Bearer <token>

Expected Response:
{
  "physician_id": "uuid",
  "report_week_start": "2026-01-01",
  "report_week_end": "2026-01-07",
  "generated_at": "2026-01-08T00:00:00Z",
  "patient_count": 25,
  "total_alerts": 3,
  "total_questions": 12,
  "patients": [...]
}
```

---

### 9. Staff Functions (Nurse/MA/Navigator)

#### 9.1 Staff Login

**What to Test:**
1. Staff logs in with credentials from invite email
2. Sets new password on first login
3. **Expected:** Redirected to Dashboard

---

#### 9.2 Staff Dashboard View

**What to Test:**
- Can see same dashboard as physician (their physician's patients only)
- Patient list shows physician's patients
- Can view patient details
- Can view timeline
- Can view shared questions

---

#### 9.3 Staff Restrictions

**Test These Are BLOCKED:**

| Action | Expected Result |
|--------|-----------------|
| Modify patient record | ❌ "Insufficient permissions" |
| Reassign patient | ❌ Option not visible or blocked |
| Create staff | ❌ Menu option not visible |
| Generate reports | ❌ "Insufficient permissions" |
| View other physician's patients | ❌ No data returned |

**API Test for Permissions:**
```bash
GET /api/v1/registration/permissions
Authorization: Bearer <staff_token>

Expected Response:
{
  "role": "nurse",
  "physician_uuid": "physician-uuid",
  "can_view_dashboard": true,
  "can_view_patients": true,
  "can_flag_concerns": true,
  "can_review_questions": true,
  "can_reassign_patients": false,
  "can_modify_records": false,
  "can_create_staff": false,
  "can_generate_reports": false,
  "patient_scope": "physician"
}
```

---

### 10. Security & Access Control Tests

#### 10.1 Cross-Physician Access (MUST FAIL)

**Test Scenario:**
1. Physician A has Patient X
2. Physician B tries to access Patient X
3. **Expected:** "Not authorized" error

**API Test:**
```bash
GET /api/v1/dashboard/patient/{patient_x_uuid}
Authorization: Bearer <physician_b_token>

Expected Response:
{
  "detail": "Physician not authorized to view patient"
}
Status: 403 Forbidden
```

---

#### 10.2 Staff Cross-Access (MUST FAIL)

**Test Scenario:**
1. Staff A works for Physician A
2. Staff A tries to access Physician B's patients
3. **Expected:** No data returned (empty list or 403)

---

#### 10.3 Audit Log Verification

**What to Test:**
1. View a patient record
2. Check audit_logs table
3. **Expected:** Entry logged with:
   - user_id
   - action: "view_patient_timeline"
   - entity_type: "patient"
   - entity_id: patient UUID
   - timestamp

**Database Check:**
```sql
SELECT * FROM audit_logs
WHERE user_id = 'physician-uuid'
AND accessed_at > now() - interval '1 hour'
ORDER BY accessed_at DESC;
```

---

## Error Handling Tests

### Authentication Errors
- Wrong password → "Invalid credentials"
- Expired token → "Session expired. Please login again."
- Missing token → "Authentication required"

### Authorization Errors
- Access other physician's patient → "Not authorized"
- Staff tries admin action → "Insufficient permissions"

### Data Errors
- Patient not found → "Patient not found"
- Invalid UUID → "Invalid patient identifier"

---

## Test Data Checklist

### Before Testing:
- [ ] Admin account exists
- [ ] At least 2 physicians created
- [ ] At least 1 staff per physician
- [ ] At least 5 patients per physician
- [ ] Patients have symptom history (varied severity)
- [ ] Some patients have escalations
- [ ] Some patients have shared questions

### Test Accounts:
```
Admin: admin@oncolife.com / [password]
Physician 1: dr.smith@clinic.com / [password]
Physician 2: dr.jones@clinic.com / [password]
Staff (Physician 1): nurse.jane@clinic.com / [password]
Staff (Physician 2): ma.bob@clinic.com / [password]
```

---

## Bug Reporting Template

```
**Bug Title:** [Short description]

**Environment:**
- Browser: [Chrome 120 / Firefox 121 / Safari 17]
- OS: [Windows 11 / macOS 14 / Ubuntu 22]
- User Role: [Admin / Physician / Staff]

**Steps to Reproduce:**
1. 
2. 
3. 

**Expected Result:**


**Actual Result:**


**Screenshots/Video:**
[Attach if available]

**Security Impact:** [Yes/No - describe if yes]

**Severity:** [Critical / High / Medium / Low]
```

---

---

## UI/UX Tests

### Dark Mode Testing (Doctor Portal)

**Toggle Location:**
- Desktop: Sidebar → Bottom section (pill toggle)
- Mobile: Top header bar (moon/sun icon)

**Dark Mode Activation:**
1. Click dark mode toggle
2. **Expected:**
   - Background changes to deep navy (#0F172A)
   - Sidebar adapts colors (no longer dark blue)
   - Cards get dark backgrounds (#1E293B)
   - Text becomes light (#F1F5F9)
   - Primary becomes brighter blue (#3B82F6)
   - Tables alternate row colors adjust
   - Smooth 0.3s transition

**Persistence Test:**
1. Enable dark mode
2. Log out and log back in
3. **Expected:** Dark mode persists

**Chart Readability:**
- [ ] Timeline chart colors visible in dark mode
- [ ] Severity badges still distinguishable
- [ ] Axis labels readable

### Responsive Design Testing

**Mobile (< 600px):**
- [ ] Hamburger menu in header
- [ ] Drawer navigation slides in with all nav items
- [ ] Patient cards stack vertically
- [ ] Tables become scrollable or cards
- [ ] Touch-friendly row selection

**Tablet (600px - 900px):**
- [ ] Sidebar visible with all 4 nav items
- [ ] Dashboard cards in 2-column grid
- [ ] Timeline chart responsive

**Desktop (> 900px):**
- [ ] Full sidebar with all menu items and labels
- [ ] Dark mode toggle visible in sidebar
- [ ] Multi-column dashboard
- [ ] Full patient tables

### Navigation Items (All Screen Sizes)

| Icon | Label | Route | Purpose |
|------|-------|-------|---------|
| 📊 | Dashboard | /dashboard | Severity-ranked patient list |
| 👥 | Patients | /patients | Full patient management |
| 📄 | Weekly Reports | /reports | Weekly summaries & statistics |
| 👤 | Staff | /staff | Staff management (Physicians only) |

### Patient Detail Navigation (From Dashboard/Patients)

| Tab | Route | Description |
|-----|-------|-------------|
| Timeline | /patients/{uuid} | Symptom zigzag chart + treatment overlay |
| Questions | Tab within detail | Shared patient questions |
| Treatment Events | Tab within detail | Chemo cycles, treatment milestones |
| Escalations | Tab within detail | Alert history (coming soon) |

---

## Test Sign-Off

| Test Area | Tester | Date | Pass/Fail |
|-----------|--------|------|-----------|
| Admin Registration | | | |
| Physician Registration | | | |
| Staff Registration | | | |
| Dashboard Landing | | | |
| Patient Timeline | | | |
| Shared Questions | | | |
| Patient Diary View | | | |
| Alerts | | | |
| Weekly Reports | | | |
| Staff Restrictions | | | |
| Security (Cross-Access) | | | |
| Audit Logging | | | |
| **Dark Mode** | | | |
| **Mobile Responsiveness** | | | |

---

## Acceptance Criteria Summary

| Requirement | Test Result |
|-------------|-------------|
| Physician registration is admin-controlled | ⬜ |
| Staff registration is physician-controlled | ⬜ |
| Dashboard matches severity ranking spec | ⬜ |
| Timeline shows multi-symptom data | ⬜ |
| Treatment overlay visible on timeline | ⬜ |
| Only shared questions visible | ⬜ |
| Diary shows shared entries only | ⬜ |
| Staff cannot modify records | ⬜ |
| No cross-physician data access | ⬜ |
| All access is audit logged | ⬜ |

---

*Last Updated: January 2026*
*Version: 2.0 - Updated with dark mode and responsive design tests*

