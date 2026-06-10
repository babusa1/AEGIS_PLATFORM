# OncoLife Patient Application - Test Guide

## Overview

This document provides a complete testing guide for the OncoLife Patient Application. Use this to verify all implemented features are working correctly.

---

## Quick Reference

| Feature | API Endpoint | Status |
|---------|--------------|--------|
| User Registration | POST /api/v1/auth/signup | ✅ Implemented |
| User Login | POST /api/v1/auth/login | ✅ Implemented |
| Symptom Checker | WS /api/v1/chat/ws/{uuid} | ✅ Implemented |
| Patient Diary | GET/POST /api/v1/diary | ✅ Implemented |
| Questions to Doctor | GET/POST /api/v1/questions | ✅ Implemented |
| Chemo Dates | GET/POST/DELETE /api/v1/chemo | ✅ Implemented |
| Profile (with Oncology) | GET/PUT /api/v1/profile | ✅ Implemented |
| Chemo Timeline | GET /api/v1/chemo/upcoming | ✅ Implemented |
| Education Content | GET /api/v1/education/tab | ✅ Implemented |

---

## Test Scenarios

### 1. Patient Onboarding Flow

#### 1.1 New Patient Registration (Fax-Initiated)

**Prerequisites:** Patient referral fax received from clinic

**Expected Flow:**
```
Fax Received → OCR Processing → Patient Account Created → Welcome Email Sent
```

**What to Test:**
1. Verify welcome email received at patient's email
2. Email contains:
   - Username (email address)
   - Temporary password
   - Login link
3. Temporary password works for first login

**API Test:**
```bash
# Check onboarding status
GET /api/v1/onboarding/status?patient_id={uuid}

Expected Response:
{
  "status": "pending_first_login",
  "email_sent": true,
  "sms_sent": true
}
```

---

#### 1.2 First Login - Mandatory Setup

**Screen Flow:**
```
Login Screen → Password Reset → Acknowledgement → Terms & Privacy → Reminder Preferences → Dashboard
```

**Step 1: Login with Temporary Password**
- Enter email from welcome email
- Enter temporary password
- Click "Login"
- **Expected:** Redirect to "Set New Password" screen

**Step 2: Set New Password**
- Enter new password (min 8 chars, 1 uppercase, 1 number, 1 special)
- Confirm password
- Click "Update Password"
- **Expected:** Redirect to Acknowledgement screen

**Step 3: Acknowledgement Screen**
- Read the acknowledgement text:
  > "I understand this tool does not replace my care team or emergency services."
- Check the acknowledgement checkbox
- Click "Continue"
- **Expected:** Redirect to Terms & Privacy screen

**Step 4: Terms & Privacy**
- View Terms & Conditions
- View Privacy Policy (HIPAA notice)
- Check both acceptance checkboxes
- Click "Accept & Continue"
- **Expected:** Redirect to Reminder Preferences screen

**Step 5: Reminder Preferences**
- See pre-filled phone/email (from referral)
- Edit if needed
- Select reminder method: Email or SMS
- Select reminder time
- Click "Save Preferences"
- **Expected:** Redirect to Main Dashboard/Chat screen

**API Tests:**
```bash
# Complete acknowledgement
POST /api/v1/onboarding/complete/acknowledgement
{ "acknowledged": true }

# Accept terms
POST /api/v1/onboarding/complete/terms
{ "terms_accepted": true, "privacy_accepted": true }

# Set reminders
POST /api/v1/onboarding/complete/reminders
{ "method": "email", "time": "09:00" }
```

---

### 2. Symptom Checker (Daily Check-In) - 7-PHASE FLOW

#### 2.1 Start New Session

**Screen Flow (7 Phases):**
```
Dashboard → Medical Disclaimer → Patient Context → Emergency Check → Grouped Symptom Selection → Ruby Chat → Summary
```

**What to Test:**

**Phase 1: Medical Disclaimer Screen**
- Click "Start Daily Check-In"
- **Expected:** Disclaimer screen displays:
  ```
  IMPORTANT MEDICAL DISCLAIMER:
  This system is an automated symptom checker. It is NOT a substitute 
  for professional medical advice, diagnosis, or treatment.
  
  If you believe you are having a medical emergency, call 911 immediately.
  
  [I Understand - Start Triage]
  ```
