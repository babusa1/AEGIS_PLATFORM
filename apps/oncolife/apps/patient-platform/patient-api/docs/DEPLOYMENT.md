# OncoLife Patient API - AWS Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the OncoLife Patient API to AWS.

---

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Docker** installed
4. **PostgreSQL** database (AWS RDS recommended)
5. **AWS Cognito** User Pool configured
6. **AWS S3** bucket for referral documents (onboarding)
7. **AWS SES** verified sender email (onboarding)
8. **AWS SNS** for SMS (onboarding)
9. **Fax Provider** (Sinch/Twilio) with webhook configured

---

## Architecture on AWS

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          AWS Infrastructure                               │
│                                                                           │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────────────┐       │
│  │   Route53   │ ───► │     ALB     │ ───► │   ECS / Fargate     │       │
│  │   (DNS)     │      │ (Load Bal.) │      │ (patient-api:8000)  │       │
│  └─────────────┘      └─────────────┘      └──────────┬──────────┘       │
│                                                       │                   │
│  ┌────────────────────────────────────────────────────┼─────────────────┐│
│  │                     ONBOARDING FLOW                │                  ││
│  │  ┌───────────┐    ┌───────────┐    ┌───────────────▼───────────────┐ ││
│  │  │ Fax       │───►│ Webhook   │───►│      S3 (Referrals)           │ ││
│  │  │ (Sinch)   │    │ /fax/sinch│    │ s3://oncolife-referrals/      │ ││
│  │  └───────────┘    └───────────┘    │ (KMS Encrypted)               │ ││
│  │                                    └───────────────┬───────────────┘ ││
│  │                                                    │                  ││
│  │  ┌───────────┐    ┌───────────┐    ┌───────────────▼───────────────┐ ││
│  │  │  SES      │◄───│ Cognito   │◄───│      Textract (OCR)           │ ││
│  │  │ (Email)   │    │ (Account) │    │ Extract: Name, DOB, Cancer... │ ││
│  │  └───────────┘    └───────────┘    └───────────────────────────────┘ ││
│  │  ┌───────────┐                                                        ││
│  │  │  SNS      │ (SMS notifications)                                    ││
│  │  └───────────┘                                                        ││
│  └───────────────────────────────────────────────────────────────────────┘│
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐│
│  │                        Private Subnet                                  ││
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                  ││
│  │  │    RDS      │   │   Cognito   │   │    S3       │                  ││
│  │  │ PostgreSQL  │   │ User Pool   │   │  (logs)     │                  ││
│  │  └─────────────┘   └─────────────┘   └─────────────┘                  ││
│  └───────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Options

### Option 1: AWS ECS with Fargate (Recommended)

Fully managed container orchestration.

### Option 2: AWS Elastic Beanstalk

Simplified deployment with managed infrastructure.

### Option 3: AWS EC2

Traditional server deployment.

---

## Option 1: ECS with Fargate

### Step 1: Create ECR Repository

```bash
#!/bin/bash
# scripts/create-ecr.sh

AWS_REGION=${AWS_REGION:-"us-west-2"}
ECR_REPO_NAME="oncolife-patient-api"

# Create ECR repository
aws ecr create-repository \
    --repository-name $ECR_REPO_NAME \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true

echo "ECR Repository created: $ECR_REPO_NAME"
```

### Step 2: Build and Push Docker Image

```bash
#!/bin/bash
# scripts/build-and-push.sh

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-"us-west-2"}
ECR_REPO_NAME="oncolife-patient-api"
IMAGE_TAG=${IMAGE_TAG:-"latest"}

ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_URI

# Build Docker image
docker build -t $ECR_REPO_NAME:$IMAGE_TAG \
    -f apps/patient-platform/patient-api/Dockerfile \
    apps/patient-platform/patient-api/

# Tag and push
docker tag $ECR_REPO_NAME:$IMAGE_TAG $ECR_URI/$ECR_REPO_NAME:$IMAGE_TAG
docker push $ECR_URI/$ECR_REPO_NAME:$IMAGE_TAG

echo "Image pushed: $ECR_URI/$ECR_REPO_NAME:$IMAGE_TAG"
```

### Step 3: Create ECS Cluster

```bash
#!/bin/bash
# scripts/create-ecs-cluster.sh

CLUSTER_NAME="oncolife-production"
AWS_REGION=${AWS_REGION:-"us-west-2"}

aws ecs create-cluster \
    --cluster-name $CLUSTER_NAME \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy \
        capacityProvider=FARGATE,weight=1 \
        capacityProvider=FARGATE_SPOT,weight=1 \
    --region $AWS_REGION

echo "ECS Cluster created: $CLUSTER_NAME"
```

### Step 4: Create Task Definition

