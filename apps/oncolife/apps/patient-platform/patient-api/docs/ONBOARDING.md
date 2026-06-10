# Patient Onboarding System - Complete Documentation

## Overview

The Patient Onboarding System handles the complete patient registration flow from clinic referral to active user. This is a **zero-friction** system where patients do not need to sign up - they are pre-registered based on clinic referrals.

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PATIENT ONBOARDING FLOW                               │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │   CLINIC     │     │   ONCOLIFE   │     │   ONCOLIFE   │     │   PATIENT    │
  │   (EHR)      │────▶│   FAX/OCR    │────▶│   COGNITO    │────▶│   WELCOME    │
  │              │     │   SYSTEM     │     │   + DB       │     │   EMAIL/SMS  │
  └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                        │
                                                                        ▼
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │   ACTIVE     │     │   REMINDER   │     │   TERMS &    │     │   PASSWORD   │
  │   USER       │◀────│   SETUP      │◀────│   PRIVACY    │◀────│   RESET      │
  │   (CHAT)     │     │              │     │   ACCEPT     │     │   (First     │
  └──────────────┘     └──────────────┘     └──────────────┘     │   Login)     │
                                                                 └──────────────┘
```

## Components

### 1. Backend Services

#### Fax Service (`services/fax_service.py`) ⭐ NEW
- **Webhook receiver** for fax providers (Sinch, Twilio, Phaxio, RingCentral)
- **Signature validation** for webhook security
- **Document download** from provider URLs
- **Base64 decoding** for inline document payloads
- **S3 upload** with KMS encryption (HIPAA compliant)
- **Provider-specific payload parsing**

#### OCR Service (`services/ocr_service.py`)
- **AWS Textract** integration for document processing
- Extracts patient demographics, treatment info, medical history
- Supports async processing for multi-page faxes
- Confidence scoring and field validation

#### Notification Service (`services/notification_service.py`)
- **AWS SES** for email notifications
- **AWS SNS** for SMS notifications
- Welcome email with credentials
- Onboarding reminders
- Audit logging

#### Onboarding Service (`services/onboarding_service.py`)
- Main orchestration service
- Manages referral processing pipeline
- Creates Cognito users with temp passwords
- Tracks onboarding progress
- Manual referral entry support

### 2. Database Models (`db/models/referral.py`)

| Table | Description |
|-------|-------------|
| `patient_referrals` | Stores all referral data from clinic faxes |
| `patient_onboarding_status` | Tracks progress through onboarding steps |
| `referral_documents` | S3 references to original fax documents |
| `onboarding_notification_log` | Audit log of all notifications sent |

### 3. API Endpoints (`api/v1/endpoints/onboarding.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/onboarding/webhook/fax` | POST | Receive fax webhook from provider |
| `/onboarding/status` | GET | Get current onboarding status |
| `/onboarding/complete/password` | POST | Mark password step complete |
| `/onboarding/complete/acknowledgement` | POST | Complete medical disclaimer |
| `/onboarding/complete/terms` | POST | Accept terms/privacy |
| `/onboarding/complete/reminders` | POST | Set reminder preferences |
| `/onboarding/referral/manual` | POST | Create manual referral (admin) |
| `/onboarding/referral/{uuid}` | GET | Get referral details (admin) |

### 4. Frontend Components (`patient-web`)

#### OnboardingWizard (`pages/OnboardingPage/OnboardingWizard.tsx`)
- Multi-step wizard with progress indicator
- Step 1: Medical Acknowledgement
- Step 2: Terms & Privacy
- Step 3: Reminder Setup
- Automatic redirect on completion

#### API Services (`api/services/onboarding.ts`)
- Type-safe API client for onboarding endpoints
- Status fetching and step completion

---

## Detailed Flow

### Phase 1: Fax Reception (Complete Flow)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 1: Clinic (EHR) → Dedicated Fax Number                                │
│  - Epic/Cerner sends referral to Oncolife's fax number                      │
│  - AWS is NOT involved yet                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 2: Fax Provider (Sinch) → Digital Conversion                          │
│  - Receives analog fax                                                       │
│  - Converts to PDF/TIFF                                                      │
│  - Triggers webhook when complete                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 3: Webhook → Oncolife API (FastAPI or AWS Lambda)                     │
│  - POST /api/v1/onboarding/webhook/fax                                       │
│  - Validates signature (HMAC-SHA256)                                         │
│  - Downloads document from provider URL                                      │
│  - Or decodes base64 payload                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 4: Upload to S3 (Encrypted)                                           │
│  - Stored in: s3://oncolife-referrals/referrals/YYYY/MM/DD/fax_id.pdf       │
│  - Encrypted with AWS KMS (HIPAA compliant)                                  │
│  - Metadata stored in RDS                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 5: OCR Processing (AWS Textract)                                      │
│  - Extracts text, forms, tables                                              │
│  - Parses patient demographics, treatment info                               │
│  - Confidence scoring per field                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 6: Data Normalization → Patient Record                                │
│  - Structured fields stored in RDS                                           │
│  - Linked to original fax for auditability                                   │
│  - Validation for required fields                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Step 7: Patient Account Creation (Cognito + DB)                            │
│  - Pre-register in AWS Cognito                                               │
│  - Generate temporary password                                               │
│  - Create local DB records                                                   │
│  - Send welcome email/SMS                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Fax Provider Integration Details

#### Supported Providers

| Provider | Webhook URL | Signature Method |
|----------|-------------|------------------|
| **Sinch** (recommended) | `/api/v1/onboarding/webhook/fax/sinch` | HMAC-SHA256 |
| **Twilio** | `/api/v1/onboarding/webhook/fax/twilio` | HMAC-SHA1 |
| **Phaxio** | `/api/v1/onboarding/webhook/fax/phaxio` | HMAC-SHA256 |
| **RingCentral** | `/api/v1/onboarding/webhook/fax/ringcentral` | HMAC-SHA256 |
| **Generic** | `/api/v1/onboarding/webhook/fax` | HMAC-SHA256 |

#### Sinch Webhook Configuration

```
Webhook URL: https://api.oncolife.com/api/v1/onboarding/webhook/fax/sinch
Method: POST
Content-Type: application/json
Headers:
  X-Webhook-Signature: <HMAC-SHA256 of body>
