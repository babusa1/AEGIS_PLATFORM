# OncoLife Automated Deployment Guide

<div align="center">

## 🚀 Deploy OncoLife to AWS in One Command

**Version 1.0 | January 2026**

</div>

---

## Overview

This guide walks you through deploying the complete OncoLife platform to AWS using our **automated deployment scripts**. The scripts handle everything from VPC creation to running services.

### Available Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| **`full-deploy.ps1`** | Full initial deployment | First-time setup (PowerShell) |
| **`full-deploy.sh`** | Full initial deployment | First-time setup (Bash) |
| **`deploy.sh`** | Update existing services | After initial deployment |
| **`cleanup-all.sh`** | Delete all resources | Fresh start or teardown |
| **`setup-monitoring.sh`** | Set up CloudWatch & alerts | After deployment |
| **`create-education-bucket.sh`** | Create S3 bucket | If not using full-deploy |

| What | Details |
|------|---------|
| **Time Required** | 20-30 minutes |
| **Skill Level** | Basic (just run the script!) |
| **What You Need** | AWS account, Docker Desktop |
| **What Gets Created** | Complete production environment |

---

## Prerequisites Checklist

Before running the script, ensure you have:

- [ ] **AWS Account** with Administrator access
- [ ] **AWS CLI** installed and configured
- [ ] **Docker Desktop** installed and running
- [ ] **PowerShell** (Windows) or Terminal (Mac/Linux)
- [ ] **Git** installed

---

## Step 1: Install Required Tools

### 1.1 Install AWS CLI

**Windows:**
```powershell
# Download and run the MSI installer from:
# https://aws.amazon.com/cli/

# Verify installation
aws --version
# Expected: aws-cli/2.x.x ...
```

**Mac:**
```bash
brew install awscli

# Verify
aws --version
```

### 1.2 Install Docker Desktop

Download from: https://www.docker.com/products/docker-desktop/

After installation:
1. Start Docker Desktop
2. Wait for it to fully start (whale icon stops animating)
3. Verify:
```powershell
docker --version
# Expected: Docker version 24.x.x ...
```

### 1.3 Configure AWS Credentials

```powershell
aws configure
```

Enter when prompted:
```
AWS Access Key ID:     [Your access key]
AWS Secret Access Key: [Your secret key]
Default region name:   us-west-2
Default output format: json
```

**Verify AWS is configured:**
```powershell
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDAXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

---

## Step 2: Clone the Repository

```powershell
git clone https://github.com/nbsaKanasu/Oncolife_Monolith.git
cd Oncolife_Monolith
```

---

## Step 3: Run the Automated Deployment

### 3.1 Start the Deployment

**Choose your platform:**

#### Option A: PowerShell (Windows - Recommended)

```powershell
.\scripts\aws\full-deploy.ps1
```

#### Option B: Bash (Linux, macOS, or Git Bash on Windows)

```bash
./scripts/aws/full-deploy.sh
```

> 💡 **Windows Users**: We recommend PowerShell. Git Bash works but PowerShell is more reliable.

### 3.2 When Prompted, Enter Database Password

The script will ask for one input:

```
Enter a password for the database.
Requirements: 8+ chars, letters, numbers, no @/"/spaces
Database Password: ********
```

**Choose a strong password like:** `<REDACTED_ROTATE_ME>`

### 3.3 Wait for Completion

The script will show progress:

```
=============================================
STEP 1: Checking Prerequisites
=============================================
  ✓ AWS Account: 123456789012
  ✓ Docker is running
  ✓ Project directory verified
  ✓ Region: us-west-2

=============================================
STEP 2: Creating VPC and Networking
=============================================
  → Creating VPC...
  ✓ VPC created: vpc-0abc123def456
  → Creating Internet Gateway...
  ✓ Internet Gateway attached
  ...
```

**Do not close the terminal!** The deployment takes 20-30 minutes.

---

## Step 4: Deployment Complete!

When finished, you'll see:

```
╔══════════════════════════════════════════════════════════════╗
║              DEPLOYMENT COMPLETE!                            ║
╚══════════════════════════════════════════════════════════════╝