- Click "I Understand - Start Triage" button
- **Expected:** Moves to Patient Context screen

**Phase 2: Patient Context (Critical Physician Data) - NEW**
- System displays quick check-in with two questions:

**Question 1: Last Chemotherapy**
```
📋 Quick Check-In
📅 When was your last chemotherapy session?
This helps us understand your treatment timeline.
```
- **Options:** Today, Yesterday, 2-3 days ago, 4-7 days ago, 1-2 weeks ago, More than 2 weeks ago, I haven't had chemotherapy yet
- Select one option
- **Expected:** Moves to Question 2

**Question 2: Physician Visit**
```
📅 When is your next scheduled physician visit?
This helps us prioritize any concerns for your upcoming appointment.
```
- **Options:** Today, Tomorrow, In 2-3 days, This week, Next week, In 2+ weeks, Not scheduled yet
- Select one option
- **Expected:** Moves to Emergency Check screen

**Phase 3: Emergency Check Screen (Urgent Safety Check)**
- System displays: "Before we assess your symptoms, we need to rule out immediate emergencies."
- **Emergency symptoms shown** (multi-select):
  - ⚠️ Trouble breathing or shortness of breath
  - ⚠️ Chest pain
  - ⚠️ Uncontrolled bleeding OR Blood in stool/urine
  - ⚠️ Fainting or Syncope
  - ⚠️ Confusion or Altered Mental Status
- **Test Path A - Emergency selected:**
  - Select any emergency symptom
  - Click "Continue"
  - **Expected:** Immediate emergency escalation path (Call 911 screen)
- **Test Path B - No emergencies:**
  - Click "None of these - Continue"
  - **Expected:** Proceeds to Grouped Symptom Selection

**Phase 4: Grouped Symptom Selection**
- System displays symptom categories in groups:
  - **Digestive Health:** Nausea, Vomiting, Diarrhea, Constipation, No Appetite, Mouth Sores
  - **Pain & Nerve:** Pain, Neuropathy (Numbness/Tingling)
  - **Systemic & Infection:** Fever, Bleeding or Bruising, Fatigue, Cough, Urinary Problems
  - **Skin & External:** Skin Rash, Swelling, Eye Complaints
- Select one or more symptoms (multi-select)
- Click "Continue"
- **Expected:** Ruby Chat interface begins

**Phase 5: Ruby Chat (Per-Symptom Questions)**
- **Expected:** Ruby introduces herself:
  ```
  "Hello! I am Ruby, your automated triage assistant. 
  I'm here to help assess your symptoms."
  ```
- For each selected symptom, answer screening questions in WhatsApp-like chat style:

**Example: Fever**
- Ruby: "Do you have a fever?" → Select (Yes/No)
- Ruby: "What is your temperature?" → Enter number
  - **Input hint:** 📝 Enter temperature in °F (e.g., 98.6 or 101.5)
- Ruby: "How long have you had the fever?" → Select option
- Ruby: "Any other symptoms with the fever?" → Multi-select

**Expected Behavior:**
- WhatsApp-style chat bubbles (Ruby on left, Patient on right)
- Questions appear one at a time
- Selected options clearly shown as patient's response
- Ruby avatar visible on her messages
- Smooth scrolling to new messages
- Progress through all selected symptoms
- **Input hints displayed for numeric fields** (temperature, days, times, etc.)

**Phase 6: Triage Result**
After all questions answered:
- **Green (Mild):** "Your symptoms are mild. Continue monitoring."
- **Yellow (Moderate):** "Monitor closely. Contact care team if worsening."
- **Orange (Severe):** "Contact your care team today."
- **Red (Urgent/Emergency):** "Seek immediate medical attention. Call 911."

**Phase 7: Summary Screen**
- System displays complete summary of session
- **Action Buttons available:**
  - 📥 **Download Summary** - Save as PDF
  - 📓 **Save to Diary** - Creates diary entry
  - 🔄 **Report Another Symptom** - Return to symptom selection
  - ✅ **Done** - Complete session
