# ==============================================================================
# OncoLife Complete AWS Deployment Script (PowerShell)
# ==============================================================================
# 
# Script:       full-deploy.ps1
# Description:  Automates the complete AWS deployment process including VPC,
#               RDS, Cognito, ECR, ECS, and ALB setup.
#
# Created:      2025-12-30
# Modified:     2026-01-16
# Author:       Naveen Babu S A
# Version:      2.1.0
#
# ==============================================================================
# This script automates the ENTIRE AWS deployment process.
# 
# Prerequisites:
#   1. AWS CLI installed and configured (run: aws configure)
#   2. Docker Desktop installed and running
#   3. Run from PowerShell (NOT Git Bash!)
#   4. Run from the project root directory (Oncolife_Monolith)
#
# Usage:
#   .\scripts\aws\full-deploy.ps1
#
# Options:
#   -Region         AWS region (default: us-east-1)
#   -Environment    Environment name (default: production)
#   -SkipVPC        Skip VPC creation (if already exists)
#   -SkipRDS        Skip RDS creation (if already exists)
#   -SkipCognito    Skip Cognito creation (if already exists)
#   -SkipBuild      Skip Docker build (use existing images)
#   -Verbose        Show detailed output
#
# Examples:
#   .\scripts\aws\full-deploy.ps1
#   .\scripts\aws\full-deploy.ps1 -Region us-east-1
#   .\scripts\aws\full-deploy.ps1 -SkipVPC -SkipRDS
#   .\scripts\aws\full-deploy.ps1 -SkipVPC -SkipRDS -SkipCognito
#
# ==============================================================================

[CmdletBinding()]
param(
    [string]$Region = "us-east-1",
    [string]$Environment = "production",
    [switch]$SkipVPC,
    [switch]$SkipRDS,
    [switch]$SkipCognito,
    [switch]$SkipBuild,
    [switch]$DryRun
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Project settings
$PROJECT_NAME = "oncolife"
$VPC_CIDR = "10.0.0.0/16"
$PUBLIC_SUBNET_1_CIDR = "10.0.1.0/24"
$PUBLIC_SUBNET_2_CIDR = "10.0.2.0/24"
$PRIVATE_SUBNET_1_CIDR = "10.0.10.0/24"
$PRIVATE_SUBNET_2_CIDR = "10.0.11.0/24"

# RDS settings
$RDS_INSTANCE_CLASS = "db.t3.medium"
$RDS_ENGINE_VERSION = "15"
$RDS_ALLOCATED_STORAGE = 100

# ECS settings
$PATIENT_API_CPU = "512"
$PATIENT_API_MEMORY = "1024"
$DOCTOR_API_CPU = "512"
$DOCTOR_API_MEMORY = "1024"
$DESIRED_COUNT = 2

# Store created resource IDs
$script:DeploymentConfig = @{}
$script:SKIP_SECURITY_GROUPS = $false

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "=============================================" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "  -> $Message" -ForegroundColor Yellow
}

function Write-Warning2 {
    param([string]$Message)
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
}

function Write-Error2 {
    param([string]$Message)
    Write-Host "  [ERROR] $Message" -ForegroundColor Red
}