Duration: 25 minutes 30 seconds

ACCESS URLS:
  Patient API:      http://oncolife-patient-alb-xxxxx.elb.amazonaws.com
  Patient API Docs: http://oncolife-patient-alb-xxxxx.elb.amazonaws.com/docs
  Doctor API:       http://oncolife-doctor-alb-xxxxx.elb.amazonaws.com
  Doctor API Docs:  http://oncolife-doctor-alb-xxxxx.elb.amazonaws.com/docs

Configuration saved to: deployment-config-20260106-143022.json
```

### 4.1 Test Your Deployment

Open a browser and test:

```
# Patient API Health Check
http://[PATIENT_ALB_DNS]/health

# Patient API Documentation (Swagger UI)
http://[PATIENT_ALB_DNS]/docs

# Doctor API Health Check
http://[DOCTOR_ALB_DNS]/health

# Doctor API Documentation (Swagger UI)
http://[DOCTOR_ALB_DNS]/docs
```

---

## Step 5: Create Databases (Required)

After deployment, you need to create the databases. Connect to RDS and run:

### Option A: Using a Bastion Host

```bash
# SSH to bastion host, then:
psql -h [RDS_ENDPOINT] -U oncolife_admin -d postgres

# In PostgreSQL:
CREATE DATABASE oncolife_patient;
CREATE DATABASE oncolife_doctor;
GRANT ALL PRIVILEGES ON DATABASE oncolife_patient TO oncolife_admin;
GRANT ALL PRIVILEGES ON DATABASE oncolife_doctor TO oncolife_admin;
\q
```

### Option B: Using AWS RDS Query Editor

1. Go to AWS Console → RDS → Query Editor
2. Connect to your database
3. Run the SQL commands above

---

## Step 6: Run Database Migrations

From a machine that can reach RDS:

```bash
# Patient API migrations
cd apps/patient-platform/patient-api
pip install -r requirements.txt
export DATABASE_URL=postgresql://oncolife_admin:PASSWORD@RDS_ENDPOINT:5432/oncolife_patient
alembic upgrade head

# Doctor API migrations
cd ../../doctor-platform/doctor-api
pip install -r requirements.txt
export DATABASE_URL=postgresql://oncolife_admin:PASSWORD@RDS_ENDPOINT:5432/oncolife_doctor
alembic upgrade head
```

---

## Step 6b: Seed Education Content (Required)

After running migrations, seed the education metadata for patient education PDFs:

### Education PDFs Structure

The `full-deploy.sh` script automatically uploads PDFs to S3 during deployment. The S3 bucket structure is:

```
s3://oncolife-education-{ACCOUNT_ID}/
├── symptoms/           # Symptom-specific PDFs (61 files)
│   ├── nausea/
│   ├── fever/
│   ├── diarrhea/
│   └── ...
├── handbooks/          # General handbooks (1 file)
│   └── chemo_basics_handbook.pdf
└── regimens/           # Chemo regimen PDFs (27 files)
    ├── r_chop/
    ├── folfox/
    └── ...
```

### Seed Education Metadata

After migrations, run the seed script to populate education metadata:

```bash
# From project root
cd apps/patient-platform/patient-api

# Set database connection
export DATABASE_URL=postgresql://oncolife_admin:PASSWORD@RDS_ENDPOINT:5432/oncolife_patient

# Run seed script
python scripts/seed_education_pdfs.py
```

**What gets seeded:**
| Table | Records | Content |
|-------|---------|---------|
| `education_pdfs` | 61 | Symptom-specific PDFs with summaries |
| `education_handbooks` | 1 | Chemo Basics Handbook |
| `education_regimen_pdfs` | 27 | Chemotherapy regimen drug info |

### Manual Education Upload (If Needed)

If education PDFs weren't uploaded during `full-deploy.sh`:

```bash
# Create bucket (if not exists)
./scripts/aws/create-education-bucket.sh