```

#### Twilio Webhook Configuration

```
Webhook URL: https://api.oncolife.com/api/v1/onboarding/webhook/fax/twilio
Method: POST
Content-Type: application/x-www-form-urlencoded
Headers:
  X-Twilio-Signature: <HMAC-SHA1 signature>
```

### Phase 2: OCR Processing

1. **AWS Textract** processes the document
2. **Form fields** are extracted (see complete list below)
3. **Validation** checks for required fields
4. **Confidence scoring** applied to each field
5. **Low confidence fields** flagged for manual review

---

## Complete OCR Field Extraction

### Data Flow: Fax → Normalized Tables

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      OCR DATA NORMALIZATION FLOW                             │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────┐
  │   Fax Document  │
  │   (PDF/TIFF)    │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐      ┌─────────────────────────────────────────────────┐
  │  AWS Textract   │────▶ │            fax_ingestion_log                    │
  │  (OCR Engine)   │      │  - Fax metadata, S3 location, processing status │
  └────────┬────────┘      └─────────────────────────────────────────────────┘
           │
           ▼
  ┌─────────────────┐      ┌─────────────────────────────────────────────────┐
  │  Field Parser   │────▶ │           ocr_field_confidence                  │
  │  + Confidence   │      │  - Per-field confidence scores & review status  │
  └────────┬────────┘      └─────────────────────────────────────────────────┘
           │
           ▼
  ┌─────────────────┐      ┌─────────────────────────────────────────────────┐
  │  Normalization  │────▶ │           patient_referrals                     │
  │  Service        │      │  - Raw intake data (complete OCR output)        │
  └────────┬────────┘      └─────────────────────────────────────────────────┘
           │
           ├────────────────────────────────────────────────────────────────┐
           │                                                                │
           ▼                                                                ▼
  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────────────┐
  │    providers    │      │   patient_info  │      │    oncology_profiles    │
  │                 │      │                 │      │                         │
  │ - Physician     │      │ - Name, DOB     │      │ - Cancer diagnosis      │
  │ - Clinic        │      │ - Email, Phone  │      │ - Treatment plan        │
  │ - NPI           │      │ - Emergency Ctc │      │ - Chemo schedule        │
  │ - Address       │      └─────────────────┘      │ - Biomarkers            │
  └─────────────────┘                               └───────────┬─────────────┘
                                                                │
                                                                ▼
                                                    ┌─────────────────────────┐
                                                    │      medications        │
                                                    │                         │
                                                    │ - Drug names & doses    │
                                                    │ - Category (chemo, etc) │
                                                    │ - Schedule              │
                                                    └─────────────────────────┘
                                                                │
                                                                ▼
                                                    ┌─────────────────────────┐
                                                    │     chemo_schedule      │
                                                    │                         │
                                                    │ - Specific dates        │
                                                    │ - Cycle/day info        │
                                                    │ - Status (ChemoTimeline)│
                                                    └─────────────────────────┘
```