- Education content appears below summary:
  - Symptom-specific tips (4-6 bullets)
  - "Read More" links to PDFs
  - Care Team Handout link
  - Mandatory disclaimer text

**API Tests:**
```bash
# Get/Create today's session
GET /api/v1/chat/session/today

# WebSocket connection
WS /api/v1/chat/ws/{chat_uuid}

# Send message
{
  "content": "fever",
  "message_type": "multi_select_response"
}
```

---

#### 2.2 Emergency Triage (Call 911)

**Trigger Conditions:**
- Temperature > 103°F with chills
- Severe bleeding
- Difficulty breathing
- Chest pain
- Confusion/altered consciousness

**Expected Screen:**
```
⚠️ EMERGENCY

Based on your symptoms, you should seek immediate medical attention.

🚨 CALL 911 or go to the nearest emergency room.

Your care team has been notified.

[Call 911 Button]
[I Understand Button]
```

**What to Verify:**
1. Red/emergency styling is prominent
2. 911 button is functional
3. Care team notification logged
4. Cannot continue regular flow until acknowledged

---

#### 2.3 Input Validation Tests

**Temperature Validation:**
| Test Input | Expected Result |
|------------|-----------------|
| `98.6` | ✅ Accepted (normal temp) |
| `101.5` | ✅ Accepted (fever range) |
| `37.5` | ✅ Auto-converts from Celsius → shows "🔄 Converted: 37.5°C = 99.5°F" |
| `85` | ❌ Error: "Temperature 85°F seems too low" |
| `115` | ❌ Error: "Temperature 115°F seems too high" |
| `abc` | ❌ Error: "Please enter a valid number" |

**Blood Pressure Validation (format: 120/80):**
| Test Input | Expected Result |
|------------|-----------------|
| `120/80` | ✅ Accepted |
| `140/90` | ✅ Accepted |
| `120` | ❌ Error: "Invalid format. Enter as 120/80" |
| `50/30` | ❌ Error: "Systolic should be 70-250" |
| `120/120` | ❌ Error: "Systolic should be higher than diastolic" |

**Heart Rate Validation (40-200 BPM):**
| Test Input | Expected Result |
|------------|-----------------|
| `72` | ✅ Accepted |
| `30` | ❌ Error: "Heart rate 30 BPM seems too low" |
| `250` | ❌ Error: "Heart rate 250 BPM seems too high" |

**Oxygen Saturation Validation (70-100%):**
| Test Input | Expected Result |
|------------|-----------------|
| `98` | ✅ Accepted |
| `95%` | ✅ Accepted (% sign ignored) |
| `60` | ❌ Error: "SpO2 60% seems too low" |
| `105` | ❌ Error: "SpO2 cannot exceed 100%" |

**Days/Times Validation:**
| Test Input | Expected Result |
|------------|-----------------|
| `3` | ✅ Accepted |
| `45` | ❌ Error: "Please enter a value between 0-30 days" |
| `-1` | ❌ Error: "Days cannot be negative" |

**Blood Sugar Validation (20-600 mg/dL):**
| Test Input | Expected Result |
|------------|-----------------|
| `120` | ✅ Accepted |
| `10` | ❌ Error: "Blood sugar 10 mg/dL seems too low" |
| `700` | ❌ Error: "Blood sugar 700 mg/dL seems too high" |

---

### 3. Patient Diary

#### 3.1 View Diary Entries

**Screen Flow:**
```
Dashboard → "My Diary" → Calendar/List View → Entry Details
```

**What to Test:**
- Calendar shows dates with entries highlighted
- Click date to see entries for that day
- Auto-generated entries from symptom checker visible
- Manual entries visible
- Entries marked for doctor show indicator

**API Test:**
```bash
GET /api/v1/diary?timezone=America/Los_Angeles

Expected Response:
{
  "entries": [
    {
      "id": 1,
      "entry_uuid": "uuid",
      "created_at": "2026-01-04T10:30:00Z",
      "title": "Symptom Check - January 04, 2026",
      "diary_entry": "Daily Check-in Summary...",
      "marked_for_doctor": true
    }
  ]
}
```

---

#### 3.2 Create Manual Diary Entry

**Screen Flow:**
```
My Diary → "Add Entry" → Entry Form → Save
```