function Get-SecureInput {
    param([string]$Prompt)
    $secure = Read-Host -Prompt $Prompt -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    return [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

function Wait-ForResource {
    param(
        [string]$Type,
        [string]$Name,
        [scriptblock]$CheckScript,
        [int]$TimeoutMinutes = 15,
        [int]$IntervalSeconds = 30
    )
    
    $endTime = (Get-Date).AddMinutes($TimeoutMinutes)
    Write-Info "Waiting for $Type '$Name' to be ready (timeout: $TimeoutMinutes min)..."
    
    while ((Get-Date) -lt $endTime) {
        try {
            $result = & $CheckScript
            if ($result) {
                Write-Host ""
                Write-Success "$Type '$Name' is ready"
                return $true
            }
        } catch {
            # Ignore errors during polling
        }
        Write-Host "." -NoNewline
        Start-Sleep -Seconds $IntervalSeconds
    }
    
    Write-Host ""
    throw "Timeout waiting for $Type '$Name'"
}

function Save-DeploymentConfig {
    $configPath = "deployment-config-$(Get-Date -Format 'yyyyMMdd-HHmmss').json"
    $script:DeploymentConfig | ConvertTo-Json -Depth 10 | Out-File $configPath -Encoding utf8
    Write-Info "Configuration saved to: $configPath"
}

function Remove-TempFiles {
    # Clean up any temp JSON files
    Remove-Item -Path "patient-task-def.json" -ErrorAction SilentlyContinue
    Remove-Item -Path "doctor-task-def.json" -ErrorAction SilentlyContinue
}

# ==============================================================================
# STEP 0: PREREQUISITES CHECK
# ==============================================================================

function Test-Prerequisites {
    Write-Step "STEP 0: Checking Prerequisites"
    
    # Check AWS CLI
    try {
        $awsVersion = aws --version 2>&1
        Write-Success "AWS CLI found: $awsVersion"
    } catch {
        Write-Error2 "AWS CLI not found. Please install it from https://aws.amazon.com/cli/"
        exit 1
    }
    
    # Check AWS credentials
    try {
        $identity = aws sts get-caller-identity 2>$null | ConvertFrom-Json
        $script:ACCOUNT_ID = $identity.Account
        Write-Success "AWS Account: $($script:ACCOUNT_ID)"
        $script:DeploymentConfig["AccountId"] = $script:ACCOUNT_ID
    } catch {
        Write-Error2 "AWS CLI not configured. Run 'aws configure' first."
        exit 1
    }
    
    # Check Docker
    try {
        docker version 2>$null | Out-Null
        Write-Success "Docker is running"
    } catch {
        Write-Error2 "Docker not running. Start Docker Desktop first."
        exit 1
    }
    
    # Check we're in the right directory
    if (-not (Test-Path "apps/patient-platform/patient-api/Dockerfile")) {
        Write-Error2 "Not in project root. cd to Oncolife_Monolith first."
        Write-Info "Current directory: $(Get-Location)"
        exit 1
    }
    Write-Success "Project directory verified"
    
    # Set region
    $env:AWS_REGION = $Region
    $env:AWS_DEFAULT_REGION = $Region
    $script:DeploymentConfig["Region"] = $Region
    Write-Success "Region: $Region"
    
    # Get availability zones
    try {
        $azs = (aws ec2 describe-availability-zones --region $Region --query 'AvailabilityZones[0:2].ZoneName' --output json | ConvertFrom-Json)
        $script:AZ1 = $azs[0]
        $script:AZ2 = $azs[1]
        Write-Success "Availability Zones: $($script:AZ1), $($script:AZ2)"
    } catch {
        Write-Error2 "Could not get availability zones. Check your AWS region."
        exit 1
    }
}

# ==============================================================================
# STEP 1: CREATE ECS SERVICE-LINKED ROLE
# ==============================================================================

function New-ECSServiceRole {
    Write-Step "STEP 1: Creating ECS Service-Linked Role"
    
    try {
        aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com 2>$null | Out-Null
        Write-Success "ECS service-linked role created"
    } catch {
        Write-Success "ECS service-linked role already exists (OK)"
    }
}

# ==============================================================================
# STEP 2: CREATE VPC AND NETWORKING
# ==============================================================================

function New-VPCInfrastructure {
    Write-Step "STEP 2: Creating VPC and Networking"
    
    if ($SkipVPC) {
        Write-Info "Skipping VPC creation (-SkipVPC flag)"
        Write-Host ""
        Write-Host "  Enter your existing AWS resource IDs:" -ForegroundColor Yellow
        
        $script:VPC_ID = Read-Host "  VPC ID (vpc-xxxxxxxx)"
        $script:PUBLIC_SUBNET_1 = Read-Host "  Public Subnet 1 ID (subnet-xxx)"
        $script:PUBLIC_SUBNET_2 = Read-Host "  Public Subnet 2 ID (subnet-xxx)"
        $script:PRIVATE_SUBNET_1 = Read-Host "  Private Subnet 1 ID (subnet-xxx)"
        $script:PRIVATE_SUBNET_2 = Read-Host "  Private Subnet 2 ID (subnet-xxx)"
        $script:SG_ALB = Read-Host "  ALB Security Group ID (sg-xxx)"
        $script:SG_ECS = Read-Host "  ECS Security Group ID (sg-xxx)"
        $script:SG_RDS = Read-Host "  RDS Security Group ID (sg-xxx)"
        
        $script:SKIP_SECURITY_GROUPS = $true
        
        # Save to config
        $script:DeploymentConfig["VpcId"] = $script:VPC_ID
        $script:DeploymentConfig["PublicSubnet1"] = $script:PUBLIC_SUBNET_1
        $script:DeploymentConfig["PublicSubnet2"] = $script:PUBLIC_SUBNET_2
        $script:DeploymentConfig["PrivateSubnet1"] = $script:PRIVATE_SUBNET_1
        $script:DeploymentConfig["PrivateSubnet2"] = $script:PRIVATE_SUBNET_2
        $script:DeploymentConfig["AlbSecurityGroup"] = $script:SG_ALB
        $script:DeploymentConfig["EcsSecurityGroup"] = $script:SG_ECS
        $script:DeploymentConfig["RdsSecurityGroup"] = $script:SG_RDS
        return
    }
    
    # Create VPC
    Write-Info "Creating VPC..."
    $vpcResult = aws ec2 create-vpc `
        --cidr-block $VPC_CIDR `
        --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=$PROJECT_NAME-vpc}]" `
        --output json | ConvertFrom-Json
    
    $script:VPC_ID = $vpcResult.Vpc.VpcId
    if (-not $script:VPC_ID) {
        throw "Failed to create VPC"
    }
    Write-Success "VPC created: $($script:VPC_ID)"
    
    # Enable DNS hostnames
    aws ec2 modify-vpc-attribute --vpc-id $script:VPC_ID --enable-dns-hostnames "{`"Value`":true}"
    aws ec2 modify-vpc-attribute --vpc-id $script:VPC_ID --enable-dns-support "{`"Value`":true}"
    Write-Success "DNS hostnames enabled"
    
    # Create Internet Gateway
    Write-Info "Creating Internet Gateway..."
    $igwResult = aws ec2 create-internet-gateway `
        --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=$PROJECT_NAME-igw}]" `
        --output json | ConvertFrom-Json
    
    $script:IGW_ID = $igwResult.InternetGateway.InternetGatewayId
    aws ec2 attach-internet-gateway --internet-gateway-id $script:IGW_ID --vpc-id $script:VPC_ID
    Write-Success "Internet Gateway attached: $($script:IGW_ID)"
    
    # Create Public Subnets
    Write-Info "Creating Public Subnets..."
    
    $pub1 = aws ec2 create-subnet `
        --vpc-id $script:VPC_ID `
        --cidr-block $PUBLIC_SUBNET_1_CIDR `
        --availability-zone $script:AZ1 `
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-public-1}]" `
        --output json | ConvertFrom-Json
    $script:PUBLIC_SUBNET_1 = $pub1.Subnet.SubnetId
    
    $pub2 = aws ec2 create-subnet `
        --vpc-id $script:VPC_ID `
        --cidr-block $PUBLIC_SUBNET_2_CIDR `
        --availability-zone $script:AZ2 `
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-public-2}]" `
        --output json | ConvertFrom-Json
    $script:PUBLIC_SUBNET_2 = $pub2.Subnet.SubnetId
    
    # Enable auto-assign public IP
    aws ec2 modify-subnet-attribute --subnet-id $script:PUBLIC_SUBNET_1 --map-public-ip-on-launch
    aws ec2 modify-subnet-attribute --subnet-id $script:PUBLIC_SUBNET_2 --map-public-ip-on-launch
    
    Write-Success "Public Subnets: $($script:PUBLIC_SUBNET_1), $($script:PUBLIC_SUBNET_2)"
    
    # Create Private Subnets
    Write-Info "Creating Private Subnets..."
    
    $priv1 = aws ec2 create-subnet `
        --vpc-id $script:VPC_ID `
        --cidr-block $PRIVATE_SUBNET_1_CIDR `
        --availability-zone $script:AZ1 `
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-private-1}]" `
        --output json | ConvertFrom-Json
    $script:PRIVATE_SUBNET_1 = $priv1.Subnet.SubnetId
    
    $priv2 = aws ec2 create-subnet `
        --vpc-id $script:VPC_ID `
        --cidr-block $PRIVATE_SUBNET_2_CIDR `
        --availability-zone $script:AZ2 `
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-private-2}]" `
        --output json | ConvertFrom-Json
    $script:PRIVATE_SUBNET_2 = $priv2.Subnet.SubnetId
    
    Write-Success "Private Subnets: $($script:PRIVATE_SUBNET_1), $($script:PRIVATE_SUBNET_2)"
    
    # Create NAT Gateway (for private subnet internet access)
    Write-Info "Creating NAT Gateway (this takes ~2 minutes)..."
    
    $eipResult = aws ec2 allocate-address --domain vpc --output json | ConvertFrom-Json
    $script:EIP_ID = $eipResult.AllocationId
    
    $natResult = aws ec2 create-nat-gateway `
        --subnet-id $script:PUBLIC_SUBNET_1 `
        --allocation-id $script:EIP_ID `
        --tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=$PROJECT_NAME-nat}]" `
        --output json | ConvertFrom-Json
    
    $script:NAT_ID = $natResult.NatGateway.NatGatewayId
    
    # Wait for NAT Gateway
    Wait-ForResource -Type "NAT Gateway" -Name $script:NAT_ID -CheckScript {
        $status = (aws ec2 describe-nat-gateways --nat-gateway-ids $script:NAT_ID --query 'NatGateways[0].State' --output text)
        return $status -eq "available"
    } -TimeoutMinutes 5 -IntervalSeconds 15
    
    # Create Route Tables
    Write-Info "Creating Route Tables..."
    
    # Public route table
    $pubRtResult = aws ec2 create-route-table `
        --vpc-id $script:VPC_ID `
        --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=$PROJECT_NAME-public-rt}]" `
        --output json | ConvertFrom-Json
    $script:PUBLIC_RT = $pubRtResult.RouteTable.RouteTableId
    
    aws ec2 create-route --route-table-id $script:PUBLIC_RT --destination-cidr-block "0.0.0.0/0" --gateway-id $script:IGW_ID | Out-Null
    aws ec2 associate-route-table --route-table-id $script:PUBLIC_RT --subnet-id $script:PUBLIC_SUBNET_1 | Out-Null
    aws ec2 associate-route-table --route-table-id $script:PUBLIC_RT --subnet-id $script:PUBLIC_SUBNET_2 | Out-Null
    
    # Private route table
    $privRtResult = aws ec2 create-route-table `
        --vpc-id $script:VPC_ID `
        --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=$PROJECT_NAME-private-rt}]" `
        --output json | ConvertFrom-Json
    $script:PRIVATE_RT = $privRtResult.RouteTable.RouteTableId
    
    aws ec2 create-route --route-table-id $script:PRIVATE_RT --destination-cidr-block "0.0.0.0/0" --nat-gateway-id $script:NAT_ID | Out-Null
    aws ec2 associate-route-table --route-table-id $script:PRIVATE_RT --subnet-id $script:PRIVATE_SUBNET_1 | Out-Null
    aws ec2 associate-route-table --route-table-id $script:PRIVATE_RT --subnet-id $script:PRIVATE_SUBNET_2 | Out-Null
    
    Write-Success "Route Tables configured"
    
    # Save to config
    $script:DeploymentConfig["VpcId"] = $script:VPC_ID
    $script:DeploymentConfig["PublicSubnet1"] = $script:PUBLIC_SUBNET_1
    $script:DeploymentConfig["PublicSubnet2"] = $script:PUBLIC_SUBNET_2
    $script:DeploymentConfig["PrivateSubnet1"] = $script:PRIVATE_SUBNET_1
    $script:DeploymentConfig["PrivateSubnet2"] = $script:PRIVATE_SUBNET_2
}