Create file: `ecs-task-definition.json`

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
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "LOG_LEVEL", "value": "INFO"},
        {"name": "AWS_REGION", "value": "us-west-2"}
      ],
      "secrets": [
        {
          "name": "POSTGRES_HOST",
          "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/db:host::"
        },
        {
          "name": "POSTGRES_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/db:password::"
        },
        {
          "name": "COGNITO_CLIENT_SECRET",
          "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/cognito:client_secret::"
        }
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

Register the task definition:

```bash
#!/bin/bash
# scripts/register-task.sh

aws ecs register-task-definition \
    --cli-input-json file://ecs-task-definition.json \
    --region us-west-2
```

### Step 5: Create ECS Service

```bash
#!/bin/bash
# scripts/create-service.sh

CLUSTER_NAME="oncolife-production"
SERVICE_NAME="patient-api-service"
TASK_DEFINITION="oncolife-patient-api"
SUBNET_IDS="subnet-xxx,subnet-yyy"  # Your private subnets
SECURITY_GROUP="sg-xxx"              # Your security group
TARGET_GROUP_ARN="arn:aws:elasticloadbalancing:..."

aws ecs create-service \
    --cluster $CLUSTER_NAME \
    --service-name $SERVICE_NAME \
    --task-definition $TASK_DEFINITION \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}" \
    --load-balancers "targetGroupArn=$TARGET_GROUP_ARN,containerName=patient-api,containerPort=8000" \
    --health-check-grace-period-seconds 120 \
    --region us-west-2
```

### Step 6: Create Application Load Balancer

```bash
#!/bin/bash
# scripts/create-alb.sh

VPC_ID="vpc-xxx"
SUBNET_IDS="subnet-xxx subnet-yyy"
SECURITY_GROUP="sg-xxx"
CERT_ARN="arn:aws:acm:us-west-2:xxx:certificate/xxx"

# Create ALB
aws elbv2 create-load-balancer \
    --name oncolife-api-alb \
    --subnets $SUBNET_IDS \
    --security-groups $SECURITY_GROUP \
    --scheme internet-facing \
    --type application

# Create Target Group
aws elbv2 create-target-group \
    --name patient-api-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /health \
    --health-check-interval-seconds 30

# Create HTTPS Listener
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn=$CERT_ARN \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN
```

---

## Option 2: Elastic Beanstalk

### Step 1: Create Procfile

```
# apps/patient-platform/patient-api/Procfile
web: uvicorn main:app --host 0.0.0.0 --port 8000
```

### Step 2: Create .ebextensions

Create `apps/patient-platform/patient-api/.ebextensions/01_python.config`:

```yaml
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: main:app

packages:
  yum:
    postgresql-devel: []
```

### Step 3: Deploy

```bash
#!/bin/bash
# scripts/eb-deploy.sh

cd apps/patient-platform/patient-api

# Initialize EB (first time)
eb init oncolife-patient-api \
    --platform "Python 3.11" \
    --region us-west-2

# Create environment (first time)
eb create production \
    --instance-type t3.medium \
    --elb-type application \
    --vpc.id vpc-xxx \
    --vpc.elbsubnets subnet-xxx,subnet-yyy \
    --vpc.ec2subnets subnet-zzz,subnet-www

# Deploy (subsequent times)
eb deploy production
```

---

## Option 3: EC2 Deployment

### Step 1: Launch EC2 Instance

```bash
#!/bin/bash
# scripts/launch-ec2.sh

aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1f0 \
    --instance-type t3.medium \
    --key-name your-key-pair \
    --security-group-ids sg-xxx \
    --subnet-id subnet-xxx \
    --iam-instance-profile Name=OncolifeEC2Role \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=oncolife-patient-api}]' \
    --user-data file://user-data.sh
```

### Step 2: User Data Script

Create `user-data.sh`:

```bash
#!/bin/bash
# EC2 User Data Script

# Update system
yum update -y

# Install Docker
amazon-linux-extras install docker -y
systemctl start docker
systemctl enable docker

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone repository
cd /opt
git clone https://github.com/nbsaKanasu/Oncolife_Monolith.git
cd Oncolife_Monolith/apps/patient-platform/patient-api

# Create .env file from Secrets Manager
aws secretsmanager get-secret-value \
    --secret-id oncolife/patient-api/env \
    --query SecretString \
    --output text > .env

# Start application
docker-compose up -d
```

---

## Database Setup (RDS PostgreSQL)

### Create RDS Instance

```bash
#!/bin/bash
# scripts/create-rds.sh

aws rds create-db-instance \
    --db-instance-identifier oncolife-db \
    --db-instance-class db.t3.medium \
    --engine postgres \
    --engine-version 15 \
    --master-username oncolife_admin \
    --master-user-password "SECURE_PASSWORD" \
    --allocated-storage 100 \
    --storage-type gp3 \
    --vpc-security-group-ids sg-xxx \
    --db-subnet-group-name oncolife-db-subnet \
    --multi-az \
    --backup-retention-period 7 \
    --storage-encrypted \
    --kms-key-id alias/oncolife-rds-key
```

### Run Migrations

After creating RDS, you need to run database migrations to create all tables.

#### Option 1: Using Migration Script (Recommended)

```bash
# From your local machine with VPN access to RDS
./scripts/aws/run-migrations.sh all
```

This will provide detailed instructions for running migrations on AWS RDS.

#### Option 2: Via SSM Session Manager

```bash
#!/bin/bash
# Connect to bastion/EC2 with SSM
aws ssm start-session --target i-xxx

# Clone repo and set up environment
cd /opt/Oncolife_Monolith/apps/patient-platform/patient-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export PATIENT_DB_HOST=oncolife-db.xxx.us-west-2.rds.amazonaws.com
export PATIENT_DB_PORT=5432
export PATIENT_DB_USER=oncolife_admin
export PATIENT_DB_PASSWORD=$(aws secretsmanager get-secret-value \
    --secret-id oncolife/db --query 'SecretString' \
    --output text | jq -r '.password')
export PATIENT_DB_NAME=oncolife_patient

# Run migrations
alembic upgrade head

# Verify tables created
psql -h $PATIENT_DB_HOST -U $PATIENT_DB_USER -d $PATIENT_DB_NAME \
    -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
```

#### Option 3: Apply SQL Script Directly

```bash
# Connect to RDS via psql
psql -h oncolife-db.xxx.us-west-2.rds.amazonaws.com \
     -U oncolife_admin \
     -d oncolife_patient \
     -f scripts/db/schema_patient_diary_doctor_dashboard.sql
```

#### Migration Files

| Migration | Description |
|-----------|-------------|
| `0001_initial_schema.py` | Core tables: users, conversations, diary, questions |
| `0002_onboarding_ocr_tables.py` | OCR/Onboarding: providers, oncology_profiles, medications, chemo_schedule, fax_ingestion_log, ocr_field_confidence |

#### Tables Created

**Core Tables:**
- `users`, `conversations`, `messages`, `diary_entries`, `patient_questions`

**Onboarding/OCR Tables:**
- `providers` - Normalized physician/clinic data
- `oncology_profiles` - Cancer diagnosis, treatment, chemo timeline
- `medications` - Chemotherapy and supportive drugs
- `chemo_schedule` - Specific appointment dates for ChemoTimeline
- `fax_ingestion_log` - HIPAA audit trail for fax reception
- `ocr_field_confidence` - Per-field OCR accuracy scores
- `ocr_confidence_thresholds` - Auto-accept/review threshold config

**Verification:**
```sql
-- Verify all core tables
\dt

-- Verify new onboarding tables
SELECT table_name FROM information_schema.tables 
WHERE table_name IN (
    'providers', 'oncology_profiles', 'medications', 
    'chemo_schedule', 'fax_ingestion_log', 'ocr_field_confidence'
);

-- Check OCR thresholds seeded
SELECT COUNT(*) FROM ocr_confidence_thresholds;
-- Should return 26 rows
```

---

## Patient Onboarding AWS Setup (NEW)

### Step 1: Create S3 Bucket for Referrals

```bash
#!/bin/bash
# scripts/create-referral-bucket.sh

BUCKET_NAME="oncolife-referrals"
AWS_REGION=${AWS_REGION:-"us-west-2"}

# Create bucket with encryption
aws s3api create-bucket \
    --bucket $BUCKET_NAME \
    --region $AWS_REGION \
    --create-bucket-configuration LocationConstraint=$AWS_REGION

# Enable versioning (required for HIPAA)
aws s3api put-bucket-versioning \
    --bucket $BUCKET_NAME \
    --versioning-configuration Status=Enabled

# Enable server-side encryption with KMS
aws s3api put-bucket-encryption \
    --bucket $BUCKET_NAME \
    --server-side-encryption-configuration '{
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "aws:kms",
                    "KMSMasterKeyID": "alias/oncolife-referrals-key"
                }
            }
        ]
    }'

# Block public access
aws s3api put-public-access-block \
    --bucket $BUCKET_NAME \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo "S3 bucket created: $BUCKET_NAME"
```

### Step 2: Configure SES for Welcome Emails

```bash
#!/bin/bash
# scripts/setup-ses.sh

SENDER_EMAIL="noreply@oncolife.com"
AWS_REGION=${AWS_REGION:-"us-west-2"}

# Verify email identity (or domain)
aws ses verify-email-identity \
    --email-address $SENDER_EMAIL \
    --region $AWS_REGION

# Create email template for welcome message
aws ses create-template \
    --template '{
        "TemplateName": "oncolife-welcome",
        "SubjectPart": "Welcome to OncoLife - Your Personal Health Companion",
        "HtmlPart": "<html>...</html>",
        "TextPart": "Welcome to OncoLife..."
    }' \
    --region $AWS_REGION

echo "SES configured for: $SENDER_EMAIL"
```

### Step 3: Configure SNS for SMS

```bash
#!/bin/bash
# scripts/setup-sns.sh

AWS_REGION=${AWS_REGION:-"us-west-2"}

# Set default SMS attributes
aws sns set-sms-attributes \
    --attributes '{
        "DefaultSMSType": "Transactional",
        "DefaultSenderID": "OncoLife"
    }' \
    --region $AWS_REGION

echo "SNS SMS configured"
```

### Step 4: Create IAM Role for Onboarding

```bash
#!/bin/bash
# scripts/create-onboarding-role.sh

ROLE_NAME="OncolifeOnboardingRole"

# Create role
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ecs-tasks.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }'

# Attach policy for S3
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "S3ReferralAccess" \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:GetObject"],
                "Resource": "arn:aws:s3:::oncolife-referrals/*"
            }
        ]
    }'

# Attach policy for Textract
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "TextractAccess" \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "textract:AnalyzeDocument",
                    "textract:StartDocumentAnalysis",
                    "textract:GetDocumentAnalysis"
                ],
                "Resource": "*"
            }
        ]
    }'

# Attach policy for SES
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "SESAccess" \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["ses:SendEmail", "ses:SendRawEmail"],
                "Resource": "*"
            }
        ]
    }'

# Attach policy for SNS
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "SNSAccess" \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["sns:Publish"],
                "Resource": "*"
            }
        ]
    }'

# Attach policy for Cognito (admin user creation)
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "CognitoAdminAccess" \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminDeleteUser",
                    "cognito-idp:AdminInitiateAuth",
                    "cognito-idp:AdminRespondToAuthChallenge"
                ],
                "Resource": "arn:aws:cognito-idp:*:*:userpool/*"
            }
        ]
    }'

echo "IAM role created: $ROLE_NAME"
```

### Step 5: Configure Fax Provider Webhook

> 📍 **This section configures Sinch (or alternative provider) to send faxes to your OncoLife API.**

#### Required Environment Variables

First, ensure these are set in your Patient API environment:

```bash
# Fax Service Settings (add to .env or Secrets Manager)
FAX_INBOUND_NUMBER=+1-555-YOUR-FAX-NUMBER
FAX_WEBHOOK_SECRET=your_secure_webhook_secret_here
S3_REFERRAL_BUCKET=oncolife-referrals-YOUR_ACCOUNT_ID
```

#### Option A: Sinch (Recommended)

1. **Log into Sinch Dashboard** at https://dashboard.sinch.com
2. Navigate to **Fax → Numbers**
3. Select your dedicated fax number
4. Configure webhook:

| Setting | Value |
|---------|-------|
| **Webhook URL** | `https://YOUR_PATIENT_ALB_URL/api/v1/onboarding/webhook/fax/sinch` |
| **Events** | `fax.received` |
| **Secret** | Same as `FAX_WEBHOOK_SECRET` in your environment |
| **Method** | POST |
| **Content-Type** | application/json |

5. **Test the webhook** by sending a test fax to your Sinch number

#### Option B: Twilio

1. Log into **Twilio Console** at https://console.twilio.com
2. Navigate to **Fax → Manage → Fax Numbers**
3. Configure incoming webhook:

| Setting | Value |
|---------|-------|
| **Webhook URL** | `https://YOUR_PATIENT_ALB_URL/api/v1/onboarding/webhook/fax/twilio` |
| **Method** | POST |

#### Option C: Phaxio

1. Log into **Phaxio Dashboard**
2. Navigate to **Webhooks**
3. Configure:

| Setting | Value |
|---------|-------|
| **Webhook URL** | `https://YOUR_PATIENT_ALB_URL/api/v1/onboarding/webhook/fax/phaxio` |
| **Events** | `fax.received` |

#### Option D: RingCentral

1. Log into **RingCentral Developer Portal**
2. Create a webhook subscription for fax events
3. Set URL: `https://YOUR_PATIENT_ALB_URL/api/v1/onboarding/webhook/fax/ringcentral`

#### Verifying Fax Webhook is Working

```bash
# Check health endpoint
curl https://YOUR_PATIENT_ALB_URL/api/v1/health

# Check CloudWatch Logs for fax processing
aws logs filter-log-events \
    --log-group-name /ecs/oncolife-patient-api \
    --filter-pattern "fax webhook"
```

#### Troubleshooting Fax Webhooks

| Issue | Solution |
|-------|----------|
| Webhook not received | Check ALB security group allows HTTPS from internet |
| Signature validation failed | Verify `FAX_WEBHOOK_SECRET` matches Sinch dashboard |
| Document not uploaded to S3 | Check `S3_REFERRAL_BUCKET` and IAM permissions |
| OCR not processing | Verify AWS Textract permissions in task role |

---

## AWS Cognito Setup

### Create User Pool

```bash
#!/bin/bash
# scripts/create-cognito.sh

aws cognito-idp create-user-pool \
    --pool-name oncolife-patients \
    --auto-verified-attributes email \
    --username-attributes email \
    --mfa-configuration OFF \
    --email-configuration SourceArn=arn:aws:ses:us-west-2:xxx:identity/noreply@oncolife.com \
    --admin-create-user-config AllowAdminCreateUserOnly=false \
    --schema Name=email,Required=true Name=given_name,Required=true Name=family_name,Required=true

# Create App Client
aws cognito-idp create-user-pool-client \
    --user-pool-id us-west-2_xxx \
    --client-name patient-api-client \
    --generate-secret \
    --explicit-auth-flows ADMIN_NO_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
    --read-attributes email given_name family_name \
    --write-attributes email given_name family_name
```

---

## Environment Configuration

### Secrets Manager Setup

```bash
#!/bin/bash
# scripts/create-secrets.sh

# Database credentials
aws secretsmanager create-secret \
    --name oncolife/db \
    --secret-string '{
        "host": "oncolife-db.xxx.us-west-2.rds.amazonaws.com",
        "port": "5432",
        "username": "oncolife_admin",
        "password": "SECURE_PASSWORD",
        "patient_db": "oncolife_patient",
        "doctor_db": "oncolife_doctor"
    }'

# Cognito credentials
aws secretsmanager create-secret \
    --name oncolife/cognito \
    --secret-string '{
        "user_pool_id": "us-west-2_xxx",
        "client_id": "xxx",
        "client_secret": "xxx"
    }'

# Onboarding secrets (NEW)
aws secretsmanager create-secret \
    --name oncolife/onboarding \
    --secret-string '{
        "fax_webhook_secret": "your_webhook_secret",
        "ses_sender_email": "noreply@oncolife.com",
        "s3_referral_bucket": "oncolife-referrals"
    }'
```

---

## Monitoring & Logging

### CloudWatch Log Group

```bash
aws logs create-log-group \
    --log-group-name /ecs/oncolife-patient-api

aws logs put-retention-policy \
    --log-group-name /ecs/oncolife-patient-api \
    --retention-in-days 30
```

### CloudWatch Alarms

```bash
#!/bin/bash
# scripts/create-alarms.sh

# High CPU alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "PatientAPI-HighCPU" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-west-2:xxx:oncolife-alerts \
    --dimensions Name=ClusterName,Value=oncolife-production Name=ServiceName,Value=patient-api-service

# 5xx Error alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "PatientAPI-5xxErrors" \
    --metric-name HTTPCode_Target_5XX_Count \
    --namespace AWS/ApplicationELB \
    --statistic Sum \
    --period 60 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-west-2:xxx:oncolife-alerts
```

---

## CI/CD Pipeline (GitHub Actions)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy Patient API

on:
  push:
    branches: [main]
    paths:
      - 'apps/patient-platform/patient-api/**'

env:
  AWS_REGION: us-west-2
  ECR_REPOSITORY: oncolife-patient-api
  ECS_CLUSTER: oncolife-production
  ECS_SERVICE: patient-api-service

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build, tag, and push image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG \
            -f apps/patient-platform/patient-api/Dockerfile \
            apps/patient-platform/patient-api/
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG \
            $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
      
      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service $ECS_SERVICE \
            --force-new-deployment
```

---

## Dockerfile

Ensure this Dockerfile exists at `apps/patient-platform/patient-api/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Quick Start Commands

```bash
# 1. Set up infrastructure
./scripts/create-ecr.sh
./scripts/create-rds.sh
./scripts/create-cognito.sh
./scripts/create-secrets.sh
./scripts/create-ecs-cluster.sh

# 2. Build and deploy
./scripts/build-and-push.sh
./scripts/register-task.sh
./scripts/create-alb.sh
./scripts/create-service.sh

# 3. Verify deployment
aws ecs describe-services \
    --cluster oncolife-production \
    --services patient-api-service

# 4. Check logs
aws logs tail /ecs/oncolife-patient-api --follow
```

---

## Rollback Procedure

```bash
#!/bin/bash
# scripts/rollback.sh

PREVIOUS_TASK_DEF="oncolife-patient-api:5"  # Previous version

aws ecs update-service \
    --cluster oncolife-production \
    --service patient-api-service \
    --task-definition $PREVIOUS_TASK_DEF \
    --force-new-deployment
```

---

## Cost Optimization Tips

1. Use **Fargate Spot** for non-critical workloads (up to 70% savings)
2. Use **Reserved Capacity** for RDS (up to 30% savings)
3. Enable **Auto Scaling** based on CPU/Memory metrics
4. Use **S3 Intelligent-Tiering** for logs
5. Consider **AWS Savings Plans** for consistent workloads

---

## Patient Education Module Setup (NEW)

The Patient Education module delivers clinician-approved education content after every symptom checker session.

### Step 1: Create S3 Bucket for Education Content

```bash
#!/bin/bash
# scripts/create-education-bucket.sh

BUCKET_NAME="oncolife-education"
AWS_REGION=${AWS_REGION:-"us-west-2"}

# Create bucket
aws s3api create-bucket \
    --bucket $BUCKET_NAME \
    --region $AWS_REGION \
    --create-bucket-configuration LocationConstraint=$AWS_REGION

# Enable versioning (no overwrite)
aws s3api put-bucket-versioning \
    --bucket $BUCKET_NAME \
    --versioning-configuration Status=Enabled

# Enable KMS encryption
aws s3api put-bucket-encryption \
    --bucket $BUCKET_NAME \
    --server-side-encryption-configuration '{
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "aws:kms",
                    "KMSMasterKeyID": "alias/oncolife-education-key"
                }
            }
        ]
    }'

# Block public access
aws s3api put-public-access-block \
    --bucket $BUCKET_NAME \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Enable CloudTrail logging for audit
echo "S3 bucket created: $BUCKET_NAME"
```

### Step 2: Create S3 Folder Structure

```bash
#!/bin/bash
# scripts/setup-education-folders.sh

BUCKET_NAME="oncolife-education"

# Create folder structure (S3 uses prefixes)
aws s3api put-object --bucket $BUCKET_NAME --key "symptoms/"
aws s3api put-object --bucket $BUCKET_NAME --key "symptoms/fever/"
aws s3api put-object --bucket $BUCKET_NAME --key "symptoms/nausea/"
aws s3api put-object --bucket $BUCKET_NAME --key "symptoms/bleeding/"
aws s3api put-object --bucket $BUCKET_NAME --key "symptoms/fatigue/"
aws s3api put-object --bucket $BUCKET_NAME --key "symptoms/pain/"
aws s3api put-object --bucket $BUCKET_NAME --key "symptoms/diarrhea/"
aws s3api put-object --bucket $BUCKET_NAME --key "symptoms/constipation/"
aws s3api put-object --bucket $BUCKET_NAME --key "symptoms/mouth/"
aws s3api put-object --bucket $BUCKET_NAME --key "care-team/"

echo "Education folder structure created"
```

### Step 3: Upload Education PDFs

```bash
#!/bin/bash
# scripts/upload-education-pdfs.sh

BUCKET_NAME="oncolife-education"
LOCAL_DOCS_DIR="./static/education"  # Local directory with PDFs

# Upload symptom-specific documents
for symptom_dir in $LOCAL_DOCS_DIR/symptoms/*/; do
    symptom_name=$(basename $symptom_dir)
    echo "Uploading $symptom_name documents..."
    
    for file in $symptom_dir*.pdf; do
        if [ -f "$file" ]; then
            aws s3 cp "$file" "s3://$BUCKET_NAME/symptoms/$symptom_name/" \
                --sse aws:kms \
                --sse-kms-key-id alias/oncolife-education-key
        fi
    done
    
    # Also upload text versions for inline content
    for file in $symptom_dir*.txt; do
        if [ -f "$file" ]; then
            aws s3 cp "$file" "s3://$BUCKET_NAME/symptoms/$symptom_name/" \
                --sse aws:kms \
                --sse-kms-key-id alias/oncolife-education-key
        fi
    done
done

# Upload care team handout
aws s3 cp "$LOCAL_DOCS_DIR/care-team/care_team_handout_v1.pdf" \
    "s3://$BUCKET_NAME/care-team/" \
    --sse aws:kms \
    --sse-kms-key-id alias/oncolife-education-key

aws s3 cp "$LOCAL_DOCS_DIR/care-team/care_team_handout_v1.txt" \
    "s3://$BUCKET_NAME/care-team/" \
    --sse aws:kms \
    --sse-kms-key-id alias/oncolife-education-key

echo "Education documents uploaded to S3"
```

### Step 4: Run Database Seed Script

The seed script populates the database with:
- Symptom catalog
- Mandatory disclaimer
- Care Team Handout metadata
- Sample education document metadata

```bash
#!/bin/bash
# Run from project root

cd apps/patient-platform/patient-api

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Set database URL (use production URL)
export DATABASE_URL="postgresql://user:password@host:5432/oncolife_patient"

# Run seed script
python scripts/seed_education_pdfs.py

echo "Education seed data loaded"
```

### Step 5: Verify Education Tables

```sql
-- Connect to database and verify tables exist
\dt symptoms
\dt education_documents
\dt disclaimers
\dt care_team_handouts
\dt symptom_sessions
\dt rule_evaluations
\dt patient_summaries
\dt medications_tried
\dt education_delivery_log
\dt education_access_log

-- Verify seed data
SELECT * FROM symptoms LIMIT 5;
SELECT * FROM disclaimers;
SELECT * FROM care_team_handouts WHERE is_current = true;
SELECT COUNT(*) FROM education_documents WHERE status = 'active';
```

### Step 6: Add IAM Policy for Education Access

```bash
#!/bin/bash
# scripts/add-education-iam-policy.sh

ROLE_NAME="OncolifeOnboardingRole"  # Or your ECS task role

# Add S3 policy for education bucket
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "S3EducationAccess" \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::oncolife-education",
                    "arn:aws:s3:::oncolife-education/*"
                ]
            }
        ]
    }'

echo "Education IAM policy added to role: $ROLE_NAME"
```

### Step 7: Update Task Definition

Add the education S3 bucket to your ECS task definition environment variables:

```json
{
  "containerDefinitions": [
    {
      "environment": [
        {"name": "S3_EDUCATION_BUCKET", "value": "oncolife-education"}
      ]
    }
  ]
}
```

### Step 8: Test Education Delivery

```bash
# Start a symptom checker session
curl -X POST "http://localhost:8000/api/v1/education/session" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"

# Complete session and get education
curl -X POST "http://localhost:8000/api/v1/education/deliver" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<session_uuid>",
    "symptom_codes": ["NAUSEA-101"],
    "severity_levels": {"NAUSEA-101": "moderate"},
    "escalation": false
  }'

# Verify education tab
curl -X GET "http://localhost:8000/api/v1/education/tab" \
  -H "Authorization: Bearer <token>"
```

---

## Complete Deployment Checklist

### Infrastructure Setup
- [ ] ECR repository created
- [ ] ECS cluster created
- [ ] RDS PostgreSQL created
- [ ] S3 referrals bucket created (KMS encrypted)
- [ ] S3 education bucket created (KMS encrypted)
- [ ] Cognito User Pool created
- [ ] SES sender email verified
- [ ] SNS SMS configured
- [ ] ALB created with HTTPS
- [ ] CloudWatch log groups created
- [ ] Secrets Manager secrets created

### Database Setup
- [ ] RDS accessible from ECS tasks
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] Education seed script run
- [ ] Verify all tables created

