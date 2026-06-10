# ==============================================================================
# OncoLife Quick Deploy Script (PowerShell)
# ==============================================================================
# This script automates the most error-prone deployment steps.
# Run this from PowerShell (NOT Git Bash!) in the project root.
#
# Usage:
#   .\scripts\aws\quick-deploy.ps1
#
# Prerequisites:
#   - AWS CLI configured (run: aws configure)
#   - Docker Desktop running
# ==============================================================================

param(
    [string]$Region = "us-east-1",
    [switch]$SkipVPC,
    [switch]$SkipRDS,
    [switch]$BuildOnly
)

$ErrorActionPreference = "Stop"

Write-Host "=============================================="
Write-Host "OncoLife Quick Deploy Script"
Write-Host "=============================================="
Write-Host ""

# ------------------------------------------------------------------------------
# Step 1: Verify Prerequisites
# ------------------------------------------------------------------------------
Write-Host "Step 1: Verifying prerequisites..." -ForegroundColor Cyan

# Check AWS CLI
try {
    $identity = aws sts get-caller-identity | ConvertFrom-Json
    $ACCOUNT_ID = $identity.Account
    Write-Host "  ✓ AWS Account: $ACCOUNT_ID" -ForegroundColor Green
} catch {
    Write-Host "  ✗ AWS CLI not configured. Run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# Check Docker
try {
    docker version | Out-Null
    Write-Host "  ✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker not running. Start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Set region
$env:AWS_REGION = $Region
Write-Host "  ✓ Region: $Region" -ForegroundColor Green

Write-Host ""

# ------------------------------------------------------------------------------
# Step 2: Create ECS Service-Linked Role (must be first!)
# ------------------------------------------------------------------------------
Write-Host "Step 2: Creating ECS service-linked role..." -ForegroundColor Cyan

try {
    aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com 2>$null
    Write-Host "  ✓ ECS service-linked role created" -ForegroundColor Green
} catch {
    Write-Host "  ✓ ECS service-linked role already exists (OK)" -ForegroundColor Green
}

Write-Host ""

# ------------------------------------------------------------------------------
# Step 3: Create ECR Repositories
# ------------------------------------------------------------------------------
Write-Host "Step 3: Creating ECR repositories..." -ForegroundColor Cyan

$repos = @("oncolife-patient-api", "oncolife-doctor-api", "oncolife-patient-web", "oncolife-doctor-web")

foreach ($repo in $repos) {
    try {
        aws ecr describe-repositories --repository-names $repo 2>$null | Out-Null
        Write-Host "  ✓ $repo already exists" -ForegroundColor Green
    } catch {
        aws ecr create-repository --repository-name $repo --image-scanning-configuration scanOnPush=true | Out-Null
        Write-Host "  ✓ Created $repo" -ForegroundColor Green
    }
}

Write-Host ""

# ------------------------------------------------------------------------------
# Step 4: Create CloudWatch Log Groups
# ------------------------------------------------------------------------------
Write-Host "Step 4: Creating CloudWatch log groups..." -ForegroundColor Cyan

$logGroups = @("/ecs/oncolife-patient-api", "/ecs/oncolife-doctor-api")

foreach ($lg in $logGroups) {
    try {
        aws logs describe-log-groups --log-group-name-prefix $lg 2>$null | Out-Null
        $exists = (aws logs describe-log-groups --log-group-name-prefix $lg | ConvertFrom-Json).logGroups.Count -gt 0
        if ($exists) {
            Write-Host "  ✓ $lg already exists" -ForegroundColor Green
        } else {
            aws logs create-log-group --log-group-name $lg
            Write-Host "  ✓ Created $lg" -ForegroundColor Green
        }
    } catch {
        aws logs create-log-group --log-group-name $lg
        Write-Host "  ✓ Created $lg" -ForegroundColor Green
    }
}

Write-Host ""

# ------------------------------------------------------------------------------
# Step 5: Login to ECR
# ------------------------------------------------------------------------------
Write-Host "Step 5: Logging in to ECR..." -ForegroundColor Cyan

$ecrPassword = aws ecr get-login-password --region $Region
$ecrPassword | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com"
Write-Host "  ✓ Logged in to ECR" -ForegroundColor Green

Write-Host ""

# ------------------------------------------------------------------------------
# Step 6: Build and Push Docker Images
# ------------------------------------------------------------------------------
Write-Host "Step 6: Building and pushing Docker images..." -ForegroundColor Cyan

# Check if we're in the right directory
if (-not (Test-Path "apps/patient-platform/patient-api/Dockerfile")) {
    Write-Host "  ✗ Not in project root. cd to Oncolife_Monolith first." -ForegroundColor Red
    exit 1
}

# Patient API
Write-Host "  Building patient-api..." -ForegroundColor Yellow
docker build -t "oncolife-patient-api:latest" -f "apps/patient-platform/patient-api/Dockerfile" "apps/patient-platform/patient-api/"
docker tag "oncolife-patient-api:latest" "$ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com/oncolife-patient-api:latest"
docker push "$ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com/oncolife-patient-api:latest"
Write-Host "  ✓ patient-api pushed" -ForegroundColor Green

# Doctor API
Write-Host "  Building doctor-api..." -ForegroundColor Yellow
docker build -t "oncolife-doctor-api:latest" -f "apps/doctor-platform/doctor-api/Dockerfile" "apps/doctor-platform/doctor-api/"
docker tag "oncolife-doctor-api:latest" "$ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com/oncolife-doctor-api:latest"
docker push "$ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com/oncolife-doctor-api:latest"
Write-Host "  ✓ doctor-api pushed" -ForegroundColor Green

Write-Host ""

if ($BuildOnly) {
    Write-Host "=============================================="
    Write-Host "BUILD COMPLETE (--BuildOnly flag set)"
    Write-Host "=============================================="
    Write-Host ""
    Write-Host "Images pushed to ECR:"
    Write-Host "  $ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com/oncolife-patient-api:latest"
    Write-Host "  $ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com/oncolife-doctor-api:latest"
    Write-Host ""
    Write-Host "Next: Run the full script without --BuildOnly to continue deployment."
    exit 0
}

# ------------------------------------------------------------------------------
# Step 7: Create ECS Cluster
# ------------------------------------------------------------------------------
Write-Host "Step 7: Creating ECS cluster..." -ForegroundColor Cyan

try {
    $clusters = (aws ecs describe-clusters --clusters "oncolife-production" | ConvertFrom-Json).clusters
    if ($clusters.Count -gt 0 -and $clusters[0].status -eq "ACTIVE") {
        Write-Host "  ✓ Cluster already exists" -ForegroundColor Green
    } else {
        throw "Create cluster"
    }
} catch {
    aws ecs create-cluster `
        --cluster-name "oncolife-production" `
        --capacity-providers "FARGATE" "FARGATE_SPOT" `
        --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 | Out-Null
    Write-Host "  ✓ Created ECS cluster: oncolife-production" -ForegroundColor Green
}

Write-Host ""

# ------------------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------------------
Write-Host "=============================================="
Write-Host "DEPLOYMENT PROGRESS COMPLETE!"
Write-Host "=============================================="
Write-Host ""
Write-Host "What was created:"
Write-Host "  ✓ ECS service-linked role"
Write-Host "  ✓ ECR repositories (4)"
Write-Host "  ✓ CloudWatch log groups (2)"
Write-Host "  ✓ Docker images built and pushed (2)"
Write-Host "  ✓ ECS cluster"
Write-Host ""
Write-Host "=============================================="
Write-Host "MANUAL STEPS STILL REQUIRED:"
Write-Host "=============================================="
Write-Host ""
Write-Host "1. CREATE VPC (AWS Console recommended):"
Write-Host "   - Go to VPC Console > Create VPC"
Write-Host "   - Use 'VPC and more' wizard"
Write-Host "   - Name: oncolife, 2 AZs, 2 public + 2 private subnets"
Write-Host ""
Write-Host "2. CREATE SECURITY GROUPS:"
Write-Host "   - ALB SG: Allow 80, 443 from internet"
Write-Host "   - ECS SG: Allow 8000, 8001 from ALB SG"
Write-Host "   - RDS SG: Allow 5432 from ECS SG"
Write-Host ""
Write-Host "3. CREATE RDS:"
Write-Host "   aws rds create-db-instance --db-instance-identifier oncolife-db ..."
Write-Host ""
Write-Host "4. CREATE SECRETS in Secrets Manager"
Write-Host ""
Write-Host "5. CREATE ALB and Target Groups"
Write-Host ""
Write-Host "6. REGISTER Task Definitions (update ACCOUNT_ID and secret ARNs)"
Write-Host ""
Write-Host "7. CREATE ECS Services"
Write-Host ""
Write-Host "See docs/STEP_BY_STEP_DEPLOYMENT.md for detailed commands."
Write-Host "See docs/DEPLOYMENT_TROUBLESHOOTING.md for error fixes."
Write-Host ""
Write-Host "=============================================="

# Save output for reference
$outputFile = "deployment-output-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"
@"
OncoLife Deployment Output
Generated: $(Get-Date)

AWS Account ID: $ACCOUNT_ID
Region: $Region

ECR Repositories:
- $ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com/oncolife-patient-api:latest
- $ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com/oncolife-doctor-api:latest
- $ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com/oncolife-patient-web:latest
- $ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com/oncolife-doctor-web:latest

ECS Cluster: oncolife-production

Log Groups:
- /ecs/oncolife-patient-api
- /ecs/oncolife-doctor-api

Next Steps: Complete VPC, Security Groups, RDS, ALB, and ECS Services
"@ | Out-File $outputFile

Write-Host "Output saved to: $outputFile"