# ==============================================================================
# STEP 3: CREATE SECURITY GROUPS
# ==============================================================================

function New-SecurityGroups {
    Write-Step "STEP 3: Creating Security Groups"
    
    if ($script:SKIP_SECURITY_GROUPS) {
        Write-Info "Skipping Security Groups (using existing from -SkipVPC)"
        Write-Success "ALB SG: $($script:SG_ALB)"
        Write-Success "ECS SG: $($script:SG_ECS)"
        Write-Success "RDS SG: $($script:SG_RDS)"
        return
    }
    
    # ALB Security Group
    Write-Info "Creating ALB Security Group..."
    $albSg = aws ec2 create-security-group `
        --group-name "$PROJECT_NAME-alb-sg" `
        --description "OncoLife ALB Security Group" `
        --vpc-id $script:VPC_ID `
        --output json | ConvertFrom-Json
    $script:SG_ALB = $albSg.GroupId
    
    aws ec2 authorize-security-group-ingress --group-id $script:SG_ALB --protocol tcp --port 443 --cidr "0.0.0.0/0" | Out-Null
    aws ec2 authorize-security-group-ingress --group-id $script:SG_ALB --protocol tcp --port 80 --cidr "0.0.0.0/0" | Out-Null
    aws ec2 create-tags --resources $script:SG_ALB --tags "Key=Name,Value=$PROJECT_NAME-alb-sg" | Out-Null
    Write-Success "ALB SG: $($script:SG_ALB)"
    
    # ECS Security Group
    Write-Info "Creating ECS Security Group..."
    $ecsSg = aws ec2 create-security-group `
        --group-name "$PROJECT_NAME-ecs-sg" `
        --description "OncoLife ECS Security Group" `
        --vpc-id $script:VPC_ID `
        --output json | ConvertFrom-Json
    $script:SG_ECS = $ecsSg.GroupId
    
    aws ec2 authorize-security-group-ingress --group-id $script:SG_ECS --protocol tcp --port 8000 --source-group $script:SG_ALB | Out-Null
    aws ec2 authorize-security-group-ingress --group-id $script:SG_ECS --protocol tcp --port 8001 --source-group $script:SG_ALB | Out-Null
    aws ec2 create-tags --resources $script:SG_ECS --tags "Key=Name,Value=$PROJECT_NAME-ecs-sg" | Out-Null
    Write-Success "ECS SG: $($script:SG_ECS)"
    
    # RDS Security Group
    Write-Info "Creating RDS Security Group..."
    $rdsSg = aws ec2 create-security-group `
        --group-name "$PROJECT_NAME-rds-sg" `
        --description "OncoLife RDS Security Group" `
        --vpc-id $script:VPC_ID `
        --output json | ConvertFrom-Json
    $script:SG_RDS = $rdsSg.GroupId
    
    aws ec2 authorize-security-group-ingress --group-id $script:SG_RDS --protocol tcp --port 5432 --source-group $script:SG_ECS | Out-Null
    aws ec2 create-tags --resources $script:SG_RDS --tags "Key=Name,Value=$PROJECT_NAME-rds-sg" | Out-Null
    Write-Success "RDS SG: $($script:SG_RDS)"
    
    # Save to config
    $script:DeploymentConfig["AlbSecurityGroup"] = $script:SG_ALB
    $script:DeploymentConfig["EcsSecurityGroup"] = $script:SG_ECS
    $script:DeploymentConfig["RdsSecurityGroup"] = $script:SG_RDS
}

# ==============================================================================
# STEP 4: CREATE RDS DATABASE
# ==============================================================================