### Content Setup
- [ ] Education PDFs uploaded to S3
- [ ] Text versions uploaded (for inline content)
- [ ] Care Team Handout uploaded
- [ ] All documents are clinician-approved
- [ ] source_document_id matches database records

### Security Setup
- [ ] VPC Flow Logs enabled
- [ ] Security Groups configured (least privilege)
- [ ] RDS encryption at rest enabled
- [ ] S3 buckets block public access
- [ ] IAM roles follow least privilege
- [ ] CloudTrail enabled for audit
- [ ] WAF configured on ALB
- [ ] GuardDuty enabled

### Application Setup
- [ ] ECS task definition registered
- [ ] ECS service created with proper task count
- [ ] Health checks passing
- [ ] CloudWatch alarms configured
- [ ] CI/CD pipeline configured

### Testing
- [ ] Health endpoint returns 200
- [ ] Authentication flow works
- [ ] Symptom checker completes
- [ ] Education delivered after session
- [ ] Patient summary generated
- [ ] Education tab loads
- [ ] S3 pre-signed URLs work
- [ ] Fax webhook receives test fax

### Monitoring
- [ ] CloudWatch dashboards created
- [ ] Alerts configured for 5xx errors
- [ ] Alerts configured for high CPU/memory
- [ ] Log retention set (30+ days)
- [ ] Access logs enabled on ALB