**What to Test:**
1. Click "Add Entry" button
2. Enter optional title
3. Enter diary text (required)
4. Toggle "Share with Doctor" (optional)
5. Click "Save"
6. **Expected:** Entry appears in list

**API Test:**
```bash
POST /api/v1/diary
{
  "title": "Feeling better today",
  "diary_entry": "Nausea has subsided. Eating better.",
  "marked_for_doctor": false
}
```

---

#### 3.3 Auto-Generated Diary Entry

**What to Test:**
After completing a symptom checker session:
1. Navigate to "My Diary"
2. **Expected:** New entry automatically created with:
   - Title: "Symptom Check - [Date]"
   - Content: Summary of symptoms reported
   - Severity levels listed
   - Triage outcome noted
   - Marked for doctor if escalation occurred

---

### 4. Questions to Ask Doctor

#### 4.1 View Questions

**Screen Flow:**
```
Dashboard → "Questions for Doctor" → Question List
```

**What to Test:**
- See list of all questions (private and shared)
- Private questions show lock icon
- Shared questions show "Shared" badge
- Answered questions show checkmark

---

#### 4.2 Create Question

**Screen Flow:**
```
Questions → "Add Question" → Question Form → Save
```

**What to Test:**
1. Click "Add Question"
2. Enter question text (required)
3. Select category: Symptom, Medication, Treatment, Other
4. Toggle "Share with Doctor" 
5. Click "Save"
6. **Expected:** Question appears in list

**API Test:**
```bash
POST /api/v1/questions
{
  "question_text": "Should I take my anti-nausea medication with food?",
  "category": "medication",
  "share_with_physician": true
}
```

---

#### 4.3 Share/Unshare Question

**What to Test:**
1. Find an existing question
2. Click "Share" toggle
3. **Expected:** Question status changes
4. Shared questions visible to physician

**API Test:**
```bash
POST /api/v1/questions/{question_id}/share?share=true
```

---

### 5. Chemotherapy Dates

#### 5.1 View Chemo Schedule

**Screen Flow:**
```
Dashboard → "My Treatment" → Chemo Calendar
```

**What to Test:**
- Calendar shows upcoming chemo dates
- Past chemo dates marked differently
- Click date for details

---

#### 5.2 Log Chemo Date

**Screen Flow:**
```
My Treatment → "Log Chemo" → Date Picker → Save
```

**What to Test:**
1. Click "Log Chemo Date"
2. Select date from calendar
3. Click "Save"
4. **Expected:** Date appears on calendar

**API Test:**
```bash
POST /api/v1/chemo/log
{
  "chemo_date": "2026-01-15"
}

GET /api/v1/chemo/history
```

---

### 6. Profile Management

#### 6.1 View Profile (with Oncology Data)

**Screen Flow:**
```
Dashboard → Profile Icon → Profile Screen
```

**What to Test:**

| Section | Fields to Verify |
|---------|-----------------|
| **Personal Info** | Name, Email, Phone, DOB, Reminder Time |
| **Treatment Info** | Diagnosis, Treatment Type, Doctor/Clinic Name |
| **Treatment Dates** | Last Chemo Date, Next Physician Visit |
| **Emergency Contact** | Contact Name, Contact Phone |

**API Test:**
```bash
GET /api/v1/profile?patient_uuid={uuid}

Expected Response:
{
  "first_name": "Test",
  "last_name": "Patient",
  "email_address": "test@example.com",
  "phone_number": "555-1234",
  "date_of_birth": "1980-05-15",
  "reminder_time": "09:00",
  "doctor_name": "Dr. Smith",
  "clinic_name": "Oncology Center",
  "diagnosis": "Breast Cancer",
  "treatment_type": "Chemotherapy",
  "chemo_start_date": "2025-12-16",
  "chemo_end_date": "2026-04-28",
  "current_cycle": 2,
  "total_cycles": 8,
  "last_chemo_date": "2026-01-10",
  "next_physician_visit": "2026-01-20",
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_phone": "555-5678"
}
```

---

#### 6.2 Update Profile (with Treatment Information)

**Screen Flow:**
```
Profile → "Edit" Button → Edit Form → "Save Changes"
```

