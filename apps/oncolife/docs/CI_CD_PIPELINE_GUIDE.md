# OncoLife - CI/CD Pipeline Guide

## Overview

This guide explains how the Continuous Integration (CI) and Continuous Deployment (CD) pipelines work for the OncoLife platform, and how to integrate them with your AWS deployment.

---

## 🔄 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              YOUR WORKFLOW                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1️⃣  DEVELOPER PUSHES CODE TO GITHUB                                        │
│      git add -A && git commit -m "feature" && git push                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
    ┌───────────────────────────┐   ┌───────────────────────────────────────┐
    │  2️⃣  CI WORKFLOW (AUTO)    │   │  3️⃣  DEPLOY WORKFLOW (MANUAL)         │
    │      .github/workflows/    │   │      .github/workflows/               │
    │      ci.yml                │   │      deploy.yml                       │
    │      Runs on EVERY push    │   │      Run from GitHub Actions tab      │
    └───────────────────────────┘   └───────────────────────────────────────┘
                │                                   │
                ▼                                   ▼
    ┌───────────────────────────┐   ┌───────────────────────────────────────┐
    │  • Lint Python & TS       │   │  • Build Docker images                │
    │  • Run unit tests         │   │  • Push to AWS ECR                    │
    │  • Build Docker images    │   │  • Run DB migrations                  │
    │    (validation only)      │   │  • Update ECS services                │
    │  • ✅ Pass / ❌ Fail       │   │  • Wait for healthy deployment        │
    └───────────────────────────┘   └───────────────────────────────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────────────┐
                                    │  4️⃣  LIVE ON AWS!                       │
                                    │  • Patient API updated                 │
                                    │  • Doctor API updated                  │
                                    │  • Web apps updated                    │
                                    └───────────────────────────────────────┘
```

---

## 📁 Workflow Files

| File | Purpose | Trigger |
|------|---------|---------|
| `.github/workflows/ci.yml` | Continuous Integration | Auto on push/PR |
| `.github/workflows/deploy.yml` | Continuous Deployment | Manual trigger |

---

## 1️⃣ CI Workflow (Automatic)

### What It Does

The CI workflow runs automatically on every push to `main` or `develop` branches, and on all pull requests.

```yaml
# Trigger conditions
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
```

### CI Jobs

| Job | Description | Duration |
|-----|-------------|----------|
| **Lint** | Checks code quality (Python: ruff, black; TypeScript: ESLint) | ~2 min |
| **Test Patient API** | Runs pytest for Patient API | ~3 min |
| **Test Doctor API** | Runs pytest for Doctor API | ~3 min |
| **Build** | Builds all Docker images (validation) | ~5 min |
| **CI Complete** | Summary status check | ~10 sec |

### CI Flow Diagram

```
┌──────────┐
│   Lint   │
└────┬─────┘
     │
     ├──────────────────────┐
     ▼                      ▼
┌─────────────────┐  ┌─────────────────┐
│ Test Patient API│  │ Test Doctor API │
└────────┬────────┘  └────────┬────────┘
         │                    │
         └──────────┬─────────┘
                    ▼
             ┌────────────┐
             │   Build    │
             └─────┬──────┘
                   ▼
            ┌─────────────┐
            │ CI Complete │
            └─────────────┘