---

## Security Checklist

### General
- [ ] Enable VPC Flow Logs
- [ ] Configure Security Groups (least privilege)
- [ ] Enable RDS encryption at rest
- [ ] Use Secrets Manager for credentials
- [ ] Enable CloudTrail for audit logging
- [ ] Configure WAF on ALB
- [ ] Enable GuardDuty for threat detection
- [ ] Set up IAM roles with least privilege

### Patient Onboarding (HIPAA)
- [ ] S3 bucket has versioning enabled
- [ ] S3 bucket has KMS encryption
- [ ] S3 bucket blocks all public access
- [ ] Fax webhook uses HTTPS only
- [ ] Fax webhook signature validation enabled
- [ ] SES sender email verified
- [ ] Cognito password policy meets requirements
- [ ] Onboarding notification logs retained
- [ ] PHI data encrypted in transit and at rest

### Patient Education (HIPAA)
- [ ] Education S3 bucket has versioning
- [ ] Education S3 bucket has KMS encryption
- [ ] Education S3 bucket blocks public access
- [ ] Pre-signed URLs expire in ≤30 minutes
- [ ] All education content clinician-approved
- [ ] source_document_id on all documents
- [ ] Education delivery logged for audit
- [ ] Patient summaries are immutable (locked=true)
- [ ] No PHI in CloudWatch logs