**What to Test:**
1. Navigate to Profile
2. Click "Edit" button
3. Update treatment information fields:
   - Last Chemotherapy Date (date picker)
   - Next Physician Visit (date picker)
   - Diagnosis
   - Treatment Type
   - Emergency Contact Name/Phone
4. Click "Save Changes"
5. **Expected:** ✅ Success message, data persisted
6. Refresh page and verify changes persist

**API Test:**
```bash
PUT /api/v1/profile?patient_uuid={uuid}
{
  "first_name": "Test",
  "last_name": "Patient",
  "phone_number": "555-1234",
  "diagnosis": "Breast Cancer Stage II",
  "treatment_type": "Neoadjuvant Chemotherapy",
  "last_chemo_date": "2026-01-10",
  "next_physician_visit": "2026-01-25",
  "emergency_contact_name": "John Doe",
  "emergency_contact_phone": "555-9999"
}
```

---

#### 6.3 Chemotherapy Timeline

**Screen Flow:**
```
Profile Page → Scroll to "Chemotherapy Timeline" section
```

**What to Test:**
1. **Upcoming Sessions:** Displays future chemo dates with countdown
2. **Recent Sessions:** Displays past chemo dates
3. **Add Date:** Click "+ Add Date", select date, confirm
4. **Delete Date:** Click 🗑️ icon, confirm deletion

**API Tests:**
```bash
# Get upcoming chemo dates
GET /api/v1/chemo/upcoming?patient_uuid={uuid}

# Get chemo history
GET /api/v1/chemo/history?patient_uuid={uuid}

# Add a chemo date
POST /api/v1/chemo/log?patient_uuid={uuid}
{
  "chemo_date": "2026-02-01"
}

# Delete a chemo date
DELETE /api/v1/chemo/2026-02-01?patient_uuid={uuid}
```

---

#### 6.4 Update Reminder Preferences

**Screen Flow:**
```
Profile → "Edit" → Update Reminder Time → Save
```

**What to Test:**
1. Navigate to Profile
2. Click "Edit" button
3. Change reminder time
4. Click "Save Changes"
5. **Expected:** Settings updated

**API Test:**
```bash
PATCH /api/v1/profile/config?patient_uuid={uuid}
{
  "reminder_method": "sms",
  "reminder_time": "08:00"
}
```

---

### 7. Education Tab

#### 7.1 View Education Library

**Screen Flow:**
```
Dashboard → "Education" → Education Library
```

**What to Test:**
- Default view: Last 7 days of symptoms
- Section: "My Current Symptoms"
- Section: "Common Chemotherapy Symptoms"
- Section: "Care Team Handouts"
- Each item shows title and brief description
- PDF links work (open in new tab/viewer)

---

#### 7.2 Search Education

**What to Test:**
1. Use search bar
2. Enter symptom name (e.g., "nausea")
3. **Expected:** Relevant education content displayed
4. Click on result to view details

**API Test:**
```bash
GET /api/v1/education/search?q=nausea
```

---

### 8. Conversation History

#### 8.1 View Past Sessions

**Screen Flow:**
```
Dashboard → "History" → Session List → Session Detail
```

**What to Test:**
- List shows all past symptom checker sessions
- Each session shows:
  - Date/time
  - Symptoms reported
  - Triage outcome (color-coded)
- Click session to see full conversation

**API Test:**
```bash
GET /api/v1/summaries/2026/1
```

---

## Error Handling Tests

### Network Errors
- Turn off WiFi during symptom checker
- **Expected:** "Connection lost. Your progress is saved." message
- Reconnect and continue from where left off

### Session Timeout
- Leave app idle for 30+ minutes
- Try to perform action
- **Expected:** Redirect to login screen

### Invalid Inputs
- Try empty diary entry → "Entry cannot be empty"
- Try invalid date for chemo → "Please select a valid date"
- Try weak password → Password requirements shown

---

## UI/UX Tests

### Dark Mode Testing

**What to Test:**

**Toggle Location:**
- Desktop/Tablet: Sidebar → Bottom (pill toggle with "Light Mode/Dark Mode" label)
- Mobile: Top header bar (moon/sun icon)