```

### Viewing CI Results

1. Go to your GitHub repository
2. Click the **Actions** tab
3. Click on the latest **CI** workflow run
4. View status of each job

**Green checkmark (✅)** = All tests passed  
**Red X (❌)** = Something failed (click to see details)

---

## 2️⃣ CD Workflow (Manual Deployment)

### What It Does

The CD workflow deploys your code to AWS. It's triggered **manually** to give you control over when deployments happen.

### CD Jobs

| Job | Description | Duration |
|-----|-------------|----------|
| **Build & Push** | Builds Docker images and pushes to ECR | ~5 min |
| **Migrate** | Runs Alembic database migrations | ~1 min |
| **Deploy** | Updates ECS services with new images | ~5 min |
| **Notify** | Sends deployment summary | ~10 sec |

### CD Flow Diagram

```
┌────────────────────┐
│  Build & Push      │
│  to ECR            │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Run Database      │
│  Migrations        │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Deploy to         │
│  ECS Fargate       │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Notification      │
│  (Success/Failure) │
└────────────────────┘
```

### How to Trigger a Deployment

1. Go to **GitHub** → your repository
2. Click the **Actions** tab
3. In the left sidebar, click **"Deploy to AWS"**
4. Click the **"Run workflow"** dropdown button (top right)
5. Select the **environment** (staging or production)
6. Click **"Run workflow"**

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Workflows          │  Deploy to AWS                        │
│  ───────────        │  ─────────────────────────────────    │
│  ▶ CI              │                                        │
│  ▶ Deploy to AWS ◀ │  [Run workflow ▼]                      │
│                     │    ┌─────────────────────────┐        │
│                     │    │ Branch: main            │        │
│                     │    │ Environment: production │        │
│                     │    │ [Run workflow]          │        │
│                     │    └─────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 GitHub Secrets Configuration

Before using the CD workflow, you must configure GitHub Secrets with your AWS credentials and deployment information.

### Required Secrets

Go to: **GitHub Repo** → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret Name | Description | Current Value |
|-------------|-------------|---------------|
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID | `296062592436` |
| `AWS_ACCESS_KEY_ID` | IAM user access key for CI/CD | (create via IAM) |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key | (create via IAM) |
| `PATIENT_DATABASE_URL` | Patient DB connection string | `postgresql://oncolife_admin:<REDACTED_ROTATE_ME>@oncolife-db.cziyoqoiu475.us-east-1.rds.amazonaws.com:5432/oncolife_patient` |
| `DOCTOR_DATABASE_URL` | Doctor DB connection string | `postgresql://oncolife_admin:<REDACTED_ROTATE_ME>@oncolife-db.cziyoqoiu475.us-east-1.rds.amazonaws.com:5432/oncolife_doctor` |
| `PATIENT_API_URL` | Patient API URL (for frontend builds) | `https://doreebziauwxa.cloudfront.net/api/v1` |
| `DOCTOR_API_URL` | Doctor API URL (for frontend builds) | `https://d3laeu67onw47.cloudfront.net/api/v1` |
| `PATIENT_WS_URL` | Patient WebSocket URL | `wss://doreebziauwxa.cloudfront.net/api/v1` |
| `PATIENT_WEB_BUCKET` | S3 bucket for Patient Web | `oncolife-patient-web-296062592436` |
| `DOCTOR_WEB_BUCKET` | S3 bucket for Doctor Web | `oncolife-doctor-web-296062592436` |
| `PATIENT_CLOUDFRONT_ID` | CloudFront distribution ID | `E33AUPKTFUG96P` |
| `DOCTOR_CLOUDFRONT_ID` | CloudFront distribution ID | `E2GRY718GCD95L` |

### Where to Find These Values

| Secret | Source |
|--------|--------|
| `AWS_ACCOUNT_ID` | AWS Console top-right dropdown → Account ID |
| `AWS_ACCESS_KEY_ID` | Created in Step 2 below |
| `AWS_SECRET_ACCESS_KEY` | Created in Step 2 below |
| `PATIENT_DATABASE_URL` | See `AWS_DEPLOYMENT_STATUS.md` for RDS endpoint and credentials |
| `DOCTOR_DATABASE_URL` | See `AWS_DEPLOYMENT_STATUS.md` for RDS endpoint and credentials |
| `PATIENT_API_URL` | CloudFront URL: `https://doreebziauwxa.cloudfront.net/api/v1` |
| `DOCTOR_API_URL` | CloudFront URL: `https://d3laeu67onw47.cloudfront.net/api/v1` |
| `PATIENT_WS_URL` | Same as PATIENT_API_URL but with `wss://` prefix |
| `*_WEB_BUCKET` | S3 bucket names from `AWS_DEPLOYMENT_STATUS.md` |
| `*_CLOUDFRONT_ID` | CloudFront distribution IDs from `AWS_DEPLOYMENT_STATUS.md` |