function New-RDSDatabase {
    Write-Step "STEP 4: Creating RDS PostgreSQL Database"
    
    if ($SkipRDS) {
        Write-Info "Skipping RDS creation (-SkipRDS flag)"
        $script:RDS_ENDPOINT = Read-Host "  Enter existing RDS endpoint (xxx.rds.amazonaws.com)"
        $script:DB_USERNAME = Read-Host "  Enter DB username (default: oncolife_admin)"
        if ([string]::IsNullOrWhiteSpace($script:DB_USERNAME)) {
            $script:DB_USERNAME = "oncolife_admin"
        }
        $script:DB_PASSWORD = Get-SecureInput "  Enter existing RDS password"
        return
    }
    
    # Get database password
    Write-Host ""
    Write-Host "  Enter a password for the database." -ForegroundColor Yellow
    Write-Host "  Requirements: 8+ chars, letters, numbers, no @/`"/spaces" -ForegroundColor Yellow
    $script:DB_PASSWORD = Get-SecureInput "  Database Password"
    $script:DB_USERNAME = "oncolife_admin"
    
    # Validate password length
    if ($script:DB_PASSWORD.Length -lt 8) {
        Write-Error2 "Password must be at least 8 characters!"
        exit 1
    }
    
    # Create DB Subnet Group
    Write-Info "Creating DB Subnet Group..."
    aws rds create-db-subnet-group `
        --db-subnet-group-name "$PROJECT_NAME-db-subnet" `
        --db-subnet-group-description "OncoLife Database Subnets" `
        --subnet-ids $script:PRIVATE_SUBNET_1 $script:PRIVATE_SUBNET_2 | Out-Null
    Write-Success "DB Subnet Group created"
    
    # Create RDS Instance
    Write-Info "Creating RDS instance (this takes 10-15 minutes)..."
    aws rds create-db-instance `
        --db-instance-identifier "$PROJECT_NAME-db" `
        --db-instance-class $RDS_INSTANCE_CLASS `
        --engine postgres `
        --engine-version $RDS_ENGINE_VERSION `
        --master-username $script:DB_USERNAME `
        --master-user-password $script:DB_PASSWORD `
        --allocated-storage $RDS_ALLOCATED_STORAGE `
        --storage-type gp3 `
        --storage-encrypted `
        --vpc-security-group-ids $script:SG_RDS `
        --db-subnet-group-name "$PROJECT_NAME-db-subnet" `
        --no-publicly-accessible `
        --backup-retention-period 7 `
        --tags "Key=Name,Value=$PROJECT_NAME-db" | Out-Null
    
    # Wait for RDS
    Wait-ForResource -Type "RDS Instance" -Name "$PROJECT_NAME-db" -CheckScript {
        $status = (aws rds describe-db-instances --db-instance-identifier "$PROJECT_NAME-db" --query 'DBInstances[0].DBInstanceStatus' --output text)
        return $status -eq "available"
    } -TimeoutMinutes 20 -IntervalSeconds 30
    
    # Get endpoint
    $script:RDS_ENDPOINT = (aws rds describe-db-instances `
        --db-instance-identifier "$PROJECT_NAME-db" `
        --query 'DBInstances[0].Endpoint.Address' `
        --output text)
    
    Write-Success "RDS Endpoint: $($script:RDS_ENDPOINT)"
    
    $script:DeploymentConfig["RdsEndpoint"] = $script:RDS_ENDPOINT
    $script:DeploymentConfig["DbUsername"] = $script:DB_USERNAME
}

# ==============================================================================
# STEP 5: CREATE COGNITO USER POOL
# ==============================================================================

function New-CognitoUserPool {
    Write-Step "STEP 5: Creating Cognito User Pool"
    
    if ($SkipCognito) {
        Write-Info "Skipping Cognito creation (-SkipCognito flag)"
        $script:COGNITO_POOL_ID = Read-Host "  Enter existing User Pool ID (us-east-1_xxxxxxxx)"
        $script:COGNITO_CLIENT_ID = Read-Host "  Enter existing Client ID"
        $script:COGNITO_CLIENT_SECRET = Get-SecureInput "  Enter existing Client Secret"
        
        Write-Success "User Pool ID: $($script:COGNITO_POOL_ID)"
        Write-Success "Client ID: $($script:COGNITO_CLIENT_ID)"
        
        $script:DeploymentConfig["CognitoPoolId"] = $script:COGNITO_POOL_ID
        $script:DeploymentConfig["CognitoClientId"] = $script:COGNITO_CLIENT_ID
        return
    }
    
    Write-Info "Creating User Pool..."
    $poolResult = aws cognito-idp create-user-pool `
        --pool-name "$PROJECT_NAME-patients" `
        --auto-verified-attributes email `
        --username-attributes email `
        --mfa-configuration OFF `
        --policies '{"PasswordPolicy":{"MinimumLength":8,"RequireUppercase":true,"RequireLowercase":true,"RequireNumbers":true,"RequireSymbols":true}}' `
        --admin-create-user-config '{"AllowAdminCreateUserOnly":true}' `
        --output json | ConvertFrom-Json
    
    $script:COGNITO_POOL_ID = $poolResult.UserPool.Id
    Write-Success "User Pool ID: $($script:COGNITO_POOL_ID)"
    
    # Create App Client with CORRECT auth flow names
    Write-Info "Creating App Client..."
    $clientResult = aws cognito-idp create-user-pool-client `
        --user-pool-id $script:COGNITO_POOL_ID `
        --client-name "$PROJECT_NAME-api-client" `
        --generate-secret `
        --explicit-auth-flows "ALLOW_ADMIN_USER_PASSWORD_AUTH" "ALLOW_REFRESH_TOKEN_AUTH" "ALLOW_USER_PASSWORD_AUTH" `
        --output json | ConvertFrom-Json
    
    $script:COGNITO_CLIENT_ID = $clientResult.UserPoolClient.ClientId
    $script:COGNITO_CLIENT_SECRET = $clientResult.UserPoolClient.ClientSecret
    Write-Success "Client ID: $($script:COGNITO_CLIENT_ID)"
    
    $script:DeploymentConfig["CognitoPoolId"] = $script:COGNITO_POOL_ID
    $script:DeploymentConfig["CognitoClientId"] = $script:COGNITO_CLIENT_ID
}

# ==============================================================================
# STEP 6: CREATE S3 BUCKETS
# ==============================================================================

function New-S3Buckets {
    Write-Step "STEP 6: Creating S3 Buckets"
    
    $buckets = @("$PROJECT_NAME-referrals-$($script:ACCOUNT_ID)", "$PROJECT_NAME-education-$($script:ACCOUNT_ID)")
    
    foreach ($bucket in $buckets) {
        Write-Info "Creating bucket: $bucket"
        
        try {
            if ($Region -eq "us-east-1") {
                aws s3api create-bucket --bucket $bucket --region $Region 2>$null | Out-Null
            } else {
                aws s3api create-bucket --bucket $bucket --region $Region --create-bucket-configuration LocationConstraint=$Region 2>$null | Out-Null
            }
        } catch {
            Write-Info "Bucket may already exist, continuing..."
        }
        
        # Enable encryption
        try {
            aws s3api put-bucket-encryption --bucket $bucket --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"}}]}' | Out-Null
        } catch { }
        
        # Block public access
        try {
            aws s3api put-public-access-block --bucket $bucket --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" | Out-Null
        } catch { }
        
        Write-Success "Bucket configured: $bucket"
    }
}