**Dark Mode Activation:**
1. Click dark mode toggle
2. **Expected:**
   - Background changes to deep navy (#0F172A)
   - Text becomes light gray (#F1F5F9)
   - Primary color shifts to lighter teal (#4DB6AC)
   - Cards/Paper backgrounds become slate (#1E293B)
   - Smooth 0.3s transition animation

**Persistence Test:**
1. Toggle to dark mode
2. Close browser tab
3. Reopen app
4. **Expected:** Dark mode persists (stored in localStorage)

**System Preference Test:**
1. Set OS to dark mode
2. Open OncoLife (first time or clear localStorage)
3. **Expected:** App automatically uses dark mode

### Responsive Design Testing

**Mobile (< 600px):**
- [ ] Bottom navigation bar visible (5 main icons: Chat, Summaries, Diary, Questions, Education)
- [ ] Profile accessible via header avatar/hamburger menu
- [ ] Full-width buttons
- [ ] Chat bubbles properly sized
- [ ] No horizontal scroll

**Tablet (600px - 900px):**
- [ ] Sidebar navigation visible with all 6 items
- [ ] Content area adjusts width
- [ ] Cards stack appropriately

**Desktop (> 900px):**
- [ ] Full sidebar with labels (Symptom Check, Summaries, Diary, Questions, Education, Profile)
- [ ] Dark mode toggle visible in sidebar
- [ ] Spacious content area
- [ ] Hover states work properly

### Navigation Items (All Screen Sizes)

| Icon | Label | Route | Purpose |
|------|-------|-------|---------|
| 💬 | Symptom Check | /chat | Daily symptom checker |
| 📄 | Summaries | /summaries | Past triage summaries |
| 📖 | Diary | /notes | Personal diary/notes |
| ❓ | Questions | /questions | Questions for doctor |
| 📚 | Education | /education | Learning resources |
| 👤 | Profile | /profile | Account settings |

### Symptom Chat UX Testing

**WhatsApp-Style Chat:**
- [ ] Ruby's messages appear on left with avatar
- [ ] Patient's messages appear on right (purple bubble)
- [ ] Smooth scroll to new messages
- [ ] Interactive options are touch-friendly (48px minimum)
- [ ] Selected options show confirmation
- [ ] Emergency symptoms highlighted in red

**Summary Screen:**
- [ ] Triage result color matches severity
- [ ] Action buttons all functional
- [ ] Education content displays correctly
- [ ] Disclaimer always visible

---

## Accessibility Tests

- [ ] Screen reader announces all buttons
- [ ] Text size can be increased
- [ ] Color contrast meets WCAG 2.1 AA (light AND dark mode)
- [ ] Touch targets are 44x44px minimum (48px on mobile)
- [ ] Form labels are associated with inputs
- [ ] Focus states visible for keyboard navigation
- [ ] Reduced motion preference respected

---

## Test Data Checklist

### Before Testing:
- [ ] Test patient account created
- [ ] At least 3 past symptom sessions exist
- [ ] At least 2 diary entries exist
- [ ] At least 1 chemo date logged
- [ ] At least 2 questions created (1 shared, 1 private)

### Test Accounts:
```
Patient 1 (New): newpatient@test.com / TempPass123!
Patient 2 (Active): activepatient@test.com / TestPass123!
```

---

## Bug Reporting Template

```
**Bug Title:** [Short description]

**Environment:**
- Device: [iPhone 13 / Android / Chrome Desktop]
- OS Version: [iOS 17 / Android 14 / Windows 11]
- App Version: [1.0.0]

**Steps to Reproduce:**
1. 
2. 
3. 

**Expected Result:**


**Actual Result:**


**Screenshots/Video:**
[Attach if available]

**Severity:** [Critical / High / Medium / Low]
```

---

## Test Sign-Off

| Test Area | Tester | Date | Pass/Fail |
|-----------|--------|------|-----------|
| Onboarding Flow | | | |
| Symptom Checker | | | |
| Patient Diary | | | |
| Questions | | | |
| Chemo Dates | | | |
| Profile | | | |
| Education | | | |
| History | | | |

---

*Last Updated: January 2026*
*Version: 2.1 - Updated for 7-phase symptom checker with Patient Context, input validation, and Celsius auto-conversion*

