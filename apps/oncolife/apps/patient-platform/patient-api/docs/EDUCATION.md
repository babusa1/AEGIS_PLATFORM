# Patient Education Module

## Overview

The Patient Education module delivers trusted, clinician-approved education content automatically after every symptom checker session. It is **rule-based, non-AI**, and ensures consistent, traceable information delivery.

## Design Principles

1. **No AI/LLM Generation** - All content is clinician-approved and copied verbatim
2. **Mandatory Disclaimer** - Shown with every education delivery
3. **Care Team Handout** - Always included in every response
4. **Full Audit Trail** - Every delivery is logged for compliance
5. **Immutable Summaries** - Patient summaries cannot be modified after generation

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Symptom        │ -> │  Education      │ -> │  Frontend       │
│  Checker        │    │  Service        │    │  Rendering      │
│  Engine         │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                      │                      │
        v                      v                      v
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Rule            │    │  S3 Documents   │    │  Chat UI        │
│ Evaluations     │    │  (KMS encrypted)│    │  Education Tab  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Database Schema

### Core Tables

```sql
-- Symptom Catalog
CREATE TABLE symptoms (
    code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    category VARCHAR(100),
    active BOOLEAN DEFAULT true
);

-- Education Documents (Critical - prevents hallucination)
CREATE TABLE education_documents (
    id UUID PRIMARY KEY,
    symptom_code VARCHAR(20) REFERENCES symptoms(code),
    title VARCHAR(255),
    inline_text TEXT NOT NULL,
    s3_pdf_path TEXT,
    source_document_id VARCHAR(100) NOT NULL,
    version INTEGER,
    approved_by VARCHAR(255),
    approved_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    priority INTEGER DEFAULT 0
);

-- Mandatory Disclaimer
CREATE TABLE disclaimers (
    id VARCHAR(50) PRIMARY KEY,
    text TEXT NOT NULL,
    active BOOLEAN DEFAULT true
);
```

### Audit Tables

```sql
-- Education Delivery Log
CREATE TABLE education_delivery_log (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES symptom_sessions(id),
    education_document_id UUID REFERENCES education_documents(id),
    delivered_at TIMESTAMP DEFAULT now()
);

-- Patient Summaries (Immutable)
CREATE TABLE patient_summaries (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES symptom_sessions(id),
    summary_text TEXT NOT NULL,
    patient_note TEXT,
    locked BOOLEAN DEFAULT true
);
```

## API Endpoints

### Education Delivery

```
POST /api/v1/education/deliver
```

Triggered when symptom checker completes. Returns:
- Education blocks for each symptom
- Care Team Handout (always)
- Mandatory disclaimer

**Request:**
```json
{
  "session_id": "uuid",
  "symptom_codes": ["BLEED-103", "NAUSEA-101"],
  "severity_levels": {"BLEED-103": "moderate", "NAUSEA-101": "mild"},
  "escalation": false
}
```

**Response:**
```json
{
  "educationBlocks": [
    {
      "symptom": "Bleeding",
      "inlineText": "• Report unusual bleeding...",
      "resourceLinks": [
        {"title": "Bleeding Guide", "url": "https://...", "type": "pdf"}
      ]
    }
  ],
  "disclaimer": {
    "id": "STD-DISCLAIMER-001",
    "text": "This information is for education only..."
  }
}
```

### Patient Summary

```
POST /api/v1/education/summary
```

Generate deterministic summary from template (not AI).

**Request:**
```json
{
  "session_id": "uuid",
  "symptoms": [{"code": "NAUSEA-101", "name": "Nausea", "severity": "moderate"}],
  "medications_tried": [{"name": "ondansetron", "effectiveness": "partial"}],
  "escalation": false
}
```

**Response:**
```json
{
  "id": "uuid",
  "summary_text": "You reported nausea (moderate). You tried ondansetron (partial relief). No urgent symptoms were detected.",
  "patient_note": null,
  "locked": true
}
```

### Add Patient Note

```
POST /api/v1/education/summary/{summary_id}/note
```

Add optional patient note (max 300 chars). Does NOT modify system text.

### Education Tab

```
GET /api/v1/education/tab
```

Returns organized education library:
1. My Current Symptoms (last 7 days)
2. Common Chemotherapy Symptoms
3. Care Team Handouts

### Search

```
GET /api/v1/education/search?q=nausea
```

Simple SQL ILIKE search. No embeddings, no NLP.

## Content Rules

### Inline Education (Chat Display)

- **4-6 bullets max**
- **Grade 6-8 reading level**
- **No medication changes**
- **No "why" explanations**
- **Copied verbatim from approved source**

### Resource Links

- Symptom-specific PDF
- Care Team Handout (always included)
- Pre-signed URLs (30 min expiry)

### Mandatory Disclaimer

```
"This information is for education only and does not replace medical advice. 
Always follow instructions from your oncology care team."
```

- Stored once in database
- Cannot be edited by frontend
- Shown with EVERY education response

## Anti-Hallucination Safeguards

### Allowed
- Copy-paste from clinician-approved docs
- Light truncation (character-based only)

### Forbidden
- Paraphrasing
- Sentence recombination
- Multi-document merging
- Any AI/LLM generation

### Engineering Control
Every education block must reference:
```sql
education_documents.source_document_id
```
**If missing → block rendering fails**

## AWS Integration

### S3 Bucket Structure

```
s3://oncolife-education/
├── symptoms/
│   ├── bleeding/
│   │   ├── bleeding_v1.pdf
│   │   └── bleeding_v1.txt
│   ├── nausea/
│   │   ├── nausea_v1.pdf
│   │   └── nausea_v1.txt
├── care-team/
│   ├── care_team_handout_v3.pdf
│   └── care_team_handout_v3.txt
```

### Security
- **Private bucket** - no public access
- **KMS encryption** at rest
- **Pre-signed URLs** for access (HTTPS only, 30 min expiry)
- **CloudTrail** for access logging

## Summary Template System

### Templates

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
    "no_symptoms": (
        "You indicated you are not experiencing any symptoms today. "
        "Continue to monitor how you feel and report any changes."
    ),
}
```

### Example Output

```
You reported nausea (moderate) and fatigue (mild).
You tried ondansetron with partial relief.
No urgent symptoms were detected.
```

## Failure Handling

| Scenario | Behavior |
|----------|----------|
| Missing education doc | Show disclaimer only |
| Missing inline text | Do not render education |
| PDF unavailable | Hide link |
| Metadata mismatch | Fail closed |

## Seeding Data

Run the seed script:

```bash
cd apps/patient-platform/patient-api
python scripts/seed_education_pdfs.py
```

This seeds:
1. Symptom catalog
2. Mandatory disclaimer
3. Care Team Handout
4. Sample education documents

## Frontend Integration

### Post-Session Flow

1. Symptom checker completes
2. Call `POST /api/v1/education/deliver`
3. Render inline education in chat
4. Show "Read more" links
5. Display mandatory disclaimer

### Education Tab

1. Call `GET /api/v1/education/tab`
2. Render sections:
   - My Current Symptoms
   - Common Symptoms
   - Care Team Handouts
3. Track document access

## Provider Portal Integration

Patient summaries are automatically visible to providers:

```sql
SELECT * FROM patient_summaries
WHERE patient_id = :patient_id
ORDER BY created_at DESC;
```

## Compliance Notes

- All education content is clinician-approved
- Full audit trail for every delivery
- Summaries are immutable (locked = true)
- No PHI in logs
- Pre-signed URLs prevent unauthorized access