# Upload PDFs
./scripts/aws/upload-education-pdfs.sh
```

---

## What Gets Created

The script automatically creates all these AWS resources:

### Networking
| Resource | Name | Purpose |
|----------|------|---------|
| VPC | oncolife-vpc | Isolated network |
| Public Subnet 1 | 10.0.1.0/24 | ALB, NAT Gateway |
| Public Subnet 2 | 10.0.2.0/24 | ALB (multi-AZ) |
| Private Subnet 1 | 10.0.10.0/24 | ECS Tasks, RDS |
| Private Subnet 2 | 10.0.11.0/24 | ECS Tasks, RDS (multi-AZ) |
| Internet Gateway | oncolife-igw | Public internet access |
| NAT Gateway | oncolife-nat | Private subnet internet access |

### Security
| Resource | Purpose |
|----------|---------|
| ALB Security Group | Allow HTTP/HTTPS from internet |
| ECS Security Group | Allow traffic from ALB only |
| RDS Security Group | Allow PostgreSQL from ECS only |

### Database
| Resource | Details |
|----------|---------|
| RDS PostgreSQL | db.t3.medium, 100GB, encrypted |
| Databases | oncolife_patient, oncolife_doctor |

### Compute
| Resource | Details |
|----------|---------|
| ECS Cluster | oncolife-production |
| Patient API Service | 2 Fargate tasks |
| Doctor API Service | 2 Fargate tasks |

### Load Balancing
| Resource | Port | Target |
|----------|------|--------|
| Patient ALB | 80 → 8000 | Patient API |
| Doctor ALB | 80 → 8001 | Doctor API |

### Storage & Secrets
| Resource | Purpose |
|----------|---------|
| ECR Repositories | Docker images |
| S3 Buckets | Referrals, Education content |
| Secrets Manager | Database credentials, Cognito secrets |

### Authentication
| Resource | Purpose |
|----------|---------|
| Cognito User Pool | Patient authentication |
| App Client | API authentication |

---

## Deployment Options

### Different Region

```powershell
.\scripts\aws\full-deploy.ps1 -Region us-east-1
```

### Use Existing VPC

If you already have a VPC:

```powershell
.\scripts\aws\full-deploy.ps1 -SkipVPC
```

The script will prompt you for:
- VPC ID
- Public Subnet IDs (2)
- Private Subnet IDs (2)

### Use Existing RDS

If you already have an RDS instance:

```powershell
.\scripts\aws\full-deploy.ps1 -SkipRDS
```

The script will prompt you for:
- RDS Endpoint
- Database Password

### Skip Docker Build

To use existing images in ECR:

```powershell
.\scripts\aws\full-deploy.ps1 -SkipBuild
```

### Combine Options

```powershell
.\scripts\aws\full-deploy.ps1 -Region us-east-1 -SkipVPC -SkipRDS
```

---

## Troubleshooting

### Script Fails Early

**Error:** `AWS CLI not configured`
```powershell
# Fix: Run aws configure
aws configure
```

**Error:** `Docker not running`
```powershell
# Fix: Start Docker Desktop and wait for it to fully start
```

### VPC Creation Fails

**Error:** `VPC limit exceeded`
```powershell
# Fix: Delete unused VPCs or request limit increase
# Or use -SkipVPC with existing VPC
.\scripts\aws\full-deploy.ps1 -SkipVPC
```

### RDS Takes Too Long

RDS creation takes 10-15 minutes. If it times out:
```powershell
# Check status manually
aws rds describe-db-instances --db-instance-identifier oncolife-db --query 'DBInstances[0].DBInstanceStatus'

# When it shows "available", run:
.\scripts\aws\full-deploy.ps1 -SkipVPC -SkipRDS
```

### Tasks Stay in PENDING

Check CloudWatch logs:
```powershell
aws logs tail "/ecs/oncolife-patient-api" --since 10m
```

Common causes:
- Secrets Manager permissions
- Security group rules
- NAT Gateway not ready

### Health Checks Failing

Wait 5 minutes after deployment, then check:
```powershell
# Check service status
aws ecs describe-services `
    --cluster oncolife-production `
    --services patient-api-service doctor-api-service `
    --query 'services[*].{Name:serviceName,Running:runningCount}'
```