# ==============================================================================
# STEP 7: CREATE SECRETS IN SECRETS MANAGER
# ==============================================================================

function New-SecretsManagerSecrets {
    Write-Step "STEP 7: Creating Secrets Manager Secrets"
    
    # Database secret
    Write-Info "Creating database secret..."
    $dbSecret = @{
        host = $script:RDS_ENDPOINT
        port = "5432"
        username = $script:DB_USERNAME
        password = $script:DB_PASSWORD
        patient_db = "oncolife_patient"
        doctor_db = "oncolife_doctor"
    } | ConvertTo-Json -Compress
    
    try {
        aws secretsmanager create-secret --name "$PROJECT_NAME/db" --secret-string $dbSecret 2>$null | Out-Null
        Write-Success "Database secret created"
    } catch {
        aws secretsmanager put-secret-value --secret-id "$PROJECT_NAME/db" --secret-string $dbSecret | Out-Null
        Write-Success "Database secret updated"
    }
    
    # Cognito secret
    Write-Info "Creating Cognito secret..."
    $cognitoSecret = @{
        user_pool_id = $script:COGNITO_POOL_ID
        client_id = $script:COGNITO_CLIENT_ID
        client_secret = $script:COGNITO_CLIENT_SECRET
    } | ConvertTo-Json -Compress
    
    try {
        aws secretsmanager create-secret --name "$PROJECT_NAME/cognito" --secret-string $cognitoSecret 2>$null | Out-Null
        Write-Success "Cognito secret created"
    } catch {
        aws secretsmanager put-secret-value --secret-id "$PROJECT_NAME/cognito" --secret-string $cognitoSecret | Out-Null
        Write-Success "Cognito secret updated"
    }
    
    # Get secret ARNs
    $script:DB_SECRET_ARN = (aws secretsmanager describe-secret --secret-id "$PROJECT_NAME/db" --query 'ARN' --output text)
    $script:COGNITO_SECRET_ARN = (aws secretsmanager describe-secret --secret-id "$PROJECT_NAME/cognito" --query 'ARN' --output text)
    
    Write-Success "DB Secret ARN: $($script:DB_SECRET_ARN)"
    Write-Success "Cognito Secret ARN: $($script:COGNITO_SECRET_ARN)"
    
    $script:DeploymentConfig["DbSecretArn"] = $script:DB_SECRET_ARN
    $script:DeploymentConfig["CognitoSecretArn"] = $script:COGNITO_SECRET_ARN
}

# ==============================================================================
# STEP 8: CREATE ECR REPOSITORIES
# ==============================================================================

function New-ECRRepositories {
    Write-Step "STEP 8: Creating ECR Repositories"
    
    $repos = @("$PROJECT_NAME-patient-api", "$PROJECT_NAME-doctor-api")
    
    foreach ($repo in $repos) {
        try {
            aws ecr describe-repositories --repository-names $repo 2>$null | Out-Null
            Write-Success "$repo already exists"
        } catch {
            aws ecr create-repository --repository-name $repo --image-scanning-configuration scanOnPush=true | Out-Null
            Write-Success "Created $repo"
        }
    }
}

# ==============================================================================
# STEP 9: CREATE CLOUDWATCH LOG GROUPS
# ==============================================================================

function New-CloudWatchLogGroups {
    Write-Step "STEP 9: Creating CloudWatch Log Groups"
    
    $logGroups = @("/ecs/$PROJECT_NAME-patient-api", "/ecs/$PROJECT_NAME-doctor-api")
    
    foreach ($lg in $logGroups) {
        try {
            aws logs create-log-group --log-group-name $lg 2>$null
            aws logs put-retention-policy --log-group-name $lg --retention-in-days 30
            Write-Success "Created: $lg"
        } catch {
            Write-Success "$lg already exists"
        }
    }
}

# ==============================================================================
# STEP 10: BUILD AND PUSH DOCKER IMAGES
# ==============================================================================

function Build-DockerImages {
    Write-Step "STEP 10: Building and Pushing Docker Images"
    
    if ($SkipBuild) {
        Write-Info "Skipping Docker build (-SkipBuild flag)"
        return
    }
    
    # Login to ECR
    Write-Info "Logging in to ECR..."
    $ecrPassword = aws ecr get-login-password --region $Region
    $ecrPassword | docker login --username AWS --password-stdin "$($script:ACCOUNT_ID).dkr.ecr.$Region.amazonaws.com"
    Write-Success "Logged in to ECR"
    
    # Build Patient API
    Write-Info "Building patient-api (this may take a few minutes)..."
    docker build -t "$PROJECT_NAME-patient-api:latest" -f "apps/patient-platform/patient-api/Dockerfile" "apps/patient-platform/patient-api/"
    docker tag "$PROJECT_NAME-patient-api:latest" "$($script:ACCOUNT_ID).dkr.ecr.$Region.amazonaws.com/$PROJECT_NAME-patient-api:latest"
    docker push "$($script:ACCOUNT_ID).dkr.ecr.$Region.amazonaws.com/$PROJECT_NAME-patient-api:latest"
    Write-Success "patient-api pushed to ECR"
    
    # Build Doctor API
    Write-Info "Building doctor-api (this may take a few minutes)..."
    docker build -t "$PROJECT_NAME-doctor-api:latest" -f "apps/doctor-platform/doctor-api/Dockerfile" "apps/doctor-platform/doctor-api/"
    docker tag "$PROJECT_NAME-doctor-api:latest" "$($script:ACCOUNT_ID).dkr.ecr.$Region.amazonaws.com/$PROJECT_NAME-doctor-api:latest"
    docker push "$($script:ACCOUNT_ID).dkr.ecr.$Region.amazonaws.com/$PROJECT_NAME-doctor-api:latest"
    Write-Success "doctor-api pushed to ECR"
}

# ==============================================================================
# STEP 11: CREATE IAM ROLES
# ==============================================================================

