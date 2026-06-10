# Education System Setup Guide

This document covers the setup and configuration of the OncoLife Education system, which provides symptom-specific educational PDFs to patients.

## Overview

The Education system consists of:
- **Database tables**: Store metadata for PDFs (title, summary, keywords, file paths)
- **PDF files**: Stored locally in `/static/education/` (dev) or S3 bucket (production)
- **API endpoints**: Serve PDFs with proper URLs based on environment
- **Frontend**: Education page displays resources and opens PDFs

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│  EducationPage.tsx → useEducationPdfs() → /api/v1/education/pdfs│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND API                               │
│  education.py → EducationService._generate_presigned_url()      │
│                                                                  │
│  Development: Returns /static/education/{path}                   │
│  Production:  Returns S3 pre-signed URL (30-min expiry)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PDF STORAGE                                 │
│  Development: apps/patient-platform/patient-api/static/education│
│  Production:  s3://oncolife-education-{account_id}/             │
└─────────────────────────────────────────────────────────────────┘
```

## Setup Steps

### Step 1: Run Database Migrations

```bash
cd apps/patient-platform/patient-api
alembic upgrade head
```

This creates three tables:
- `education_pdfs` - Symptom-specific PDFs
- `education_handbooks` - General handbooks
- `education_regimen_pdfs` - Chemotherapy regimen PDFs

### Step 2: Seed Education Metadata

```bash
cd apps/patient-platform/patient-api
python scripts/seed_education_pdfs.py
```

This populates the database with metadata for all PDFs:
- ~60 symptom PDFs
- 1 handbook
- ~28 regimen PDFs

### Step 3: Verify PDF Files Exist

Ensure PDFs exist in the static folder:
```
apps/patient-platform/patient-api/static/education/
├── symptoms/
│   ├── nausea/
│   ├── fatigue/
│   ├── constipation/
│   └── ... (15+ symptom categories)
├── handbooks/
│   └── chemo_basics_handbook.pdf
└── regimens/
    ├── abvd/
    ├── r_chop/
    └── ... (6 regimens)
```

### Step 4: Start Services

**Backend (port 8000):**
```bash
cd apps/patient-platform/patient-api
uvicorn src.main:app --reload --port 8000
```

**Frontend (port 5173):**
```bash
cd apps/patient-platform/patient-web
npm run dev
```

### Step 5: Test

1. Navigate to `http://localhost:5173`
2. Go to Education page
3. Click "Read PDF" on any resource
4. PDF should open in new tab

## Database Schema

### education_pdfs
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| symptom_code | VARCHAR(50) | e.g., "NAU-203", "FEV-202" |
| symptom_name | VARCHAR(100) | Human-readable name |
| title | VARCHAR(255) | Document title |
| source | VARCHAR(100) | Source org (ACS, NCI, etc.) |
| file_path | VARCHAR(500) | Relative path to PDF |
| summary | TEXT | Brief description |
| keywords | ARRAY | Search keywords |
| display_order | INTEGER | Sort order |
| is_active | BOOLEAN | Active flag |

### education_handbooks
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| title | VARCHAR(255) | Handbook title |
| description | TEXT | Description |
| file_path | VARCHAR(500) | Relative path |
| handbook_type | VARCHAR(50) | general, emergency, etc. |
| display_order | INTEGER | Sort order |
| is_active | BOOLEAN | Active flag |

### education_regimen_pdfs
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| regimen_code | VARCHAR(50) | e.g., "R-CHOP", "FOLFOX" |
| regimen_name | VARCHAR(100) | Full name |
| title | VARCHAR(255) | Document title |
| source | VARCHAR(100) | Source organization |
| file_path | VARCHAR(500) | Relative path |
| document_type | VARCHAR(50) | overview, drug_info, etc. |
| drug_name | VARCHAR(100) | Drug name (if applicable) |
| display_order | INTEGER | Sort order |
| is_active | BOOLEAN | Active flag |

## AWS Production Deployment

### Current Production Resources

| Resource | Value |
|----------|-------|
| S3 Bucket | `oncolife-education-east-296062592436` |
| Region | `us-east-1` |
| PDF Count | 85+ files (symptoms, handbooks, regimens) |
| Patient API | https://doreebziauwxa.cloudfront.net |

### Environment Variables (Set in ECS Task Definition)

```bash
S3_EDUCATION_BUCKET=oncolife-education-east-296062592436
S3_REFERRAL_BUCKET=oncolife-referrals-296062592436
LOCAL_DEV_MODE=true   # For demo mode login bypass
AWS_REGION=us-east-1
```

### S3 Bucket Structure

```
s3://oncolife-education-east-296062592436/
├── symptoms/
│   ├── bleeding/
│   ├── breathing/
│   ├── cognition/
│   ├── constipation/
│   ├── dehydration/
│   ├── diarrhea/
│   ├── emotional/
│   ├── fatigue/
│   ├── fever/
│   ├── hair/
│   ├── headache/
│   ├── mouth/
│   ├── nausea/
│   ├── neutropenia/
│   ├── neuropathy/
│   ├── pain/
│   ├── sexual/
│   ├── skin/
│   ├── sleep/
│   ├── swallowing/
│   ├── swelling/
│   ├── urinary/
│   └── weight/
├── handbooks/
│   └── chemo_basics_handbook.pdf
└── regimens/
    ├── abvd/
    ├── carboplatin/
    ├── chemo-immunotherapy/
    ├── cisplatin-gemcitabine/
    ├── folfox/
    └── r_chop/
```

### Upload PDFs to S3

PDFs are automatically uploaded during `full-deploy.sh`:
```bash
aws s3 sync "$LOCAL_EDUCATION_PATH/symptoms/" "s3://$EDUCATION_BUCKET/symptoms/"
aws s3 sync "$LOCAL_EDUCATION_PATH/handbooks/" "s3://$EDUCATION_BUCKET/handbooks/"
aws s3 sync "$LOCAL_EDUCATION_PATH/regimens/" "s3://$EDUCATION_BUCKET/regimens/"
```

Or manually:
```bash
./scripts/aws/upload-education-pdfs.sh
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/education/pdfs` | GET | Get all active PDFs |
| `/api/v1/education/tab` | GET | Get education tab content |
| `/api/v1/education/search?q=` | GET | Search documents |
| `/api/v1/education/document/{id}` | GET | Get specific document |
| `/api/v1/education/symptoms` | GET | Get symptom catalog |

## Troubleshooting

### PDF not loading locally
1. Check backend is running on port 8000
2. Verify Vite proxy includes `/static`:
   ```typescript
   // vite.config.ts
   proxy: {
     '/static': {
       target: 'http://localhost:8000',
       changeOrigin: true,
     }
   }
   ```

### Wrong PDF paths in database
Re-run the seed script to reset metadata:
```bash
python scripts/seed_education_pdfs.py
```

### S3 URLs not working in production
1. Verify `S3_EDUCATION_BUCKET` env var is set
2. Verify `LOCAL_DEV_MODE=false`
3. Check ECS task role has S3 GetObject permission

## Adding New PDFs

1. **Add PDF file** to appropriate folder in `static/education/`
2. **Add metadata** to `scripts/seed_education_pdfs.py`
3. **Re-run seed script**: `python scripts/seed_education_pdfs.py`
4. **Upload to S3** (for production): `./scripts/aws/upload-education-pdfs.sh`