### For More Help

See: [DEPLOYMENT_TROUBLESHOOTING.md](DEPLOYMENT_TROUBLESHOOTING.md)

---

## Saving Your Configuration

After deployment, a config file is saved:

```
deployment-config-20260106-143022.json
```

This contains all resource IDs. **Keep this file safe!**

```json
{
    "AccountId": "123456789012",
    "Region": "us-west-2",
    "VpcId": "vpc-0abc123...",
    "PublicSubnet1": "subnet-...",
    "RdsEndpoint": "oncolife-db.xxxxx.rds.amazonaws.com",
    "PatientAlbDns": "oncolife-patient-alb-xxxxx.elb.amazonaws.com",
    "DoctorAlbDns": "oncolife-doctor-alb-xxxxx.elb.amazonaws.com",
    ...
}
```

---

## Next Steps After Deployment

1. **✅ Create Databases** - See Step 5 above
2. **✅ Run Migrations** - See Step 6 above
3. **⬜ Set Up CI/CD** - See [CI/CD Pipeline Guide](CI_CD_PIPELINE_GUIDE.md) for automated deployments
4. **⬜ Deploy Frontend** - Use S3 + CloudFront or ECS
5. **⬜ Set Up Monitoring** - See "Monitoring Setup" section below
6. **⬜ (Optional) Set Up Custom Domains** - See [STEP_BY_STEP_DEPLOYMENT.md](STEP_BY_STEP_DEPLOYMENT.md) Section 11
7. **⬜ (Optional) Configure HTTPS** - Request ACM certificates and add HTTPS listeners

> 💡 **Tip**: Custom domains are **OPTIONAL**! You can use the ALB DNS names directly for testing and development. See the next section.

---

## Step 8: Set Up Monitoring (Recommended)

### 8.1 Run Monitoring Setup Script

This creates SNS topics, CloudWatch log groups, and a dashboard:

```bash
# Bash
./scripts/aws/setup-monitoring.sh production your-email@company.com

# PowerShell
# (Use AWS Console or Bash script)
```

### 8.2 Configure Slack Notifications (Optional)

1. Create a Slack Incoming Webhook in your workspace
2. Add to environment variables:

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/xxx/yyy/zzz"
```

### 8.3 Apply CloudWatch Alarms (Requires Terraform)

```bash
cd scripts/aws

# Initialize Terraform
terraform init

# Review what will be created
terraform plan -var="sns_alert_topic_arn=arn:aws:sns:us-west-2:ACCOUNT:oncolife-production-alerts"

# Apply alarms
terraform apply
```

This creates alarms for:
- ECS CPU/Memory > 80%
- No running tasks (critical)
- ALB 5xx errors > 10/min
- RDS CPU > 80%, storage < 5GB
- Authentication failures > 50/min

### 8.4 Test Health Endpoints

```bash
# Basic health (for ALB)
curl http://$PATIENT_ALB/health

# Readiness (checks database connection)
curl http://$PATIENT_ALB/api/v1/health/ready

# Detailed (includes system metrics)
curl http://$PATIENT_ALB/api/v1/health/detailed
```

---

## Using ALB DNS Names Directly (No Custom Domain Required)

> 🎯 **For Testing & Development**: You don't need to set up custom domains! The AWS ALB DNS names work immediately after deployment.

### Your Application URLs

After deployment, your apps are accessible at:

| Application | URL Example |
|-------------|-------------|
| **Patient API** | `http://oncolife-patient-alb-123456789.us-west-2.elb.amazonaws.com` |
| **Patient API Docs** | `http://oncolife-patient-alb-123456789.us-west-2.elb.amazonaws.com/docs` |
| **Doctor API** | `http://oncolife-doctor-alb-987654321.us-west-2.elb.amazonaws.com` |
| **Doctor API Docs** | `http://oncolife-doctor-alb-987654321.us-west-2.elb.amazonaws.com/docs` |