---

## Production Environment Variables

Complete list of environment variables for production:

```env
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
APP_NAME=OncoLife Patient API
APP_VERSION=1.0.0

# Server
HOST=0.0.0.0
PORT=8000

# Database
POSTGRES_HOST=oncolife-db.xxx.us-west-2.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_USER=oncolife_admin
POSTGRES_PASSWORD=<from-secrets-manager>
POSTGRES_PATIENT_DB=oncolife_patient

# AWS Core
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=<use-iam-role-instead>
AWS_SECRET_ACCESS_KEY=<use-iam-role-instead>

# AWS Cognito
COGNITO_USER_POOL_ID=us-west-2_xxx
COGNITO_CLIENT_ID=xxx
COGNITO_CLIENT_SECRET=<from-secrets-manager>

# AWS S3
S3_REFERRAL_BUCKET=oncolife-referrals
S3_EDUCATION_BUCKET=oncolife-education

# AWS SES
SES_SENDER_EMAIL=noreply@oncolife.com
SES_SENDER_NAME=OncoLife Care

# AWS SNS
SNS_ENABLED=true

# Fax Webhook
FAX_WEBHOOK_SECRET=<from-secrets-manager>

# CORS
CORS_ORIGINS=https://app.oncolife.com
```

---

## Troubleshooting

