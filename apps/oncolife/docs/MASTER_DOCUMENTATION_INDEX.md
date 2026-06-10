# 📚 OncoLife Master Documentation Index

> **Your single source of truth for all OncoLife documentation.**
> 
> This guide tells you exactly which document to read for any task.

**Version 2.1 | Updated January 2026**

**Developer:** NAVEEN BABU S A

---

## 🚦 Start Here - Quick Navigation

### I want to...

| Goal | Go To | Time |
|------|-------|------|
| **Deploy to AWS for the first time** | [AUTOMATED_DEPLOYMENT_GUIDE.md](AUTOMATED_DEPLOYMENT_GUIDE.md) | 45-60 min |
| **Set up my local development environment** | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | 15-30 min |
| **Understand the system architecture** | [ARCHITECTURE.md](ARCHITECTURE.md) | 20 min read |
| **Fix a deployment error** | [DEPLOYMENT_TROUBLESHOOTING.md](DEPLOYMENT_TROUBLESHOOTING.md) | As needed |
| **Set up CI/CD with GitHub Actions** | [CI_CD_PIPELINE_GUIDE.md](CI_CD_PIPELINE_GUIDE.md) | 30 min |
| **Configure Sinch fax webhook** | [Patient API DEPLOYMENT.md - Step 5](../apps/patient-platform/patient-api/docs/DEPLOYMENT.md#step-5-configure-fax-provider-webhook) | 10 min |
| **Run tests** | [TESTING_AND_CI_GUIDE.md](TESTING_AND_CI_GUIDE.md) | 15 min |
| **Present to executives/stakeholders** | [EXECUTIVE_PRESENTATION.md](EXECUTIVE_PRESENTATION.md) | 10 min read |
| **Train users on the patient app** | [user-manuals/PATIENT_USER_MANUAL.md](user-manuals/PATIENT_USER_MANUAL.md) | Handout |
| **Train users on the doctor app** | [user-manuals/DOCTOR_USER_MANUAL.md](user-manuals/DOCTOR_USER_MANUAL.md) | Handout |

---

## 📋 Complete Documentation Map

### 🔴 Deployment & Infrastructure (DevOps)

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[AUTOMATED_DEPLOYMENT_GUIDE.md](AUTOMATED_DEPLOYMENT_GUIDE.md)** | One-command AWS deployment using scripts | **First-time deployment** - START HERE |
| [STEP_BY_STEP_DEPLOYMENT.md](STEP_BY_STEP_DEPLOYMENT.md) | Manual AWS CLI commands | Learning what each step does, custom deployments |
| [CI_CD_PIPELINE_GUIDE.md](CI_CD_PIPELINE_GUIDE.md) | GitHub Actions setup | Setting up automated deployments after initial setup |
| [DEPLOYMENT_TROUBLESHOOTING.md](DEPLOYMENT_TROUBLESHOOTING.md) | Fix common errors | Something went wrong during deployment |
| [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) | Feature completion checklist | Tracking what's done vs pending |

### 🔵 Development & Architecture

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** | Local setup, code patterns, APIs | **New developer onboarding** |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flow, components | Understanding how everything connects |
| [TESTING_AND_CI_GUIDE.md](TESTING_AND_CI_GUIDE.md) | Running tests, CI pipeline | Writing/running tests |
| [testing/PATIENT_APP_TEST_GUIDE.md](testing/PATIENT_APP_TEST_GUIDE.md) | Patient app testing | Testing patient-specific features |
| [testing/DOCTOR_APP_TEST_GUIDE.md](testing/DOCTOR_APP_TEST_GUIDE.md) | Doctor app testing | Testing doctor-specific features |

### 🟢 Features & API Documentation

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [PATIENT_DIARY_DOCTOR_DASHBOARD.md](PATIENT_DIARY_DOCTOR_DASHBOARD.md) | Diary feature + Doctor analytics | Understanding the diary/dashboard features |
| [Patient API FEATURES.md](../apps/patient-platform/patient-api/docs/FEATURES.md) | All 27 symptom modules | Complete patient API feature reference |
| [Patient API ONBOARDING.md](../apps/patient-platform/patient-api/docs/ONBOARDING.md) | Fax → OCR → Welcome flow | Understanding patient onboarding pipeline |
| [Patient API EDUCATION.md](../apps/patient-platform/patient-api/docs/EDUCATION.md) | Post-session education | Understanding education delivery |
| [Patient API DEPLOYMENT.md](../apps/patient-platform/patient-api/docs/DEPLOYMENT.md) | **Sinch/Fax webhook config** | Configuring external services |
| [Doctor API README.md](../apps/doctor-platform/doctor-api/docs/README.md) | Doctor API overview | Doctor API endpoints |
| [Doctor API DASHBOARD.md](../apps/doctor-platform/doctor-api/docs/DOCTOR_DASHBOARD.md) | Dashboard analytics | Doctor dashboard features |

### 🟡 End-User Documentation

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [EXECUTIVE_PRESENTATION.md](EXECUTIVE_PRESENTATION.md) | High-level overview | Presenting to stakeholders |
| [user-manuals/PATIENT_USER_MANUAL.md](user-manuals/PATIENT_USER_MANUAL.md) | Patient app user guide | Training patients |
| [user-manuals/DOCTOR_USER_MANUAL.md](user-manuals/DOCTOR_USER_MANUAL.md) | Doctor app user guide | Training clinical staff |

---

## 🛠️ AWS Deployment Scripts Reference

All scripts are in `scripts/aws/`:

| Script | Purpose | When to Use |
|--------|---------|-------------|
| **`full-deploy.ps1`** | Complete AWS deployment (PowerShell) | **First-time deployment on Windows** |
| **`full-deploy.sh`** | Complete AWS deployment (Bash) | **First-time deployment on Linux/Mac/Git Bash** |
| `deploy.sh` | Re-deploy after code changes | Updating existing ECS services |
| `cleanup-all.sh` | Delete all AWS resources | Fresh start or teardown |
| `setup-monitoring.sh` | CloudWatch alarms + SNS alerts | Post-deployment monitoring |
| `create-education-bucket.sh` | Create S3 bucket for education PDFs | Setting up education feature |
| `upload-education-pdfs.sh` | Upload education content to S3 | Populating education library |
| `setup-infrastructure.sh` | Partial infrastructure setup | Manual infrastructure creation |
| `cloudwatch-alarms.tf` | Terraform for CloudWatch alarms | Infrastructure-as-code approach |

---

## 🔌 External Service Configuration

### Sinch Fax Webhook Setup

**Full Documentation:** [Patient API DEPLOYMENT.md - Step 5](../apps/patient-platform/patient-api/docs/DEPLOYMENT.md#step-5-configure-fax-provider-webhook)

**Quick Setup:**

1. **Get your deployed Patient API URL** (from ALB DNS or custom domain)
   ```
   https://patient-alb-xxxxx.us-west-2.elb.amazonaws.com
   ```

2. **Log into Sinch Dashboard** → Fax → Numbers → Select your number

3. **Configure webhook:**
   | Field | Value |
   |-------|-------|
   | URL | `https://YOUR_PATIENT_API_URL/api/v1/onboarding/webhook/fax/sinch` |
   | Events | `fax.received` |
   | Secret | Same as `FAX_WEBHOOK_SECRET` in your environment |

4. **Environment Variables Required:**
   ```bash
   FAX_INBOUND_NUMBER=+1-555-YOUR-FAX
   FAX_WEBHOOK_SECRET=your_secret_here
   S3_REFERRAL_BUCKET=oncolife-referrals-ACCOUNT_ID
   ```

**Alternative Providers Supported:**
- Twilio: `/api/v1/onboarding/webhook/fax/twilio`
- Phaxio: `/api/v1/onboarding/webhook/fax/phaxio`
- RingCentral: `/api/v1/onboarding/webhook/fax/ringcentral`

---

## 📊 GitHub Secrets Required for CI/CD

Configure in: **GitHub Repo** → **Settings** → **Secrets and variables** → **Actions**

| Secret | Description | Source |
|--------|-------------|--------|
| `AWS_ACCOUNT_ID` | 12-digit AWS account | AWS Console top-right |
| `AWS_ACCESS_KEY_ID` | IAM user access key | IAM Console |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key | IAM Console |
| `PATIENT_DATABASE_URL` | Patient DB connection | `deployment-config.json` |
| `DOCTOR_DATABASE_URL` | Doctor DB connection | `deployment-config.json` |
| `PATIENT_API_URL` | Patient API endpoint | ALB DNS or custom domain |
| `DOCTOR_API_URL` | Doctor API endpoint | ALB DNS or custom domain |
| `PATIENT_WS_URL` | WebSocket URL | Same as PATIENT_API_URL with `wss://` |

**Full Guide:** [CI_CD_PIPELINE_GUIDE.md - GitHub Secrets](CI_CD_PIPELINE_GUIDE.md#-github-secrets-configuration)

---

## 📁 Repository Structure

```
OncoLife_Monolith/
├── apps/
│   ├── patient-platform/
│   │   ├── patient-api/          # Python FastAPI backend
│   │   │   ├── docs/             # ← Patient API specific docs
│   │   │   │   ├── DEPLOYMENT.md # ← SINCH WEBHOOK CONFIG HERE
│   │   │   │   ├── EDUCATION.md
│   │   │   │   ├── FEATURES.md
│   │   │   │   └── ONBOARDING.md
│   │   │   ├── src/              # Source code
│   │   │   └── tests/            # Unit tests
│   │   ├── patient-server/       # Node.js BFF (optional)
│   │   └── patient-web/          # React frontend
│   └── doctor-platform/
│       ├── doctor-api/           # Python FastAPI backend
│       │   ├── docs/             # ← Doctor API specific docs
│       │   │   ├── DOCTOR_DASHBOARD.md
│       │   │   └── README.md
│       │   ├── src/
│       │   └── tests/
│       └── doctor-web/           # React frontend
├── docs/                         # ← PROJECT-WIDE DOCS (this folder)
│   ├── MASTER_DOCUMENTATION_INDEX.md  # ← YOU ARE HERE
│   ├── AUTOMATED_DEPLOYMENT_GUIDE.md
│   ├── STEP_BY_STEP_DEPLOYMENT.md
│   ├── CI_CD_PIPELINE_GUIDE.md
│   ├── DEPLOYMENT_TROUBLESHOOTING.md
│   ├── DEPLOYMENT_STATUS.md
│   ├── DEVELOPER_GUIDE.md
│   ├── ARCHITECTURE.md
│   ├── TESTING_AND_CI_GUIDE.md
│   ├── PATIENT_DIARY_DOCTOR_DASHBOARD.md
│   ├── EXECUTIVE_PRESENTATION.md
│   ├── testing/
│   │   ├── DOCTOR_APP_TEST_GUIDE.md
│   │   └── PATIENT_APP_TEST_GUIDE.md
│   └── user-manuals/
│       ├── DOCTOR_USER_MANUAL.md
│       └── PATIENT_USER_MANUAL.md
├── packages/                     # Shared packages
├── scripts/
│   ├── aws/                      # AWS deployment scripts
│   │   ├── full-deploy.ps1       # PowerShell full deployment
│   │   ├── full-deploy.sh        # Bash full deployment
│   │   ├── deploy.sh             # Re-deployment script
│   │   ├── cleanup-all.sh        # Delete all resources
│   │   └── setup-monitoring.sh   # CloudWatch setup
│   └── db/                       # Database scripts
├── .github/workflows/            # CI/CD pipelines
│   ├── ci.yml                    # Lint → Test → Build
│   └── deploy.yml                # Build → Push → Deploy
├── docker-compose.yml            # Local development
└── README.md                     # Project overview
```

---

## 📝 Quick Reference Cards

### First-Time Deployment Checklist

```
[ ] 1. Install prerequisites: AWS CLI, Docker, Git
[ ] 2. Configure AWS credentials: aws configure
[ ] 3. Clone repo: git clone https://github.com/nbsaKanasu/Oncolife_Monolith.git
[ ] 4. Run deployment: ./scripts/aws/full-deploy.sh (or .ps1)
[ ] 5. Save deployment-config-*.json output
[ ] 6. Configure Sinch webhook (see above)
[ ] 7. Set up GitHub Secrets for CI/CD
[ ] 8. Run setup-monitoring.sh for alerts
[ ] 9. Test health endpoints
```

### Re-Deployment After Code Changes

```bash
# Option 1: Use deploy script (recommended)
./scripts/aws/deploy.sh

# Option 2: Use GitHub Actions (fully automated)
git push origin main  # Triggers CI, then manually trigger deploy.yml
```

### Cleanup / Start Fresh

```bash
./scripts/aws/cleanup-all.sh
```

---

## 🆘 Getting Help

| Issue | Solution |
|-------|----------|
| Deployment failed | Check [DEPLOYMENT_TROUBLESHOOTING.md](DEPLOYMENT_TROUBLESHOOTING.md) |
| Local dev not working | Check [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |
| Tests failing | Check [TESTING_AND_CI_GUIDE.md](TESTING_AND_CI_GUIDE.md) |
| Need to explain system | Use [EXECUTIVE_PRESENTATION.md](EXECUTIVE_PRESENTATION.md) |
| User training needed | Use user manuals in [user-manuals/](user-manuals/) |

---

## 📅 Document Versions

| Document | Last Updated | Version |
|----------|--------------|---------|
| MASTER_DOCUMENTATION_INDEX.md | January 2026 | 1.0 |
| AUTOMATED_DEPLOYMENT_GUIDE.md | January 2026 | 2.0 |
| All other docs | January 2026 | 1.x |

---

*This master index should be your starting point. If you're unsure which document to read, start here!*