### Get Your ALB URLs

```powershell
# Get Patient API URL
$PATIENT_URL = aws elbv2 describe-load-balancers --names "oncolife-patient-alb" --query 'LoadBalancers[0].DNSName' --output text
Write-Host "Patient API: http://$PATIENT_URL"
Write-Host "Patient Docs: http://$PATIENT_URL/docs"

# Get Doctor API URL
$DOCTOR_URL = aws elbv2 describe-load-balancers --names "oncolife-doctor-alb" --query 'LoadBalancers[0].DNSName' --output text
Write-Host "Doctor API: http://$DOCTOR_URL"
Write-Host "Doctor Docs: http://$DOCTOR_URL/docs"
```

### Configure GitHub Secrets with ALB URLs

For CI/CD, use the ALB DNS names directly:

| Secret | Value (using ALB DNS) |
|--------|----------------------|
| `PATIENT_API_URL` | `http://oncolife-patient-alb-XXXXX.us-west-2.elb.amazonaws.com` |
| `PATIENT_WS_URL` | `ws://oncolife-patient-alb-XXXXX.us-west-2.elb.amazonaws.com` |
| `DOCTOR_API_URL` | `http://oncolife-doctor-alb-XXXXX.us-west-2.elb.amazonaws.com` |

> ⚠️ **Note**: ALB URLs use `http://` and `ws://` (not `https://` or `wss://`). For production with HTTPS, you'll need custom domains and ACM certificates.

### When You're Ready for Production

When you want to use custom domains (e.g., `api.oncolife.com`):
1. Register/configure your domain in Route 53
2. Request ACM certificates
3. Add HTTPS listeners to ALBs
4. Create Route 53 alias records

See [STEP_BY_STEP_DEPLOYMENT.md](STEP_BY_STEP_DEPLOYMENT.md) Section 11 for details.

---

## Re-Deploying After Code Changes

After your initial deployment, use **`deploy.sh`** for updates (NOT `full-deploy.sh`):

```bash
# Re-deploy all services with latest code
./scripts/aws/deploy.sh

# Re-deploy only Patient API
./scripts/aws/deploy.sh patient-api

# Re-deploy only Doctor API
./scripts/aws/deploy.sh doctor-api

# Check infrastructure status
./scripts/aws/deploy.sh check
```

**Why two scripts?**

| Script | Use When | What It Does |
|--------|----------|--------------|
| `full-deploy.sh/ps1` | First-time deployment | Creates VPC, RDS, ECS, everything from scratch |
| `deploy.sh` | Updates after initial deployment | Rebuilds Docker images and updates ECS services |

---

## Step 7: Set Up CI/CD (Automated Future Deployments)

After your initial deployment, set up CI/CD so future code changes deploy automatically.

### Quick Overview

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Push Code      │ → │   CI Tests       │ → │   Manual Deploy  │
│   to GitHub      │    │   (Automatic)    │    │   (One Click)    │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

### What You Need

1. **GitHub Secrets** - AWS credentials and deployment info
2. **CI/CD IAM User** - Dedicated AWS user for GitHub Actions

### Configure GitHub Secrets

Go to: **GitHub Repo** → **Settings** → **Secrets** → **Actions** → **New repository secret**

| Secret Name | Where to Get Value |
|-------------|-------------------|
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID |
| `AWS_ACCESS_KEY_ID` | CI/CD IAM user (see guide) |
| `AWS_SECRET_ACCESS_KEY` | CI/CD IAM user (see guide) |
| `PATIENT_DATABASE_URL` | `postgresql://user:pass@RDS_ENDPOINT:5432/oncolife_patient` |
| `DOCTOR_DATABASE_URL` | `postgresql://user:pass@RDS_ENDPOINT:5432/oncolife_doctor` |
| `PATIENT_API_URL` | Your Patient ALB DNS or custom domain |
| `DOCTOR_API_URL` | Your Doctor ALB DNS or custom domain |
| `PATIENT_WS_URL` | `wss://` + Patient API URL |