### All Extracted OCR Fields

#### Patient Demographics (Required)

| Field | Table Column | Displayed? | Threshold | Example |
|-------|--------------|------------|-----------|---------|
| First Name | `patient_first_name` | ✅ | 95% | "Test" |
| Last Name | `patient_last_name` | ✅ | 95% | "test" |
| Date of Birth | `patient_dob` | ✅ | 98% | "12/16/1961" |
| Sex | `patient_sex` | ✅ | 95% | "female" |
| Email | `patient_email` | ✅ | 95% | "test@yahoo.com" |
| Phone | `patient_phone` | ✅ | 95% | "503-330-1631" |
| MRN | `patient_mrn` | ❌ Internal | 98% | "12345678" |

#### Physician & Clinic (Normalized to `providers` table)

| Field | Table Column | Displayed? | Threshold | Example |
|-------|--------------|------------|-----------|---------|
| Physician Name | `full_name` | ✅ | 90% | "Abhishek Harshad Patel, MD" |
| NPI | `npi` | ❌ Internal | 98% | "1234567890" |
| Specialty | `specialty` | ❌ Internal | 85% | "Hematology/Oncology" |
| Clinic Name | `clinic_name` | ✅ | 90% | "Arizona Center for Cancer Care" |
| Clinic Address | `clinic_address` | ❌ Internal | 85% | "19646 N. 27th Avenue, Suite 301" |
| Clinic City | `clinic_city` | ❌ Internal | 85% | "Phoenix" |
| Clinic State | `clinic_state` | ❌ Internal | 85% | "AZ" |
| Clinic ZIP | `clinic_zip` | ❌ Internal | 90% | "85027" |
| Phone | `phone` | ✅ | 90% | "623-238-7700" |
| Fax | `fax` | ❌ Internal | 90% | "480-882-5007" |

#### Cancer Diagnosis (Stored in `oncology_profiles`)

| Field | Table Column | Displayed? | Threshold | Example |
|-------|--------------|------------|-----------|---------|
| Cancer Type | `cancer_type` | ✅ | 90% | "Lobular carcinoma of left breast" |
| Cancer Stage | `cancer_stage` | ❌ Hidden | 92% | "IIB" |
| Diagnosis Date | `cancer_diagnosis_date` | ✅ | 95% | "10/20/2025" |
| Histology | `cancer_histology` | ❌ Hidden | 88% | "Invasive Lobular Carcinoma" |
| Grade | `cancer_grade` | ❌ Hidden | 90% | "GX" |
| ICD-10 Code | `cancer_icd10_code` | ❌ Internal | 95% | "C50.912" |
| SNOMED Code | `cancer_snomed_code` | ❌ Internal | 90% | "METASTATIC MALIGNANT NEOPLASM..." |

#### Biomarkers (Stored in `oncology_profiles`)

| Field | Table Column | Displayed? | Threshold | Example |
|-------|--------------|------------|-----------|---------|
| ER Status | `er_status` | ❌ Hidden | 92% | "Positive (+)" or "98%" |
| PR Status | `pr_status` | ❌ Hidden | 92% | "Positive (+)" or "5%" |
| HER2 Status | `her2_status` | ❌ Hidden | 92% | "Negative (-)" |
| Ki-67 | `ki67_percentage` | ❌ Hidden | 90% | "15" (percentage) |
| Oncotype Score | `oncotype_score` | ❌ Hidden | 95% | "25" |

