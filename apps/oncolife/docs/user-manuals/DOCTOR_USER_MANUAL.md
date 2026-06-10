# OncoLife Physician Dashboard - User Manual

<div align="center">

## Clinical Monitoring & Patient Management Platform

**Version 1.1 | January 2026**

**Developer:** NAVEEN BABU S A

</div>

---

## Welcome to OncoLife Physician Dashboard

OncoLife helps you monitor your oncology patients' symptoms between visits, identify concerning trends early, and improve patient communication—all from one dashboard.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard Overview](#2-dashboard-overview)
3. [Patient List & Prioritization](#3-patient-list--prioritization)
4. [Patient Detail View](#4-patient-detail-view)
5. [Symptom Timeline](#5-symptom-timeline)
6. [Patient Questions](#6-patient-questions)
7. [Patient Diary Access](#7-patient-diary-access)
8. [Alerts & Escalations](#8-alerts--escalations)
9. [Weekly Reports](#9-weekly-reports)
10. [Managing Your Staff](#10-managing-your-staff)
11. [Settings & Support](#11-settings--support)

---

## 1. Getting Started

### Account Creation

Your account is created by your clinic administrator. You will receive:
- A **welcome email** to your work email address
- Your **username** (your email)
- A **temporary password**

### First-Time Login

1. **Go to:** dashboard.oncolife.com
2. **Enter** your email and temporary password
3. **Create** a new secure password:
   ```
   Requirements:
   ✓ Minimum 12 characters
   ✓ Uppercase and lowercase letters
   ✓ At least one number
   ✓ At least one special character
   ```
4. **(Optional)** Set up Multi-Factor Authentication (MFA)
5. **Access** your dashboard

### Security Requirements

| Requirement | Description |
|-------------|-------------|
| Password Expiry | Every 90 days |
| Session Timeout | 30 minutes of inactivity |
| Failed Attempts | Account locks after 5 failures |
| MFA | Required for admin functions |

---

## 2. Dashboard Overview

After logging in, you'll see the main dashboard:

```
┌────────────────────────────────────────────────────────────┐
│ OncoLife Physician Dashboard           Dr. Smith  👤  🔔  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  📊 Patient Overview           Last 7 days ▼              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 🔴 3 Urgent  │ 🟠 5 Severe │ 🟡 12 Moderate │ 🟢 30  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  👥 Patients Requiring Attention                           │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 🔴 Smith, John     | Fever 103°F      | 2 hrs ago   │ │
│  │ 🟠 Johnson, Mary   | Severe nausea    | 5 hrs ago   │ │
│  │ 🟠 Williams, Bob   | Pain 8/10        | 1 day ago   │ │
│  │ 🟡 Davis, Linda    | Moderate fatigue | 1 day ago   │ │
│  │ ...                                                  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ─────────────────────────────────────────────────────────│
│  🏠 Dashboard │ 👥 Patients │ 📈 Reports │ 👤 Staff │ ⚙️ │
└────────────────────────────────────────────────────────────┘
```

### Main Navigation

**Sidebar Menu (Desktop) / Drawer Menu (Mobile):**

| Icon | Menu Item | Route | Description |
|------|-----------|-------|-------------|
| 📊 | Dashboard | /dashboard | Severity-ranked patient list with stats |
| 👥 | Patients | /patients | Full patient list & management |
| 📄 | Weekly Reports | /reports | Generate & view weekly summaries |
| 👤 | Staff | /staff | Manage your nurses, MAs, navigators |

**Clicking a Patient Row Opens:**

| Tab | What You'll See |
|-----|-----------------|
| **Timeline** | Zigzag symptom severity chart over time |
| **Questions** | Patient's shared questions for you |
| **Treatment Events** | Chemo cycles, medication changes |
| **Escalations** | History of red flag alerts |

### Key Metrics

| Metric | Meaning |
|--------|---------|
| 🔴 Urgent | Patients with emergency-level symptoms |
| 🟠 Severe | Patients needing same-day review |
| 🟡 Moderate | Patients to monitor |
| 🟢 Stable | Patients doing well |

---

## 3. Patient List & Prioritization

### Understanding the Patient List

Patients are **automatically sorted** by clinical urgency:

**Sorting Priority:**
1. **Escalations** (red flag symptoms) → Top
2. **Highest severity** in last 7 days → Higher
3. **Most recent activity** → If equal severity

### Patient Row Information

```
┌─────────────────────────────────────────────────────────────┐
│ 🔴 Smith, John          │ Fever 103°F │ Jan 4, 2:30 PM  │ > │
│    Stage IIB Breast     │ ⚠️ Escalated │                 │   │
└─────────────────────────────────────────────────────────────┘
```

| Element | Description |
|---------|-------------|
| 🔴/🟠/🟡/🟢 | Severity badge (highest in period) |
| Patient Name | Click to view details |
| Primary Symptom | Most concerning symptom |
| ⚠️ Escalation Icon | Urgent rule triggered |
| Timestamp | Last check-in time |

### Filtering Options

| Filter | Purpose |
|--------|---------|
| Time Period | 7 days, 14 days, 30 days |
| Severity | Show only Urgent/Severe/etc. |
| Search | Find specific patient by name |

---

## 4. Patient Detail View

Click on any patient to see their complete information:

```
┌────────────────────────────────────────────────────────────┐
│ ← Back       John Smith                    🖨️ Export     │
├────────────────────────────────────────────────────────────┤
│ DOB: 12/16/1961  │  Dx: Breast Cancer  │  Stage: IIB     │
│ Regimen: ddAC → Paclitaxel  │  Cycle: 2 of 8             │
├────────────────────────────────────────────────────────────┤
│  📈 Timeline │ ❓ Questions │ 📓 Diary │ 🔔 Alerts       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  [Content based on selected tab]                          │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Tabs Available

| Tab | Shows |
|-----|-------|
| 📈 Timeline | Symptom severity over time (chart) |
| ❓ Questions | Patient questions shared with you |
| 📓 Diary | System summaries & shared entries |
| 🔔 Alerts | Escalation history |

---

## 5. Symptom Timeline

The timeline visualization helps identify symptom patterns and correlate with treatment.

### Reading the Chart

```
Severity
  4 │        ●───●                    ← Urgent
    │       /     \
  3 │      ●       ●                  ← Severe
    │     /         \    ○
  2 │    ●           ●──○──○          ← Moderate
    │   /                   \
  1 │──●─────────────────────●─       ← Mild
    └──┼────┼────┼────┼────┼────┼──
       1    5    10   15   20   25
                   Days

    ● Nausea   ○ Fatigue   ┃ Chemo Date
```

### Chart Features

| Feature | How to Use |
|---------|------------|
| **Hover** | See exact values and dates |
| **Toggle Symptoms** | Click legend to show/hide lines |
| **Zoom** | Select date range |
| **Treatment Markers** | Vertical dashed lines for chemo dates |

### Treatment Overlay

| Marker | Meaning |
|--------|---------|
| Blue dashed line | Chemo date |
| Orange dashed line | Cycle start |
| Green dashed line | Regimen change |

**Hover** over any marker to see:
- Event type
- Date
- Additional details (drug, cycle number)

---

## 6. Patient Questions

View questions your patients have submitted and chosen to share.

### Viewing Questions

1. Click on a patient
2. Select the **❓ Questions** tab
3. See all shared questions

```
┌────────────────────────────────────────────────────────┐
│ ❓ Patient Questions                                   │
├────────────────────────────────────────────────────────┤
│ ○ Should I take anti-nausea meds before eating?       │
│   Category: Medication  │  Asked: Jan 3, 2026         │
├────────────────────────────────────────────────────────┤
│ ○ Is it normal to feel this tired during week 2?      │
│   Category: Symptom  │  Asked: Jan 2, 2026            │
└────────────────────────────────────────────────────────┘
```

### Important Privacy Note

| You See | You Don't See |
|---------|---------------|
| ✅ Questions marked "Share with Doctor" | ❌ Private questions |
| ✅ Shared diary entries | ❌ Private diary notes |
| ✅ System-generated summaries | ❌ Draft entries |

**Patients control what they share.** Only explicitly shared content is visible.

---

## 7. Patient Diary Access

The diary tab shows patient-reported information.

### What You Can See

1. **System-Generated Summaries**
   - Auto-created after each symptom check-in
   - Contains: symptoms, severity, triage result
   
2. **Shared Diary Entries**
   - Personal notes patient chose to share
   - Marked entries for discussion

### Reading Diary Entries

```
┌────────────────────────────────────────────────────────┐
│ 📓 Patient Diary                                       │
├────────────────────────────────────────────────────────┤
│ Jan 4, 2026 - Daily Check-In Summary                  │
│ ─────────────────────────────────────────────────────  │
│ Symptoms: Nausea (moderate), Fatigue (mild)           │
│ Triage: Monitor closely                               │
│ Patient Note: "Felt better after eating crackers"     │
├────────────────────────────────────────────────────────┤
│ Jan 3, 2026 - Daily Check-In Summary                  │
│ ─────────────────────────────────────────────────────  │
│ Symptoms: Nausea (severe), Fever (mild)              │
│ Triage: Contact care team                             │
│ Patient Note: [No shared note]                        │
└────────────────────────────────────────────────────────┘
```

---

## 8. Alerts & Escalations

Monitor urgent situations that require attention.

### Alert Types

| Alert Level | Trigger | Action Required |
|-------------|---------|-----------------|
| 🔴 Emergency | Fever >103°F with confusion, severe bleeding, chest pain | Immediate contact |
| 🟠 Urgent | Severe symptoms, multiple concerning factors | Same-day review |
| 🟡 Warning | Worsening trends over time | Close monitoring |

### Viewing Alerts

1. From Dashboard: Click **🔔** notification icon
2. From Patient: Select **🔔 Alerts** tab

### Alert Details Include

- Date & time of escalation
- Symptoms that triggered alert
- Severity levels
- Patient's responses
- Actions taken (if any)

---

## 9. Weekly Reports

Generate comprehensive reports for your patient panel.

### Accessing Reports

1. Click **📈 Reports** in navigation
2. Select week range
3. Click **"Generate Report"**

### Report Contents

```
┌────────────────────────────────────────────────────────┐
│ Weekly Report: Dec 28, 2025 - Jan 3, 2026             │
├────────────────────────────────────────────────────────┤
│ SUMMARY                                                │
│ • Total Patients: 50                                   │
│ • Check-ins Completed: 312                             │
│ • Escalations: 5                                       │
│ • Shared Questions: 23                                 │
├────────────────────────────────────────────────────────┤
│ PATIENTS REQUIRING ATTENTION                           │
│ 1. Smith, John - 2 escalations (fever)                │
│ 2. Johnson, Mary - Worsening nausea trend             │
│ 3. Williams, Bob - Shared 4 questions                 │
├────────────────────────────────────────────────────────┤
│ SYMPTOM TRENDS                                         │
│ Most Common: Fatigue (78%), Nausea (65%)              │
│ Improving: Pain (↓15%)                                │
│ Worsening: Nausea (↑8%)                               │
└────────────────────────────────────────────────────────┘
```

### Export Options

| Format | Use Case |
|--------|----------|
| 📄 PDF | Print or share |
| 📊 CSV | Data analysis |

---

## 10. Managing Your Staff

As a physician, you can add staff members (nurses, MAs, navigators) to help monitor your patients.

### Adding a Staff Member

1. Click **👤 Staff** in navigation
2. Click **"+ Add Staff Member"**
3. Enter their information:
   - Email address
   - First name
   - Last name
   - Role: Nurse / MA / Navigator
4. Click **"Send Invite"**

### What Staff Can Do

| Permission | Nurse | MA | Navigator |
|------------|-------|-------|-----------|
| View dashboard | ✅ | ✅ | ✅ |
| View patient details | ✅ | ✅ | ✅ |
| View questions | ✅ | ✅ | ✅ |
| View alerts | ✅ | ✅ | ✅ |
| Generate reports | ❌ | ❌ | ❌ |
| Add other staff | ❌ | ❌ | ❌ |
| Modify patient records | ❌ | ❌ | ❌ |

### Staff Scope

- Staff can **only** see **your** patients
- Staff **cannot** see other physicians' patients
- All staff actions are audit logged

### Managing Existing Staff

1. Go to **👤 Staff**
2. See list of your staff members
3. Click on a staff member to:
   - View their activity
   - Disable their access
   - Remove them

---

## 11. Settings & Support

### Account Settings

Access via **⚙️ Settings** or click your profile icon:

| Setting | Description |
|---------|-------------|
| Change Password | Update your password |
| MFA Settings | Enable/disable two-factor |
| Notification Preferences | Email alerts for escalations |
| Session Settings | Auto-logout timer |
| **Dark Mode** | Toggle light/dark theme |

### Dark Mode 🌙

The physician dashboard supports a dark theme that reduces eye strain during long hours.

**To Enable Dark Mode:**

**On Desktop:**
1. Look at the bottom of the sidebar (left menu)
2. Find "Light Mode" or "Dark Mode" label
3. Click the toggle switch to change

**On Mobile:**
1. Look for the moon/sun icon in the header
2. Tap to toggle between modes

**What Changes in Dark Mode:**
- Background becomes dark navy (#0F172A)
- Cards have slate backgrounds
- Primary color shifts to brighter blue
- Charts adapt for readability
- Tables have dark alternating rows

**Your preference is saved** - it will persist across sessions.

### Getting Help

**Technical Support:**
- Email: support@oncolife.com
- Phone: 1-800-XXX-XXXX
- Hours: Mon-Fri, 8 AM - 6 PM PT

**Training Resources:**
- Video tutorials available in Settings
- Schedule a training session

---

## Quick Reference

### Daily Workflow

```
☐ Log in to dashboard
☐ Review urgent patients (red/orange)
☐ Check new escalations
☐ Review shared questions
☐ Update notes as needed
☐ Generate weekly report (Fridays)
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + /` | Search patients |
| `Esc` | Close modal/panel |
| `←` `→` | Navigate timeline |
| `Ctrl + P` | Print/Export |

### Severity Response Guide

| Color | Patient Status | Suggested Action |
|-------|----------------|------------------|
| 🔴 Red | Emergency symptoms | Contact immediately, document |
| 🟠 Orange | Severe symptoms | Same-day outreach |
| 🟡 Yellow | Moderate symptoms | Review within 48 hours |
| 🟢 Green | Stable | Continue routine monitoring |

---

## Compliance & Security

### HIPAA Compliance

- All data is encrypted in transit and at rest
- Access is role-based and audited
- No PHI in system logs
- Annual security training required

### Audit Trail

All actions are logged:
- Who accessed what patient
- When and from where
- What actions were taken

### Data Access

- You can **only** see your assigned patients
- Cross-physician access is blocked at the database level
- Admin access requires separate authorization

---

## Troubleshooting

### Common Issues

**"Cannot see patient data"**
- Verify you are assigned to this patient
- Check if patient is active in the system
- Contact admin if issue persists

**"Session expired"**
- Re-login with your credentials
- Sessions timeout after 30 minutes of inactivity

**"Report not generating"**
- Check selected date range
- Ensure you have patients in the system
- Try a smaller date range first

**"Staff invite not sending"**
- Verify email address is correct
- Check spam/junk folder
- Contact support if persistent

---

<div align="center">

**Thank you for using OncoLife!**

*Improving patient outcomes through better monitoring.*

Questions? Contact support@oncolife.com

</div>

---

*Version 2.0 | January 2026 - Updated with dark mode support*
*© 2026 OncoLife Health Technologies*