### Deploy After Setup

1. Push code to GitHub
2. CI runs automatically (tests, linting)
3. Go to **Actions** → **Deploy to AWS** → **Run workflow**
4. ECS services update automatically!

📖 **Full Guide:** [CI/CD Pipeline Guide](CI_CD_PIPELINE_GUIDE.md)

---

## Cleanup (Delete Everything)

### Option A: Automated Cleanup Script (Recommended)

Use the cleanup script to delete all OncoLife resources:

```bash
# Bash (Git Bash on Windows, Linux, macOS)
./scripts/aws/cleanup-all.sh

# With specific region
./scripts/aws/cleanup-all.sh --region us-east-1
```

This script deletes: VPC, ECS, ALB, RDS, ECR, Cognito, S3 buckets, Secrets, and more.

### Option B: Manual Cleanup (PowerShell)

```powershell
# Delete ECS Services
aws ecs update-service --cluster oncolife-production --service patient-api-service --desired-count 0
aws ecs update-service --cluster oncolife-production --service doctor-api-service --desired-count 0
aws ecs delete-service --cluster oncolife-production --service patient-api-service
aws ecs delete-service --cluster oncolife-production --service doctor-api-service

# Delete ALBs
aws elbv2 delete-load-balancer --load-balancer-arn [PATIENT_ALB_ARN]
aws elbv2 delete-load-balancer --load-balancer-arn [DOCTOR_ALB_ARN]

# Delete RDS
aws rds delete-db-instance --db-instance-identifier oncolife-db --skip-final-snapshot

# Delete VPC (will fail if resources still exist)
# Use AWS Console for easier cleanup
```

---

## Quick Reference - All Scripts

### Initial Deployment (First Time)

| Script | Platform | Purpose |
|--------|----------|---------|
| `.\scripts\aws\full-deploy.ps1` | PowerShell (Windows) | Deploy everything - creates all infrastructure |
| `./scripts/aws/full-deploy.sh` | Bash (Linux/Mac/Git Bash) | Deploy everything - creates all infrastructure |

**Options for full-deploy scripts:**
| Option | Purpose |
|--------|---------|
| `-SkipVPC` / `--skip-vpc` | Use existing VPC |
| `-SkipRDS` / `--skip-rds` | Use existing RDS |
| `-SkipCognito` / `--skip-cognito` | Use existing Cognito |
| `-SkipBuild` / `--skip-build` | Use existing Docker images |
| `-Region` / `--region` | Deploy to different region |

### Re-Deployment (Update Existing Services)

| Script | Platform | Purpose |
|--------|----------|---------|
| `./scripts/aws/deploy.sh` | Bash | Rebuild and redeploy to existing ECS services |
| `./scripts/aws/deploy.sh check` | Bash | Check infrastructure status |

### Cleanup

| Script | Platform | Purpose |
|--------|----------|---------|
| `./scripts/aws/cleanup-all.sh` | Bash | Delete ALL OncoLife AWS resources |

### Monitoring

| Script | Platform | Purpose |
|--------|----------|---------|
| `./scripts/aws/setup-monitoring.sh email@example.com` | Bash | Create SNS topics, CloudWatch dashboard |

### Other Utilities

| Script | Platform | Purpose |
|--------|----------|---------|
| `./scripts/aws/create-education-bucket.sh` | Bash | Create S3 bucket for education content |
| `./scripts/aws/upload-education-pdfs.sh` | Bash | Upload PDF files to education bucket |

---

## Support

| Resource | Link |
|----------|------|
| Troubleshooting | [DEPLOYMENT_TROUBLESHOOTING.md](DEPLOYMENT_TROUBLESHOOTING.md) |
| Manual Deployment | [STEP_BY_STEP_DEPLOYMENT.md](STEP_BY_STEP_DEPLOYMENT.md) |
| Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Developer Guide | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |

---

<div align="center">

**Happy Deploying! 🚀**

*OncoLife Platform | © 2026*

</div>