function New-IAMRoles {
    Write-Step "STEP 11: Creating IAM Roles"
    
    $trustPolicy = @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Principal = @{ Service = "ecs-tasks.amazonaws.com" }
                Action = "sts:AssumeRole"
            }
        )
    } | ConvertTo-Json -Depth 10 -Compress
    
    # Create execution role
    Write-Info "Creating Task Execution Role..."
    try {
        aws iam create-role --role-name "ecsTaskExecutionRole" --assume-role-policy-document $trustPolicy 2>$null | Out-Null
        Write-Success "Created ecsTaskExecutionRole"
    } catch {
        Write-Info "ecsTaskExecutionRole already exists (OK)"
    }
    
    aws iam attach-role-policy --role-name "ecsTaskExecutionRole" --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy" 2>$null
    aws iam attach-role-policy --role-name "ecsTaskExecutionRole" --policy-arn "arn:aws:iam::aws:policy/SecretsManagerReadWrite" 2>$null
    Write-Success "Task Execution Role configured"
    
    # Create task role
    Write-Info "Creating Task Role..."
    try {
        aws iam create-role --role-name "${PROJECT_NAME}TaskRole" --assume-role-policy-document $trustPolicy 2>$null | Out-Null
        Write-Success "Created ${PROJECT_NAME}TaskRole"
    } catch {
        Write-Info "${PROJECT_NAME}TaskRole already exists (OK)"
    }
    
    $taskPolicy = @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Action = @("s3:GetObject", "s3:PutObject", "s3:ListBucket")
                Resource = @("arn:aws:s3:::$PROJECT_NAME-*", "arn:aws:s3:::$PROJECT_NAME-*/*")
            },
            @{
                Effect = "Allow"
                Action = @("cognito-idp:AdminCreateUser", "cognito-idp:AdminDeleteUser", "cognito-idp:AdminInitiateAuth", "cognito-idp:AdminRespondToAuthChallenge", "cognito-idp:AdminGetUser")
                Resource = "*"
            },
            @{
                Effect = "Allow"
                Action = @("ses:SendEmail", "ses:SendRawEmail")
                Resource = "*"
            },
            @{
                Effect = "Allow"
                Action = @("sns:Publish")
                Resource = "*"
            },
            @{
                Effect = "Allow"
                Action = @("textract:AnalyzeDocument", "textract:StartDocumentAnalysis", "textract:GetDocumentAnalysis")
                Resource = "*"
            }
        )
    } | ConvertTo-Json -Depth 10 -Compress
    
    aws iam put-role-policy --role-name "${PROJECT_NAME}TaskRole" --policy-name "OncolifePermissions" --policy-document $taskPolicy 2>$null
    Write-Success "Task Role configured"
}

# ==============================================================================
# STEP 12: CREATE ECS CLUSTER
# ==============================================================================