### Education Not Delivered

1. Check if session completed:
```sql
SELECT * FROM symptom_sessions WHERE id = '<session_id>';
-- status should be 'COMPLETED', education_delivered should be true
```

2. Check if documents exist:
```sql
SELECT * FROM education_documents 
WHERE symptom_code = 'NAUSEA-101' AND status = 'active';
```

3. Check S3 access:
```bash
aws s3 ls s3://oncolife-education/symptoms/nausea/
```

4. Check pre-signed URL generation:
```bash
# In Python
import boto3
s3 = boto3.client('s3')
url = s3.generate_presigned_url('get_object', 
    Params={'Bucket': 'oncolife-education', 'Key': 'symptoms/nausea/nausea_v1.pdf'},
    ExpiresIn=1800)
print(url)
```

### Summary Not Generated

1. Check session has symptoms:
```sql
SELECT selected_symptoms FROM symptom_sessions WHERE id = '<session_id>';
```

2. Check summary table:
```sql
SELECT * FROM patient_summaries WHERE session_id = '<session_id>';
```

### Disclaimer Missing

1. Verify disclaimer seeded:
```sql
SELECT * FROM disclaimers WHERE active = true;
```

2. Re-run seed script if needed:
```bash
python scripts/seed_education_pdfs.py
```

