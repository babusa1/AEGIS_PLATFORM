# OncoLife - Complete AWS Deployment Guide

**Version 2.1 | Updated January 2026**

**Developer:** NAVEEN BABU S A

> ⚠️ **IMPORTANT**: This guide includes fixes for common deployment errors. Read each section carefully, especially the "Common Errors" boxes.

---

## Table of Contents

1. [Pre-Deployment Checklist](#1-pre-deployment-checklist)
2. [Windows vs Linux/Mac Notes](#2-windows-vs-linuxmac-notes)
3. [Phase 1: AWS Foundation](#3-phase-1-aws-foundation)
4. [Phase 2: Container Infrastructure](#4-phase-2-container-infrastructure)
5. [Phase 3: Build and Deploy](#5-phase-3-build-and-deploy)
6. [Phase 4: Database Setup](#6-phase-4-database-setup)
7. [Phase 5: Verification](#7-phase-5-verification)
8. [Phase 6: CI/CD Setup (Automated Deployments)](#8-phase-6-cicd-setup-automated-deployments)
9. [Using ALB URLs Without Custom Domains](#using-alb-urls-without-custom-domains) ← **No domain needed!**
10. [Troubleshooting Guide](#9-troubleshooting-guide)
11. [Common Errors and Fixes](#10-common-errors-and-fixes)

---

## 1. Pre-Deployment Checklist

### Required Tools

| Tool | Version | Verify Command | Install Guide |
|------|---------|----------------|---------------|
| AWS CLI | v2.x | `aws --version` | [AWS CLI Install](https://aws.amazon.com/cli/) |
| Docker Desktop | Latest | `docker --version` | [Docker Install](https://docker.com) |
| Git | Latest | `git --version` | [Git Install](https://git-scm.com) |
| Python | 3.11+ | `python --version` | [Python Install](https://python.org) |
| Node.js | 18+ | `node --version` | [Node Install](https://nodejs.org) |

### AWS Account Setup

- [ ] AWS Account with **Administrator Access**
- [ ] AWS CLI configured: `aws configure`
- [ ] Region set to `us-west-2` (or your preferred region)

**Verify AWS Setup:**
```bash
# Test AWS credentials
aws sts get-caller-identity

# Should return:
# {
#     "UserId": "AIDAXXXXXXXXXX",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-user"
# }
```

### Clone Repository

```bash
git clone https://github.com/nbsaKanasu/Oncolife_Monolith.git
cd Oncolife_Monolith
```

---

## 2. Windows vs Linux/Mac Notes

> ⚠️ **CRITICAL FOR WINDOWS USERS**: Git Bash can mangle paths. Use **PowerShell** or **Command Prompt** for AWS CLI commands.

### Windows (PowerShell) - Use This!

```powershell
# Set your region and get account ID
$AWS_REGION = "us-west-2"
$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)

# Verify
Write-Host "Account: $ACCOUNT_ID, Region: $AWS_REGION"
```

### Linux/Mac (Bash)

```bash
# Set your region and get account ID
export AWS_REGION="us-west-2"
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Verify
echo "Account: $ACCOUNT_ID, Region: $AWS_REGION"
```

### Common Windows Path Issues

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid parameter: /ecs/...` | Git Bash converts `/ecs` to `C:/Program Files/Git/ecs` | Use PowerShell instead |
| `InvalidParameterException` on log group | Path mangling | Run in PowerShell, not Git Bash |

---

## 3. Phase 1: AWS Foundation

### Step 1.1: Create ECS Service-Linked Role (MUST DO FIRST!)

> ⚠️ **CRITICAL**: This role MUST exist before creating ECS clusters. Do this FIRST!

**PowerShell:**
```powershell
# Create ECS service-linked role (ignore error if already exists)
aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com

# If you get "InvalidInput... Role already exists" - that's OK, continue
```

**Bash:**
```bash
aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com 2>/dev/null || echo "Role already exists - OK"
```

### Step 1.2: Create VPC (Using AWS Console - Recommended)

> Using the console is easier and avoids CLI complexity for VPC.

1. Go to **VPC Console** → **Create VPC**
2. Select **"VPC and more"**
3. Configure:
   - **Name tag auto-generation**: `oncolife`
   - **IPv4 CIDR**: `10.0.0.0/16`
   - **Number of AZs**: `2`
   - **Public subnets**: `2`
   - **Private subnets**: `2`
   - **NAT gateways**: `1 per AZ` (or `1` to save cost)
   - **VPC endpoints**: `S3`
4. Click **Create VPC**
5. Wait for completion (~3 minutes)

**Record these values (you'll need them later):**
```
VPC ID:              vpc-xxxxxxxxx
Public Subnet 1:     subnet-xxxxxxxxx (e.g., 10.0.0.0/24)
Public Subnet 2:     subnet-yyyyyyyyy (e.g., 10.0.16.0/24)
Private Subnet 1:    subnet-zzzzzzzzz (e.g., 10.0.128.0/24)
Private Subnet 2:    subnet-wwwwwwwww (e.g., 10.0.144.0/24)
```

### Step 1.3: Create Security Groups

**PowerShell:**
```powershell
# Get your VPC ID (replace or use your recorded value)
$VPC_ID = "vpc-xxxxxxxxx"

# ALB Security Group (public access)
$SG_ALB = (aws ec2 create-security-group `
    --group-name "oncolife-alb-sg" `
    --description "OncoLife ALB Security Group" `
    --vpc-id $VPC_ID `
    --query 'GroupId' --output text)

Write-Host "ALB Security Group: $SG_ALB"

# Allow HTTPS from internet
aws ec2 authorize-security-group-ingress `
    --group-id $SG_ALB `
    --protocol tcp `
    --port 443 `
    --cidr "0.0.0.0/0"

# Allow HTTP (for redirect)
aws ec2 authorize-security-group-ingress `
    --group-id $SG_ALB `
    --protocol tcp `
    --port 80 `
    --cidr "0.0.0.0/0"

# ECS Security Group (internal)
$SG_ECS = (aws ec2 create-security-group `
    --group-name "oncolife-ecs-sg" `
    --description "OncoLife ECS Security Group" `
    --vpc-id $VPC_ID `
    --query 'GroupId' --output text)

Write-Host "ECS Security Group: $SG_ECS"

# Allow traffic from ALB (Patient API - port 8000)
aws ec2 authorize-security-group-ingress `
    --group-id $SG_ECS `
    --protocol tcp `
    --port 8000 `
    --source-group $SG_ALB

# Allow traffic from ALB (Doctor API - port 8001)
aws ec2 authorize-security-group-ingress `
    --group-id $SG_ECS `
    --protocol tcp `
    --port 8001 `
    --source-group $SG_ALB

# RDS Security Group
$SG_RDS = (aws ec2 create-security-group `
    --group-name "oncolife-rds-sg" `
    --description "OncoLife RDS Security Group" `
    --vpc-id $VPC_ID `
    --query 'GroupId' --output text)

Write-Host "RDS Security Group: $SG_RDS"

# Allow PostgreSQL from ECS
aws ec2 authorize-security-group-ingress `
    --group-id $SG_RDS `
    --protocol tcp `
    --port 5432 `
    --source-group $SG_ECS
```

**Bash:**
```bash
VPC_ID="vpc-xxxxxxxxx"

# ALB Security Group
SG_ALB=$(aws ec2 create-security-group \
    --group-name "oncolife-alb-sg" \
    --description "OncoLife ALB Security Group" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)
echo "ALB SG: $SG_ALB"

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ALB \
    --protocol tcp --port 443 --cidr "0.0.0.0/0"

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ALB \
    --protocol tcp --port 80 --cidr "0.0.0.0/0"

# ECS Security Group
SG_ECS=$(aws ec2 create-security-group \
    --group-name "oncolife-ecs-sg" \
    --description "OncoLife ECS Security Group" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)
echo "ECS SG: $SG_ECS"

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ECS \
    --protocol tcp --port 8000 \
    --source-group $SG_ALB

# Allow Doctor API port
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ECS \
    --protocol tcp --port 8001 \
    --source-group $SG_ALB

# RDS Security Group
SG_RDS=$(aws ec2 create-security-group \
    --group-name "oncolife-rds-sg" \
    --description "OncoLife RDS Security Group" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)
echo "RDS SG: $SG_RDS"

aws ec2 authorize-security-group-ingress \
    --group-id $SG_RDS \
    --protocol tcp --port 5432 \
    --source-group $SG_ECS
```

### Step 1.4: Create RDS PostgreSQL

```powershell
# Variables (fill in your subnet IDs)
$PRIVATE_SUBNET_1 = "subnet-zzzzzzzzz"
$PRIVATE_SUBNET_2 = "subnet-wwwwwwwww"
$SG_RDS = "sg-xxxxxxxxx"  # from previous step
$DB_PASSWORD = "YourSecurePassword123!"  # Change this!

# Create DB Subnet Group
aws rds create-db-subnet-group `
    --db-subnet-group-name "oncolife-db-subnet" `
    --db-subnet-group-description "OncoLife Database Subnets" `
    --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2

# Create RDS Instance (takes 10-15 minutes)
aws rds create-db-instance `
    --db-instance-identifier "oncolife-db" `
    --db-instance-class "db.t3.medium" `
    --engine "postgres" `
    --engine-version "15" `
    --master-username "oncolife_admin" `
    --master-user-password $DB_PASSWORD `
    --allocated-storage 100 `
    --storage-type "gp3" `
    --storage-encrypted `
    --vpc-security-group-ids $SG_RDS `
    --db-subnet-group-name "oncolife-db-subnet" `
    --no-publicly-accessible `
    --backup-retention-period 7

Write-Host "RDS creating... This takes 10-15 minutes."
Write-Host "Run: aws rds describe-db-instances --db-instance-identifier oncolife-db --query 'DBInstances[0].DBInstanceStatus'"
```

**Wait for RDS to be available:**
```powershell
# Check status (run repeatedly until "available")
aws rds describe-db-instances `
    --db-instance-identifier "oncolife-db" `
    --query 'DBInstances[0].DBInstanceStatus' --output text

# When ready, get the endpoint
$RDS_ENDPOINT = (aws rds describe-db-instances `
    --db-instance-identifier "oncolife-db" `
    --query 'DBInstances[0].Endpoint.Address' --output text)

Write-Host "RDS Endpoint: $RDS_ENDPOINT"
```

### Step 1.5: Create Cognito User Pool

```powershell
# Create User Pool
$POOL_RESULT = (aws cognito-idp create-user-pool `
    --pool-name "oncolife-patients" `
    --auto-verified-attributes "email" `
    --username-attributes "email" `
    --mfa-configuration "OFF" `
    --policies '{"PasswordPolicy":{"MinimumLength":8,"RequireUppercase":true,"RequireLowercase":true,"RequireNumbers":true,"RequireSymbols":true}}' `
    --admin-create-user-config '{"AllowAdminCreateUserOnly":true}' `
    --query 'UserPool.Id' --output text)

Write-Host "User Pool ID: $POOL_RESULT"

# Create App Client
$CLIENT_RESULT = (aws cognito-idp create-user-pool-client `
    --user-pool-id $POOL_RESULT `
    --client-name "patient-api-client" `
    --generate-secret `
    --explicit-auth-flows "ADMIN_NO_SRP_AUTH" "ALLOW_REFRESH_TOKEN_AUTH" "ALLOW_USER_PASSWORD_AUTH" `
    --query 'UserPoolClient.[ClientId,ClientSecret]' --output text)

Write-Host "Client ID and Secret: $CLIENT_RESULT"
```

### Step 1.6: Create S3 Buckets

```powershell
# Create Referrals Bucket
aws s3api create-bucket `
    --bucket "oncolife-referrals-$ACCOUNT_ID" `
    --region $AWS_REGION `
    --create-bucket-configuration LocationConstraint=$AWS_REGION

# Enable encryption
aws s3api put-bucket-encryption `
    --bucket "oncolife-referrals-$ACCOUNT_ID" `
    --server-side-encryption-configuration '{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"aws:kms\"}}]}'

# Block public access
aws s3api put-public-access-block `
    --bucket "oncolife-referrals-$ACCOUNT_ID" `
    --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Create Education Bucket (same settings)
aws s3api create-bucket `
    --bucket "oncolife-education-$ACCOUNT_ID" `
    --region $AWS_REGION `
    --create-bucket-configuration LocationConstraint=$AWS_REGION

aws s3api put-bucket-encryption `
    --bucket "oncolife-education-$ACCOUNT_ID" `
    --server-side-encryption-configuration '{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"aws:kms\"}}]}'

aws s3api put-public-access-block `
    --bucket "oncolife-education-$ACCOUNT_ID" `
    --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

Write-Host "Buckets created: oncolife-referrals-$ACCOUNT_ID, oncolife-education-$ACCOUNT_ID"
```

### Step 1.7: Create Secrets in Secrets Manager

```powershell
# Database credentials (replace with your values!)
$DB_SECRET = @{
    host = $RDS_ENDPOINT
    port = "5432"
    username = "oncolife_admin"
    password = $DB_PASSWORD
    patient_db = "oncolife_patient"
    doctor_db = "oncolife_doctor"
} | ConvertTo-Json -Compress

aws secretsmanager create-secret `
    --name "oncolife/db" `
    --secret-string $DB_SECRET

# Cognito credentials
$COGNITO_SECRET = @{
    user_pool_id = $POOL_RESULT
    client_id = "YOUR_CLIENT_ID"      # From Step 1.5
    client_secret = "YOUR_SECRET"     # From Step 1.5
} | ConvertTo-Json -Compress

aws secretsmanager create-secret `
    --name "oncolife/cognito" `
    --secret-string $COGNITO_SECRET

# Fax webhook secret (generate a random one)
$WEBHOOK_SECRET = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})

aws secretsmanager create-secret `
    --name "oncolife/fax" `
    --secret-string "{`"webhook_secret`":`"$WEBHOOK_SECRET`"}"

Write-Host "Webhook Secret (save this): $WEBHOOK_SECRET"
```

---

## 4. Phase 2: Container Infrastructure

### Step 2.1: Create ECR Repositories

> ⚠️ **IMPORTANT**: Create repositories for ALL 4 applications upfront!

```powershell
# ==========================================
# BACKEND API REPOSITORIES
# ==========================================

# Patient API repository
aws ecr create-repository `
    --repository-name "oncolife-patient-api" `
    --image-scanning-configuration scanOnPush=true

# Doctor API repository
aws ecr create-repository `
    --repository-name "oncolife-doctor-api" `
    --image-scanning-configuration scanOnPush=true

# ==========================================
# FRONTEND WEB REPOSITORIES (if using ECS for frontend)
# ==========================================

# Patient Web repository
aws ecr create-repository `
    --repository-name "oncolife-patient-web" `
    --image-scanning-configuration scanOnPush=true

# Doctor Web repository
aws ecr create-repository `
    --repository-name "oncolife-doctor-web" `
    --image-scanning-configuration scanOnPush=true
```

**Verify repositories created:**
```powershell
aws ecr describe-repositories --query 'repositories[*].repositoryName'
# Expected: ["oncolife-patient-api", "oncolife-doctor-api", "oncolife-patient-web", "oncolife-doctor-web"]
```

### Step 2.2: Create CloudWatch Log Group

> ⚠️ **WINDOWS USERS**: Run this in PowerShell, NOT Git Bash!

```powershell
# Create log groups BEFORE creating ECS resources
aws logs create-log-group --log-group-name "/ecs/oncolife-patient-api"
aws logs create-log-group --log-group-name "/ecs/oncolife-doctor-api"

# Set retention
aws logs put-retention-policy `
    --log-group-name "/ecs/oncolife-patient-api" `
    --retention-in-days 30

aws logs put-retention-policy `
    --log-group-name "/ecs/oncolife-doctor-api" `
    --retention-in-days 30
```

### Step 2.3: Create ECS Cluster

> ⚠️ **If you get "InvalidParameterException" here, you skipped Step 1.1!**

```powershell
aws ecs create-cluster `
    --cluster-name "oncolife-production" `
    --capacity-providers "FARGATE" "FARGATE_SPOT" `
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1
```

### Step 2.4: Create IAM Roles

**Task Execution Role:**
```powershell
# Create trust policy file
@'
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
        "Action": "sts:AssumeRole"
    }]
}
'@ | Out-File -FilePath "trust-policy.json" -Encoding utf8

# Create role
aws iam create-role `
    --role-name "ecsTaskExecutionRole" `
    --assume-role-policy-document "file://trust-policy.json"

# Attach managed policy
aws iam attach-role-policy `
    --role-name "ecsTaskExecutionRole" `
    --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"

# Allow Secrets Manager access
aws iam attach-role-policy `
    --role-name "ecsTaskExecutionRole" `
    --policy-arn "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
```

**Task Role (for application permissions):**
```powershell
# Create task role
aws iam create-role `
    --role-name "oncolifeTaskRole" `
    --assume-role-policy-document "file://trust-policy.json"

# Create inline policy
@'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
            "Resource": ["arn:aws:s3:::oncolife-*", "arn:aws:s3:::oncolife-*/*"]
        },
        {
            "Effect": "Allow",
            "Action": [
                "cognito-idp:AdminCreateUser",
                "cognito-idp:AdminDeleteUser",
                "cognito-idp:AdminInitiateAuth",
                "cognito-idp:AdminRespondToAuthChallenge",
                "cognito-idp:AdminGetUser"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": ["ses:SendEmail", "ses:SendRawEmail"],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": ["sns:Publish"],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": ["textract:AnalyzeDocument", "textract:StartDocumentAnalysis", "textract:GetDocumentAnalysis"],
            "Resource": "*"
        }
    ]
}
'@ | Out-File -FilePath "task-policy.json" -Encoding utf8

aws iam put-role-policy `
    --role-name "oncolifeTaskRole" `
    --policy-name "OncolifePermissions" `
    --policy-document "file://task-policy.json"

# Cleanup
Remove-Item "trust-policy.json", "task-policy.json"
```

### Step 2.5: Create ALBs and Target Groups (Patient + Doctor)

> ⚠️ **You need TWO separate ALBs** - one for Patient API and one for Doctor API!

#### 2.5.1: Patient API ALB

```powershell
# Get your public subnet IDs
$PUBLIC_SUBNET_1 = "subnet-xxxxxxxxx"  # From Step 1.2
$PUBLIC_SUBNET_2 = "subnet-yyyyyyyyy"
$SG_ALB = "sg-xxxxxxxxx"  # From Step 1.3
$VPC_ID = "vpc-xxxxxxxxx"  # Your VPC ID

# ==========================================
# PATIENT API ALB (Port 8000)
# ==========================================

# Create Patient ALB
$PATIENT_ALB_ARN = (aws elbv2 create-load-balancer `
    --name "oncolife-patient-alb" `
    --subnets $PUBLIC_SUBNET_1 $PUBLIC_SUBNET_2 `
    --security-groups $SG_ALB `
    --scheme "internet-facing" `
    --type "application" `
    --query 'LoadBalancers[0].LoadBalancerArn' --output text)

Write-Host "Patient ALB ARN: $PATIENT_ALB_ARN"

# Create Patient Target Group
$PATIENT_TG_ARN = (aws elbv2 create-target-group `
    --name "patient-api-tg" `
    --protocol "HTTP" `
    --port 8000 `
    --vpc-id $VPC_ID `
    --target-type "ip" `
    --health-check-path "/health" `
    --health-check-interval-seconds 30 `
    --healthy-threshold-count 2 `
    --unhealthy-threshold-count 3 `
    --query 'TargetGroups[0].TargetGroupArn' --output text)

Write-Host "Patient Target Group ARN: $PATIENT_TG_ARN"

# Create HTTP Listener (redirect to HTTPS)
aws elbv2 create-listener `
    --load-balancer-arn $PATIENT_ALB_ARN `
    --protocol "HTTP" `
    --port 80 `
    --default-actions 'Type=redirect,RedirectConfig={Protocol=HTTPS,Port=443,StatusCode=HTTP_301}'

# Get Patient ALB DNS
$PATIENT_ALB_DNS = (aws elbv2 describe-load-balancers `
    --load-balancer-arns $PATIENT_ALB_ARN `
    --query 'LoadBalancers[0].DNSName' --output text)

Write-Host "Patient API URL: http://$PATIENT_ALB_DNS"
```

#### 2.5.2: Doctor API ALB

```powershell
# ==========================================
# DOCTOR API ALB (Port 8001)
# ==========================================

# Create Doctor ALB
$DOCTOR_ALB_ARN = (aws elbv2 create-load-balancer `
    --name "oncolife-doctor-alb" `
    --subnets $PUBLIC_SUBNET_1 $PUBLIC_SUBNET_2 `
    --security-groups $SG_ALB `
    --scheme "internet-facing" `
    --type "application" `
    --query 'LoadBalancers[0].LoadBalancerArn' --output text)

Write-Host "Doctor ALB ARN: $DOCTOR_ALB_ARN"

# Create Doctor Target Group
$DOCTOR_TG_ARN = (aws elbv2 create-target-group `
    --name "doctor-api-tg" `
    --protocol "HTTP" `
    --port 8001 `
    --vpc-id $VPC_ID `
    --target-type "ip" `
    --health-check-path "/health" `
    --health-check-interval-seconds 30 `
    --healthy-threshold-count 2 `
    --unhealthy-threshold-count 3 `
    --query 'TargetGroups[0].TargetGroupArn' --output text)

Write-Host "Doctor Target Group ARN: $DOCTOR_TG_ARN"

# Create HTTP Listener (redirect to HTTPS)
aws elbv2 create-listener `
    --load-balancer-arn $DOCTOR_ALB_ARN `
    --protocol "HTTP" `
    --port 80 `
    --default-actions 'Type=redirect,RedirectConfig={Protocol=HTTPS,Port=443,StatusCode=HTTP_301}'

# Get Doctor ALB DNS
$DOCTOR_ALB_DNS = (aws elbv2 describe-load-balancers `
    --load-balancer-arns $DOCTOR_ALB_ARN `
    --query 'LoadBalancers[0].DNSName' --output text)

Write-Host "Doctor API URL: http://$DOCTOR_ALB_DNS"
```

#### 2.5.3: Summary of ALBs Created

| Component | Name | Port | Health Check |
|-----------|------|------|--------------|
| **Patient ALB** | `oncolife-patient-alb` | 80/443 → 8000 | `/health` |
| **Doctor ALB** | `oncolife-doctor-alb` | 80/443 → 8001 | `/health` |

> 📝 **Note**: For HTTPS, you need ACM certificates. See Step 2.5.4 below.

#### 2.5.4: (Optional) Add HTTPS Listeners with ACM Certificate

```powershell
# First, request certificates in ACM Console or via CLI:
# aws acm request-certificate --domain-name api.oncolife.com --validation-method DNS

# Then create HTTPS listeners:
# Patient HTTPS Listener
aws elbv2 create-listener `
    --load-balancer-arn $PATIENT_ALB_ARN `
    --protocol "HTTPS" `
    --port 443 `
    --certificates CertificateArn=arn:aws:acm:REGION:ACCOUNT:certificate/CERT_ID `
    --default-actions "Type=forward,TargetGroupArn=$PATIENT_TG_ARN"

# Doctor HTTPS Listener
aws elbv2 create-listener `
    --load-balancer-arn $DOCTOR_ALB_ARN `
    --protocol "HTTPS" `
    --port 443 `
    --certificates CertificateArn=arn:aws:acm:REGION:ACCOUNT:certificate/CERT_ID `
    --default-actions "Type=forward,TargetGroupArn=$DOCTOR_TG_ARN"
```

### Step 2.6: Register Task Definitions (Patient + Doctor)

> ⚠️ **You need TWO task definitions** - one for Patient API and one for Doctor API!

#### 2.6.1: Patient API Task Definition

Create `patient-task-definition.json`:

```json
{
  "family": "oncolife-patient-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/oncolifeTaskRole",
  "containerDefinitions": [
    {
      "name": "patient-api",
      "image": "ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/oncolife-patient-api:latest",
      "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
      "essential": true,
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "DEBUG", "value": "false"},
        {"name": "LOG_LEVEL", "value": "INFO"},
        {"name": "AWS_REGION", "value": "us-west-2"}
      ],
      "secrets": [
        {"name": "PATIENT_DB_HOST", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/db-XXXXXX:host::"},
        {"name": "PATIENT_DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/db-XXXXXX:password::"},
        {"name": "PATIENT_DB_USER", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/db-XXXXXX:username::"},
        {"name": "PATIENT_DB_NAME", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/db-XXXXXX:patient_db::"},
        {"name": "COGNITO_USER_POOL_ID", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/cognito-XXXXXX:user_pool_id::"},
        {"name": "COGNITO_CLIENT_ID", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/cognito-XXXXXX:client_id::"},
        {"name": "COGNITO_CLIENT_SECRET", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/cognito-XXXXXX:client_secret::"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/oncolife-patient-api",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

> ⚠️ **IMPORTANT**: Replace `ACCOUNT_ID` and the `-XXXXXX` suffix with your actual secret ARNs!

**Get your secret ARNs:**
```powershell
aws secretsmanager describe-secret --secret-id "oncolife/db" --query 'ARN' --output text
aws secretsmanager describe-secret --secret-id "oncolife/cognito" --query 'ARN' --output text
```

**Register the Patient task definition:**
```powershell
# First, update the JSON file with your ACCOUNT_ID
(Get-Content patient-task-definition.json) -replace 'ACCOUNT_ID', $ACCOUNT_ID | Set-Content patient-task-definition.json

aws ecs register-task-definition --cli-input-json "file://patient-task-definition.json"
```

#### 2.6.2: Doctor API Task Definition

Create `doctor-task-definition.json`:

```json
{
  "family": "oncolife-doctor-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/oncolifeTaskRole",
  "containerDefinitions": [
    {
      "name": "doctor-api",
      "image": "ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/oncolife-doctor-api:latest",
      "portMappings": [{"containerPort": 8001, "protocol": "tcp"}],
      "essential": true,
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "DEBUG", "value": "false"},
        {"name": "LOG_LEVEL", "value": "INFO"},
        {"name": "AWS_REGION", "value": "us-west-2"}
      ],
      "secrets": [
        {"name": "DOCTOR_DB_HOST", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/db-XXXXXX:host::"},
        {"name": "DOCTOR_DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/db-XXXXXX:password::"},
        {"name": "DOCTOR_DB_USER", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/db-XXXXXX:username::"},
        {"name": "DOCTOR_DB_NAME", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/db-XXXXXX:doctor_db::"},
        {"name": "COGNITO_USER_POOL_ID", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/cognito-XXXXXX:user_pool_id::"},
        {"name": "COGNITO_CLIENT_ID", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/cognito-XXXXXX:client_id::"},
        {"name": "COGNITO_CLIENT_SECRET", "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/cognito-XXXXXX:client_secret::"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/oncolife-doctor-api",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8001/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

**Register the Doctor task definition:**
```powershell
(Get-Content doctor-task-definition.json) -replace 'ACCOUNT_ID', $ACCOUNT_ID | Set-Content doctor-task-definition.json

aws ecs register-task-definition --cli-input-json "file://doctor-task-definition.json"
```

### Step 2.7: Create ECS Services (Patient + Doctor)

> ⚠️ **IMPORTANT**: Create the services ONLY after the task definitions exist!

#### 2.7.1: Patient API Service

```powershell
$PRIVATE_SUBNET_1 = "subnet-zzzzzzzzz"  # Private subnets!
$PRIVATE_SUBNET_2 = "subnet-wwwwwwwww"
$SG_ECS = "sg-xxxxxxxxx"

# Create Patient API Service
aws ecs create-service `
    --cluster "oncolife-production" `
    --service-name "patient-api-service" `
    --task-definition "oncolife-patient-api" `
    --desired-count 2 `
    --launch-type "FARGATE" `
    --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_1,$PRIVATE_SUBNET_2],securityGroups=[$SG_ECS],assignPublicIp=DISABLED}" `
    --load-balancers "targetGroupArn=$PATIENT_TG_ARN,containerName=patient-api,containerPort=8000" `
    --health-check-grace-period-seconds 120

Write-Host "Patient API Service created!"
```

#### 2.7.2: Doctor API Service

```powershell
# Create Doctor API Service
aws ecs create-service `
    --cluster "oncolife-production" `
    --service-name "doctor-api-service" `
    --task-definition "oncolife-doctor-api" `
    --desired-count 2 `
    --launch-type "FARGATE" `
    --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_1,$PRIVATE_SUBNET_2],securityGroups=[$SG_ECS],assignPublicIp=DISABLED}" `
    --load-balancers "targetGroupArn=$DOCTOR_TG_ARN,containerName=doctor-api,containerPort=8001" `
    --health-check-grace-period-seconds 120

Write-Host "Doctor API Service created!"
```

#### 2.7.3: Verify Services Created

```powershell
# Check both services
aws ecs describe-services `
    --cluster "oncolife-production" `
    --services "patient-api-service" "doctor-api-service" `
    --query 'services[*].{name:serviceName,status:status,desired:desiredCount,running:runningCount}'
```

---

## 5. Phase 3: Build and Deploy

> 📝 **Note:** This phase covers 4 applications:
> - Patient API (backend)
> - Doctor API (backend)
> - Patient Web (frontend)
> - Doctor Web (frontend)

### Step 3.1: Build and Push Docker Images (APIs)

```powershell
cd Oncolife_Monolith

# Login to ECR (do this once)
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com"
```

#### 3.1.1: Build and Push Patient API

```powershell
# Build Patient API image
docker build `
    -t "oncolife-patient-api:latest" `
    -f "apps/patient-platform/patient-api/Dockerfile" `
    "apps/patient-platform/patient-api/"

# Tag and push
docker tag "oncolife-patient-api:latest" "$ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/oncolife-patient-api:latest"
docker push "$ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/oncolife-patient-api:latest"

Write-Host "Patient API image pushed!"
```

#### 3.1.2: Build and Push Doctor API

```powershell
# Build Doctor API image
docker build `
    -t "oncolife-doctor-api:latest" `
    -f "apps/doctor-platform/doctor-api/Dockerfile" `
    "apps/doctor-platform/doctor-api/"

# Tag and push
docker tag "oncolife-doctor-api:latest" "$ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/oncolife-doctor-api:latest"
docker push "$ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/oncolife-doctor-api:latest"

Write-Host "Doctor API image pushed!"
```

### Step 3.2: Force New Deployments

```powershell
# Deploy Patient API
aws ecs update-service `
    --cluster "oncolife-production" `
    --service "patient-api-service" `
    --force-new-deployment

# Deploy Doctor API
aws ecs update-service `
    --cluster "oncolife-production" `
    --service "doctor-api-service" `
    --force-new-deployment

# Monitor both deployments
aws ecs describe-services `
    --cluster "oncolife-production" `
    --services "patient-api-service" "doctor-api-service" `
    --query 'services[*].{name:serviceName,desired:desiredCount,running:runningCount,status:status}'
```

### Step 3.3: Monitor Deployment Progress

```powershell
# Watch deployments (run repeatedly until running = desired)
while ($true) {
    Clear-Host
    Write-Host "=== ECS Service Status ===" -ForegroundColor Cyan
    aws ecs describe-services `
        --cluster "oncolife-production" `
        --services "patient-api-service" "doctor-api-service" `
        --query 'services[*].{Service:serviceName,Status:status,Desired:desiredCount,Running:runningCount,Pending:pendingCount}' `
        --output table
    Start-Sleep -Seconds 10
}
# Press Ctrl+C to stop
```

### Step 3.4: Build and Deploy Frontend (Two Options)

> Choose ONE of these options for frontend deployment:
> - **Option A (Recommended):** S3 + CloudFront (lower cost, better performance)
> - **Option B:** Docker + ECS (containerized, same as APIs)

---

#### Option A: S3 + CloudFront (Recommended)

**Create S3 Buckets for Static Hosting:**
```powershell
# Create Patient Web bucket
aws s3api create-bucket `
    --bucket "oncolife-patient-web-$ACCOUNT_ID" `
    --region $AWS_REGION `
    --create-bucket-configuration LocationConstraint=$AWS_REGION

# Create Doctor Web bucket
aws s3api create-bucket `
    --bucket "oncolife-doctor-web-$ACCOUNT_ID" `
    --region $AWS_REGION `
    --create-bucket-configuration LocationConstraint=$AWS_REGION

# Enable static website hosting
aws s3 website "s3://oncolife-patient-web-$ACCOUNT_ID" `
    --index-document index.html `
    --error-document index.html

aws s3 website "s3://oncolife-doctor-web-$ACCOUNT_ID" `
    --index-document index.html `
    --error-document index.html
```

**Build and Upload Patient Web:**
```powershell
cd apps/patient-platform/patient-web

# Install dependencies and build
npm ci
$env:VITE_API_BASE_URL = "https://api.oncolife.com"
$env:VITE_WS_BASE_URL = "wss://api.oncolife.com"
npm run build

# Upload to S3
aws s3 sync dist/ "s3://oncolife-patient-web-$ACCOUNT_ID" --delete

# Set cache headers
aws s3 cp "s3://oncolife-patient-web-$ACCOUNT_ID" "s3://oncolife-patient-web-$ACCOUNT_ID" `
    --recursive --metadata-directive REPLACE `
    --cache-control "max-age=31536000,public" `
    --exclude "index.html"

aws s3 cp "s3://oncolife-patient-web-$ACCOUNT_ID/index.html" "s3://oncolife-patient-web-$ACCOUNT_ID/index.html" `
    --cache-control "no-cache,no-store,must-revalidate"
```

**Build and Upload Doctor Web:**
```powershell
cd apps/doctor-platform/doctor-web

npm ci
$env:VITE_API_BASE_URL = "https://doctor-api.oncolife.com"
$env:VITE_PATIENT_API_URL = "https://api.oncolife.com"
npm run build

aws s3 sync dist/ "s3://oncolife-doctor-web-$ACCOUNT_ID" --delete
```

**Create CloudFront Distributions (via Console recommended):**
1. Go to CloudFront Console → Create Distribution
2. Origin: S3 bucket endpoint
3. Configure: HTTPS redirect, custom domain, ACM certificate
4. Error pages: 403/404 → /index.html (for SPA routing)

---

#### Option B: Docker + ECS (Containerized)

**Create ECR Repositories for Frontend:**
```powershell
aws ecr create-repository --repository-name "oncolife-patient-web" --image-scanning-configuration scanOnPush=true
aws ecr create-repository --repository-name "oncolife-doctor-web" --image-scanning-configuration scanOnPush=true
```

**Build and Push Patient Web:**

> ⚠️ **IMPORTANT**: Frontend builds MUST run from the **monorepo root** directory (not inside the app folder). This is because the frontends depend on shared packages (`packages/ui-components`).

```powershell
# IMPORTANT: Run from monorepo root!
cd Oncolife_Monolith

# Build Patient Web with production API URL
docker build `
    -f "apps/patient-platform/patient-web/Dockerfile" `
    --build-arg VITE_API_BASE_URL=https://api.oncolife.com `
    --build-arg VITE_WS_BASE_URL=wss://api.oncolife.com `
    -t "oncolife-patient-web:latest" .

docker tag "oncolife-patient-web:latest" "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/oncolife-patient-web:latest"
docker push "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/oncolife-patient-web:latest"
```

**Build and Push Doctor Web:**
```powershell
# IMPORTANT: Run from monorepo root!
cd Oncolife_Monolith

# Build Doctor Web with production API URL
docker build `
    -f "apps/doctor-platform/doctor-web/Dockerfile" `
    --build-arg VITE_API_BASE_URL=https://doctor-api.oncolife.com `
    --build-arg VITE_PATIENT_API_URL=https://api.oncolife.com `
    -t "oncolife-doctor-web:latest" .

docker tag "oncolife-doctor-web:latest" "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/oncolife-doctor-web:latest"
docker push "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/oncolife-doctor-web:latest"
```

**Create ECS Services for Frontend:**
> Similar to API services, but using port 80 and the web Docker images.
> Use separate ALBs or path-based routing on existing ALBs.

---

## 6. Phase 4: Database Setup

### Step 4.1: Connect to RDS

You'll need a bastion host or SSM Session Manager to connect to RDS in private subnets.

**Option A: Using a Bastion Host**
```bash
# SSH to bastion, then connect
psql -h YOUR_RDS_ENDPOINT -U oncolife_admin -d postgres
```

**Option B: Using RDS Query Editor (AWS Console)**
1. Go to RDS Console → Query Editor
2. Connect to your database

### Step 4.2: Create Databases

```sql
CREATE DATABASE oncolife_patient;
CREATE DATABASE oncolife_doctor;
GRANT ALL PRIVILEGES ON DATABASE oncolife_patient TO oncolife_admin;
GRANT ALL PRIVILEGES ON DATABASE oncolife_doctor TO oncolife_admin;
```

### Step 4.3: Run Migrations (Alembic)

From a machine that can reach RDS (bastion or local with VPN):

```bash
cd apps/patient-platform/patient-api
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt

# Set environment variables
export PATIENT_DB_HOST=your-rds-endpoint
export PATIENT_DB_PORT=5432
export PATIENT_DB_NAME=oncolife_patient
export PATIENT_DB_USER=oncolife_admin
export PATIENT_DB_PASSWORD=your_password

# OR use DATABASE_URL
export DATABASE_URL=postgresql://oncolife_admin:password@your-rds-endpoint:5432/oncolife_patient

# Run migrations
alembic upgrade head
echo "Patient API migrations complete!"

# Repeat for Doctor API
cd ../../doctor-platform/doctor-api
export POSTGRES_DOCTOR_DB=oncolife_doctor
export DATABASE_URL=postgresql://oncolife_admin:password@your-rds-endpoint:5432/oncolife_doctor
alembic upgrade head
echo "Doctor API migrations complete!"
```

**Alternative: Direct Table Creation (Quick Setup)**

```bash
cd src
python -c "
from db.base import Base
from db.session import engine
from db.models import *
Base.metadata.create_all(bind=engine)
print('Tables created!')
"
```

### Step 4.4: Seed Education Data

```bash
# Seed education PDF metadata (run from patient-api directory)
cd apps/patient-platform/patient-api
python scripts/seed_education_pdfs.py
```

---

## 7. Phase 5: Verification

### Step 5.1: Get ALB DNS Names

```powershell
# Get Patient API URL
$PATIENT_ALB_DNS = (aws elbv2 describe-load-balancers `
    --names "oncolife-patient-alb" `
    --query 'LoadBalancers[0].DNSName' --output text)

Write-Host "Patient API URL: http://$PATIENT_ALB_DNS"

# Get Doctor API URL
$DOCTOR_ALB_DNS = (aws elbv2 describe-load-balancers `
    --names "oncolife-doctor-alb" `
    --query 'LoadBalancers[0].DNSName' --output text)

Write-Host "Doctor API URL: http://$DOCTOR_ALB_DNS"
```

### Step 5.2: Test Health Endpoints

```powershell
# Test Patient API
Write-Host "Testing Patient API..."
Invoke-RestMethod -Uri "http://$PATIENT_ALB_DNS/health" -Method GET

# Test Doctor API
Write-Host "Testing Doctor API..."
Invoke-RestMethod -Uri "http://$DOCTOR_ALB_DNS/health" -Method GET
```

**Expected response for both:**
```json
{"status":"healthy","timestamp":"...","version":"1.0.0"}
```

### Step 5.3: Check CloudWatch Logs

```powershell
# Patient API logs
Write-Host "=== Patient API Logs ===" -ForegroundColor Cyan
aws logs tail "/ecs/oncolife-patient-api" --since 5m

# Doctor API logs
Write-Host "=== Doctor API Logs ===" -ForegroundColor Cyan
aws logs tail "/ecs/oncolife-doctor-api" --since 5m
```

### Step 5.4: Test API Endpoints

```powershell
# Test Patient Auth endpoint
Invoke-RestMethod -Uri "http://$PATIENT_ALB_DNS/api/v1/auth/status" -Method GET

# Test Doctor Auth endpoint
Invoke-RestMethod -Uri "http://$DOCTOR_ALB_DNS/api/v1/auth/status" -Method GET
```

### Step 5.5: Verify Target Group Health

```powershell
# Check Patient Target Group health
aws elbv2 describe-target-health `
    --target-group-arn $PATIENT_TG_ARN `
    --query 'TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}'

# Check Doctor Target Group health
aws elbv2 describe-target-health `
    --target-group-arn $DOCTOR_TG_ARN `
    --query 'TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}'
```

**Expected:** All targets should show `"Health": "healthy"`

---

## 8. Phase 6: CI/CD Setup (Automated Deployments)

GitHub Actions is pre-configured for automated CI/CD. Follow these steps to enable it.

> 📖 **For comprehensive CI/CD documentation**, see the [CI/CD Pipeline Guide](CI_CD_PIPELINE_GUIDE.md) which includes:
> - Detailed workflow explanations
> - Complete IAM policy configurations
> - Troubleshooting guide
> - Rollback procedures

### Step 6.1: Configure GitHub Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AWS_ACCOUNT_ID` | Your AWS account ID | `123456789012` |
| `AWS_ACCESS_KEY_ID` | IAM user access key | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key | `wJalrXUtnFEMI/K7MDENG/...` |
| `PATIENT_DATABASE_URL` | Patient DB connection string | `postgresql://user:pass@host:5432/oncolife_patient` |
| `DOCTOR_DATABASE_URL` | Doctor DB connection string | `postgresql://user:pass@host:5432/oncolife_doctor` |
| `PATIENT_API_URL` | Patient API URL (ALB DNS or custom domain) | `http://oncolife-patient-alb-xxx.elb.amazonaws.com` |
| `PATIENT_WS_URL` | WebSocket URL (ALB DNS or custom domain) | `ws://oncolife-patient-alb-xxx.elb.amazonaws.com` |
| `DOCTOR_API_URL` | Doctor API URL (ALB DNS or custom domain) | `http://oncolife-doctor-alb-xxx.elb.amazonaws.com` |

> 💡 **No Custom Domain?** Use ALB DNS names directly! See [Using ALB URLs Without Custom Domains](#using-alb-urls-without-custom-domains) below.

### Step 6.2: Create IAM User for GitHub Actions

```powershell
# Create IAM user for CI/CD
aws iam create-user --user-name github-actions-oncolife

# Create access key
aws iam create-access-key --user-name github-actions-oncolife
# Save the AccessKeyId and SecretAccessKey as GitHub secrets!

# Create policy document
@'
{
    "Version": "2012-10-17",
    "Statement": [
        {
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
            "Effect": "Allow",
            "Action": [
                "ecs:UpdateService",
                "ecs:DescribeServices",
                "ecs:DescribeClusters"
            ],
            "Resource": "*"
        }
    ]
}
'@ | Out-File -FilePath "github-actions-policy.json" -Encoding utf8

# Attach policy
aws iam put-user-policy `
    --user-name github-actions-oncolife `
    --policy-name OncolifeDeployPolicy `
    --policy-document "file://github-actions-policy.json"

Remove-Item "github-actions-policy.json"
```

### Step 6.3: Test CI Workflow

1. Push a commit to a feature branch
2. Create a Pull Request to `main`
3. Watch the **Actions** tab for CI to run
4. CI should: Lint → Test → Build Docker images

### Step 6.4: Test CD Workflow

1. Merge a PR to `main`
2. Watch the **Actions** tab for CD to run
3. CD should: Build → Push to ECR → Run Migrations → Deploy to ECS

### Step 6.5: Manual Deployment (Optional)

You can trigger deployments manually:

1. Go to **Actions** → **Deploy to AWS**
2. Click **Run workflow**
3. Select environment (staging/production)
4. Click **Run workflow**

### CI/CD Workflow Files

| File | Trigger | Purpose |
|------|---------|---------|
| `.github/workflows/ci.yml` | PR, push to main | Lint, test, build |
| `.github/workflows/deploy.yml` | Merge to main | Build, push, migrate, deploy |

---

## Using ALB URLs Without Custom Domains

> 🎯 **Custom domains are OPTIONAL!** You can deploy and test with just the ALB DNS names.

### When to Use ALB URLs Directly

| Scenario | Use ALB DNS | Use Custom Domain |
|----------|-------------|-------------------|
| Development/Testing | ✅ Yes | ❌ Not needed |
| Staging Environment | ✅ Yes | ⚠️ Optional |
| Production (Internal) | ✅ Yes | ⚠️ Optional |
| Production (Public-facing) | ❌ | ✅ Recommended |

### Get Your ALB URLs

After creating ALBs in Phase 2, get your URLs:

```powershell
# Get Patient API URL
$PATIENT_ALB = aws elbv2 describe-load-balancers --names "oncolife-patient-alb" --query 'LoadBalancers[0].DNSName' --output text
Write-Host "Patient API URL: http://$PATIENT_ALB"
Write-Host "Patient WebSocket: ws://$PATIENT_ALB"

# Get Doctor API URL
$DOCTOR_ALB = aws elbv2 describe-load-balancers --names "oncolife-doctor-alb" --query 'LoadBalancers[0].DNSName' --output text
Write-Host "Doctor API URL: http://$DOCTOR_ALB"
```

**Example Output:**
```
Patient API URL: http://oncolife-patient-alb-1234567890.us-west-2.elb.amazonaws.com
Patient WebSocket: ws://oncolife-patient-alb-1234567890.us-west-2.elb.amazonaws.com
Doctor API URL: http://oncolife-doctor-alb-0987654321.us-west-2.elb.amazonaws.com
```

### Configure GitHub Secrets with ALB URLs

Use these URLs directly in your GitHub Secrets:

| Secret | Value Example |
|--------|---------------|
| `PATIENT_API_URL` | `http://oncolife-patient-alb-1234567890.us-west-2.elb.amazonaws.com` |
| `PATIENT_WS_URL` | `ws://oncolife-patient-alb-1234567890.us-west-2.elb.amazonaws.com` |
| `DOCTOR_API_URL` | `http://oncolife-doctor-alb-0987654321.us-west-2.elb.amazonaws.com` |

### Test Your APIs

```powershell
# Test Patient API
Invoke-RestMethod -Uri "http://$PATIENT_ALB/health"
# Expected: { "status": "healthy", ... }

# View Swagger UI
Start-Process "http://$PATIENT_ALB/docs"

# Test Doctor API
Invoke-RestMethod -Uri "http://$DOCTOR_ALB/health"
```

### Limitations of ALB URLs (vs Custom Domains)

| Feature | ALB URL | Custom Domain |
|---------|---------|---------------|
| **HTTP** | ✅ Works | ✅ Works |
| **HTTPS** | ❌ Not available | ✅ With ACM certificate |
| **WebSocket (ws://)** | ✅ Works | ✅ Works |
| **WebSocket (wss://)** | ❌ Not available | ✅ With ACM certificate |
| **URL appearance** | Long AWS URL | Your branded URL |
| **SEO/Branding** | ❌ Not ideal | ✅ Professional |

> 📝 **When to Add Custom Domains**: Add them when you're ready for production, need HTTPS, or want professional branding. See Phase 7 below.

---

## 9. Troubleshooting Guide

### Container Won't Start

```powershell
# Get task ARN
$TASK_ARN = (aws ecs list-tasks `
    --cluster "oncolife-production" `
    --query 'taskArns[0]' --output text)

# Describe task for error
aws ecs describe-tasks `
    --cluster "oncolife-production" `
    --tasks $TASK_ARN `
    --query 'tasks[0].{status:lastStatus,reason:stoppedReason}'

# Check logs
aws logs tail "/ecs/oncolife-patient-api" --since 30m
```

### Database Connection Issues

```powershell
# Verify security group allows traffic
aws ec2 describe-security-groups `
    --group-ids $SG_RDS `
    --query 'SecurityGroups[0].IpPermissions'

# Check RDS status
aws rds describe-db-instances `
    --db-instance-identifier "oncolife-db" `
    --query 'DBInstances[0].{status:DBInstanceStatus,endpoint:Endpoint.Address}'
```

### Secrets Not Found

```powershell
# List secrets
aws secretsmanager list-secrets --query 'SecretList[?starts_with(Name, `oncolife`)].Name'

# Get secret ARN (needed for task definition)
aws secretsmanager describe-secret --secret-id "oncolife/db" --query 'ARN'
```

---

## 10. Common Errors and Fixes

### Error: `InvalidParameterException` on Log Groups

**Cause:** Windows Git Bash converts `/ecs/...` to `C:/Program Files/Git/ecs/...`

**Fix:** Use **PowerShell** instead of Git Bash for all AWS CLI commands.

```powershell
# Correct (PowerShell):
aws logs create-log-group --log-group-name "/ecs/oncolife-patient-api"
```

---

### Error: `InvalidParameterException` on CreateCluster

**Cause:** ECS Service-Linked Role doesn't exist.

**Fix:** Create the role FIRST:

```powershell
aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com
```

---

### Error: `ServiceNotFoundException` on UpdateService

**Cause:** Trying to update a service that doesn't exist yet.

**Fix:** Use `create-service` first, not `update-service`:

```powershell
# Wrong (service doesn't exist):
aws ecs update-service --cluster ... --service patient-api-service ...

# Correct:
aws ecs create-service --cluster ... --service-name patient-api-service ...
```

---

### Error: `InvalidInput` on CreateServiceLinkedRole

**Message:** "Service role name AWSServiceRoleForECS has been taken"

**Cause:** Role already exists - this is OK!

**Fix:** Ignore this error and continue.

---

### Error: Task Stuck in PENDING

**Cause:** Usually networking or IAM issues.

**Fix:**
1. Check security groups allow traffic
2. Check subnets have route to NAT Gateway
3. Check task execution role has permissions
4. Check secrets ARNs are correct in task definition

---

### Error: Container Exits Immediately

**Cause:** Application crash on startup.

**Fix:**
```powershell
# Check logs
aws logs tail "/ecs/oncolife-patient-api" --since 10m

# Common issues:
# - Missing environment variables
# - Database connection failed
# - Import errors
```

---

### Error: Frontend Docker Build Fails - Cannot find module '@oncolife/ui-components'

**Cause:** Docker build context doesn't include the shared packages folder.

**Fix:** Build from the **monorepo root**, not from inside the app folder:

```powershell
# ❌ WRONG - this will fail!
cd apps/patient-platform/patient-web
docker build -t "oncolife-patient-web:latest" .

# ✅ CORRECT - run from monorepo root
cd Oncolife_Monolith
docker build -f apps/patient-platform/patient-web/Dockerfile -t "oncolife-patient-web:latest" .
```

The Dockerfiles for `patient-web` and `doctor-web` are designed to run from the monorepo root because they need access to `packages/ui-components`.

---

### Error: CI/CD Deploy Workflow Fails in 7 Seconds

**Cause:** GitHub Secrets are not configured.

**Fix:** Configure these secrets in your GitHub repository:
1. Go to: `https://github.com/YOUR_USER/Oncolife_Monolith/settings/secrets/actions`
2. Add all required secrets (see Phase 6 CI/CD Setup section)

Required secrets:
- `AWS_ACCOUNT_ID`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `PATIENT_DATABASE_URL`
- `DOCTOR_DATABASE_URL`
- `PATIENT_API_URL`
- `PATIENT_WS_URL`
- `DOCTOR_API_URL`

---

## Quick Reference: All Required IDs

> ⚠️ **IMPORTANT FOR TEAM**: As you complete each deployment step, **FILL IN THE VALUES BELOW** and save this document. These IDs are needed for:
> - Task definitions
> - CI/CD GitHub Secrets
> - Troubleshooting
> - Future deployments
>
> **Copy this section to a secure location (e.g., AWS Secrets Manager, 1Password, or team wiki) after filling in.**

### 📝 Fill In During Deployment:

```
AWS Account ID:        ____________________  ← Get with: aws sts get-caller-identity
AWS Region:            ____________________  ← e.g., us-west-2

VPC (from Phase 1, Step 1.2):
  VPC ID:              vpc-________________
  Public Subnet 1:     subnet-______________  (for ALB)
  Public Subnet 2:     subnet-______________  (for ALB)
  Private Subnet 1:    subnet-______________  (for ECS tasks)
  Private Subnet 2:    subnet-______________  (for ECS tasks)

Security Groups (from Phase 1, Step 1.3):
  ALB SG:              sg-__________________
  ECS SG:              sg-__________________
  RDS SG:              sg-__________________

RDS Database (from Phase 1, Step 1.4):
  Endpoint:            __________________.rds.amazonaws.com
  Port:                5432
  Master Username:     oncolife_admin
  Master Password:     ____________________  ← KEEP SECURE!

Cognito (from Phase 1, Step 1.5):
  User Pool ID:        us-west-2_____________
  Client ID:           __________________________
  Client Secret:       __________________________  ← KEEP SECURE!

S3 Buckets (from Phase 1, Step 1.6):
  Referrals:           oncolife-referrals-${ACCOUNT_ID}
  Education:           oncolife-education-${ACCOUNT_ID}

PATIENT API (from Phase 2):
  ALB ARN:             arn:aws:elasticloadbalancing:...
  ALB DNS:             oncolife-patient-alb-________.elb.amazonaws.com
  Target Group ARN:    arn:aws:elasticloadbalancing:...
  ECS Service:         patient-api-service

DOCTOR API (from Phase 2):
  ALB ARN:             arn:aws:elasticloadbalancing:...
  ALB DNS:             oncolife-doctor-alb-________.elb.amazonaws.com
  Target Group ARN:    arn:aws:elasticloadbalancing:...
  ECS Service:         doctor-api-service

Secrets Manager ARNs (from Phase 1, Step 1.7):
  oncolife/db:         arn:aws:secretsmanager:us-west-2:${ACCOUNT_ID}:secret:oncolife/db-______
  oncolife/cognito:    arn:aws:secretsmanager:us-west-2:${ACCOUNT_ID}:secret:oncolife/cognito-______
  oncolife/fax:        arn:aws:secretsmanager:us-west-2:${ACCOUNT_ID}:secret:oncolife/fax-______

ALB URLs (Available Immediately - No Domain Required):
  Patient API:         http://oncolife-patient-alb-________.elb.amazonaws.com
  Patient WebSocket:   ws://oncolife-patient-alb-________.elb.amazonaws.com
  Doctor API:          http://oncolife-doctor-alb-________.elb.amazonaws.com

FINAL URLs (OPTIONAL - after Route 53/CloudFront setup):
  Patient API:         https://___________________  (or use ALB URL above)
  Doctor API:          https://___________________  (or use ALB URL above)
  Patient Web:         https://___________________
  Doctor Web:          https://___________________
```

### 🔐 GitHub Secrets (for CI/CD - Phase 6):

Once deployment is complete, add these to GitHub Repository Settings → Secrets:

| Secret Name | Value From Above |
|-------------|------------------|
| `AWS_ACCOUNT_ID` | AWS Account ID |
| `AWS_ACCESS_KEY_ID` | IAM user access key (create dedicated CI/CD user) |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `PATIENT_DATABASE_URL` | `postgresql://oncolife_admin:PASSWORD@RDS_ENDPOINT:5432/oncolife_patient` |
| `DOCTOR_DATABASE_URL` | `postgresql://oncolife_admin:PASSWORD@RDS_ENDPOINT:5432/oncolife_doctor` |
| `PATIENT_API_URL` | **ALB URL** or custom domain (e.g., `http://oncolife-patient-alb-xxx.elb.amazonaws.com`) |
| `PATIENT_WS_URL` | **ALB URL** or custom domain (e.g., `ws://oncolife-patient-alb-xxx.elb.amazonaws.com`) |
| `DOCTOR_API_URL` | **ALB URL** or custom domain (e.g., `http://oncolife-doctor-alb-xxx.elb.amazonaws.com`) |

> 💡 **No Custom Domain?** Use ALB URLs directly! Example: `http://oncolife-patient-alb-123456789.us-west-2.elb.amazonaws.com`
> 
> 💡 **Tip**: Use `aws secretsmanager get-secret-value --secret-id oncolife/db` to retrieve stored credentials.

---

## 11. Phase 7: Route 53 & Custom Domains (OPTIONAL - Skip for Testing)

> 🔔 **This entire phase is OPTIONAL!** 
> - For testing and development, use ALB DNS URLs directly (see section above)
> - Only set up custom domains when you need HTTPS or professional branding
> - You can complete this phase later when you're ready for production

### Step 11.1: Register or Configure Domain

If you have a domain (e.g., `oncolife.com`), set up Route 53:

```powershell
# Create hosted zone (if not using existing domain)
aws route53 create-hosted-zone \
    --name "oncolife.com" \
    --caller-reference "oncolife-$(Get-Date -Format 'yyyyMMddHHmmss')"
```

### Step 11.2: Request ACM Certificates

```powershell
# Request certificate for Patient API
aws acm request-certificate `
    --domain-name "api.oncolife.com" `
    --validation-method DNS `
    --region $AWS_REGION

# Request certificate for Doctor API
aws acm request-certificate `
    --domain-name "doctor-api.oncolife.com" `
    --validation-method DNS `
    --region $AWS_REGION

# Request certificate for Patient Web (if using CloudFront, request in us-east-1)
aws acm request-certificate `
    --domain-name "app.oncolife.com" `
    --validation-method DNS `
    --region us-east-1

# Request certificate for Doctor Web
aws acm request-certificate `
    --domain-name "doctor.oncolife.com" `
    --validation-method DNS `
    --region us-east-1
```

**Validate certificates:** Add the CNAME records shown in ACM console to Route 53.

### Step 11.3: Create Route 53 Records

```powershell
# Get ALB DNS names
$PATIENT_ALB_DNS = (aws elbv2 describe-load-balancers --names "oncolife-patient-alb" --query 'LoadBalancers[0].DNSName' --output text)
$DOCTOR_ALB_DNS = (aws elbv2 describe-load-balancers --names "oncolife-doctor-alb" --query 'LoadBalancers[0].DNSName' --output text)

# Get hosted zone ID
$HOSTED_ZONE_ID = (aws route53 list-hosted-zones-by-name --dns-name "oncolife.com" --query 'HostedZones[0].Id' --output text)
$HOSTED_ZONE_ID = $HOSTED_ZONE_ID -replace '/hostedzone/', ''
```

Create `route53-records.json`:
```json
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.oncolife.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "ALB_HOSTED_ZONE_ID",
          "DNSName": "PATIENT_ALB_DNS",
          "EvaluateTargetHealth": true
        }
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "doctor-api.oncolife.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "ALB_HOSTED_ZONE_ID",
          "DNSName": "DOCTOR_ALB_DNS",
          "EvaluateTargetHealth": true
        }
      }
    }
  ]
}
```

```powershell
aws route53 change-resource-record-sets `
    --hosted-zone-id $HOSTED_ZONE_ID `
    --change-batch file://route53-records.json
```

### Step 11.4: Add HTTPS Listeners to ALBs

After certificates are validated:

```powershell
# Get certificate ARNs
$PATIENT_CERT_ARN = (aws acm list-certificates --query "CertificateSummaryList[?DomainName=='api.oncolife.com'].CertificateArn" --output text)
$DOCTOR_CERT_ARN = (aws acm list-certificates --query "CertificateSummaryList[?DomainName=='doctor-api.oncolife.com'].CertificateArn" --output text)

# Create HTTPS listener for Patient ALB
aws elbv2 create-listener `
    --load-balancer-arn $PATIENT_ALB_ARN `
    --protocol HTTPS `
    --port 443 `
    --certificates CertificateArn=$PATIENT_CERT_ARN `
    --default-actions "Type=forward,TargetGroupArn=$PATIENT_TG_ARN"

# Create HTTPS listener for Doctor ALB
aws elbv2 create-listener `
    --load-balancer-arn $DOCTOR_ALB_ARN `
    --protocol HTTPS `
    --port 443 `
    --certificates CertificateArn=$DOCTOR_CERT_ARN `
    --default-actions "Type=forward,TargetGroupArn=$DOCTOR_TG_ARN"
```

---

## 12. Deployment Verification Checklist

Use this checklist to verify your deployment is complete and working:

### Infrastructure Checklist

| Component | Command to Verify | Expected |
|-----------|-------------------|----------|
| VPC | `aws ec2 describe-vpcs --filters "Name=tag:Name,Values=*oncolife*"` | VPC exists |
| Subnets | `aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID"` | 4 subnets (2 public, 2 private) |
| Security Groups | `aws ec2 describe-security-groups --filters "Name=group-name,Values=oncolife-*"` | 3 SGs (ALB, ECS, RDS) |
| RDS | `aws rds describe-db-instances --db-instance-identifier oncolife-db` | Status: "available" |
| ECR Repos | `aws ecr describe-repositories --query 'repositories[*].repositoryName'` | 4 repos (patient-api, doctor-api, patient-web, doctor-web) |
| ECS Cluster | `aws ecs describe-clusters --clusters oncolife-production` | Status: "ACTIVE" |
| ECS Services | `aws ecs describe-services --cluster oncolife-production --services patient-api-service doctor-api-service` | runningCount >= 1 |

### API Health Checks

```powershell
# Patient API
Invoke-RestMethod -Uri "http://$PATIENT_ALB_DNS/health"
# Expected: { "status": "healthy", ... }

# Patient API Docs
Start-Process "http://$PATIENT_ALB_DNS/docs"
# Expected: Swagger UI loads

# Doctor API
Invoke-RestMethod -Uri "http://$DOCTOR_ALB_DNS/health"
# Expected: { "status": "healthy", ... }

# Doctor API Docs
Start-Process "http://$DOCTOR_ALB_DNS/docs"
# Expected: Swagger UI loads
```

### Database Verification

```sql
-- Connect to RDS and verify tables exist
\c oncolife_patient
\dt
-- Expected: patient_info, conversations, messages, etc.

\c oncolife_doctor
\dt
-- Expected: staff_profiles, audit_logs, etc.
```

### Frontend Verification (if deployed)

| App | URL | Expected |
|-----|-----|----------|
| Patient Web | `https://app.oncolife.com` or S3 URL | Login page loads |
| Doctor Web | `https://doctor.oncolife.com` or S3 URL | Login page loads |

### CI/CD Verification

1. **Push a test commit** to a feature branch
2. **Check GitHub Actions** → CI workflow runs
3. **Create a PR** to main
4. **Merge PR** → CD workflow triggers (if configured)

### Final Checklist

- [ ] VPC with 4 subnets created
- [ ] Security groups configured correctly
- [ ] RDS instance running and accessible
- [ ] ECR repositories have images pushed
- [ ] ECS cluster running with healthy services
- [ ] ALBs returning healthy responses
- [ ] Database migrations applied
- [ ] Education content seeded
- [ ] GitHub secrets configured
- [ ] Custom domains set up (optional)
- [ ] HTTPS working (optional)

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   PATIENT SIDE                              DOCTOR SIDE                     │
│   ────────────                              ───────────                     │
│                                                                              │
│   Route 53: api.oncolife.com                Route 53: doctor-api.oncolife   │
│         │                                         │                         │
│         ▼                                         ▼                         │
│   ┌─────────────────┐                       ┌─────────────────┐            │
│   │  Patient ALB    │                       │  Doctor ALB     │            │
│   │  (Port 443/80)  │                       │  (Port 443/80)  │            │
│   └────────┬────────┘                       └────────┬────────┘            │
│            │                                         │                      │
│            ▼                                         ▼                      │
│   ┌─────────────────┐                       ┌─────────────────┐            │
│   │ Target Group    │                       │ Target Group    │            │
│   │ (Port 8000)     │                       │ (Port 8001)     │            │
│   └────────┬────────┘                       └────────┬────────┘            │
│            │                                         │                      │
│            ▼                                         ▼                      │
│   ┌─────────────────┐                       ┌─────────────────┐            │
│   │ ECS Service     │                       │ ECS Service     │            │
│   │ patient-api     │                       │ doctor-api      │            │
│   │ (2 tasks)       │                       │ (2 tasks)       │            │
│   └────────┬────────┘                       └────────┬────────┘            │
│            │                                         │                      │
│            └──────────────────┬──────────────────────┘                      │
│                               │                                             │
│                               ▼                                             │
│                       ┌─────────────────┐                                  │
│                       │      RDS        │                                  │
│                       │  PostgreSQL     │                                  │
│                       │ (patient_db +   │                                  │
│                       │  doctor_db)     │                                  │
│                       └─────────────────┘                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*Document Version: 2.0*
*Last Updated: January 2026*
*© 2026 OncoLife Health Technologies*