function New-ECSCluster {
    Write-Step "STEP 12: Creating ECS Cluster"
    
    try {
        $clusters = (aws ecs describe-clusters --clusters "$PROJECT_NAME-$Environment" 2>$null | ConvertFrom-Json).clusters
        if ($clusters.Count -gt 0 -and $clusters[0].status -eq "ACTIVE") {
            Write-Success "Cluster already exists"
            return
        }
    } catch { }
    
    aws ecs create-cluster `
        --cluster-name "$PROJECT_NAME-$Environment" `
        --capacity-providers "FARGATE" "FARGATE_SPOT" `
        --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 | Out-Null
    
    Write-Success "ECS Cluster created: $PROJECT_NAME-$Environment"
    $script:DeploymentConfig["EcsCluster"] = "$PROJECT_NAME-$Environment"
}

# ==============================================================================
# STEP 13: CREATE ALB AND TARGET GROUPS
# ==============================================================================

function New-ALBInfrastructure {
    Write-Step "STEP 13: Creating ALB and Target Groups"
    
    # Patient API ALB
    Write-Info "Creating Patient API ALB..."
    $patientAlb = aws elbv2 create-load-balancer `
        --name "$PROJECT_NAME-patient-alb" `
        --subnets $script:PUBLIC_SUBNET_1 $script:PUBLIC_SUBNET_2 `
        --security-groups $script:SG_ALB `
        --scheme internet-facing `
        --type application `
        --output json | ConvertFrom-Json
    
    $script:PATIENT_ALB_ARN = $patientAlb.LoadBalancers[0].LoadBalancerArn
    $script:PATIENT_ALB_DNS = $patientAlb.LoadBalancers[0].DNSName
    Write-Success "Patient ALB: $($script:PATIENT_ALB_DNS)"
    
    # Patient Target Group
    $patientTg = aws elbv2 create-target-group `
        --name "patient-api-tg" `
        --protocol HTTP `
        --port 8000 `
        --vpc-id $script:VPC_ID `
        --target-type ip `
        --health-check-path "/health" `
        --health-check-interval-seconds 30 `
        --healthy-threshold-count 2 `
        --unhealthy-threshold-count 3 `
        --output json | ConvertFrom-Json
    
    $script:PATIENT_TG_ARN = $patientTg.TargetGroups[0].TargetGroupArn
    Write-Success "Patient Target Group created"
    
    # Patient HTTP Listener
    aws elbv2 create-listener `
        --load-balancer-arn $script:PATIENT_ALB_ARN `
        --protocol HTTP `
        --port 80 `
        --default-actions "Type=forward,TargetGroupArn=$($script:PATIENT_TG_ARN)" | Out-Null
    Write-Success "Patient HTTP Listener created"
    
    # Doctor API ALB
    Write-Info "Creating Doctor API ALB..."
    $doctorAlb = aws elbv2 create-load-balancer `
        --name "$PROJECT_NAME-doctor-alb" `
        --subnets $script:PUBLIC_SUBNET_1 $script:PUBLIC_SUBNET_2 `
        --security-groups $script:SG_ALB `
        --scheme internet-facing `
        --type application `
        --output json | ConvertFrom-Json
    
    $script:DOCTOR_ALB_ARN = $doctorAlb.LoadBalancers[0].LoadBalancerArn
    $script:DOCTOR_ALB_DNS = $doctorAlb.LoadBalancers[0].DNSName
    Write-Success "Doctor ALB: $($script:DOCTOR_ALB_DNS)"
    
    # Doctor Target Group
    $doctorTg = aws elbv2 create-target-group `
        --name "doctor-api-tg" `
        --protocol HTTP `
        --port 8001 `
        --vpc-id $script:VPC_ID `
        --target-type ip `
        --health-check-path "/health" `
        --health-check-interval-seconds 30 `
        --healthy-threshold-count 2 `
        --unhealthy-threshold-count 3 `
        --output json | ConvertFrom-Json
    
    $script:DOCTOR_TG_ARN = $doctorTg.TargetGroups[0].TargetGroupArn
    Write-Success "Doctor Target Group created"
    
    # Doctor HTTP Listener
    aws elbv2 create-listener `
        --load-balancer-arn $script:DOCTOR_ALB_ARN `
        --protocol HTTP `
        --port 80 `
        --default-actions "Type=forward,TargetGroupArn=$($script:DOCTOR_TG_ARN)" | Out-Null
    Write-Success "Doctor HTTP Listener created"
    
    $script:DeploymentConfig["PatientAlbDns"] = $script:PATIENT_ALB_DNS
    $script:DeploymentConfig["DoctorAlbDns"] = $script:DOCTOR_ALB_DNS
    $script:DeploymentConfig["PatientTgArn"] = $script:PATIENT_TG_ARN
    $script:DeploymentConfig["DoctorTgArn"] = $script:DOCTOR_TG_ARN
}

# ==============================================================================
# STEP 14: REGISTER TASK DEFINITIONS
# ==============================================================================

function Register-TaskDefinitions {
    Write-Step "STEP 14: Registering Task Definitions"
    
    # Patient API Task Definition
    Write-Info "Registering Patient API Task Definition..."
    
    $patientTaskDef = @{
        family = "$PROJECT_NAME-patient-api"
        networkMode = "awsvpc"
        requiresCompatibilities = @("FARGATE")
        cpu = $PATIENT_API_CPU
        memory = $PATIENT_API_MEMORY
        executionRoleArn = "arn:aws:iam::$($script:ACCOUNT_ID):role/ecsTaskExecutionRole"
        taskRoleArn = "arn:aws:iam::$($script:ACCOUNT_ID):role/${PROJECT_NAME}TaskRole"
        containerDefinitions = @(
            @{
                name = "patient-api"
                image = "$($script:ACCOUNT_ID).dkr.ecr.$Region.amazonaws.com/$PROJECT_NAME-patient-api:latest"
                portMappings = @(@{ containerPort = 8000; protocol = "tcp" })
                essential = $true
                environment = @(
                    @{ name = "ENVIRONMENT"; value = $Environment }
                    @{ name = "DEBUG"; value = "false" }
                    @{ name = "LOG_LEVEL"; value = "INFO" }
                    @{ name = "AWS_REGION"; value = $Region }
                )
                secrets = @(
                    @{ name = "PATIENT_DB_HOST"; valueFrom = "$($script:DB_SECRET_ARN):host::" }
                    @{ name = "PATIENT_DB_PASSWORD"; valueFrom = "$($script:DB_SECRET_ARN):password::" }
                    @{ name = "PATIENT_DB_USER"; valueFrom = "$($script:DB_SECRET_ARN):username::" }
                    @{ name = "PATIENT_DB_NAME"; valueFrom = "$($script:DB_SECRET_ARN):patient_db::" }
                    @{ name = "COGNITO_USER_POOL_ID"; valueFrom = "$($script:COGNITO_SECRET_ARN):user_pool_id::" }
                    @{ name = "COGNITO_CLIENT_ID"; valueFrom = "$($script:COGNITO_SECRET_ARN):client_id::" }
                )
                logConfiguration = @{
                    logDriver = "awslogs"
                    options = @{
                        "awslogs-group" = "/ecs/$PROJECT_NAME-patient-api"
                        "awslogs-region" = $Region
                        "awslogs-stream-prefix" = "ecs"
                    }
                }
                healthCheck = @{
                    command = @("CMD-SHELL", "curl -f http://localhost:8000/health || exit 1")
                    interval = 30
                    timeout = 5
                    retries = 3
                    startPeriod = 60
                }
            }
        )
    }
    
    $patientTaskDef | ConvertTo-Json -Depth 10 | Out-File -FilePath "patient-task-def.json" -Encoding utf8
    aws ecs register-task-definition --cli-input-json "file://patient-task-def.json" | Out-Null
    Remove-Item "patient-task-def.json" -ErrorAction SilentlyContinue
    Write-Success "Patient API Task Definition registered"
    
    # Doctor API Task Definition
    Write-Info "Registering Doctor API Task Definition..."
    
    $doctorTaskDef = @{
        family = "$PROJECT_NAME-doctor-api"
        networkMode = "awsvpc"
        requiresCompatibilities = @("FARGATE")
        cpu = $DOCTOR_API_CPU
        memory = $DOCTOR_API_MEMORY
        executionRoleArn = "arn:aws:iam::$($script:ACCOUNT_ID):role/ecsTaskExecutionRole"
        taskRoleArn = "arn:aws:iam::$($script:ACCOUNT_ID):role/${PROJECT_NAME}TaskRole"
        containerDefinitions = @(
            @{
                name = "doctor-api"
                image = "$($script:ACCOUNT_ID).dkr.ecr.$Region.amazonaws.com/$PROJECT_NAME-doctor-api:latest"
                portMappings = @(@{ containerPort = 8001; protocol = "tcp" })
                essential = $true
                environment = @(
                    @{ name = "ENVIRONMENT"; value = $Environment }
                    @{ name = "DEBUG"; value = "false" }
                    @{ name = "LOG_LEVEL"; value = "INFO" }
                    @{ name = "AWS_REGION"; value = $Region }
                )
                secrets = @(
                    @{ name = "DOCTOR_DB_HOST"; valueFrom = "$($script:DB_SECRET_ARN):host::" }
                    @{ name = "DOCTOR_DB_PASSWORD"; valueFrom = "$($script:DB_SECRET_ARN):password::" }
                    @{ name = "DOCTOR_DB_USER"; valueFrom = "$($script:DB_SECRET_ARN):username::" }
                    @{ name = "DOCTOR_DB_NAME"; valueFrom = "$($script:DB_SECRET_ARN):doctor_db::" }
                    @{ name = "COGNITO_USER_POOL_ID"; valueFrom = "$($script:COGNITO_SECRET_ARN):user_pool_id::" }
                    @{ name = "COGNITO_CLIENT_ID"; valueFrom = "$($script:COGNITO_SECRET_ARN):client_id::" }
                )
                logConfiguration = @{
                    logDriver = "awslogs"
                    options = @{
                        "awslogs-group" = "/ecs/$PROJECT_NAME-doctor-api"
                        "awslogs-region" = $Region
                        "awslogs-stream-prefix" = "ecs"
                    }
                }
                healthCheck = @{
                    command = @("CMD-SHELL", "curl -f http://localhost:8001/health || exit 1")
                    interval = 30
                    timeout = 5
                    retries = 3
                    startPeriod = 60
                }
            }
        )
    }
    
    $doctorTaskDef | ConvertTo-Json -Depth 10 | Out-File -FilePath "doctor-task-def.json" -Encoding utf8
    aws ecs register-task-definition --cli-input-json "file://doctor-task-def.json" | Out-Null
    Remove-Item "doctor-task-def.json" -ErrorAction SilentlyContinue
    Write-Success "Doctor API Task Definition registered"
}

# ==============================================================================
# STEP 15: CREATE ECS SERVICES
# ==============================================================================

function New-ECSServices {
    Write-Step "STEP 15: Creating ECS Services"
    
    $networkConfig = "awsvpcConfiguration={subnets=[$($script:PRIVATE_SUBNET_1),$($script:PRIVATE_SUBNET_2)],securityGroups=[$($script:SG_ECS)],assignPublicIp=DISABLED}"
    
    # Patient API Service
    Write-Info "Creating Patient API Service..."
    aws ecs create-service `
        --cluster "$PROJECT_NAME-$Environment" `
        --service-name "patient-api-service" `
        --task-definition "$PROJECT_NAME-patient-api" `
        --desired-count $DESIRED_COUNT `
        --launch-type FARGATE `
        --network-configuration $networkConfig `
        --load-balancers "targetGroupArn=$($script:PATIENT_TG_ARN),containerName=patient-api,containerPort=8000" `
        --health-check-grace-period-seconds 120 | Out-Null
    
    Write-Success "Patient API Service created"
    
    # Doctor API Service
    Write-Info "Creating Doctor API Service..."
    aws ecs create-service `
        --cluster "$PROJECT_NAME-$Environment" `
        --service-name "doctor-api-service" `
        --task-definition "$PROJECT_NAME-doctor-api" `
        --desired-count $DESIRED_COUNT `
        --launch-type FARGATE `
        --network-configuration $networkConfig `
        --load-balancers "targetGroupArn=$($script:DOCTOR_TG_ARN),containerName=doctor-api,containerPort=8001" `
        --health-check-grace-period-seconds 120 | Out-Null
    
    Write-Success "Doctor API Service created"
}

# ==============================================================================
# STEP 16: VERIFY DEPLOYMENT
# ==============================================================================

function Test-Deployment {
    Write-Step "STEP 16: Verifying Deployment"
    
    Write-Info "Waiting for services to stabilize (this may take 2-5 minutes)..."
    
    # Wait for services
    $attempts = 0
    $maxAttempts = 20
    
    while ($attempts -lt $maxAttempts) {
        try {
            $services = aws ecs describe-services `
                --cluster "$PROJECT_NAME-$Environment" `
                --services "patient-api-service" "doctor-api-service" `
                --output json | ConvertFrom-Json
            
            $patientRunning = ($services.services | Where-Object { $_.serviceName -eq "patient-api-service" }).runningCount
            $doctorRunning = ($services.services | Where-Object { $_.serviceName -eq "doctor-api-service" }).runningCount
            
            Write-Host "  Patient API: $patientRunning running, Doctor API: $doctorRunning running" -ForegroundColor Yellow
            
            if ($patientRunning -ge 1 -and $doctorRunning -ge 1) {
                Write-Success "Services are running!"
                break
            }
        } catch {
            Write-Host "  Checking services..." -ForegroundColor Yellow
        }
        
        $attempts++
        Start-Sleep -Seconds 15
    }
    
    # Give ALB time to register targets
    Write-Info "Waiting for ALB to register targets..."
    Start-Sleep -Seconds 30
    
    # Test health endpoints
    Write-Info "Testing health endpoints..."
    
    try {
        $patientHealth = Invoke-RestMethod -Uri "http://$($script:PATIENT_ALB_DNS)/health" -Method GET -TimeoutSec 10
        Write-Success "Patient API healthy: $($patientHealth.status)"
    } catch {
        Write-Warning2 "Patient API not responding yet (may still be starting)"
    }
    
    try {
        $doctorHealth = Invoke-RestMethod -Uri "http://$($script:DOCTOR_ALB_DNS)/health" -Method GET -TimeoutSec 10
        Write-Success "Doctor API healthy: $($doctorHealth.status)"
    } catch {
        Write-Warning2 "Doctor API not responding yet (may still be starting)"
    }
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