---

---

## Doctor Dashboard Module Deployment

The Doctor Dashboard provides analytics-driven clinical monitoring for physicians and staff.

### Step 1: Create Database Tables

```bash
#!/bin/bash
# Run against the DOCTOR database

psql -h $RDS_HOST -U $DB_USER -d oncolife_doctor -f scripts/db/schema_patient_diary_doctor_dashboard.sql

# Verify tables created
psql -h $RDS_HOST -U $DB_USER -d oncolife_doctor -c "
SELECT table_name FROM information_schema.tables 
WHERE table_name IN (
  'symptom_time_series', 
  'treatment_events',
  'physician_reports',
  'audit_logs'
);
"
```

### Step 2: Create Cognito User Pool for Physicians

```bash
#!/bin/bash
# scripts/create-doctor-cognito.sh

AWS_REGION=${AWS_REGION:-"us-west-2"}

# Create separate user pool for physicians/staff
aws cognito-idp create-user-pool \
    --pool-name oncolife-physicians \
    --auto-verified-attributes email \
    --username-attributes email \
    --mfa-configuration OPTIONAL \
    --software-token-mfa-configuration Enabled=true \
    --email-configuration SourceArn=arn:aws:ses:us-west-2:xxx:identity/noreply@oncolife.com \
    --admin-create-user-config AllowAdminCreateUserOnly=true \
    --password-policy '{
        "MinimumLength": 12,
        "RequireUppercase": true,
        "RequireLowercase": true,
        "RequireNumbers": true,
        "RequireSymbols": true
    }' \
    --schema \
        Name=email,Required=true \
        Name=given_name,Required=true \
        Name=family_name,Required=true \
    --user-attribute-update-settings AttributesRequireVerificationBeforeUpdate=email

# Create App Client
aws cognito-idp create-user-pool-client \
    --user-pool-id us-west-2_xxx \
    --client-name doctor-api-client \
    --generate-secret \
    --explicit-auth-flows ADMIN_NO_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
    --read-attributes email given_name family_name custom:role custom:physician_id \
    --write-attributes email given_name family_name

echo "Physician Cognito pool created"
```

### Step 3: Create Admin User (One-Time)

```bash
#!/bin/bash
# Create the first admin user who can create physicians

ADMIN_EMAIL="admin@oncolife.com"
ADMIN_TEMP_PASSWORD="TempPass123!"

aws cognito-idp admin-create-user \
    --user-pool-id $COGNITO_POOL_ID \
    --username $ADMIN_EMAIL \
    --temporary-password $ADMIN_TEMP_PASSWORD \
    --user-attributes \
        Name=email,Value=$ADMIN_EMAIL \
        Name=email_verified,Value=true \
        Name=custom:role,Value=admin

# Also insert into database
psql -h $RDS_HOST -U $DB_USER -d oncolife_doctor -c "
INSERT INTO staff_profiles (email_address, first_name, last_name, role)
VALUES ('$ADMIN_EMAIL', 'System', 'Admin', 'admin');
"

echo "Admin user created: $ADMIN_EMAIL"
```

### Step 4: Configure ECS Task Definition for Doctor API

```json
{
  "family": "oncolife-doctor-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/oncolifeDoctorTaskRole",
  "containerDefinitions": [
    {
      "name": "doctor-api",
      "image": "ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/oncolife-doctor-api:latest",
      "portMappings": [
        {
          "containerPort": 8001,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "LOG_LEVEL", "value": "INFO"},
        {"name": "AWS_REGION", "value": "us-west-2"}
      ],
      "secrets": [
        {
          "name": "DOCTOR_DB_HOST",
          "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/db:host::"
        },
        {
          "name": "DOCTOR_DB_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/db:password::"
        },
        {
          "name": "COGNITO_CLIENT_SECRET",
          "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT_ID:secret:oncolife/cognito-doctor:client_secret::"
        }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8001/api/v1/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

### Step 5: Create IAM Role for Doctor API

```bash
#!/bin/bash
# scripts/create-doctor-iam-role.sh