---

## 👤 Create CI/CD IAM User

Create a dedicated IAM user for GitHub Actions with minimal required permissions.

### Step 1: Create the User

```powershell
# Create the user
aws iam create-user --user-name github-actions-oncolife

# Create access keys (SAVE THESE!)
aws iam create-access-key --user-name github-actions-oncolife
```

**Output:**
```json
{
    "AccessKey": {
        "UserName": "github-actions-oncolife",
        "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",      ← Save as AWS_ACCESS_KEY_ID
        "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG...", ← Save as AWS_SECRET_ACCESS_KEY
        "Status": "Active"
    }
}
```

### Step 2: Create the Policy

Create a file named `github-actions-policy.json`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ECRAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:PutImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload"
            ],
            "Resource": "*"
        },
        {
            "Sid": "ECSAccess",
            "Effect": "Allow",
            "Action": [
                "ecs:UpdateService",
                "ecs:DescribeServices",
                "ecs:DescribeClusters",
                "ecs:DescribeTaskDefinition",
                "ecs:RegisterTaskDefinition"
            ],
            "Resource": "*"
        },
        {
            "Sid": "IAMPassRole",
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": [
                "arn:aws:iam::*:role/ecsTaskExecutionRole",
                "arn:aws:iam::*:role/oncolife-TaskRole"
            ]
        }
    ]
}
```

### Step 3: Attach the Policy

```powershell
aws iam put-user-policy `
    --user-name github-actions-oncolife `
    --policy-name CICD-Policy `
    --policy-document file://github-actions-policy.json
```

---

## 📊 Deployment Process Details

### What Happens During Deployment

```
Deploy to AWS Workflow
═══════════════════════════════════════════════════════════════════════

Step 1: Build & Push to ECR (5 min)
───────────────────────────────────────────────────────────────────────
├── 🔐 Configure AWS credentials
├── 🔑 Login to Amazon ECR
├── 🏗️  Build Patient API Docker image
│   └── Push to: {account}.dkr.ecr.{region}.amazonaws.com/oncolife-patient-api:latest
├── 🏗️  Build Doctor API Docker image
│   └── Push to: {account}.dkr.ecr.{region}.amazonaws.com/oncolife-doctor-api:latest
├── 🏗️  Build Patient Web Docker image (with VITE_API_URL baked in)
│   └── Push to: {account}.dkr.ecr.{region}.amazonaws.com/oncolife-patient-web:latest
└── 🏗️  Build Doctor Web Docker image
    └── Push to: {account}.dkr.ecr.{region}.amazonaws.com/oncolife-doctor-web:latest

Step 2: Database Migrations (1 min)
───────────────────────────────────────────────────────────────────────
├── 📦 Install Alembic and dependencies
├── 🗄️  Run Patient API migrations: alembic upgrade head
└── 🗄️  Run Doctor API migrations: alembic upgrade head

Step 3: Deploy to ECS (5 min)
───────────────────────────────────────────────────────────────────────
├── 🔄 Update patient-api-service (force new deployment)
├── 🔄 Update doctor-api-service (force new deployment)
├── 🔄 Update patient-web-service (force new deployment)
├── 🔄 Update doctor-web-service (force new deployment)
├── ⏳ Wait for patient-api-service to stabilize
└── ⏳ Wait for doctor-api-service to stabilize

Step 4: Notification
───────────────────────────────────────────────────────────────────────
└── 📢 Output deployment summary (success/failure)
```

### Zero-Downtime Deployment

ECS Fargate performs **rolling deployments**:

1. New tasks are started with the new image
2. Health checks verify new tasks are healthy
3. Traffic is shifted to new tasks
4. Old tasks are drained and stopped

```
Before Deployment:
┌──────────────────────────────────────────┐
│  ECS Service: patient-api-service        │
│  ┌─────────────┐  ┌─────────────┐        │
│  │ Task v1.0   │  │ Task v1.0   │        │
│  │ (running)   │  │ (running)   │        │
│  └─────────────┘  └─────────────┘        │
└──────────────────────────────────────────┘

During Deployment:
┌──────────────────────────────────────────┐
│  ECS Service: patient-api-service        │
│  ┌─────────────┐  ┌─────────────┐        │
│  │ Task v1.0   │  │ Task v2.0   │ ← New  │
│  │ (draining)  │  │ (starting)  │        │
│  └─────────────┘  └─────────────┘        │
└──────────────────────────────────────────┘

After Deployment:
┌──────────────────────────────────────────┐
│  ECS Service: patient-api-service        │
│  ┌─────────────┐  ┌─────────────┐        │
│  │ Task v2.0   │  │ Task v2.0   │        │
│  │ (running)   │  │ (running)   │        │
│  └─────────────┘  └─────────────┘        │
└──────────────────────────────────────────┘
```

---

## ✅ Integration Checklist

Complete these steps to fully integrate CI/CD with your AWS deployment:

| # | Task | Command/Action | Status |
|---|------|----------------|--------|
| 1 | Deploy to AWS | Run `.\scripts\aws\full-deploy.ps1` | ⬜ |
| 2 | Save deployment config | Keep `deployment-config-*.json` safe | ⬜ |
| 3 | Get AWS Account ID | `aws sts get-caller-identity --query Account` | ⬜ |
| 4 | Create CI/CD IAM user | See "Create CI/CD IAM User" section | ⬜ |
| 5 | Get database URLs | Combine RDS endpoint + credentials | ⬜ |
| 6 | Get API URLs | From ALB DNS or custom domain | ⬜ |
| 7 | Add `AWS_ACCOUNT_ID` to GitHub Secrets | GitHub → Settings → Secrets | ⬜ |
| 8 | Add `AWS_ACCESS_KEY_ID` to GitHub Secrets | GitHub → Settings → Secrets | ⬜ |
| 9 | Add `AWS_SECRET_ACCESS_KEY` to GitHub Secrets | GitHub → Settings → Secrets | ⬜ |
| 10 | Add `PATIENT_DATABASE_URL` to GitHub Secrets | GitHub → Settings → Secrets | ⬜ |
| 11 | Add `DOCTOR_DATABASE_URL` to GitHub Secrets | GitHub → Settings → Secrets | ⬜ |
| 12 | Add `PATIENT_API_URL` to GitHub Secrets | GitHub → Settings → Secrets | ⬜ |
| 13 | Add `DOCTOR_API_URL` to GitHub Secrets | GitHub → Settings → Secrets | ⬜ |
| 14 | Add `PATIENT_WS_URL` to GitHub Secrets | GitHub → Settings → Secrets | ⬜ |
| 15 | Push a code change | `git push origin main` | ⬜ |
| 16 | Verify CI runs | GitHub → Actions → CI workflow | ⬜ |
| 17 | Trigger manual deploy | GitHub → Actions → Deploy to AWS → Run workflow | ⬜ |
| 18 | Verify deployment | Check API health endpoints | ⬜ |

---

## 🐛 Troubleshooting

### CI Failures

| Error | Cause | Solution |
|-------|-------|----------|
| `Lint failed` | Code style issues | Run `black` and `ruff` locally |
| `Test failed` | Unit test failures | Check test output, fix tests |
| `Build failed` | Dockerfile issues | Test Docker build locally |

### CD Failures