function Main {
    $startTime = Get-Date
    
    Write-Host ""
    Write-Host "+==============================================================+" -ForegroundColor Magenta
    Write-Host "|       ONCOLIFE COMPLETE AWS DEPLOYMENT SCRIPT (PowerShell)   |" -ForegroundColor Magenta
    Write-Host "|                                                              |" -ForegroundColor Magenta
    Write-Host "|  This script will deploy the complete OncoLife platform     |" -ForegroundColor Magenta
    Write-Host "|  to AWS. Estimated time: 20-30 minutes                       |" -ForegroundColor Magenta
    Write-Host "+==============================================================+" -ForegroundColor Magenta
    Write-Host ""
    
    if ($DryRun) {
        Write-Host "DRY RUN MODE - No changes will be made" -ForegroundColor Yellow
        return
    }
    
    try {
        # Execute all steps
        Test-Prerequisites
        New-ECSServiceRole
        New-VPCInfrastructure
        New-SecurityGroups
        New-RDSDatabase
        New-CognitoUserPool
        New-S3Buckets
        New-SecretsManagerSecrets
        New-ECRRepositories
        New-CloudWatchLogGroups
        Build-DockerImages
        New-IAMRoles
        New-ECSCluster
        New-ALBInfrastructure
        Register-TaskDefinitions
        New-ECSServices
        Test-Deployment
        
        # Save configuration
        Save-DeploymentConfig
        
        $endTime = Get-Date
        $duration = $endTime - $startTime
        
        # Final Summary
        Write-Host ""
        Write-Host "+==============================================================+" -ForegroundColor Green
        Write-Host "|              DEPLOYMENT COMPLETE!                            |" -ForegroundColor Green
        Write-Host "+==============================================================+" -ForegroundColor Green
        Write-Host ""
        Write-Host "Duration: $($duration.Minutes) minutes $($duration.Seconds) seconds" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "ACCESS URLS:" -ForegroundColor Cyan
        Write-Host "  Patient API:      http://$($script:PATIENT_ALB_DNS)" -ForegroundColor White
        Write-Host "  Patient API Docs: http://$($script:PATIENT_ALB_DNS)/docs" -ForegroundColor White
        Write-Host "  Doctor API:       http://$($script:DOCTOR_ALB_DNS)" -ForegroundColor White
        Write-Host "  Doctor API Docs:  http://$($script:DOCTOR_ALB_DNS)/docs" -ForegroundColor White
        Write-Host ""
        Write-Host "NEXT STEPS:" -ForegroundColor Cyan
        Write-Host "  1. Create databases: Connect to RDS and run:" -ForegroundColor White
        Write-Host "     CREATE DATABASE oncolife_patient;" -ForegroundColor Yellow
        Write-Host "     CREATE DATABASE oncolife_doctor;" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  2. Run migrations from a bastion host or local with VPN" -ForegroundColor White
        Write-Host ""
        Write-Host "  3. (Optional) Set up custom domains with Route 53 and ACM" -ForegroundColor White
        Write-Host ""
        Write-Host "Configuration saved to: deployment-config-*.json" -ForegroundColor Cyan
        Write-Host ""
        
    } catch {
        Write-Host ""
        Write-Host "+==============================================================+" -ForegroundColor Red
        Write-Host "|              DEPLOYMENT FAILED                               |" -ForegroundColor Red
        Write-Host "+==============================================================+" -ForegroundColor Red
        Write-Host ""
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Write-Host "To resume deployment after fixing the issue:" -ForegroundColor Yellow
        Write-Host "  .\scripts\aws\full-deploy.ps1 -SkipVPC -SkipRDS -SkipCognito" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "See docs/DEPLOYMENT_TROUBLESHOOTING.md for help." -ForegroundColor Yellow
        Write-Host ""
        
        # Clean up temp files
        Remove-TempFiles
        
        # Save partial config
        Save-DeploymentConfig
        
        exit 1
    } finally {
        # Clean up temp files
        Remove-TempFiles
    }
}

# Run main
Main