ROLE_NAME="OncolifeDoctorTaskRole"

aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ecs-tasks.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }'

# Cognito Admin Access (for physician/staff registration)
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "CognitoAdminAccess" \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminDeleteUser",
                    "cognito-idp:AdminInitiateAuth",
                    "cognito-idp:AdminRespondToAuthChallenge",
                    "cognito-idp:AdminSetUserMFAPreference"
                ],
                "Resource": "arn:aws:cognito-idp:*:*:userpool/*"
            }
        ]
    }'

# SES Access (for invite emails)
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "SESAccess" \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["ses:SendEmail", "ses:SendRawEmail"],
                "Resource": "*"
            }
        ]
    }'

# S3 Access (for weekly reports)
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name "S3ReportAccess" \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:GetObject"],
                "Resource": "arn:aws:s3:::oncolife-reports/*"
            }
        ]
    }'

echo "Doctor API IAM role created: $ROLE_NAME"
```

### Step 6: Deploy Doctor API

```bash
#!/bin/bash
# scripts/deploy-doctor-api.sh

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-"us-west-2"}
ECR_REPO_NAME="oncolife-doctor-api"

# Build and push
docker build -t $ECR_REPO_NAME \
    -f apps/doctor-platform/doctor-api/Dockerfile \
    apps/doctor-platform/doctor-api/

ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI

docker tag $ECR_REPO_NAME:latest $ECR_URI/$ECR_REPO_NAME:latest
docker push $ECR_URI/$ECR_REPO_NAME:latest

# Update ECS service
aws ecs update-service \
    --cluster oncolife-production \
    --service doctor-api-service \
    --force-new-deployment

echo "Doctor API deployed"
```

### Step 7: Verify Dashboard Endpoints

```bash
# Test health check
curl -X GET "https://doctor-api.oncolife.com/api/v1/health"

# Login as admin
TOKEN=$(curl -s -X POST "https://doctor-api.oncolife.com/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email": "admin@oncolife.com", "password": "YourPassword"}' \
    | jq -r '.tokens.access_token')

# Get dashboard
curl -X GET "https://doctor-api.oncolife.com/api/v1/dashboard" \
    -H "Authorization: Bearer $TOKEN"

# Get patient timeline
curl -X GET "https://doctor-api.oncolife.com/api/v1/dashboard/patient/{patient_uuid}" \
    -H "Authorization: Bearer $TOKEN"
```

### Step 8: Set Up Weekly Report Cron (EventBridge)

```bash
#!/bin/bash
# Create EventBridge rule for weekly reports

aws events put-rule \
    --name "oncolife-weekly-reports" \
    --schedule-expression "cron(0 6 ? * MON *)" \
    --state ENABLED \
    --description "Generate weekly physician reports every Monday at 6 AM"

# Add Lambda target (or ECS task) to generate reports
# This would invoke a Lambda or ECS task that:
# 1. Queries dashboard service for each physician
# 2. Generates PDF from report data
# 3. Stores in S3
# 4. Sends email notification
```

---

## Doctor Dashboard Security Checklist

### Authentication & Authorization
- [ ] Separate Cognito pool for physicians/staff
- [ ] `AdminCreateUserOnly=true` for physician pool
- [ ] MFA enabled (OPTIONAL or REQUIRED)
- [ ] Password policy enforced (12+ chars, mixed)
- [ ] Admin user created and secured

### Data Access
- [ ] All queries scoped by physician_id
- [ ] Staff can only see their physician's patients
- [ ] No cross-physician data leakage
- [ ] Patient questions filtered by share_with_physician

### Audit & Compliance
- [ ] Audit logs table created
- [ ] All patient views logged
- [ ] All report downloads logged
- [ ] IP addresses captured
- [ ] No PHI in CloudWatch logs

### Registration Flow
- [ ] Physicians created by admin only
- [ ] Staff created by physicians only
- [ ] Invite emails sent with temp passwords
- [ ] Force password change on first login

---

## Doctor Dashboard Environment Variables

```env
# Application
ENVIRONMENT=production
APP_NAME="OncoLife Doctor API"
APP_VERSION="1.0.0"

# Server
HOST=0.0.0.0
PORT=8001

# Doctor Database
DOCTOR_DB_HOST=oncolife-db.xxx.us-west-2.rds.amazonaws.com
DOCTOR_DB_PORT=5432
DOCTOR_DB_USER=oncolife_admin
DOCTOR_DB_PASSWORD=<from-secrets-manager>
DOCTOR_DB_NAME=oncolife_doctor

# Patient Database (read-only access)
PATIENT_DB_HOST=oncolife-db.xxx.us-west-2.rds.amazonaws.com
PATIENT_DB_PORT=5432
PATIENT_DB_USER=oncolife_readonly
PATIENT_DB_PASSWORD=<from-secrets-manager>
PATIENT_DB_NAME=oncolife_patient

# AWS Cognito (Physician Pool)
COGNITO_USER_POOL_ID=us-west-2_xxx
COGNITO_CLIENT_ID=xxx
COGNITO_CLIENT_SECRET=<from-secrets-manager>

# AWS SES (Invite emails)
SES_SENDER_EMAIL=noreply@oncolife.com
SES_SENDER_NAME="OncoLife Portal"

# AWS S3 (Reports)
S3_REPORTS_BUCKET=oncolife-reports

# CORS
CORS_ORIGINS=https://doctor.oncolife.com
```

---

*Last Updated: January 2026*