#### AJCC Staging (Stored in `oncology_profiles`)

| Field | Table Column | Displayed? | Threshold | Example |
|-------|--------------|------------|-----------|---------|
| T Category | `ajcc_t_category` | ❌ Hidden | 92% | "cTX" |
| N Category | `ajcc_n_category` | ❌ Hidden | 92% | "cNX" |
| M Category | `ajcc_m_category` | ❌ Hidden | 92% | "cM0" |
| Stage Group | `ajcc_stage_group` | ❌ Hidden | 92% | "IIB" |

#### Treatment Plan (Stored in `oncology_profiles`)

| Field | Table Column | Displayed? | Threshold | Example |
|-------|--------------|------------|-----------|---------|
| Line of Treatment | `line_of_treatment` | ✅ | 88% | "Neoadjuvant" |
| Treatment Goal | `treatment_goal` | ❌ Hidden | 85% | "[No plan goal]" |
| Chemo Plan Name | `chemo_plan_name` | ✅ | 88% | "OP SOC ddAC every 2 weeks f/b PACLitaxel..." |
| Chemo Regimen | `chemo_regimen_description` | ❌ Hidden | 85% | Full regimen text |
| Start Date | `chemo_start_date` | ✅ | 95% | "12/16/2025" |
| End Date | `chemo_end_date` | ✅ | 95% | "4/28/2026" |
| Current Cycle | `current_cycle` | ✅ | 95% | "0" |
| Total Cycles | `total_cycles` | ✅ | 95% | "8" |
| Department | `treatment_department` | ❌ Hidden | 85% | "HonorHealth Cancer Care - Deer Valley Infusion" |
| Status | `treatment_status` | ❌ Internal | 90% | "Active" |

#### Appointments (Stored in `oncology_profiles`)

| Field | Table Column | Displayed? | Threshold | Example |
|-------|--------------|------------|-----------|---------|
| Next Chemo Date | `next_chemo_date` | ✅ ChemoTimeline | 95% | "2026-01-27" |
| Next Clinic Visit | `next_clinic_visit` | ✅ Profile | 90% | "2026-02-01" |
| Last Chemo Date | `last_chemo_date` | ✅ ChemoTimeline | 95% | "2026-01-13" |

#### Medications (Normalized to `medications` table)

| Field | Table Column | Displayed? | Threshold | Example |
|-------|--------------|------------|-----------|---------|
| Drug Name | `medication_name` | ✅ Profile | 90% | "DOXOrubicin (ADRIAMYCIN SOLN)" |
| Generic Name | `generic_name` | ❌ Hidden | 85% | "doxorubicin" |
| Brand Name | `brand_name` | ❌ Hidden | 85% | "ADRIAMYCIN" |
| Category | `category` | ❌ Hidden | 90% | "chemotherapy" |
| Dose | `dose` | ✅ Profile | 92% | "112 mg" |
| Dose per m² | `dose_per_m2` | ❌ Hidden | 90% | "60 mg/m2" |
| Route | `route` | ❌ Hidden | 88% | "IV push" |
| Frequency | `frequency` | ❌ Hidden | 88% | "q2 weeks" |
| Cycle Day | `cycle_day` | ❌ Hidden | 88% | "Day 1" |

**Example Medications Extracted:**

| Drug | Category | Dose | Route | Schedule |
|------|----------|------|-------|----------|
| DOXOrubicin (ADRIAMYCIN) | chemotherapy | 112 mg (60 mg/m2) | IV push | q2 weeks x 4 cycles |
| cyclophosphamide (CYTOXAN) | chemotherapy | 1,120 mg (600 mg/m2) | IV infusion | q2 weeks x 4 cycles |
| PACLitaxel (TaxOL) | chemotherapy | 150 mg (80 mg/m2) | IVPB | Days 1,8,15 q3 weeks |
| letrozole (FEMARA) | hormone_therapy | 2.5 mg | Oral | Daily |
| ribociclib (KISQALI) | targeted_therapy | 600 mg | Oral | Days 1-21 of 28 |

#### Chemo Schedule (Normalized to `chemo_schedule` table)

