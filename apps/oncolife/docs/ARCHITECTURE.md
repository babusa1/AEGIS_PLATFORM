# OncoLife Architecture Guide

**Version 2.1 | Updated January 2026**

**Developer:** NAVEEN BABU S A

## Overview

OncoLife is a healthcare platform built with a modular monorepo architecture. This document provides a comprehensive overview of the system architecture, design patterns, and code organization.

---

## Table of Contents

1. [Solution Architecture](#solution-architecture)
2. [AWS Deployment Architecture](#aws-deployment-architecture)
3. [Security Architecture](#security-architecture)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [Backend Architecture](#backend-architecture-patient-api)
6. [Frontend Architecture](#frontend-architecture-patient-web)
7. [Patient Onboarding Architecture](#patient-onboarding-architecture-new)
8. [Symptom Checker Architecture](#symptom-checker-architecture)
9. [Doctor Dashboard Architecture](#doctor-dashboard-architecture)
10. [API Design Patterns](#api-design-patterns)
11. [Database Design](#database-design)
12. [Security](#security)
13. [Configuration](#configuration)

---

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ONCOLIFE PLATFORM ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────────┐
                                    │   CLINIC EHR    │
                                    │  (Epic, etc.)   │
                                    └────────┬────────┘
                                             │ Fax Referral
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                    FAX INTAKE LAYER                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐   │
│  │ Sinch/Twilio│───▶│ Webhook     │───▶│ Fax Service │───▶│ S3 (KMS Encrypted)  │   │
│  │ Fax Provider│    │ Endpoint    │    │ HMAC Valid  │    │ Referral Documents  │   │
│  └─────────────┘    └─────────────┘    └──────┬──────┘    └─────────────────────┘   │
└──────────────────────────────────────────────│───────────────────────────────────────┘
                                               ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                    OCR & ONBOARDING LAYER                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐   │
│  │ AWS Textract│───▶│ OCR Service │───▶│ Confidence  │───▶│ OnboardingService   │   │
│  │ Forms/Tables│    │ Field Parse │    │ Thresholds  │    │ Patient Creation    │   │
│  └─────────────┘    └─────────────┘    └──────┬──────┘    └──────────┬──────────┘   │
│                                               │                       │              │
│                            ┌──────────────────┴───────────────────────┘              │
│                            ▼                                                         │
│                     ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐   │
│                     │Manual Review│    │AWS Cognito  │    │ AWS SES/SNS         │   │
│                     │(if < thresh)│    │Patient Pool │    │ Welcome Email/SMS   │   │
│                     └─────────────┘    └─────────────┘    └─────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────┐              ┌────────────────────────────────┐
│        PATIENT PLATFORM        │              │        DOCTOR PLATFORM         │
│                                │              │                                │
│  ┌──────────────────────────┐  │              │  ┌──────────────────────────┐  │
│  │    Patient Web App       │  │              │  │    Doctor Web App        │  │
│  │    (React + Vite + MUI)  │  │              │  │    (React + Vite + MUI)  │  │
│  │  ┌────────────────────┐  │  │              │  │  ┌────────────────────┐  │  │
│  │  │ Login/Onboarding   │  │  │              │  │  │ Login (MFA)        │  │  │
│  │  │ Symptom Checker    │  │  │              │  │  │ Dashboard          │  │  │
│  │  │ My Diary           │  │  │              │  │  │ Patient Timeline   │  │  │
│  │  │ Questions          │  │  │              │  │  │ Weekly Reports     │  │  │
│  │  │ Education          │  │  │              │  │  │ Staff Management   │  │  │
│  │  │ Profile            │  │  │              │  │  │ Alerts             │  │  │
│  │  └────────────────────┘  │  │              │  │  └────────────────────┘  │  │
│  └────────────┬─────────────┘  │              │  └────────────┬─────────────┘  │
│               │                │              │               │                │
│               ▼                │              │               ▼                │
│  ┌──────────────────────────┐  │              │  ┌──────────────────────────┐  │
│  │    Patient API           │  │              │  │    Doctor API            │  │
│  │    (FastAPI)             │  │              │  │    (FastAPI)             │  │
│  │  ┌────────────────────┐  │  │              │  │  ┌────────────────────┐  │  │
│  │  │ API Layer (v1)     │  │  │              │  │  │ API Layer (v1)     │  │  │
│  │  │  - auth.py         │  │  │              │  │  │  - auth.py         │  │  │
│  │  │  - chat.py         │  │  │              │  │  │  - dashboard.py    │  │  │
│  │  │  - diary.py        │  │  │              │  │  │  - patients.py     │  │  │
│  │  │  - questions.py    │  │  │              │  │  │  - registration.py │  │  │
│  │  │  - education.py    │  │  │              │  │  │  - staff.py        │  │  │
│  │  │  - profile.py      │  │  │              │  │  │  - reports.py      │  │  │
│  │  │  - chemo.py        │  │  │              │  │  │                    │  │  │
│  │  │  - onboarding.py   │  │  │              │  │  └────────────────────┘  │  │
│  │  └────────────────────┘  │  │              │  │  ┌────────────────────┐  │  │
│  │  ┌────────────────────┐  │  │              │  │  │ Service Layer      │  │  │
│  │  │ Service Layer      │  │  │              │  │  │  - DashboardSvc    │  │  │
│  │  │  - AuthService     │  │  │◄────────────►│  │  │  - RegistrationSvc │  │  │
│  │  │  - DiaryService    │  │  │   Cross-DB   │  │  │  - AuditService    │  │  │
│  │  │  - EducationSvc    │  │  │   Queries    │  │  │  - PatientService  │  │  │
│  │  │  - ProfileService  │  │  │              │  │  │  - ReportService   │  │  │
│  │  │  - ChemoService    │  │  │              │  │  └────────────────────┘  │  │
│  │  │  - OnboardingSvc   │  │  │              │  │  ┌────────────────────┐  │  │
│  │  │  - SymptomEngine   │  │  │              │  │  │ Repository Layer   │  │  │
│  │  └────────────────────┘  │  │              │  │  │  - StaffRepo       │  │  │
│  │  ┌────────────────────┐  │  │              │  │  │  - StaffRepo       │  │  │
│  │  │ Repository Layer   │  │  │              │  │  │  - ClinicRepo      │  │  │
│  │  │  - DiaryRepo       │  │  │              │  │  └────────────────────┘  │  │
│  │  │  - SummaryRepo     │  │  │              │  └──────────────────────────┘  │
│  │  │  - ConversationRepo│  │  │              │                                │
│  │  └────────────────────┘  │  │              └────────────────────────────────┘
│  └──────────────────────────┘  │
│                                │
└────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATA LAYER                                         │
│                                                                                       │
│  ┌─────────────────────────────────────────┐  ┌─────────────────────────────────┐   │
│  │         PATIENT DATABASE (RDS)          │  │     DOCTOR DATABASE (RDS)       │   │
│  │                                         │  │                                 │   │
│  │  ┌─────────────┐  ┌─────────────────┐  │  │  ┌─────────────┐  ┌───────────┐ │   │
│  │  │patient_info │  │conversations    │  │  │  │staff_profiles│ │audit_logs │ │   │
│  │  │providers    │  │messages         │  │  │  │staff_assoc  │  │clinics    │ │   │
│  │  │oncology_prof│  │diary_entries    │  │  │  │physician_rep│  │           │ │   │
│  │  │medications  │  │patient_questions│  │  │  └─────────────┘  └───────────┘ │   │
│  │  │referrals    │  │education_docs   │  │  │                                 │   │
│  │  │fax_logs     │  │disclaimers      │  │  │  Queries patient_db for:        │   │
│  │  │ocr_confid   │  │chemo_dates      │  │  │  - Symptom data                 │   │
│  │  └─────────────┘  └─────────────────┘  │  │  - Timeline charts              │   │
│  │                                         │  │  - Weekly reports               │   │
│  └─────────────────────────────────────────┘  └─────────────────────────────────┘   │
│                                                                                       │
│  ┌─────────────────────────────────────────┐  ┌─────────────────────────────────┐   │
│  │         AWS S3 BUCKETS                  │  │     AWS COGNITO                 │   │
│  │                                         │  │                                 │   │
│  │  oncolife-referrals/                    │  │  Patient User Pool              │   │
│  │    └── faxes/{year}/{month}/{id}.pdf   │  │   - Email/Phone login           │   │
│  │                                         │  │   - Temp password flow          │   │
│  │  oncolife-education/                    │  │                                 │   │
│  │    └── symptoms/{code}/{file}.pdf      │  │  Physician User Pool            │   │
│  │    └── handouts/care_team_v1.pdf       │  │   - Admin-created accounts      │   │
│  │                                         │  │   - MFA enabled                 │   │
│  │  (All KMS Encrypted)                    │  │   - Role attributes             │   │
│  └─────────────────────────────────────────┘  └─────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    SYMPTOM CHECKER ENGINE (5 Phases)                            │
│                                                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                          │
│  │DISCLAIMER│─▶│EMERGENCY │─▶│ SYMPTOM  │─▶│  RUBY    │─▶│ SUMMARY  │                          │
│  │  Phase   │  │  CHECK   │  │ SELECTION│  │  CHAT    │  │  PHASE   │                          │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘                          │
│                                                    │                                            │
│  Note: Patient context (chemo dates, physician    ▼                                            │
│  visit) is now stored in Profile page, not here.                                               │
│                        ┌─────────────────────────────────────────────────────────────────────┐ │
│                        │                    27 SYMPTOM MODULES with INPUT VALIDATION          │ │
│                        │  FEV-202  NAU-203  DIA-205  CON-210  SKI-212  ...                    │ │
│                        │  Validates: Temp (°F/°C), BP (120/80), HR (BPM), O2%, Days, etc.    │ │
│                        └─────────────────────────────────────────────────────────────────────┘ │
│                                                            │                                    │
│                                                            ▼                                    │
│  ┌────────────────┐   ┌────────────────┐   ┌────────────────┐   ┌────────────────┐            │
│  │ Triage Result  │   │ Education      │   │ Diary Entry    │   │ Patient        │            │
│  │ (Color Badge)  │   │ Delivery       │   │ Auto-populate  │   │ Summary        │            │
│  └────────────────┘   └────────────────┘   └────────────────┘   └────────────────┘            │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## AWS Deployment Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                           AWS DEPLOYMENT ARCHITECTURE                                 │
│                                  (us-east-1)                                         │
└──────────────────────────────────────────────────────────────────────────────────────┘

                                 ┌─────────────┐
                                 │   Route 53  │
                                 │   DNS       │
                                 └──────┬──────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
                    ▼                                       ▼
           ┌───────────────┐                       ┌───────────────┐
           │ app.oncolife  │                       │doctor.oncolife│
           │    .com       │                       │    .com       │
           └───────┬───────┘                       └───────┬───────┘
                   │                                       │
                   ▼                                       ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              VPC (10.0.0.0/16)                                        │
│                                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                         PUBLIC SUBNETS (10.0.1.0/24, 10.0.2.0/24)               │ │
│  │                                                                                  │ │
│  │  ┌────────────────────────────────┐    ┌────────────────────────────────────┐  │ │
│  │  │     Application Load Balancer  │    │     Application Load Balancer      │  │ │
│  │  │         (Patient ALB)          │    │         (Doctor ALB)               │  │ │
│  │  │                                │    │                                    │  │ │
│  │  │  Listeners:                    │    │  Listeners:                        │  │ │
│  │  │   - HTTPS:443 → Patient TG     │    │   - HTTPS:443 → Doctor TG          │  │ │
│  │  │   - HTTP:80 → Redirect 443     │    │   - HTTP:80 → Redirect 443         │  │ │
│  │  │                                │    │                                    │  │ │
│  │  │  Health Check: /health         │    │  Health Check: /health             │  │ │
│  │  └────────────────────────────────┘    └────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                   │                                       │                          │
│                   ▼                                       ▼                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                        PRIVATE SUBNETS (10.0.3.0/24, 10.0.4.0/24)              │ │
│  │                                                                                  │ │
│  │  ┌──────────────────────────────────────────────────────────────────────────┐  │ │
│  │  │                         ECS CLUSTER (Fargate)                            │  │ │
│  │  │                                                                          │  │ │
│  │  │  ┌────────────────────────┐        ┌────────────────────────┐           │  │ │
│  │  │  │   Patient API Service  │        │   Doctor API Service   │           │  │ │
│  │  │  │                        │        │                        │           │  │ │
│  │  │  │  Tasks: 2 (min)        │        │  Tasks: 2 (min)        │           │  │ │
│  │  │  │  CPU: 512              │        │  CPU: 512              │           │  │ │
│  │  │  │  Memory: 1024MB        │        │  Memory: 1024MB        │           │  │ │
│  │  │  │  Port: 8000            │        │  Port: 8001            │           │  │ │
│  │  │  │                        │        │                        │           │  │ │
│  │  │  │  Image: ECR/patient-api│        │  Image: ECR/doctor-api │           │  │ │
│  │  │  └────────────────────────┘        └────────────────────────┘           │  │ │
│  │  │                                                                          │  │ │
│  │  │  ┌────────────────────────┐        ┌────────────────────────┐           │  │ │
│  │  │  │  Patient Web Service   │        │   Doctor Web Service   │           │  │ │
│  │  │  │  (Static via S3/CF)    │        │  (Static via S3/CF)    │           │  │ │
│  │  │  └────────────────────────┘        └────────────────────────┘           │  │ │
│  │  └──────────────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                                  │ │
│  │                   │                              │                               │ │
│  │                   ▼                              ▼                               │ │
│  │  ┌──────────────────────────────────────────────────────────────────────────┐  │ │
│  │  │                              RDS (PostgreSQL)                             │  │ │
│  │  │                                                                          │  │ │
│  │  │  ┌────────────────────────┐        ┌────────────────────────┐           │  │ │
│  │  │  │   oncolife-patient-db  │        │   oncolife-doctor-db   │           │  │ │
│  │  │  │                        │        │                        │           │  │ │
│  │  │  │  Instance: db.t3.medium│        │  Instance: db.t3.medium│           │  │ │
│  │  │  │  Storage: 100GB GP3    │        │  Storage: 50GB GP3     │           │  │ │
│  │  │  │  Multi-AZ: Yes         │        │  Multi-AZ: Yes         │           │  │ │
│  │  │  │  Encrypted: KMS        │        │  Encrypted: KMS        │           │  │ │
│  │  │  │                        │        │                        │           │  │ │
│  │  │  │  Port: 5432            │        │  Port: 5432            │           │  │ │
│  │  │  └────────────────────────┘        └────────────────────────┘           │  │ │
│  │  └──────────────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                       │
└──────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              AWS SERVICES (Outside VPC)                               │
│                                                                                       │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐ │
│  │  AWS Cognito   │  │    AWS S3      │  │  AWS Textract  │  │  Secrets Manager   │ │
│  │                │  │                │  │                │  │                    │ │
│  │ Patient Pool   │  │ oncolife-      │  │ OCR Processing │  │ Database creds     │ │
│  │ Doctor Pool    │  │  referrals/    │  │ Forms + Tables │  │ Cognito secrets    │ │
│  │                │  │ oncolife-      │  │                │  │ API keys           │ │
│  │ JWT Tokens     │  │  education/    │  │                │  │                    │ │
│  └────────────────┘  └────────────────┘  └────────────────┘  └────────────────────┘ │
│                                                                                       │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐ │
│  │    AWS SES     │  │    AWS SNS     │  │  CloudWatch    │  │    CloudTrail      │ │
│  │                │  │                │  │                │  │                    │ │
│  │ Welcome emails │  │ SMS notifs     │  │ Logs           │  │ Audit trail        │ │
│  │ Invites        │  │ Reminders      │  │ Metrics        │  │ API logging        │ │
│  │ Reminders      │  │                │  │ Alarms         │  │ (No PHI)           │ │
│  └────────────────┘  └────────────────┘  └────────────────┘  └────────────────────┘ │
│                                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │                                  ECR                                            │ │
│  │                                                                                 │ │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐    │ │
│  │  │ oncolife-patient-api│  │ oncolife-doctor-api │  │ (future: web images)│    │ │
│  │  │ :latest, :v1.0.0    │  │ :latest, :v1.0.0    │  │                     │    │ │
│  │  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘    │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Security Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              SECURITY ARCHITECTURE                                    │
└──────────────────────────────────────────────────────────────────────────────────────┘

                              INTERNET
                                  │
                                  ▼
                         ┌───────────────┐
                         │   WAF Rules   │  ← Rate limiting, SQL injection protection
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │  CloudFront   │  ← DDoS protection, SSL/TLS termination
                         └───────┬───────┘
                                 │
          ┌──────────────────────┴──────────────────────┐
          │                                              │
          ▼                                              ▼
┌─────────────────────┐                      ┌─────────────────────┐
│   Patient ALB       │                      │   Doctor ALB        │
│   (HTTPS only)      │                      │   (HTTPS only)      │
│                     │                      │                     │
│   Security Group:   │                      │   Security Group:   │
│   - Inbound: 443    │                      │   - Inbound: 443    │
│   - Outbound: 8000  │                      │   - Outbound: 8001  │
└──────────┬──────────┘                      └──────────┬──────────┘
           │                                            │
           ▼                                            ▼
┌─────────────────────┐                      ┌─────────────────────┐
│   ECS Tasks         │                      │   ECS Tasks         │
│                     │                      │                     │
│   Security Group:   │                      │   Security Group:   │
│   - Inbound: 8000   │                      │   - Inbound: 8001   │
│     from ALB SG     │                      │     from ALB SG     │
│   - Outbound: 5432  │                      │   - Outbound: 5432  │
│     to RDS SG       │                      │     to RDS SG       │
└──────────┬──────────┘                      └──────────┬──────────┘
           │                                            │
           └──────────────────┬─────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   RDS PostgreSQL    │
                    │                     │
                    │   Security Group:   │
                    │   - Inbound: 5432   │
                    │     from ECS SG     │
                    │   - No public access│
                    │                     │
                    │   Encryption:       │
                    │   - At rest: KMS    │
                    │   - In transit: SSL │
                    └─────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA PROTECTION                                          │
│                                                                                       │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐                    │
│  │  At Rest        │   │  In Transit     │   │  Access Control │                    │
│  │                 │   │                 │   │                 │                    │
│  │  - RDS: KMS     │   │  - HTTPS/TLS 1.2│   │  - Cognito JWT  │                    │
│  │  - S3: KMS      │   │  - RDS: SSL     │   │  - IAM Roles    │                    │
│  │  - EBS: KMS     │   │  - Internal VPC │   │  - SG Rules     │                    │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘                    │
│                                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                           HIPAA COMPLIANCE                                       │ │
│  │                                                                                  │ │
│  │  ✓ PHI encrypted at rest and in transit                                        │ │
│  │  ✓ No PHI in CloudWatch logs (configured)                                      │ │
│  │  ✓ Audit trail via CloudTrail                                                  │ │
│  │  ✓ Access logging for S3 buckets                                               │ │
│  │  ✓ Database-level access control (physician scoping)                           │ │
│  │  ✓ MFA for administrative access                                               │ │
│  │  ✓ BAA signed with AWS                                                         │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### Patient Onboarding Flow

```
Clinic EHR → Fax → Sinch → Webhook → S3 → Textract → OCR Service
                                                          │
                    ┌─────────────────────────────────────┘
                    ▼
            ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
            │ Confidence    │────▶│ Patient       │────▶│ Cognito       │
            │ Check         │     │ Record        │     │ Account       │
            │ (≥ thresholds)│     │ Creation      │     │ Creation      │
            └───────────────┘     └───────────────┘     └───────────────┘
                    │                                           │
                    ▼                                           ▼
            ┌───────────────┐                           ┌───────────────┐
            │ Manual Review │                           │ Welcome Email │
            │ (if < thresh) │                           │ + SMS via SES │
            └───────────────┘                           └───────────────┘
```

### Daily Symptom Check-In Flow

```
Patient App → WebSocket → Symptom Engine → Questions → Triage Logic
                                                            │
                    ┌───────────────────────────────────────┘
                    │
                    ├──▶ Conversation Record (patient_db)
                    │
                    ├──▶ Diary Auto-Populate
                    │
                    ├──▶ Education Delivery
                    │
                    └──▶ Summary Generation
```

### Doctor Dashboard Flow

```
Doctor Login → Cognito Auth → JWT Token
                                  │
                                  ▼
                    ┌───────────────────────────────────────┐
                    │         DashboardService              │
                    │                                       │
                    │  1. Get physician's patient list      │
                    │  2. Query symptom data (patient_db)   │
                    │  3. Calculate severity rankings       │
                    │  4. Return sorted patient list        │
                    └───────────────────────────────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────────────────┐
                    │         Audit Logging                 │
                    │  (Every access logged to audit_logs)  │
                    └───────────────────────────────────────┘
```

---

## System Overview (Simple View)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│  ┌─────────────────────────┐         ┌─────────────────────────┐           │
│  │     Patient Web (React) │         │     Doctor Web (React)  │           │
│  │     Port: 5173          │         │     Port: 5174          │           │
│  └───────────┬─────────────┘         └───────────┬─────────────┘           │
│              │                                    │                         │
│              │ HTTP/WebSocket                     │ HTTP                    │
│              ▼                                    ▼                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                              API LAYER                                       │
│  ┌─────────────────────────┐         ┌─────────────────────────┐           │
│  │   Patient API (FastAPI) │         │   Doctor API (FastAPI)  │           │
│  │   Port: 8000            │         │   Port: 8001            │           │
│  │   /api/v1/*             │         │   /api/v1/*             │           │
│  └───────────┬─────────────┘         └───────────┬─────────────┘           │
│              │                                    │                         │
│              ▼                                    ▼                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                           DATABASE LAYER                                     │
│  ┌─────────────────────────┐         ┌─────────────────────────┐           │
│  │   Patient Database      │◄────────│   Doctor Database       │           │
│  │   (PostgreSQL)          │ read    │   (PostgreSQL)          │           │
│  │   - patient_info        │ only    │   - staff_profiles      │           │
│  │   - conversations       │         │   - all_clinics         │           │
│  │   - diary_entries       │         │   - staff_associations  │           │
│  │   - chemo_dates         │         │   - audit_logs          │           │
│  └─────────────────────────┘         └─────────────────────────┘           │
├─────────────────────────────────────────────────────────────────────────────┤
│                         EXTERNAL SERVICES                                    │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                   │
│  │     AWS Cognito         │  │    Fax Provider         │                   │
│  │  Authentication         │  │  (Sinch/Twilio)         │                   │
│  └─────────────────────────┘  └─────────────────────────┘                   │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                   │
│  │     AWS Textract        │  │     AWS SES/SNS         │                   │
│  │     (OCR)               │  │  (Email/SMS)            │                   │
│  └─────────────────────────┘  └─────────────────────────┘                   │
│  ┌─────────────────────────┐                                                │
│  │     AWS S3              │  Document Storage (KMS Encrypted)              │
│  └─────────────────────────┘                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Backend Architecture (Patient API)

### Layered Architecture

```
┌─────────────────────────────────────────────┐
│              API Layer (api/v1/)            │
│  Routes, Request/Response handling          │
│  - auth.py, chat.py, diary.py, etc.        │
├─────────────────────────────────────────────┤
│            Service Layer (services/)         │
│  Business logic, orchestration              │
│  - AuthService, ChatService, etc.           │
├─────────────────────────────────────────────┤
│          Repository Layer (db/repositories/) │
│  Data access, queries                       │
│  - PatientRepository, ConversationRepo      │
├─────────────────────────────────────────────┤
│            Database Layer (db/models/)       │
│  ORM models, schema                         │
│  - PatientInfo, Conversations, Messages     │
└─────────────────────────────────────────────┘
```

### Directory Structure

```
patient-api/src/
├── main.py                      # FastAPI application entry point
│
├── core/                        # Core infrastructure
│   ├── __init__.py
│   ├── config.py               # Pydantic settings (env vars)
│   ├── exceptions.py           # Custom exception classes
│   ├── logging.py              # Structured logging setup
│   └── middleware/             # Request middleware
│       ├── __init__.py
│       ├── correlation_id.py   # Request tracing
│       ├── error_handler.py    # Global exception handling
│       └── request_logging.py  # Request/response logging
│
├── db/                          # Database layer
│   ├── __init__.py
│   ├── base.py                 # SQLAlchemy Base, TimestampMixin
│   ├── session.py              # Database session management
│   ├── patient_models.py       # Legacy models (still used)
│   ├── doctor_models.py        # Doctor DB models (read-only)
│   ├── models/                 # New modular models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── patient.py
│   │   ├── conversation.py
│   │   └── medical.py
│   └── repositories/           # Data access layer
│       ├── __init__.py
│       ├── base.py             # Generic CRUD repository
│       ├── patient_repository.py
│       ├── conversation_repository.py
│       ├── chemo_repository.py
│       ├── diary_repository.py
│       ├── summary_repository.py
│       └── profile_repository.py
│
├── services/                    # Business logic layer
│   ├── __init__.py
│   ├── base.py                 # Base service class
│   ├── auth_service.py         # Cognito authentication
│   ├── chat_service.py         # Symptom checker chat
│   ├── chemo_service.py        # Chemotherapy tracking
│   ├── diary_service.py        # Diary entries
│   ├── summary_service.py      # Conversation summaries
│   ├── profile_service.py      # Patient profiles
│   ├── patient_service.py      # Patient operations
│   │
│   │ # Patient Onboarding Services (NEW)
│   ├── fax_service.py          # Fax webhook reception & S3 upload
│   ├── ocr_service.py          # AWS Textract OCR processing
│   ├── notification_service.py # AWS SES/SNS email & SMS
│   └── onboarding_service.py   # Main orchestration service
│
├── api/                         # API layer (versioned)
│   ├── __init__.py
│   ├── deps.py                 # FastAPI dependencies
│   └── v1/
│       ├── __init__.py
│       ├── router.py           # Main v1 router
│       └── endpoints/
│           ├── __init__.py
│           ├── auth.py         # POST /auth/login, /signup
│           ├── onboarding.py   # POST /onboarding/webhook/fax, status, complete/*
│           ├── chat.py         # GET/POST /chat/*, WS /chat/ws/*
│           ├── chemo.py        # POST /chemo/log, GET /chemo/history
│           ├── diary.py        # CRUD /diary/*
│           ├── summaries.py    # GET /summaries/*
│           ├── profile.py      # GET/PATCH /profile/*
│           ├── patients.py     # Patient management
│           └── health.py       # Health checks
│
└── routers/                     # Symptom Checker Engine
    └── chat/
        └── symptom_checker/
            ├── __init__.py
            ├── constants.py            # Triage levels, message types
            ├── symptom_definitions.py  # 27 symptom modules
            └── symptom_engine.py       # State machine engine
```

---

## Frontend Architecture (Patient Web)

### Directory Structure

```
patient-web/src/
├── main.tsx                     # React entry point
├── App.tsx                      # Root component with routing
│
├── api/                         # Type-safe API layer
│   ├── index.ts                # Main exports
│   ├── client.ts               # HTTP client with interceptors
│   ├── types.ts                # TypeScript type definitions
│   └── services/               # Domain-specific API calls
│       ├── index.ts
│       ├── auth.ts             # Authentication API
│       ├── chat.ts             # Chat + WebSocket API
│       ├── chemo.ts            # Chemotherapy API
│       ├── diary.ts            # Diary API
│       ├── profile.ts          # Profile API
│       └── summaries.ts        # Summaries API
│
├── config/                      # Configuration
│   └── api.ts                  # API endpoints config
│
├── context/                     # React Context providers
│   ├── index.ts
│   └── AuthContext.tsx         # Authentication state
│
├── hooks/                       # Custom React hooks
│   ├── index.ts
│   ├── useAuth.ts              # Authentication hook
│   ├── useChat.ts              # Chat/WebSocket hook
│   └── useApi.ts               # Generic API hook
│
├── components/                  # React components
│   ├── common/                 # Shared components
│   │   ├── index.ts
│   │   ├── ErrorBoundary.tsx   # Error handling
│   │   └── ErrorBoundary.css
│   └── chat/                   # Chat-specific components
│       ├── SymptomChat.css
│       └── SymptomMessageBubble.tsx
│
├── pages/                       # Page components (React Router routes)
│   ├── ChatsPage/               # /chat - Symptom checker (5-phase flow)
│   │   ├── ChatsPage.tsx
│   │   └── SymptomChatPage.tsx
│   ├── SummariesPage/           # /summaries - Past triage results
│   ├── NotesPage/               # /notes - Personal health diary
│   ├── QuestionsPage/           # /questions - Questions for doctor
│   │   ├── QuestionsPage.tsx
│   │   └── QuestionsPage.styles.ts
│   ├── EducationPage/           # /education - Learning resources
│   ├── ProfilePage/             # /profile - Account settings
│   ├── LoginPage/               # /login - Authentication
│   └── OnboardingPage/          # First-time setup wizard
│
├── services/                    # API service hooks
│   ├── questions.ts             # Questions CRUD hooks
│   ├── notes.ts                 # Diary CRUD hooks
│   ├── summaries.ts             # Summaries fetch hooks
│   └── chatService.ts           # WebSocket service
│
└── utils/                       # Utility functions
    └── apiClient.ts             # Axios instance with interceptors
```

### State Management Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                     AuthProvider (Context)                       │
│  - isAuthenticated, user, login(), logout()                     │
├─────────────────────────────────────────────────────────────────┤
│                          App Component                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     ErrorBoundary                           ││
│  │  ┌───────────────────────────────────────────────────────┐  ││
│  │  │                    Router                             │  ││
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │  ││
│  │  │  │  LoginPage  │ │  ChatsPage  │ │  Other Pages    │ │  ││
│  │  │  │             │ │  useChat()  │ │  useApi()       │ │  ││
│  │  │  └─────────────┘ └─────────────┘ └─────────────────┘ │  ││
│  │  └───────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture (Doctor Web)

### Directory Structure

```
doctor-web/src/
├── main.tsx                     # React entry point
├── App.tsx                      # Root component with routing
│
├── config/                      # Configuration
│   └── api.ts                   # API endpoints config
│
├── contexts/                    # React Context providers
│   ├── AuthContext.tsx          # Authentication state
│   └── UserContext.tsx          # User profile state
│
├── components/                  # React components
│   └── Layout.tsx               # Sidebar navigation, responsive
│
├── pages/                       # Page components (React Router routes)
│   ├── Dashboard/               # /dashboard - Severity-ranked patient list
│   │   ├── DashboardPage.tsx    # Stats cards + patient list
│   │   └── index.tsx
│   ├── Patients/                # /patients - Patient management
│   │   ├── PatientsPage.tsx
│   │   └── components/          # Add/Edit modals
│   ├── PatientDetail/           # /patients/:uuid - Patient timeline view
│   │   └── PatientDetailPage.tsx # Zigzag chart, questions, treatment events
│   ├── Reports/                 # /reports - Weekly physician reports
│   │   └── ReportsPage.tsx      # Week selector, stats, patient table
│   ├── Staff/                   # /staff - Staff management
│   └── LoginPage/               # /login - Authentication
│
├── services/                    # API service hooks
│   ├── dashboard.ts             # Dashboard + timeline + reports hooks
│   ├── patients.ts              # Patient CRUD hooks
│   ├── staff.ts                 # Staff CRUD hooks
│   └── login.ts                 # Auth hooks
│
└── utils/                       # Utility functions
    └── apiClient.ts             # Axios instance with interceptors
```

### Doctor Web Routes

| Route | Component | Purpose |
|-------|-----------|---------|
| /login | LoginPage | Physician/Staff authentication |
| /dashboard | DashboardPage | Severity-ranked patient list with stats |
| /patients | PatientsPage | Full patient list with CRUD |
| /patients/:uuid | PatientDetailPage | Timeline, questions, treatment events |
| /reports | ReportsPage | Weekly summaries and generation |
| /staff | StaffPage | Manage nurses, MAs, navigators |

---

## Patient Onboarding Architecture (NEW)

### Zero-Friction Onboarding Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PATIENT ONBOARDING PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
  │ CLINIC  │───▶│ FAX PROVIDER │───▶│  WEBHOOK    │───▶│  S3 UPLOAD  │
  │ (Epic)  │    │   (Sinch)    │    │ /fax/sinch  │    │ (KMS Enc.)  │
  └─────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                              │
                                                              ▼
  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
  │  WELCOME    │◀───│   COGNITO   │◀───│    DB       │◀───│  TEXTRACT   │
  │  EMAIL/SMS  │    │   Account   │    │   Store     │    │   (OCR)     │
  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
        │
        ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                    FIRST LOGIN ONBOARDING WIZARD                         │
  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
  │  │  PASSWORD   │─▶│   MEDICAL   │─▶│   TERMS &   │─▶│  REMINDER   │    │
  │  │   RESET     │  │ ACKNOWLEDGE │  │   PRIVACY   │  │   SETUP     │    │
  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
  └─────────────────────────────────────────────────────────────────────────┘
```

### AWS Services Used

| Service | Purpose | HIPAA |
|---------|---------|-------|
| **S3** | Store referral documents | ✅ KMS encrypted |
| **Textract** | OCR for fax documents | ✅ HIPAA eligible |
| **Cognito** | User authentication | ✅ HIPAA eligible |
| **SES** | Welcome/reminder emails | ✅ HIPAA eligible |
| **SNS** | SMS notifications | ✅ HIPAA eligible |

### Data Extracted from Referrals

| Category | Fields |
|----------|--------|
| **Patient** | Name, DOB, Email, Phone, MRN, Sex |
| **Physician** | Name, NPI, Clinic |
| **Diagnosis** | Cancer type, Staging, Date |
| **Treatment** | Chemo regimen, Start/End dates, Cycles |
| **History** | Medical, Surgical, Medications |
| **Vitals** | Height, Weight, BMI, BP, Pulse |

### Onboarding Database Tables

| Table | Description |
|-------|-------------|
| `patient_referrals` | All referral data from clinic faxes |
| `patient_onboarding_status` | Progress through onboarding steps |
| `referral_documents` | S3 references to fax documents |
| `onboarding_notification_log` | Audit trail of emails/SMS |

See [ONBOARDING.md](../apps/patient-platform/patient-api/docs/ONBOARDING.md) for complete documentation.

---

## Symptom Checker Architecture

### 27 Symptom Modules

| Category | Modules |
|----------|---------|
| **Emergency (5)** | Trouble Breathing, Chest Pain, Bleeding/Bruising, Fainting, Altered Mental Status |
| **Common Side Effects (5)** | Fever, Dehydration, Nausea, Vomiting, Diarrhea |
| **Pain (7)** | Pain Router, Port/IV Site, Headache, Abdominal, Leg/Calf, Joint/Muscle, Neuropathy |
| **Other (10)** | Constipation, Fatigue, Eye Complaints, Mouth Sores, No Appetite, Urinary Problems, Skin Rash, Swelling, Cough, Falls & Balance |

### State Machine Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   GREETING  │────►│  SYMPTOM    │────►│  SCREENING  │────►│  FOLLOW-UP  │
│             │     │  SELECTION  │     │  QUESTIONS  │     │  QUESTIONS  │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                   │
                    ┌─────────────────────────────────────────────┘
                    ▼
              ┌─────────────┐     ┌─────────────┐
              │   TRIAGE    │────►│  COMPLETE   │
              │  EVALUATION │     │             │
              └─────────────┘     └─────────────┘

Triage Levels:
- call_911: Emergency - immediate action required
- notify_care_team: Alert - care team notification
- none: Monitor - continue observation
```

---

## Doctor Dashboard Architecture

### Analytics-Driven Clinical Monitoring

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              DOCTOR DASHBOARD ARCHITECTURE                            │
└──────────────────────────────────────────────────────────────────────────────────────┘

                         ┌────────────────────────────────────┐
                         │         Doctor Web App              │
                         │                                     │
                         │  ┌─────────────────────────────┐   │
                         │  │    Dashboard Landing View    │   │
                         │  │    (Severity-Ranked List)    │   │
                         │  └─────────────────────────────┘   │
                         │  ┌─────────────────────────────┐   │
                         │  │    Patient Detail View       │   │
                         │  │    (Symptom Timeline)        │   │
                         │  └─────────────────────────────┘   │
                         │  ┌─────────────────────────────┐   │
                         │  │    Weekly Reports            │   │
                         │  │    Staff Management          │   │
                         │  └─────────────────────────────┘   │
                         └───────────────┬────────────────────┘
                                         │
                                         ▼
                         ┌────────────────────────────────────┐
                         │         Doctor API (FastAPI)        │
                         │                                     │
                         │  ┌─────────────────────────────┐   │
                         │  │     DashboardService         │   │
                         │  │                              │   │
                         │  │  get_ranked_patient_list()  │   │
                         │  │  get_patient_timeline()      │   │
                         │  │  get_shared_questions()      │   │
                         │  │  get_weekly_report()         │   │
                         │  └─────────────────────────────┘   │
                         │  ┌─────────────────────────────┐   │
                         │  │     RegistrationService      │   │
                         │  │     AuditService             │   │
                         │  └─────────────────────────────┘   │
                         └───────────────┬────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    │                                         │
                    ▼                                         ▼
         ┌─────────────────────┐               ┌─────────────────────┐
         │   Doctor Database    │               │   Patient Database   │
         │                      │               │   (Read-Only Access) │
         │  - staff_profiles    │               │                      │
         │  - audit_logs        │               │  - conversations     │
         │  - staff_associations│               │  - severity_list     │
         │  - clinics           │               │  - patient_questions │
         └─────────────────────┘               │  - diary_entries     │
                                               └─────────────────────┘
```

### Patient Ranking Algorithm

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           SEVERITY RANKING ALGORITHM                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘

Input: All patients assigned to physician
Period: Last 7 days (configurable)

SORT ORDER:
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                                                                    │
│  Priority 1: has_escalation = TRUE         → TOP OF LIST                          │
│              (conversation_state = 'EMERGENCY')                                    │
│                                                                                    │
│  Priority 2: max_severity (highest wins)                                          │
│              urgent (4) > severe (3) > moderate (2) > mild (1)                    │
│                                                                                    │
│  Priority 3: last_checkin (most recent wins)                                      │
│              If equal severity, sort by activity                                   │
│                                                                                    │
└───────────────────────────────────────────────────────────────────────────────────┘

OUTPUT:
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  🔴 Smith, John      │ Fever 103°F + Confusion   │ 2 hrs ago  │ ← has_escalation   │
│  🟠 Johnson, Mary    │ Severe nausea             │ 5 hrs ago  │ ← max_severity=3   │
│  🟠 Williams, Bob    │ Pain 8/10                 │ 1 day ago  │ ← max_severity=3   │
│  🟡 Davis, Linda     │ Moderate fatigue          │ 1 day ago  │ ← max_severity=2   │
│  🟢 Brown, Mike      │ Mild headache             │ 3 days ago │ ← max_severity=1   │
└─────────────────────────────────────────────────────────────────────────────────────┘

Color Mapping:
  🔴 Red    = urgent (4)   = Emergency symptoms
  🟠 Orange = severe (3)   = Needs same-day review
  🟡 Yellow = moderate (2) = Monitor closely
  🟢 Green  = mild (1)     = Stable
```

### Symptom Timeline Data Structure

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           TIMELINE DATA FOR CHARTING                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘

API Response: GET /api/v1/dashboard/patient/{uuid}

{
  "patient_uuid": "abc-123",
  "period_days": 30,
  
  "symptom_series": {
    "nausea": [
      {"date": "2026-01-01", "severity": "moderate", "severity_numeric": 2},
      {"date": "2026-01-03", "severity": "mild",     "severity_numeric": 1},
      {"date": "2026-01-05", "severity": "severe",   "severity_numeric": 3}
    ],
    "fatigue": [
      {"date": "2026-01-02", "severity": "severe",   "severity_numeric": 3},
      {"date": "2026-01-04", "severity": "moderate", "severity_numeric": 2}
    ]
  },
  
  "treatment_events": [
    {"event_type": "chemo_date", "event_date": "2026-01-01", "metadata": {}},
    {"event_type": "chemo_date", "event_date": "2026-01-15", "metadata": {}}
  ]
}

CHART VISUALIZATION:

Severity
   4 │        ●───●                    ← Urgent
     │       /     \
   3 │      ●       ●                  ← Severe  (nausea peak)
     │     /         \    ○
   2 │    ●           ●──○──○          ← Moderate (fatigue)
     │   /                   \
   1 │──●─────────────────────●─       ← Mild
     └──┼────┼────┼────┼────┼────┼──
        1    5    10   15   20   25
                    Days

     ● Nausea   ○ Fatigue   ┃ Chemo Date (vertical marker)
```

### Access Control Model

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           PHYSICIAN-SCOPED ACCESS CONTROL                            │
└─────────────────────────────────────────────────────────────────────────────────────┘

ROLES:
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  ADMIN           │ Create physicians, Manage clinics          │ System-wide        │
│  PHYSICIAN       │ View own patients, Create staff, Reports   │ Own patients only  │
│  STAFF (Nurse/MA)│ View dashboard, Flag concerns              │ Physician's patients│
└─────────────────────────────────────────────────────────────────────────────────────┘

ENFORCEMENT:
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                      │
│  Doctor A logs in                                                                    │
│       │                                                                              │
│       ▼                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  1. Extract physician_id from JWT token                                      │   │
│  │  2. Query: SELECT patient_uuid FROM associations WHERE physician = :id       │   │
│  │  3. Only return data for those patients                                      │   │
│  │                                                                               │   │
│  │  RESULT: Doctor A sees ONLY Doctor A's patients                              │   │
│  │          No cross-physician data access possible                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  Staff of Doctor A logs in                                                           │
│       │                                                                              │
│       ▼                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  1. Extract staff_id from JWT, lookup physician_uuid                         │   │
│  │  2. Query: Uses physician's patient list                                     │   │
│  │  3. Staff inherits physician's patient scope                                 │   │
│  │                                                                               │   │
│  │  RESULT: Staff sees same patients as their physician                         │   │
│  │          Cannot create staff, modify records, or reassign                     │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## API Design Patterns

### Endpoint Naming Convention

```
/api/v1/{resource}              # Collection (GET list, POST create)
/api/v1/{resource}/{uuid}       # Instance (GET, PATCH, DELETE)
/api/v1/{resource}/{uuid}/{sub} # Sub-resource
```

### Request/Response Pattern

```python
# Request Models (Pydantic)
class CreateDiaryRequest(BaseModel):
    title: Optional[str]
    diary_entry: str
    marked_for_doctor: bool = False

# Response Models
class DiaryEntryResponse(BaseModel):
    entry_uuid: UUID
    title: Optional[str]
    diary_entry: str
    created_at: datetime
    
    class Config:
        from_attributes = True
```

### Error Handling

```python
# Custom Exceptions (core/exceptions.py)
class NotFoundError(AppError):
    """Resource not found."""
    def __init__(self, message: str):
        super().__init__(message, status_code=404)

class AuthorizationError(AppError):
    """User not authorized."""
    def __init__(self, message: str):
        super().__init__(message, status_code=403)

# Usage in endpoints
@router.get("/{uuid}")
async def get_resource(uuid: UUID):
    resource = service.get_by_uuid(uuid)
    if not resource:
        raise NotFoundError(f"Resource {uuid} not found")
    return resource
```

---

## Database Design

### Patient Database Tables - Core

| Table | Description |
|-------|-------------|
| `patient_info` | Patient profiles (name, email, DOB, emergency contacts) |
| `patient_configurations` | Patient settings (reminders, consent, timezone) |
| `patient_physician_associations` | Patient-doctor relationships |
| `patient_diary_entries` | Health journal entries with mood/symptoms |
| `patient_chemo_dates` | Legacy chemotherapy date tracking |
| `conversations` | Chat sessions with triage level |
| `messages` | Chat messages with metadata |
| `patient_questions` | "Questions for Doctor" feature |
| `education_content` | Symptom-linked educational materials |

### Patient Database Tables - Onboarding & OCR

| Table | Description |
|-------|-------------|
| `patient_referrals` | Complete OCR output from fax referrals |
| `referral_documents` | S3 references to original fax PDFs |
| `patient_onboarding_status` | Progress through onboarding wizard |
| `onboarding_notification_log` | Email/SMS audit trail |

### Patient Database Tables - Normalized OCR Data (NEW)

| Table | Description |
|-------|-------------|
| `providers` | Normalized physician/clinic data (NPI, address, contact) |
| `oncology_profiles` | Cancer diagnosis, biomarkers, treatment plan, chemo timeline |
| `medications` | Normalized medication list (chemotherapy, supportive, etc.) |
| `chemo_schedule` | Specific chemotherapy appointment dates for ChemoTimeline |
| `fax_ingestion_log` | HIPAA audit trail for all fax receptions |
| `ocr_field_confidence` | Per-field OCR accuracy scores for quality assurance |
| `ocr_confidence_thresholds` | Configuration for auto-accept/manual-review thresholds |

### Doctor Database Tables - Core

| Table | Description |
|-------|-------------|
| `staff_profiles` | Doctor/nurse profiles (role, specialty) |
| `all_clinics` | Healthcare facilities (address, contact) |
| `staff_associations` | Staff-clinic relationships |

### Doctor Database Tables - Analytics & Reporting

| Table | Description |
|-------|-------------|
| `symptom_time_series` | Time-series symptom data for clinical analytics |
| `treatment_events` | Chemo cycle events for timeline overlays |
| `physician_reports` | Weekly report metadata and S3 paths |
| `audit_logs` | HIPAA-compliant access logging |

### Database Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PATIENT DATABASE ENTITY RELATIONSHIPS                     │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌────────────────────────┐
                    │    fax_ingestion_log   │
                    │  (HIPAA Audit Trail)   │
                    └───────────┬────────────┘
                                │ 1:N
                                ▼
        ┌───────────────────────────────────────────────────────────┐
        │                  ocr_field_confidence                      │
        │        (Per-field scores for all extracted fields)         │
        └───────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         patient_referrals (Raw OCR Data)                     │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
            ┌────────────────────────┼────────────────────────┐
            │                        │                        │
            ▼                        ▼                        ▼
   ┌────────────────┐      ┌────────────────┐       ┌────────────────┐
   │   providers    │      │  patient_info  │       │referral_docs   │
   │                │      │                │       │  (S3 Links)    │
   │ - full_name    │      │ - name, email  │       └────────────────┘
   │ - npi          │      │ - dob, phone   │
   │ - clinic_name  │      │ - emergency_   │
   │ - address      │      │   contact_*    │
   └───────┬────────┘      └───────┬────────┘
           │ 1:N                   │ 1:1
           ▼                       ▼
   ┌────────────────────────────────────────────────────────────────┐
   │                      oncology_profiles                          │
   │                                                                 │
   │  - cancer_type, stage, grade, histology                         │
   │  - er_status, pr_status, her2_status, oncotype_score            │
   │  - chemo_plan_name, chemo_start_date, chemo_end_date            │
   │  - current_cycle, total_cycles                                  │
   │  - next_chemo_date, next_clinic_visit, last_chemo_date          │
   │  - bmi, height_cm, weight_kg, ecog_status                       │
   │  - history_of_cancer, past_medical_history, past_surgical_history│
   └───────────────────────────────┬────────────────────────────────┘
                                   │ 1:N
                                   ▼
                    ┌──────────────────────────────────┐
                    │           medications             │
                    │                                  │
                    │  - medication_name               │
                    │  - category (chemotherapy, etc.) │
                    │  - dose, route, frequency        │
                    │  - cycle_day, cycles_planned     │
                    └────────────────┬─────────────────┘
                                     │
                                     ▼
                    ┌──────────────────────────────────┐
                    │        chemo_schedule            │
                    │       (ChemoTimeline UI)         │
                    │                                  │
                    │  - scheduled_date                │
                    │  - cycle_number, day_of_cycle    │
                    │  - medications (JSONB array)     │
                    │  - status (scheduled/completed)  │
                    └──────────────────────────────────┘

   ┌───────────────────────────────────────────────────────────────┐
   │  DOCTOR DB: Queries patient_db for cross-database analytics  │
   │  - symptom_time_series: Patient symptom trends over time     │
   │  - treatment_events: Chemo cycle markers for timeline        │
   │  - physician_reports: Weekly summary PDFs (S3)               │
   │  - audit_logs: All PHI access logged for HIPAA               │
   └───────────────────────────────────────────────────────────────┘
```

---

## Security

### Authentication Flow

```
1. User enters email/password
2. Frontend calls POST /api/v1/auth/login
3. Backend validates with AWS Cognito
4. Cognito returns JWT tokens
5. Frontend stores access_token in localStorage
6. Frontend includes token in Authorization header
7. Backend validates token on each request
```

### Authorization

```python
# Dependency injection for protected routes
@router.get("/protected")
async def protected_endpoint(
    current_user: TokenData = Depends(get_current_user)
):
    # current_user.sub = user UUID
    return {"user_id": current_user.sub}
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | development/staging/production | development |
| `DEBUG` | Enable debug mode | false |
| `LOG_LEVEL` | Logging level | INFO |
| `POSTGRES_HOST` | Database host | localhost |
| `POSTGRES_PORT` | Database port | 5432 |
| `POSTGRES_USER` | Database user | - |
| `POSTGRES_PASSWORD` | Database password | - |
| `POSTGRES_PATIENT_DB` | Patient database name | - |
| `POSTGRES_DOCTOR_DB` | Doctor database name | - |
| `AWS_REGION` | AWS region | us-west-2 |
| `COGNITO_USER_POOL_ID` | Cognito user pool | - |
| `COGNITO_CLIENT_ID` | Cognito client ID | - |
| `CORS_ORIGINS` | Allowed origins | - |

### Onboarding-Specific Variables (NEW)

| Variable | Description | Default |
|----------|-------------|---------|
| `S3_REFERRAL_BUCKET` | S3 bucket for fax documents | oncolife-referrals |
| `SES_SENDER_EMAIL` | Email sender address | noreply@oncolife.com |
| `SES_SENDER_NAME` | Email sender display name | OncoLife Care |
| `SNS_ENABLED` | Enable SMS notifications | true |
| `FAX_WEBHOOK_SECRET` | HMAC secret for webhook validation | - |
| `TERMS_VERSION` | Current terms version | 1.0 |
| `PRIVACY_VERSION` | Current privacy policy version | 1.0 |

---

## Related Documentation

- [Features Documentation](apps/patient-platform/patient-api/docs/FEATURES.md)
- [Deployment Guide](apps/patient-platform/patient-api/docs/DEPLOYMENT.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)

---

## Architecture Diagrams Summary

| Diagram | Description |
|---------|-------------|
| **Solution Architecture** | Complete platform overview with all components |
| **AWS Deployment Architecture** | Infrastructure diagram with VPC, ECS, RDS, etc. |
| **Security Architecture** | Network security, encryption, HIPAA compliance |
| **Data Flow Diagrams** | How data moves through onboarding, symptom checker, and dashboard |
| **Doctor Dashboard Architecture** | Analytics engine, ranking algorithm, access control |

---

*Last Updated: January 2026*
*Version: 2.0 - Added comprehensive architecture diagrams*