| Error | Cause | Solution |
|-------|-------|----------|
| `ECR login failed` | Invalid AWS credentials | Check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` |
| `Push to ECR failed` | No ECR repository | Create ECR repos (done by `full-deploy.ps1`) |
| `Migration failed` | Database connection | Check `DATABASE_URL` secret format |
| `ECS update failed` | Service not found | Verify ECS cluster and service names |
| `Service not stable` | Container crashes | Check CloudWatch logs |

### Checking CloudWatch Logs

```powershell
# View Patient API logs
aws logs tail /ecs/oncolife-patient-api --follow

# View Doctor API logs  
aws logs tail /ecs/oncolife-doctor-api --follow
```

---

## 🔄 Rollback Procedure

If a deployment causes issues, you can rollback:

### Option 1: Redeploy Previous Commit

1. Go to GitHub → **Actions** → **Deploy to AWS**
2. Find a previous successful deployment
3. Click **"Re-run all jobs"**

### Option 2: Manual Rollback

```powershell
# List recent task definitions
aws ecs list-task-definitions --family oncolife-patient-api --sort DESC

# Update service to use previous task definition
aws ecs update-service `
    --cluster oncolife-production `
    --service patient-api-service `
    --task-definition oncolife-patient-api:PREVIOUS_REVISION
```

---

## 💡 Best Practices

1. **Always check CI first**: Ensure CI passes before deploying
2. **Use staging environment**: Test in staging before production
3. **Small, frequent deployments**: Deploy often with small changes
4. **Monitor after deployment**: Watch CloudWatch logs and metrics
5. **Document changes**: Use clear commit messages
6. **Protect main branch**: Require PR reviews before merge

---

---

## 📊 Monitoring & Alerts Integration

### Production Monitoring Features

The deployment includes comprehensive monitoring:

| Feature | Status | Description |
|---------|--------|-------------|
| **Health Endpoints** | ✅ | `/health`, `/api/v1/health/ready`, `/api/v1/health/live`, `/api/v1/health/detailed` |
| **Rate Limiting** | ✅ | Auth endpoints limited (5/min login, 3/min password reset) |
| **CloudWatch Alarms** | ✅ | CPU, Memory, 5xx errors, DB health |
| **Slack Notifications** | ✅ | Error and critical alerts |
| **Email Alerts** | ✅ | Via AWS SNS |

### Slack Notifications from CI/CD

Uncomment this in `deploy.yml` to enable Slack notifications:

```yaml
- name: Send Slack notification
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    fields: repo,message,commit,author,action,eventName,ref,workflow
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

Add `SLACK_WEBHOOK_URL` to your GitHub Secrets.

### Monitoring After Deployment

```bash
# View deployment status
aws ecs describe-services \
    --cluster oncolife-production \
    --services patient-api-service doctor-api-service \
    --query 'services[*].{name:serviceName,running:runningCount,status:status}'

# Check health endpoints
curl http://$PATIENT_ALB/api/v1/health/ready
curl http://$DOCTOR_ALB/api/v1/health/ready

# View CloudWatch logs
aws logs tail /ecs/oncolife-patient-api --follow
```

---

## 📚 Related Documentation

- [Automated Deployment Guide](AUTOMATED_DEPLOYMENT_GUIDE.md) - One-script AWS deployment
- [Step-by-Step Deployment Guide](STEP_BY_STEP_DEPLOYMENT.md) - Manual AWS deployment
- [Deployment Status](DEPLOYMENT_STATUS.md) - Feature completion checklist
- [Deployment Troubleshooting](DEPLOYMENT_TROUBLESHOOTING.md) - Common deployment issues
- [Developer Guide](DEVELOPER_GUIDE.md) - Local development setup
- [Architecture Guide](ARCHITECTURE.md) - System architecture overview

---

## 📞 Support

If you encounter issues with the CI/CD pipeline:

1. Check the workflow logs in GitHub Actions
2. Review CloudWatch logs for ECS services
3. Consult the [Deployment Troubleshooting Guide](DEPLOYMENT_TROUBLESHOOTING.md)
4. Check AWS service health in the AWS Console