| Field | Table Column | Displayed? | Threshold | Example |
|-------|--------------|------------|-----------|---------|
| Date | `scheduled_date` | ✅ ChemoTimeline | 95% | "2026-01-13" |
| Time | `scheduled_time` | ❌ Hidden | 85% | "09:00" |
| Cycle | `cycle_number` | ✅ ChemoTimeline | 95% | "3" |
| Day of Cycle | `day_of_cycle` | ❌ Hidden | 90% | "1" |
| Medications | `medications` (JSONB) | ✅ ChemoTimeline | 90% | ["DOXOrubicin", "cyclophosphamide"] |
| Status | `status` | ✅ ChemoTimeline | 95% | "scheduled" |

**Example Schedule from Fax:**

| Date | Cycle | Medications |
|------|-------|-------------|
| 12/16/2025 | 1 | DOXOrubicin, cyclophosphamide |
| 12/30/2025 | 2 | DOXOrubicin, cyclophosphamide |
| 1/13/2026 | 3 | DOXOrubicin, cyclophosphamide |
| 1/27/2026 | 4 | DOXOrubicin, cyclophosphamide |
| 2/10/2026 | 5 | PACLitaxel (Days 1,8,15) |

#### Vitals (Stored in `oncology_profiles`)

| Field | Table Column | Displayed? | Threshold | Example |
|-------|--------------|------------|-----------|---------|
| Height | `height_cm` | ❌ Hidden | 95% | "172.7" (from 5'8") |
| Weight | `weight_kg` | ❌ Hidden | 95% | "73.4" |
| BMI | `bmi` | ❌ Hidden | 95% | "24.61" |
| Blood Pressure | `blood_pressure` (referral) | ❌ Hidden | 90% | "115/58" |
| Pulse | `pulse` (referral) | ❌ Hidden | 90% | "56" |
| Temperature | `temperature_f` (referral) | ❌ Hidden | 90% | "98.0" |
| SpO2 | `spo2` (referral) | ❌ Hidden | 90% | "98" |
| ECOG Status | `ecog_status` | ❌ Hidden | 92% | "0" |

#### Medical History (Stored in `patient_referrals` and `oncology_profiles`)

| Field | Table Column | Displayed? | Threshold | Example |
|-------|--------------|------------|-----------|---------|
| History of Cancer | `history_of_cancer` | ❌ Hidden | 85% | "Lobular carcinoma in situ dx 11/18/21..." |
| Past Medical | `past_medical_history` | ❌ Hidden | 85% | "Abnormal Pap smear, COVID 7/2022..." |
| Past Surgical | `past_surgical_history` | ❌ Hidden | 85% | "Bilateral mastectomy 8/9/22..." |
| Family History | `family_history` (JSONB) | ❌ Hidden | 80% | {"aunt": "breast cancer", ...} |
| Genetic Testing | `genetic_testing` | ❌ Hidden | 88% | "Ambry negative" |
| Allergies | `allergies` | ❌ Hidden | 90% | "No Known Allergies" |

#### Social/Behavioral (Stored in `patient_referrals`)

| Field | Table Column | Displayed? | Threshold | Example |
|-------|--------------|------------|-----------|---------|
| Tobacco Use | `tobacco_use` | ❌ Hidden | 90% | "Never" |
| Alcohol Use | `alcohol_use` | ❌ Hidden | 85% | "2-3 times a week" |
| Drug Use | `drug_use` | ❌ Hidden | 85% | "Never" |
| Social Drivers | `social_drivers` (JSONB) | ❌ Hidden | 80% | Full SDOH data |

---

## OCR Confidence Thresholds

### Threshold Categories

| Category | Auto-Accept | Manual Review | Reject | Description |
|----------|-------------|---------------|--------|-------------|
| **Critical Patient ID** | ≥ 98% | 85-97% | < 85% | Name, DOB - must be accurate |
| **Contact Info** | ≥ 95% | 80-94% | < 80% | Email, Phone - important for login |
| **Physician Info** | ≥ 90% | 75-89% | < 75% | Provider lookup and linking |
| **Diagnosis** | ≥ 90% | 75-89% | < 75% | Cancer type, staging |
| **Treatment Plan** | ≥ 88% | 70-87% | < 70% | Dates, cycles |
| **Medications** | ≥ 90% | 75-89% | < 75% | Drug names, doses |
| **Vitals** | ≥ 95% | 85-94% | < 85% | Numeric values |
| **History** | ≥ 85% | 70-84% | < 70% | Free text fields |

### Manual Review Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MANUAL REVIEW WORKFLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘

  Field Extracted with Low Confidence
           │
           ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Confidence < auto_accept_threshold?                                     │
  │                                                                          │
  │  YES ──────────────────────────────────────────────────────────────────┐ │
  │                                                                         │ │
  │  ┌───────────────────────────────────────────────────────────────────┐ │ │
  │  │  Confidence >= manual_review_threshold?                           │ │ │
  │  │                                                                   │ │ │
  │  │  YES ─────────────────────────────────────────────────────────┐  │ │ │
  │  │                                                                │  │ │ │
  │  │  ┌──────────────────────────────────────────────────────────┐ │  │ │ │
  │  │  │  Status: "requires_review"                               │ │  │ │ │
  │  │  │  - Add to review queue                                   │ │  │ │ │
  │  │  │  - Notify admin (optional)                               │ │  │ │ │
  │  │  │  - Highlight in UI (yellow)                              │ │  │ │ │
  │  │  └──────────────────────────────────────────────────────────┘ │  │ │ │
  │  │                                                                │  │ │ │
  │  │  NO ────────────────────────────────────────────────────────┐ │  │ │ │
  │  │                                                              │ │  │ │ │
  │  │  ┌──────────────────────────────────────────────────────────┐│ │  │ │ │
  │  │  │  Status: "rejected"                                      ││ │  │ │ │
  │  │  │  - Mark field as unusable                                ││ │  │ │ │
  │  │  │  - Require manual entry                                  ││ │  │ │ │
  │  │  │  - Highlight in UI (red)                                 ││ │  │ │ │
  │  │  └──────────────────────────────────────────────────────────┘│ │  │ │ │
  │  └───────────────────────────────────────────────────────────────┘ │ │ │
  │                                                                     │ │ │
  │  NO (auto-accept) ─────────────────────────────────────────────────┘ │ │
  │                                                                       │ │
  │  ┌─────────────────────────────────────────────────────────────────┐ │ │
  │  │  Status: "accepted"                                              │ │ │
  │  │  - Use extracted value directly                                  │ │ │
  │  │  - No human review needed                                        │ │ │
  │  │  - Proceed with normalization                                    │ │ │
  │  └─────────────────────────────────────────────────────────────────┘ │ │
  └──────────────────────────────────────────────────────────────────────┘ │
                                                                            │
                                                                            ▼
                                                         ┌─────────────────────┐
                                                         │  Normalize & Store  │
                                                         │  in target tables   │
                                                         └─────────────────────┘
```

---

## Database Tables (Complete Schema)

### New Tables for OCR/Onboarding

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `fax_ingestion_log` | HIPAA audit trail | fax_id, received_at, ocr_status, s3_key |
| `ocr_field_confidence` | Per-field scores | field_name, confidence_score, status |
| `ocr_confidence_thresholds` | Validation config | field_category, auto_accept_threshold |
| `providers` | Physician/clinic data | full_name, npi, clinic_name |
| `oncology_profiles` | Cancer/treatment | cancer_type, chemo_plan_name, biomarkers |
| `medications` | Normalized drug list | medication_name, category, dose |
| `chemo_schedule` | Appointment dates | scheduled_date, cycle_number, status |

### Migration

Run the new migration:

```bash
cd apps/patient-platform/patient-api
alembic upgrade head
```

Or run the SQL script directly:

```bash
psql -h $DB_HOST -U $DB_USER -d oncolife_patient \
  -f scripts/db/schema_patient_diary_doctor_dashboard.sql
```

---

### Phase 3: Patient Account Creation

1. **Cognito user** created with:
   - Email as username
   - Auto-generated temporary password
   - Email verified flag set
2. **Local DB records** created:
   - `patient_info` - Demographics
   - `patient_configurations` - Settings
   - `patient_physician_associations` - Care team link
   - `patient_onboarding_status` - Progress tracking
3. **Referral** linked to patient account

### Phase 4: Welcome Notification

1. **Email sent** via AWS SES containing:
   - Login URL
   - Username (email)
   - Temporary password
   - Brief explanation
2. **SMS sent** (optional) via AWS SNS:
   - Short welcome message
   - Link to app

### Phase 5: First Login (Mandatory Steps)

#### Step 1: Password Reset
- Cognito forces `NEW_PASSWORD_REQUIRED` challenge
- Patient creates new secure password
- Frontend calls `/onboarding/complete/password`

#### Step 2: Acknowledgement
- Patient reads medical disclaimer
- Must check acknowledgement box
- IP address logged for audit
- Frontend calls `/onboarding/complete/acknowledgement`

#### Step 3: Terms & Privacy
- Must accept Terms & Conditions
- Must accept Privacy Policy
- HIPAA notice acknowledged
- Version numbers stored for compliance
- Frontend calls `/onboarding/complete/terms`

#### Step 4: Reminder Setup
- Choose notification channel (email/SMS/both)
- Set daily reminder time
- Timezone automatically detected
- Frontend calls `/onboarding/complete/reminders`

### Phase 6: Onboarding Complete

1. **Patient is fully activated**
2. **Redirected to Chat screen**
3. **Referral status** updated to `COMPLETED`
4. **Daily reminders** will start based on preference

---

## AWS Services Required

### Cognito
- User Pool for patient authentication
- App client with ADMIN_USER_PASSWORD_AUTH flow
- Temporary password support

### S3
- Bucket for referral document storage
- Lifecycle policies for retention

### Textract
- Document analysis for OCR
- Form and table extraction

### SES
- Verified sender email
- Email templates (optional)

### SNS
- SMS messaging enabled
- Transactional message type

---

## Environment Variables

```env
# AWS Core
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret

# Cognito
COGNITO_USER_POOL_ID=us-west-2_xxxxx
COGNITO_CLIENT_ID=xxxxx
COGNITO_CLIENT_SECRET=xxxxx

# S3
S3_REFERRAL_BUCKET=oncolife-referrals

# SES
SES_SENDER_EMAIL=noreply@oncolife.com
SES_SENDER_NAME=OncoLife Care

# SNS
SNS_ENABLED=true

# Fax Webhook
FAX_WEBHOOK_SECRET=your-webhook-secret

# Onboarding
ONBOARDING_TEMP_PASSWORD_LENGTH=12
TERMS_VERSION=1.0
PRIVACY_VERSION=1.0
```

---

## Database Migration

```sql
-- Create referral tables
CREATE TABLE patient_referrals (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'received',
    status_message TEXT,
    
    -- Source
    fax_number VARCHAR(20),
    fax_received_at TIMESTAMP WITH TIME ZONE,
    
    -- Patient Demographics
    patient_first_name VARCHAR(100),
    patient_last_name VARCHAR(100),
    patient_email VARCHAR(255),
    patient_phone VARCHAR(20),
    patient_dob DATE,
    patient_sex VARCHAR(20),
    patient_mrn VARCHAR(50),
    
    -- Physician
    attending_physician_name VARCHAR(255),
    clinic_name VARCHAR(255),
    
    -- Cancer/Treatment
    cancer_type VARCHAR(255),
    cancer_staging VARCHAR(100),
    chemo_plan_name VARCHAR(500),
    chemo_start_date DATE,
    chemo_end_date DATE,
    chemo_current_cycle INTEGER,
    chemo_total_cycles INTEGER,
    
    -- Vitals
    bmi FLOAT,
    height_cm FLOAT,
    weight_kg FLOAT,
    blood_pressure VARCHAR(20),
    
    -- History
    past_medical_history TEXT,
    past_surgical_history TEXT,
    current_medications JSONB,
    
    -- Raw Data
    raw_extracted_data JSONB,
    extraction_confidence FLOAT,
    fields_needing_review JSONB,
    
    -- Patient Link
    patient_uuid UUID,
    cognito_user_id VARCHAR(100)
);

CREATE TABLE patient_onboarding_status (
    id SERIAL PRIMARY KEY,
    referral_uuid UUID UNIQUE REFERENCES patient_referrals(uuid),
    patient_uuid UUID,
    
    -- Current Step
    current_step VARCHAR(50) NOT NULL DEFAULT 'not_started',
    
    -- Password Reset
    password_reset_completed BOOLEAN DEFAULT FALSE,
    password_reset_at TIMESTAMP WITH TIME ZONE,
    
    -- Acknowledgement
    acknowledgement_completed BOOLEAN DEFAULT FALSE,
    acknowledgement_text TEXT,
    acknowledgement_at TIMESTAMP WITH TIME ZONE,
    acknowledgement_ip VARCHAR(50),
    
    -- Terms & Privacy
    terms_accepted BOOLEAN DEFAULT FALSE,
    terms_version VARCHAR(20),
    terms_accepted_at TIMESTAMP WITH TIME ZONE,
    privacy_accepted BOOLEAN DEFAULT FALSE,
    privacy_version VARCHAR(20),
    privacy_accepted_at TIMESTAMP WITH TIME ZONE,
    hipaa_acknowledged BOOLEAN DEFAULT FALSE,
    
    -- Reminders
    reminder_preference_set BOOLEAN DEFAULT FALSE,
    reminder_channel VARCHAR(20),
    reminder_time VARCHAR(10),
    reminder_timezone VARCHAR(50),
    
    -- Completion
    is_fully_onboarded BOOLEAN DEFAULT FALSE,
    onboarding_completed_at TIMESTAMP WITH TIME ZONE,
    first_login_at TIMESTAMP WITH TIME ZONE,
    
    -- Notifications
    welcome_email_sent BOOLEAN DEFAULT FALSE,
    welcome_email_sent_at TIMESTAMP WITH TIME ZONE,
    welcome_sms_sent BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE referral_documents (
    id SERIAL PRIMARY KEY,
    referral_uuid UUID REFERENCES patient_referrals(uuid),
    s3_bucket VARCHAR(255) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    file_name VARCHAR(255),
    file_type VARCHAR(50),
    page_count INTEGER DEFAULT 1,
    textract_job_id VARCHAR(255),
    raw_ocr_text TEXT,
    ocr_confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE onboarding_notification_log (
    id SERIAL PRIMARY KEY,
    patient_uuid UUID,
    referral_uuid UUID,
    notification_type VARCHAR(50),
    channel VARCHAR(20),
    recipient VARCHAR(255),
    status VARCHAR(20),
    status_message TEXT,
    aws_message_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_referrals_status ON patient_referrals(status);
CREATE INDEX idx_referrals_patient_uuid ON patient_referrals(patient_uuid);
CREATE INDEX idx_onboarding_patient_uuid ON patient_onboarding_status(patient_uuid);
CREATE INDEX idx_notification_log_patient ON onboarding_notification_log(patient_uuid);
```

---

## Testing

### Manual Referral (for testing)

```bash
curl -X POST "http://localhost:8000/api/v1/onboarding/referral/manual" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+15031234567",
    "dob": "1960-05-15",
    "cancer_type": "Breast Cancer",
    "physician_name": "Dr. Smith",
    "send_welcome": true
  }'
```

### Check Onboarding Status

```bash
curl "http://localhost:8000/api/v1/onboarding/status" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Fax Service Integration

### Supported Providers
- Phaxio
- eFax
- RingCentral Fax
- Twilio Fax

### Webhook Payload Example (Phaxio)

```json
{
  "fax_id": "12345678",
  "from_number": "+15551234567",
  "to_number": "+18005551234",
  "received_at": "2026-01-04T12:00:00Z",
  "pages": 3,
  "s3_bucket": "oncolife-referrals",
  "s3_key": "faxes/2026/01/04/12345678.pdf"
}
```

### Webhook Security

Validate incoming requests using HMAC signature:

```python
expected_sig = hmac.new(
    settings.fax_webhook_secret.encode(),
    request_body,
    hashlib.sha256,
).hexdigest()

if not hmac.compare_digest(x_webhook_signature, expected_sig):
    raise HTTPException(status_code=401)
```

---

## Compliance Notes

### HIPAA
- All PHI encrypted in transit (TLS) and at rest (S3, RDS)
- Access logging enabled
- IP addresses logged for legal compliance
- Consent and acceptance timestamps stored

### Data Retention
- Referral documents: 7 years (HIPAA requirement)
- Notification logs: 3 years
- Onboarding status: Indefinite (linked to patient)

---

*Last Updated: January 2026*

