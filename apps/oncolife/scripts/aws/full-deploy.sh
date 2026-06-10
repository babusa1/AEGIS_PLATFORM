#!/bin/bash
# =============================================================================
# OncoLife Complete AWS Deployment Script (Bash Version)
# =============================================================================
# Developer: NAVEEN BABU S A
# Version: 2.1 | Updated January 2026
# =============================================================================
# This script automates the ENTIRE AWS deployment process.
#
# Usage: ./scripts/aws/full-deploy.sh
#
# Prerequisites:
#   1. AWS CLI installed and configured (run: aws configure)
#   2. Docker installed and running
#   3. Run from the project root directory (Oncolife_Monolith)
#
# Note: This script works with Git Bash on Windows (MINGW64)
#
# Options:
#   --region REGION      AWS region (default: us-east-1)
#   --skip-vpc          Skip VPC/Security Groups (prompts for existing IDs)
#   --skip-rds          Skip RDS creation (prompts for existing endpoint)
#   --skip-cognito      Skip Cognito creation (prompts for existing IDs)
#   --skip-build        Skip Docker build (use existing images in ECR)
#   --help              Show this help message
#
# Re-running after partial failure:
#   ./scripts/aws/full-deploy.sh --skip-vpc --skip-rds
#   ./scripts/aws/full-deploy.sh --skip-vpc --skip-rds --skip-cognito
#
# =============================================================================

# Prevent Git Bash from converting Unix paths to Windows paths
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"

set -e

# =============================================================================
# CONFIGURATION
# =============================================================================

AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="oncolife"
ENVIRONMENT="production"

# VPC Configuration
VPC_CIDR="10.0.0.0/16"
PUBLIC_SUBNET_1_CIDR="10.0.1.0/24"
PUBLIC_SUBNET_2_CIDR="10.0.2.0/24"
PRIVATE_SUBNET_1_CIDR="10.0.10.0/24"
PRIVATE_SUBNET_2_CIDR="10.0.11.0/24"

# RDS Configuration
RDS_INSTANCE_CLASS="db.t3.medium"
RDS_ENGINE_VERSION="15"
RDS_ALLOCATED_STORAGE="100"

# ECS Configuration
PATIENT_API_CPU="512"
PATIENT_API_MEMORY="1024"
DOCTOR_API_CPU="512"
DOCTOR_API_MEMORY="1024"
DESIRED_COUNT="2"

# Flags
SKIP_VPC=false
SKIP_RDS=false
SKIP_BUILD=false
SKIP_SECURITY_GROUPS=false
SKIP_COGNITO=false

# Colors (with fallback for Windows)
if [[ "$TERM" == "dumb" ]] || [[ -z "$TERM" ]]; then
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    MAGENTA=''
    NC=''
else
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    MAGENTA='\033[0;35m'
    NC='\033[0m'
fi

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

log_step() {
    echo ""
    echo -e "${CYAN}=============================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}=============================================${NC}"
}

log_info() {
    echo -e "${BLUE}  -> $1${NC}"
}

log_success() {
    echo -e "${GREEN}  [OK] $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}  [WARN] $1${NC}"
}

log_error() {
    echo -e "${RED}  [ERROR] $1${NC}"
}

get_password() {
    echo ""
    echo -e "${YELLOW}  Enter a password for the database.${NC}"
    echo -e "${YELLOW}  Requirements: 8+ chars, letters, numbers, no @/\"/spaces${NC}"
    read -sp "  Database Password: " DB_PASSWORD
    echo ""
    
    # Validate password length
    if [ ${#DB_PASSWORD} -lt 8 ]; then
        log_error "Password must be at least 8 characters!"
        get_password
    fi
}

wait_for_resource() {
    local type=$1
    local name=$2
    local check_cmd=$3
    local timeout=${4:-900}  # 15 minutes default
    local interval=${5:-30}
    
    log_info "Waiting for $type '$name' to be ready (timeout: $((timeout/60)) min)..."
    
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if eval "$check_cmd" 2>/dev/null; then
            log_success "$type '$name' is ready"
            return 0
        fi
        echo -n "."
        sleep $interval
        elapsed=$((elapsed + interval))
    done
    
    echo ""
    log_error "Timeout waiting for $type '$name'"
    return 1
}

# Cleanup function for temp files
cleanup_temp_files() {
    rm -f ./patient-task-def.json ./doctor-task-def.json 2>/dev/null || true
}

# Set trap to cleanup on exit
trap cleanup_temp_files EXIT

# =============================================================================
# PARSE ARGUMENTS
# =============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --skip-vpc)
            SKIP_VPC=true
            shift
            ;;
        --skip-rds)
            SKIP_RDS=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-cognito)
            SKIP_COGNITO=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --region REGION    AWS region (default: us-east-1)"
            echo "  --skip-vpc        Skip VPC/Security Groups (prompts for existing IDs)"
            echo "  --skip-rds        Skip RDS creation (prompts for existing endpoint)"
            echo "  --skip-cognito    Skip Cognito creation (prompts for existing IDs)"
            echo "  --skip-build      Skip Docker build (use existing images in ECR)"
            echo "  --help            Show this help"
            echo ""
            echo "For re-running after partial failure:"
            echo "  $0 --skip-vpc --skip-rds"
            echo "  $0 --skip-vpc --skip-rds --skip-cognito"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# STEP 0: PREREQUISITES CHECK
# =============================================================================

check_prerequisites() {
    log_step "STEP 0: Checking Prerequisites"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install it first."
        log_info "Install from: https://aws.amazon.com/cli/"
        exit 1
    fi
    log_success "AWS CLI found"
    
    # Test AWS credentials
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
    if [ -z "$ACCOUNT_ID" ]; then
        log_error "AWS CLI not configured. Run 'aws configure' first."
        exit 1
    fi
    log_success "AWS Account: $ACCOUNT_ID"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker Desktop."
        exit 1
    fi
    
    if ! docker info &> /dev/null 2>&1; then
        log_error "Docker daemon is not running. Please start Docker Desktop."
        exit 1
    fi
    log_success "Docker is running"
    
    # Check we're in the right directory
    if [ ! -f "apps/patient-platform/patient-api/Dockerfile" ]; then
        log_error "Not in project root. Please cd to Oncolife_Monolith first."
        log_info "Current directory: $(pwd)"
        exit 1
    fi
    log_success "Project directory verified"
    
    # Check curl (needed for health checks)
    if ! command -v curl &> /dev/null; then
        log_warning "curl not found - health checks will be skipped"
    fi
    
    # Set region
    export AWS_REGION
    export AWS_DEFAULT_REGION=$AWS_REGION
    log_success "Region: $AWS_REGION"
    
    # Get availability zones
    AZ1=$(aws ec2 describe-availability-zones --region $AWS_REGION --query 'AvailabilityZones[0].ZoneName' --output text 2>/dev/null)
    AZ2=$(aws ec2 describe-availability-zones --region $AWS_REGION --query 'AvailabilityZones[1].ZoneName' --output text 2>/dev/null)
    
    if [ -z "$AZ1" ] || [ -z "$AZ2" ]; then
        log_error "Could not get availability zones. Check your AWS region."
        exit 1
    fi
    log_success "Availability Zones: $AZ1, $AZ2"
}

# =============================================================================
# STEP 1: CREATE ECS SERVICE-LINKED ROLE
# =============================================================================

create_ecs_service_role() {
    log_step "STEP 1: Creating ECS Service-Linked Role"
    
    if aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com 2>/dev/null; then
        log_success "ECS service-linked role created"
    else
        log_success "ECS service-linked role already exists (OK)"
    fi
}

# =============================================================================
# STEP 2: CREATE VPC AND NETWORKING
# =============================================================================

create_vpc_infrastructure() {
    log_step "STEP 2: Creating VPC and Networking"
    
    if [ "$SKIP_VPC" = true ]; then
        log_info "Skipping VPC creation (--skip-vpc flag)"
        
        # Try to auto-detect existing VPC and resources
        log_info "Attempting to auto-detect existing resources..."
        
        VPC_ID=$(aws ec2 describe-vpcs \
            --filters "Name=tag:Name,Values=$PROJECT_NAME-vpc" \
            --query 'Vpcs[0].VpcId' \
            --output text 2>/dev/null || echo "")
        
        if [ -n "$VPC_ID" ] && [ "$VPC_ID" != "None" ]; then
            log_success "Found VPC: $VPC_ID"
            
            # Auto-detect subnets
            PUBLIC_SUBNET_1=$(aws ec2 describe-subnets \
                --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$PROJECT_NAME-public-1" \
                --query 'Subnets[0].SubnetId' --output text 2>/dev/null || echo "")
            PUBLIC_SUBNET_2=$(aws ec2 describe-subnets \
                --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$PROJECT_NAME-public-2" \
                --query 'Subnets[0].SubnetId' --output text 2>/dev/null || echo "")
            PRIVATE_SUBNET_1=$(aws ec2 describe-subnets \
                --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$PROJECT_NAME-private-1" \
                --query 'Subnets[0].SubnetId' --output text 2>/dev/null || echo "")
            PRIVATE_SUBNET_2=$(aws ec2 describe-subnets \
                --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$PROJECT_NAME-private-2" \
                --query 'Subnets[0].SubnetId' --output text 2>/dev/null || echo "")
            
            log_success "Found subnets: $PUBLIC_SUBNET_1, $PUBLIC_SUBNET_2, $PRIVATE_SUBNET_1, $PRIVATE_SUBNET_2"
            
            # Auto-detect security groups
            SG_ALB=$(aws ec2 describe-security-groups \
                --filters "Name=group-name,Values=$PROJECT_NAME-alb-sg" "Name=vpc-id,Values=$VPC_ID" \
                --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")
            SG_ECS=$(aws ec2 describe-security-groups \
                --filters "Name=group-name,Values=$PROJECT_NAME-ecs-sg" "Name=vpc-id,Values=$VPC_ID" \
                --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")
            SG_RDS=$(aws ec2 describe-security-groups \
                --filters "Name=group-name,Values=$PROJECT_NAME-rds-sg" "Name=vpc-id,Values=$VPC_ID" \
                --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")
            
            if [ -n "$SG_ALB" ] && [ "$SG_ALB" != "None" ]; then
                log_success "Found security groups: ALB=$SG_ALB, ECS=$SG_ECS, RDS=$SG_RDS"
                SKIP_SECURITY_GROUPS=true
            else
                log_info "Security groups not found, will create them"
            fi
            
            return
        fi
        
        # Fallback to manual input if auto-detect fails
        log_warning "Could not auto-detect resources. Please enter manually:"
        echo ""
        echo "  Enter your existing AWS resource IDs:"
        read -p "  VPC ID (vpc-xxxxxxxx): " VPC_ID
        read -p "  Public Subnet 1 ID (subnet-xxx): " PUBLIC_SUBNET_1
        read -p "  Public Subnet 2 ID (subnet-xxx): " PUBLIC_SUBNET_2
        read -p "  Private Subnet 1 ID (subnet-xxx): " PRIVATE_SUBNET_1
        read -p "  Private Subnet 2 ID (subnet-xxx): " PRIVATE_SUBNET_2
        read -p "  ALB Security Group ID (sg-xxx): " SG_ALB
        read -p "  ECS Security Group ID (sg-xxx): " SG_ECS
        read -p "  RDS Security Group ID (sg-xxx): " SG_RDS
        SKIP_SECURITY_GROUPS=true
        return
    fi
    
    # Check if VPC already exists
    VPC_ID=$(aws ec2 describe-vpcs \
        --filters "Name=tag:Name,Values=$PROJECT_NAME-vpc" \
        --query 'Vpcs[0].VpcId' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$VPC_ID" ] && [ "$VPC_ID" != "None" ]; then
        log_success "VPC already exists (reusing): $VPC_ID"
        
        # Get existing subnets
        PUBLIC_SUBNET_1=$(aws ec2 describe-subnets \
            --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$PROJECT_NAME-public-1" \
            --query 'Subnets[0].SubnetId' --output text)
        PUBLIC_SUBNET_2=$(aws ec2 describe-subnets \
            --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$PROJECT_NAME-public-2" \
            --query 'Subnets[0].SubnetId' --output text)
        PRIVATE_SUBNET_1=$(aws ec2 describe-subnets \
            --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$PROJECT_NAME-private-1" \
            --query 'Subnets[0].SubnetId' --output text)
        PRIVATE_SUBNET_2=$(aws ec2 describe-subnets \
            --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$PROJECT_NAME-private-2" \
            --query 'Subnets[0].SubnetId' --output text)
        
        log_success "Subnets: $PUBLIC_SUBNET_1, $PUBLIC_SUBNET_2, $PRIVATE_SUBNET_1, $PRIVATE_SUBNET_2"
        return
    fi
    
    # Create VPC
    log_info "Creating VPC..."
    VPC_ID=$(aws ec2 create-vpc \
        --cidr-block $VPC_CIDR \
        --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=$PROJECT_NAME-vpc}]" \
        --query 'Vpc.VpcId' \
        --output text)
    
    if [ -z "$VPC_ID" ]; then
        log_error "Failed to create VPC"
        exit 1
    fi
    log_success "VPC created: $VPC_ID"
    
    # Enable DNS hostnames
    aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames '{"Value":true}'
    aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support '{"Value":true}'
    log_success "DNS hostnames enabled"
    
    # Create Internet Gateway
    log_info "Creating Internet Gateway..."
    IGW_ID=$(aws ec2 create-internet-gateway \
        --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=$PROJECT_NAME-igw}]" \
        --query 'InternetGateway.InternetGatewayId' \
        --output text)
    aws ec2 attach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID
    log_success "Internet Gateway attached: $IGW_ID"
    
    # Create Public Subnets
    log_info "Creating Public Subnets..."
    PUBLIC_SUBNET_1=$(aws ec2 create-subnet \
        --vpc-id $VPC_ID \
        --cidr-block $PUBLIC_SUBNET_1_CIDR \
        --availability-zone $AZ1 \
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-public-1}]" \
        --query 'Subnet.SubnetId' \
        --output text)
    
    PUBLIC_SUBNET_2=$(aws ec2 create-subnet \
        --vpc-id $VPC_ID \
        --cidr-block $PUBLIC_SUBNET_2_CIDR \
        --availability-zone $AZ2 \
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-public-2}]" \
        --query 'Subnet.SubnetId' \
        --output text)
    
    # Enable auto-assign public IP
    aws ec2 modify-subnet-attribute --subnet-id $PUBLIC_SUBNET_1 --map-public-ip-on-launch
    aws ec2 modify-subnet-attribute --subnet-id $PUBLIC_SUBNET_2 --map-public-ip-on-launch
    log_success "Public Subnets: $PUBLIC_SUBNET_1, $PUBLIC_SUBNET_2"
    
    # Create Private Subnets
    log_info "Creating Private Subnets..."
    PRIVATE_SUBNET_1=$(aws ec2 create-subnet \
        --vpc-id $VPC_ID \
        --cidr-block $PRIVATE_SUBNET_1_CIDR \
        --availability-zone $AZ1 \
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-private-1}]" \
        --query 'Subnet.SubnetId' \
        --output text)
    
    PRIVATE_SUBNET_2=$(aws ec2 create-subnet \
        --vpc-id $VPC_ID \
        --cidr-block $PRIVATE_SUBNET_2_CIDR \
        --availability-zone $AZ2 \
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-private-2}]" \
        --query 'Subnet.SubnetId' \
        --output text)
    log_success "Private Subnets: $PRIVATE_SUBNET_1, $PRIVATE_SUBNET_2"
    
    # Create NAT Gateway
    log_info "Creating NAT Gateway (this takes ~2 minutes)..."
    EIP_ID=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)
    
    NAT_ID=$(aws ec2 create-nat-gateway \
        --subnet-id $PUBLIC_SUBNET_1 \
        --allocation-id $EIP_ID \
        --tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=$PROJECT_NAME-nat}]" \
        --query 'NatGateway.NatGatewayId' \
        --output text)
    
    # Wait for NAT Gateway
    wait_for_resource "NAT Gateway" "$NAT_ID" \
        "aws ec2 describe-nat-gateways --nat-gateway-ids $NAT_ID --query 'NatGateways[0].State' --output text | grep -q available" \
        300 15
    
    # Create Route Tables
    log_info "Creating Route Tables..."
    
    # Public route table
    PUBLIC_RT=$(aws ec2 create-route-table \
        --vpc-id $VPC_ID \
        --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=$PROJECT_NAME-public-rt}]" \
        --query 'RouteTable.RouteTableId' \
        --output text)
    
    aws ec2 create-route --route-table-id $PUBLIC_RT --destination-cidr-block "0.0.0.0/0" --gateway-id $IGW_ID > /dev/null
    aws ec2 associate-route-table --route-table-id $PUBLIC_RT --subnet-id $PUBLIC_SUBNET_1 > /dev/null
    aws ec2 associate-route-table --route-table-id $PUBLIC_RT --subnet-id $PUBLIC_SUBNET_2 > /dev/null
    
    # Private route table
    PRIVATE_RT=$(aws ec2 create-route-table \
        --vpc-id $VPC_ID \
        --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=$PROJECT_NAME-private-rt}]" \
        --query 'RouteTable.RouteTableId' \
        --output text)
    
    aws ec2 create-route --route-table-id $PRIVATE_RT --destination-cidr-block "0.0.0.0/0" --nat-gateway-id $NAT_ID > /dev/null
    aws ec2 associate-route-table --route-table-id $PRIVATE_RT --subnet-id $PRIVATE_SUBNET_1 > /dev/null
    aws ec2 associate-route-table --route-table-id $PRIVATE_RT --subnet-id $PRIVATE_SUBNET_2 > /dev/null
    
    log_success "Route Tables configured"
}

# =============================================================================
# STEP 3: CREATE SECURITY GROUPS
# =============================================================================

create_security_groups() {
    log_step "STEP 3: Creating Security Groups"
    
    if [ "$SKIP_SECURITY_GROUPS" = true ]; then
        log_info "Skipping Security Groups (using existing from --skip-vpc)"
        log_success "ALB SG: $SG_ALB"
        log_success "ECS SG: $SG_ECS"
        log_success "RDS SG: $SG_RDS"
        return
    fi
    
    # -------------------------------------------------------------------------
    # ALB Security Group - Check if exists first
    # -------------------------------------------------------------------------
    log_info "Creating ALB Security Group..."
    SG_ALB=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=$PROJECT_NAME-alb-sg" "Name=vpc-id,Values=$VPC_ID" \
        --query 'SecurityGroups[0].GroupId' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$SG_ALB" ] || [ "$SG_ALB" = "None" ]; then
        SG_ALB=$(aws ec2 create-security-group \
            --group-name "$PROJECT_NAME-alb-sg" \
            --description "OncoLife ALB Security Group" \
            --vpc-id $VPC_ID \
            --query 'GroupId' \
            --output text)
        
        aws ec2 authorize-security-group-ingress --group-id $SG_ALB --protocol tcp --port 443 --cidr "0.0.0.0/0" > /dev/null 2>&1 || true
        aws ec2 authorize-security-group-ingress --group-id $SG_ALB --protocol tcp --port 80 --cidr "0.0.0.0/0" > /dev/null 2>&1 || true
        aws ec2 create-tags --resources $SG_ALB --tags "Key=Name,Value=$PROJECT_NAME-alb-sg" > /dev/null
        log_success "ALB SG created: $SG_ALB"
    else
        log_success "ALB SG already exists (reusing): $SG_ALB"
    fi
    
    # -------------------------------------------------------------------------
    # ECS Security Group - Check if exists first
    # -------------------------------------------------------------------------
    log_info "Creating ECS Security Group..."
    SG_ECS=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=$PROJECT_NAME-ecs-sg" "Name=vpc-id,Values=$VPC_ID" \
        --query 'SecurityGroups[0].GroupId' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$SG_ECS" ] || [ "$SG_ECS" = "None" ]; then
        SG_ECS=$(aws ec2 create-security-group \
            --group-name "$PROJECT_NAME-ecs-sg" \
            --description "OncoLife ECS Security Group" \
            --vpc-id $VPC_ID \
            --query 'GroupId' \
            --output text)
        
        aws ec2 authorize-security-group-ingress --group-id $SG_ECS --protocol tcp --port 8000 --source-group $SG_ALB > /dev/null 2>&1 || true
        aws ec2 authorize-security-group-ingress --group-id $SG_ECS --protocol tcp --port 8001 --source-group $SG_ALB > /dev/null 2>&1 || true
        aws ec2 create-tags --resources $SG_ECS --tags "Key=Name,Value=$PROJECT_NAME-ecs-sg" > /dev/null
        log_success "ECS SG created: $SG_ECS"
    else
        log_success "ECS SG already exists (reusing): $SG_ECS"
    fi
    
    # -------------------------------------------------------------------------
    # RDS Security Group - Check if exists first
    # -------------------------------------------------------------------------
    log_info "Creating RDS Security Group..."
    SG_RDS=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=$PROJECT_NAME-rds-sg" "Name=vpc-id,Values=$VPC_ID" \
        --query 'SecurityGroups[0].GroupId' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$SG_RDS" ] || [ "$SG_RDS" = "None" ]; then
        SG_RDS=$(aws ec2 create-security-group \
            --group-name "$PROJECT_NAME-rds-sg" \
            --description "OncoLife RDS Security Group" \
            --vpc-id $VPC_ID \
            --query 'GroupId' \
            --output text)
        
        aws ec2 authorize-security-group-ingress --group-id $SG_RDS --protocol tcp --port 5432 --source-group $SG_ECS > /dev/null 2>&1 || true
        aws ec2 create-tags --resources $SG_RDS --tags "Key=Name,Value=$PROJECT_NAME-rds-sg" > /dev/null
        log_success "RDS SG created: $SG_RDS"
    else
        log_success "RDS SG already exists (reusing): $SG_RDS"
    fi
}

# =============================================================================
# STEP 4: CREATE RDS DATABASE
# =============================================================================

create_rds_database() {
    log_step "STEP 4: Creating RDS PostgreSQL Database"
    
    if [ "$SKIP_RDS" = true ]; then
        log_info "Skipping RDS creation (--skip-rds flag)"
        
        # Try to auto-detect existing RDS
        RDS_ENDPOINT=$(aws rds describe-db-instances \
            --db-instance-identifier "$PROJECT_NAME-db" \
            --query 'DBInstances[0].Endpoint.Address' \
            --output text 2>/dev/null || echo "")
        
        if [ -n "$RDS_ENDPOINT" ] && [ "$RDS_ENDPOINT" != "None" ]; then
            log_success "Found existing RDS: $RDS_ENDPOINT"
            DB_USERNAME="oncolife_admin"
            log_warning "Using existing RDS. Please enter the DB password you set during initial creation."
            get_password
        else
            read -p "  Enter existing RDS endpoint (xxx.rds.amazonaws.com): " RDS_ENDPOINT
            read -p "  Enter DB username (default: oncolife_admin): " DB_USERNAME
            DB_USERNAME="${DB_USERNAME:-oncolife_admin}"
            get_password
        fi
        return
    fi
    
    # Check if RDS already exists
    RDS_STATUS=$(aws rds describe-db-instances \
        --db-instance-identifier "$PROJECT_NAME-db" \
        --query 'DBInstances[0].DBInstanceStatus' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$RDS_STATUS" ] && [ "$RDS_STATUS" != "None" ]; then
        log_success "RDS instance already exists (status: $RDS_STATUS)"
        
        if [ "$RDS_STATUS" = "available" ]; then
            RDS_ENDPOINT=$(aws rds describe-db-instances \
                --db-instance-identifier "$PROJECT_NAME-db" \
                --query 'DBInstances[0].Endpoint.Address' \
                --output text)
            log_success "RDS Endpoint: $RDS_ENDPOINT"
            DB_USERNAME="oncolife_admin"
            log_warning "Using existing RDS. Please enter the DB password you set during initial creation."
            get_password
            return
        else
            log_info "Waiting for RDS to become available..."
            wait_for_resource "RDS Instance" "$PROJECT_NAME-db" \
                "aws rds describe-db-instances --db-instance-identifier $PROJECT_NAME-db --query 'DBInstances[0].DBInstanceStatus' --output text | grep -q available" \
                1200 30
            RDS_ENDPOINT=$(aws rds describe-db-instances \
                --db-instance-identifier "$PROJECT_NAME-db" \
                --query 'DBInstances[0].Endpoint.Address' \
                --output text)
            DB_USERNAME="oncolife_admin"
            log_warning "Using existing RDS. Please enter the DB password you set during initial creation."
            get_password
            return
        fi
    fi
    
    # Get database password for new instance
    get_password
    DB_USERNAME="oncolife_admin"
    
    # Create DB Subnet Group - check if exists first
    log_info "Creating DB Subnet Group..."
    if aws rds describe-db-subnet-groups --db-subnet-group-name "$PROJECT_NAME-db-subnet" 2>/dev/null > /dev/null; then
        log_success "DB Subnet Group already exists (reusing)"
    else
        aws rds create-db-subnet-group \
            --db-subnet-group-name "$PROJECT_NAME-db-subnet" \
            --db-subnet-group-description "OncoLife Database Subnets" \
            --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 > /dev/null
        log_success "DB Subnet Group created"
    fi
    
    # Create RDS Instance
    log_info "Creating RDS instance (this takes 10-15 minutes)..."
    aws rds create-db-instance \
        --db-instance-identifier "$PROJECT_NAME-db" \
        --db-instance-class $RDS_INSTANCE_CLASS \
        --engine postgres \
        --engine-version $RDS_ENGINE_VERSION \
        --master-username $DB_USERNAME \
        --master-user-password "$DB_PASSWORD" \
        --allocated-storage $RDS_ALLOCATED_STORAGE \
        --storage-type gp3 \
        --storage-encrypted \
        --vpc-security-group-ids $SG_RDS \
        --db-subnet-group-name "$PROJECT_NAME-db-subnet" \
        --no-publicly-accessible \
        --backup-retention-period 7 \
        --tags "Key=Name,Value=$PROJECT_NAME-db" > /dev/null
    
    # Wait for RDS
    wait_for_resource "RDS Instance" "$PROJECT_NAME-db" \
        "aws rds describe-db-instances --db-instance-identifier $PROJECT_NAME-db --query 'DBInstances[0].DBInstanceStatus' --output text | grep -q available" \
        1200 30
    
    # Get endpoint
    RDS_ENDPOINT=$(aws rds describe-db-instances \
        --db-instance-identifier "$PROJECT_NAME-db" \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text)
    
    log_success "RDS Endpoint: $RDS_ENDPOINT"
}

# =============================================================================
# STEP 5: CREATE COGNITO USER POOL
# =============================================================================

create_cognito_user_pool() {
    log_step "STEP 5: Creating Cognito User Pool"
    
    if [ "$SKIP_COGNITO" = true ]; then
        log_info "Skipping Cognito creation (--skip-cognito flag)"
        
        # Try to auto-detect existing Cognito
        COGNITO_POOL_ID=$(aws cognito-idp list-user-pools --max-results 50 \
            --query "UserPools[?Name=='$PROJECT_NAME-patients'].Id | [0]" \
            --output text 2>/dev/null || echo "")
        
        if [ -n "$COGNITO_POOL_ID" ] && [ "$COGNITO_POOL_ID" != "None" ]; then
            log_success "Found existing User Pool: $COGNITO_POOL_ID"
            
            # Try to get existing client
            COGNITO_CLIENT_ID=$(aws cognito-idp list-user-pool-clients \
                --user-pool-id $COGNITO_POOL_ID \
                --query "UserPoolClients[?ClientName=='$PROJECT_NAME-api-client'].ClientId | [0]" \
                --output text 2>/dev/null || echo "")
            
            if [ -n "$COGNITO_CLIENT_ID" ] && [ "$COGNITO_CLIENT_ID" != "None" ]; then
                COGNITO_CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
                    --user-pool-id $COGNITO_POOL_ID \
                    --client-id $COGNITO_CLIENT_ID \
                    --query 'UserPoolClient.ClientSecret' \
                    --output text)
                log_success "Found existing Client: $COGNITO_CLIENT_ID"
                return
            fi
        fi
        
        # Fallback to manual input
        read -p "  Enter existing User Pool ID (us-east-1_xxxxxxxx): " COGNITO_POOL_ID
        read -p "  Enter existing Client ID: " COGNITO_CLIENT_ID
        read -sp "  Enter existing Client Secret: " COGNITO_CLIENT_SECRET
        echo ""
        log_success "User Pool ID: $COGNITO_POOL_ID"
        log_success "Client ID: $COGNITO_CLIENT_ID"
        return
    fi
    
    # Check if User Pool already exists
    COGNITO_POOL_ID=$(aws cognito-idp list-user-pools --max-results 50 \
        --query "UserPools[?Name=='$PROJECT_NAME-patients'].Id | [0]" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$COGNITO_POOL_ID" ] && [ "$COGNITO_POOL_ID" != "None" ]; then
        log_success "User Pool already exists (reusing): $COGNITO_POOL_ID"
        
        # Check if client exists
        COGNITO_CLIENT_ID=$(aws cognito-idp list-user-pool-clients \
            --user-pool-id $COGNITO_POOL_ID \
            --query "UserPoolClients[?ClientName=='$PROJECT_NAME-api-client'].ClientId | [0]" \
            --output text 2>/dev/null || echo "")
        
        if [ -n "$COGNITO_CLIENT_ID" ] && [ "$COGNITO_CLIENT_ID" != "None" ]; then
            COGNITO_CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
                --user-pool-id $COGNITO_POOL_ID \
                --client-id $COGNITO_CLIENT_ID \
                --query 'UserPoolClient.ClientSecret' \
                --output text)
            log_success "App Client already exists (reusing): $COGNITO_CLIENT_ID"
            return
        fi
    else
        log_info "Creating User Pool..."
        COGNITO_POOL_ID=$(aws cognito-idp create-user-pool \
            --pool-name "$PROJECT_NAME-patients" \
            --auto-verified-attributes email \
            --username-attributes email \
            --mfa-configuration OFF \
            --policies '{"PasswordPolicy":{"MinimumLength":8,"RequireUppercase":true,"RequireLowercase":true,"RequireNumbers":true,"RequireSymbols":true}}' \
            --admin-create-user-config '{"AllowAdminCreateUserOnly":true}' \
            --query 'UserPool.Id' \
            --output text)
        log_success "User Pool created: $COGNITO_POOL_ID"
    fi
    
    # Create App Client if it doesn't exist
    log_info "Creating App Client..."
    COGNITO_CLIENT_ID=$(aws cognito-idp create-user-pool-client \
        --user-pool-id $COGNITO_POOL_ID \
        --client-name "$PROJECT_NAME-api-client" \
        --generate-secret \
        --explicit-auth-flows "ALLOW_ADMIN_USER_PASSWORD_AUTH" "ALLOW_REFRESH_TOKEN_AUTH" "ALLOW_USER_PASSWORD_AUTH" \
        --query 'UserPoolClient.ClientId' \
        --output text)
    
    # Get client secret (need separate call)
    COGNITO_CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
        --user-pool-id $COGNITO_POOL_ID \
        --client-id $COGNITO_CLIENT_ID \
        --query 'UserPoolClient.ClientSecret' \
        --output text)
    log_success "App Client created: $COGNITO_CLIENT_ID"
}

# =============================================================================
# STEP 6: CREATE S3 BUCKETS
# =============================================================================

create_s3_buckets() {
    log_step "STEP 6: Creating S3 Buckets"
    
    for bucket in "$PROJECT_NAME-referrals-$ACCOUNT_ID" "$PROJECT_NAME-education-$ACCOUNT_ID"; do
        log_info "Creating bucket: $bucket"
        
        if [ "$AWS_REGION" = "us-east-1" ]; then
            aws s3api create-bucket --bucket $bucket --region $AWS_REGION 2>/dev/null || true
        else
            aws s3api create-bucket --bucket $bucket --region $AWS_REGION \
                --create-bucket-configuration LocationConstraint=$AWS_REGION 2>/dev/null || true
        fi
        
        # Enable encryption
        aws s3api put-bucket-encryption --bucket $bucket \
            --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"}}]}' 2>/dev/null || true
        
        # Block public access
        aws s3api put-public-access-block --bucket $bucket \
            --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" 2>/dev/null || true
        
        log_success "Bucket configured: $bucket"
    done
    
    # Create folder structure for education bucket
    EDUCATION_BUCKET="$PROJECT_NAME-education-$ACCOUNT_ID"
    log_info "Creating education bucket folder structure..."
    aws s3api put-object --bucket "$EDUCATION_BUCKET" --key "symptoms/" > /dev/null 2>&1 || true
    aws s3api put-object --bucket "$EDUCATION_BUCKET" --key "handbooks/" > /dev/null 2>&1 || true
    aws s3api put-object --bucket "$EDUCATION_BUCKET" --key "regimens/" > /dev/null 2>&1 || true
    log_success "Education bucket folder structure created"
}

# =============================================================================
# STEP 6b: UPLOAD EDUCATION PDFs TO S3
# =============================================================================

upload_education_pdfs() {
    log_step "STEP 6b: Uploading Education PDFs to S3"
    
    EDUCATION_BUCKET="$PROJECT_NAME-education-$ACCOUNT_ID"
    LOCAL_EDUCATION_PATH="apps/patient-platform/patient-api/static/education"
    
    if [ ! -d "$LOCAL_EDUCATION_PATH" ]; then
        log_warning "Education PDF folder not found: $LOCAL_EDUCATION_PATH"
        log_info "Skipping education PDF upload - you can run upload-education-pdfs.sh later"
        return
    fi
    
    # Count PDFs
    PDF_COUNT=$(find "$LOCAL_EDUCATION_PATH" -name "*.pdf" 2>/dev/null | wc -l)
    if [ "$PDF_COUNT" -eq 0 ]; then
        log_warning "No PDF files found in $LOCAL_EDUCATION_PATH"
        return
    fi
    
    log_info "Found $PDF_COUNT PDF files to upload..."
    
    # Upload symptoms
    if [ -d "$LOCAL_EDUCATION_PATH/symptoms" ]; then
        log_info "Uploading symptom education PDFs..."
        aws s3 sync "$LOCAL_EDUCATION_PATH/symptoms/" "s3://$EDUCATION_BUCKET/symptoms/" \
            --content-type "application/pdf" > /dev/null 2>&1
        log_success "Symptom PDFs uploaded"
    fi
    
    # Upload handbooks
    if [ -d "$LOCAL_EDUCATION_PATH/handbooks" ]; then
        log_info "Uploading handbook PDFs..."
        aws s3 sync "$LOCAL_EDUCATION_PATH/handbooks/" "s3://$EDUCATION_BUCKET/handbooks/" \
            --content-type "application/pdf" > /dev/null 2>&1
        log_success "Handbook PDFs uploaded"
    fi
    
    # Upload regimens
    if [ -d "$LOCAL_EDUCATION_PATH/regimens" ]; then
        log_info "Uploading regimen education PDFs..."
        aws s3 sync "$LOCAL_EDUCATION_PATH/regimens/" "s3://$EDUCATION_BUCKET/regimens/" \
            --content-type "application/pdf" > /dev/null 2>&1
        log_success "Regimen PDFs uploaded"
    fi
    
    log_success "Education PDFs uploaded to s3://$EDUCATION_BUCKET/"
}

# =============================================================================
# STEP 7: CREATE SECRETS IN SECRETS MANAGER
# =============================================================================

create_secrets() {
    log_step "STEP 7: Creating Secrets Manager Secrets"
    
    # Database secret - using printf for better JSON handling
    log_info "Creating database secret..."
    DB_SECRET=$(printf '{"host":"%s","port":"5432","username":"%s","password":"%s","patient_db":"oncolife_patient","doctor_db":"oncolife_doctor"}' \
        "$RDS_ENDPOINT" "$DB_USERNAME" "$DB_PASSWORD")
    
    if aws secretsmanager create-secret --name "$PROJECT_NAME/db" --secret-string "$DB_SECRET" 2>/dev/null; then
        log_success "Database secret created"
    else
        aws secretsmanager put-secret-value --secret-id "$PROJECT_NAME/db" --secret-string "$DB_SECRET" > /dev/null
        log_success "Database secret updated"
    fi
    
    # Cognito secret
    log_info "Creating Cognito secret..."
    COGNITO_SECRET=$(printf '{"user_pool_id":"%s","client_id":"%s","client_secret":"%s"}' \
        "$COGNITO_POOL_ID" "$COGNITO_CLIENT_ID" "$COGNITO_CLIENT_SECRET")
    
    if aws secretsmanager create-secret --name "$PROJECT_NAME/cognito" --secret-string "$COGNITO_SECRET" 2>/dev/null; then
        log_success "Cognito secret created"
    else
        aws secretsmanager put-secret-value --secret-id "$PROJECT_NAME/cognito" --secret-string "$COGNITO_SECRET" > /dev/null
        log_success "Cognito secret updated"
    fi
    
    # Get secret ARNs
    DB_SECRET_ARN=$(aws secretsmanager describe-secret --secret-id "$PROJECT_NAME/db" --query 'ARN' --output text)
    COGNITO_SECRET_ARN=$(aws secretsmanager describe-secret --secret-id "$PROJECT_NAME/cognito" --query 'ARN' --output text)
    
    log_success "DB Secret ARN: $DB_SECRET_ARN"
    log_success "Cognito Secret ARN: $COGNITO_SECRET_ARN"
}

# =============================================================================
# STEP 8: CREATE ECR REPOSITORIES
# =============================================================================

create_ecr_repositories() {
    log_step "STEP 8: Creating ECR Repositories"
    
    for repo in "$PROJECT_NAME-patient-api" "$PROJECT_NAME-doctor-api"; do
        if aws ecr describe-repositories --repository-names $repo 2>/dev/null > /dev/null; then
            log_success "$repo already exists"
        else
            aws ecr create-repository --repository-name $repo --image-scanning-configuration scanOnPush=true > /dev/null
            log_success "Created $repo"
        fi
    done
}

# =============================================================================
# STEP 9: CREATE CLOUDWATCH LOG GROUPS
# =============================================================================

create_cloudwatch_log_groups() {
    log_step "STEP 9: Creating CloudWatch Log Groups"
    
    # Note: Using explicit string to avoid Git Bash path conversion
    local log_group_patient="/ecs/${PROJECT_NAME}-patient-api"
    local log_group_doctor="/ecs/${PROJECT_NAME}-doctor-api"
    
    for lg in "$log_group_patient" "$log_group_doctor"; do
        if aws logs create-log-group --log-group-name "$lg" 2>/dev/null; then
            aws logs put-retention-policy --log-group-name "$lg" --retention-in-days 30
            log_success "Created: $lg"
        else
            log_success "$lg already exists"
        fi
    done
}

# =============================================================================
# STEP 10: BUILD AND PUSH DOCKER IMAGES
# =============================================================================

build_docker_images() {
    log_step "STEP 10: Building and Pushing Docker Images"
    
    if [ "$SKIP_BUILD" = true ]; then
        log_info "Skipping Docker build (--skip-build flag)"
        return
    fi
    
    # Login to ECR
    log_info "Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
    log_success "Logged in to ECR"
    
    # Build Patient API
    log_info "Building patient-api (this may take a few minutes)..."
    docker build -t "$PROJECT_NAME-patient-api:latest" -f "apps/patient-platform/patient-api/Dockerfile" "apps/patient-platform/patient-api/"
    docker tag "$PROJECT_NAME-patient-api:latest" "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-patient-api:latest"
    docker push "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-patient-api:latest"
    log_success "patient-api pushed to ECR"
    
    # Build Doctor API
    log_info "Building doctor-api (this may take a few minutes)..."
    docker build -t "$PROJECT_NAME-doctor-api:latest" -f "apps/doctor-platform/doctor-api/Dockerfile" "apps/doctor-platform/doctor-api/"
    docker tag "$PROJECT_NAME-doctor-api:latest" "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-doctor-api:latest"
    docker push "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-doctor-api:latest"
    log_success "doctor-api pushed to ECR"
}

# =============================================================================
# STEP 11: CREATE IAM ROLES
# =============================================================================

create_iam_roles() {
    log_step "STEP 11: Creating IAM Roles"
    
    # Trust policy as a single line JSON
    TRUST_POLICY='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
    
    # Create execution role
    log_info "Creating Task Execution Role..."
    if aws iam create-role --role-name "ecsTaskExecutionRole" --assume-role-policy-document "$TRUST_POLICY" 2>/dev/null; then
        log_success "Created ecsTaskExecutionRole"
    else
        log_info "ecsTaskExecutionRole already exists (OK)"
    fi
    
    aws iam attach-role-policy --role-name "ecsTaskExecutionRole" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy" 2>/dev/null || true
    aws iam attach-role-policy --role-name "ecsTaskExecutionRole" \
        --policy-arn "arn:aws:iam::aws:policy/SecretsManagerReadWrite" 2>/dev/null || true
    log_success "Task Execution Role configured"
    
    # Create task role
    log_info "Creating Task Role..."
    if aws iam create-role --role-name "${PROJECT_NAME}TaskRole" --assume-role-policy-document "$TRUST_POLICY" 2>/dev/null; then
        log_success "Created ${PROJECT_NAME}TaskRole"
    else
        log_info "${PROJECT_NAME}TaskRole already exists (OK)"
    fi
    
    # Task policy as single line
    TASK_POLICY=$(printf '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:ListBucket"],"Resource":["arn:aws:s3:::%s-*","arn:aws:s3:::%s-*/*"]},{"Effect":"Allow","Action":["cognito-idp:AdminCreateUser","cognito-idp:AdminDeleteUser","cognito-idp:AdminInitiateAuth","cognito-idp:AdminRespondToAuthChallenge","cognito-idp:AdminGetUser"],"Resource":"*"}]}' "$PROJECT_NAME" "$PROJECT_NAME")
    
    aws iam put-role-policy --role-name "${PROJECT_NAME}TaskRole" \
        --policy-name "OncolifePermissions" --policy-document "$TASK_POLICY" 2>/dev/null || true
    log_success "Task Role configured"
}

# =============================================================================
# STEP 12: CREATE ECS CLUSTER
# =============================================================================

create_ecs_cluster() {
    log_step "STEP 12: Creating ECS Cluster"
    
    CLUSTER_NAME="$PROJECT_NAME-$ENVIRONMENT"
    
    # Check cluster status
    CLUSTER_STATUS=$(aws ecs describe-clusters \
        --clusters $CLUSTER_NAME \
        --query 'clusters[0].status' \
        --output text 2>/dev/null || echo "")
    
    if [ "$CLUSTER_STATUS" = "ACTIVE" ]; then
        log_success "Cluster already exists and is ACTIVE (reusing)"
        return
    fi
    
    # If cluster exists but is INACTIVE, delete it first
    if [ "$CLUSTER_STATUS" = "INACTIVE" ]; then
        log_warning "Cluster exists but is INACTIVE, deleting and recreating..."
        aws ecs delete-cluster --cluster $CLUSTER_NAME > /dev/null 2>&1 || true
        sleep 3
    fi
    
    aws ecs create-cluster \
        --cluster-name $CLUSTER_NAME \
        --capacity-providers "FARGATE" "FARGATE_SPOT" \
        --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 > /dev/null
    
    log_success "ECS Cluster created: $CLUSTER_NAME"
}

# =============================================================================
# STEP 13: CREATE ALB AND TARGET GROUPS
# =============================================================================

create_alb_infrastructure() {
    log_step "STEP 13: Creating ALB and Target Groups"
    
    # -------------------------------------------------------------------------
    # Patient API ALB - Check if exists first
    # -------------------------------------------------------------------------
    log_info "Creating Patient API ALB..."
    PATIENT_ALB_ARN=$(aws elbv2 describe-load-balancers \
        --names "$PROJECT_NAME-patient-alb" \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$PATIENT_ALB_ARN" ] || [ "$PATIENT_ALB_ARN" = "None" ]; then
        PATIENT_ALB_ARN=$(aws elbv2 create-load-balancer \
            --name "$PROJECT_NAME-patient-alb" \
            --subnets $PUBLIC_SUBNET_1 $PUBLIC_SUBNET_2 \
            --security-groups $SG_ALB \
            --scheme internet-facing \
            --type application \
            --query 'LoadBalancers[0].LoadBalancerArn' \
            --output text)
        log_success "Patient ALB created"
    else
        log_success "Patient ALB already exists (reusing)"
    fi
    
    PATIENT_ALB_DNS=$(aws elbv2 describe-load-balancers \
        --load-balancer-arns $PATIENT_ALB_ARN \
        --query 'LoadBalancers[0].DNSName' \
        --output text)
    log_success "Patient ALB: $PATIENT_ALB_DNS"
    
    # -------------------------------------------------------------------------
    # Patient Target Group - Check if exists first
    # -------------------------------------------------------------------------
    PATIENT_TG_ARN=$(aws elbv2 describe-target-groups \
        --names "patient-api-tg" \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$PATIENT_TG_ARN" ] || [ "$PATIENT_TG_ARN" = "None" ]; then
        PATIENT_TG_ARN=$(aws elbv2 create-target-group \
            --name "patient-api-tg" \
            --protocol HTTP \
            --port 8000 \
            --vpc-id $VPC_ID \
            --target-type ip \
            --health-check-path "/health" \
            --health-check-interval-seconds 30 \
            --healthy-threshold-count 2 \
            --unhealthy-threshold-count 3 \
            --query 'TargetGroups[0].TargetGroupArn' \
            --output text)
        log_success "Patient Target Group created"
    else
        log_success "Patient Target Group already exists (reusing)"
    fi
    
    # -------------------------------------------------------------------------
    # Patient HTTP Listener - Check if exists first
    # -------------------------------------------------------------------------
    PATIENT_LISTENER_ARN=$(aws elbv2 describe-listeners \
        --load-balancer-arn $PATIENT_ALB_ARN \
        --query 'Listeners[?Port==`80`].ListenerArn' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$PATIENT_LISTENER_ARN" ] || [ "$PATIENT_LISTENER_ARN" = "None" ]; then
        aws elbv2 create-listener \
            --load-balancer-arn $PATIENT_ALB_ARN \
            --protocol HTTP \
            --port 80 \
            --default-actions "Type=forward,TargetGroupArn=$PATIENT_TG_ARN" > /dev/null
        log_success "Patient HTTP Listener created"
    else
        log_success "Patient HTTP Listener already exists (reusing)"
    fi
    
    # -------------------------------------------------------------------------
    # Doctor API ALB - Check if exists first
    # -------------------------------------------------------------------------
    log_info "Creating Doctor API ALB..."
    DOCTOR_ALB_ARN=$(aws elbv2 describe-load-balancers \
        --names "$PROJECT_NAME-doctor-alb" \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$DOCTOR_ALB_ARN" ] || [ "$DOCTOR_ALB_ARN" = "None" ]; then
        DOCTOR_ALB_ARN=$(aws elbv2 create-load-balancer \
            --name "$PROJECT_NAME-doctor-alb" \
            --subnets $PUBLIC_SUBNET_1 $PUBLIC_SUBNET_2 \
            --security-groups $SG_ALB \
            --scheme internet-facing \
            --type application \
            --query 'LoadBalancers[0].LoadBalancerArn' \
            --output text)
        log_success "Doctor ALB created"
    else
        log_success "Doctor ALB already exists (reusing)"
    fi
    
    DOCTOR_ALB_DNS=$(aws elbv2 describe-load-balancers \
        --load-balancer-arns $DOCTOR_ALB_ARN \
        --query 'LoadBalancers[0].DNSName' \
        --output text)
    log_success "Doctor ALB: $DOCTOR_ALB_DNS"
    
    # -------------------------------------------------------------------------
    # Doctor Target Group - Check if exists first
    # -------------------------------------------------------------------------
    DOCTOR_TG_ARN=$(aws elbv2 describe-target-groups \
        --names "doctor-api-tg" \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$DOCTOR_TG_ARN" ] || [ "$DOCTOR_TG_ARN" = "None" ]; then
        DOCTOR_TG_ARN=$(aws elbv2 create-target-group \
            --name "doctor-api-tg" \
            --protocol HTTP \
            --port 8001 \
            --vpc-id $VPC_ID \
            --target-type ip \
            --health-check-path "/health" \
            --health-check-interval-seconds 30 \
            --healthy-threshold-count 2 \
            --unhealthy-threshold-count 3 \
            --query 'TargetGroups[0].TargetGroupArn' \
            --output text)
        log_success "Doctor Target Group created"
    else
        log_success "Doctor Target Group already exists (reusing)"
    fi
    
    # -------------------------------------------------------------------------
    # Doctor HTTP Listener - Check if exists first
    # -------------------------------------------------------------------------
    DOCTOR_LISTENER_ARN=$(aws elbv2 describe-listeners \
        --load-balancer-arn $DOCTOR_ALB_ARN \
        --query 'Listeners[?Port==`80`].ListenerArn' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$DOCTOR_LISTENER_ARN" ] || [ "$DOCTOR_LISTENER_ARN" = "None" ]; then
        aws elbv2 create-listener \
            --load-balancer-arn $DOCTOR_ALB_ARN \
            --protocol HTTP \
            --port 80 \
            --default-actions "Type=forward,TargetGroupArn=$DOCTOR_TG_ARN" > /dev/null
        log_success "Doctor HTTP Listener created"
    else
        log_success "Doctor HTTP Listener already exists (reusing)"
    fi
}

# =============================================================================
# STEP 14: REGISTER TASK DEFINITIONS
# =============================================================================

register_task_definitions() {
    log_step "STEP 14: Registering Task Definitions"
    
    # Patient API Task Definition
    log_info "Registering Patient API Task Definition..."
    
    # Create JSON file in current directory (works on Windows Git Bash)
    cat > ./patient-task-def.json <<EOFPATIENT
{
    "family": "$PROJECT_NAME-patient-api",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "$PATIENT_API_CPU",
    "memory": "$PATIENT_API_MEMORY",
    "executionRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/ecsTaskExecutionRole",
    "taskRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/${PROJECT_NAME}TaskRole",
    "containerDefinitions": [
        {
            "name": "patient-api",
            "image": "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-patient-api:latest",
            "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
            "essential": true,
            "environment": [
                {"name": "ENVIRONMENT", "value": "$ENVIRONMENT"},
                {"name": "DEBUG", "value": "false"},
                {"name": "LOG_LEVEL", "value": "INFO"},
                {"name": "AWS_REGION", "value": "$AWS_REGION"},
                {"name": "S3_EDUCATION_BUCKET", "value": "$PROJECT_NAME-education-$ACCOUNT_ID"},
                {"name": "S3_REFERRAL_BUCKET", "value": "$PROJECT_NAME-referrals-$ACCOUNT_ID"},
                {"name": "LOCAL_DEV_MODE", "value": "false"}
            ],
            "secrets": [
                {"name": "PATIENT_DB_HOST", "valueFrom": "$DB_SECRET_ARN:host::"},
                {"name": "PATIENT_DB_PASSWORD", "valueFrom": "$DB_SECRET_ARN:password::"},
                {"name": "PATIENT_DB_USER", "valueFrom": "$DB_SECRET_ARN:username::"},
                {"name": "PATIENT_DB_NAME", "valueFrom": "$DB_SECRET_ARN:patient_db::"},
                {"name": "COGNITO_USER_POOL_ID", "valueFrom": "$COGNITO_SECRET_ARN:user_pool_id::"},
                {"name": "COGNITO_CLIENT_ID", "valueFrom": "$COGNITO_SECRET_ARN:client_id::"}
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/$PROJECT_NAME-patient-api",
                    "awslogs-region": "$AWS_REGION",
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
EOFPATIENT
    
    # Register using file:// with explicit path
    aws ecs register-task-definition --cli-input-json file://patient-task-def.json > /dev/null
    rm -f ./patient-task-def.json
    log_success "Patient API Task Definition registered"
    
    # Doctor API Task Definition
    log_info "Registering Doctor API Task Definition..."
    
    cat > ./doctor-task-def.json <<EOFDOCTOR
{
    "family": "$PROJECT_NAME-doctor-api",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "$DOCTOR_API_CPU",
    "memory": "$DOCTOR_API_MEMORY",
    "executionRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/ecsTaskExecutionRole",
    "taskRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/${PROJECT_NAME}TaskRole",
    "containerDefinitions": [
        {
            "name": "doctor-api",
            "image": "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-doctor-api:latest",
            "portMappings": [{"containerPort": 8001, "protocol": "tcp"}],
            "essential": true,
            "environment": [
                {"name": "ENVIRONMENT", "value": "$ENVIRONMENT"},
                {"name": "DEBUG", "value": "false"},
                {"name": "LOG_LEVEL", "value": "INFO"},
                {"name": "AWS_REGION", "value": "$AWS_REGION"},
                {"name": "S3_EDUCATION_BUCKET", "value": "$PROJECT_NAME-education-$ACCOUNT_ID"},
                {"name": "S3_REFERRAL_BUCKET", "value": "$PROJECT_NAME-referrals-$ACCOUNT_ID"},
                {"name": "LOCAL_DEV_MODE", "value": "false"}
            ],
            "secrets": [
                {"name": "DOCTOR_DB_HOST", "valueFrom": "$DB_SECRET_ARN:host::"},
                {"name": "DOCTOR_DB_PASSWORD", "valueFrom": "$DB_SECRET_ARN:password::"},
                {"name": "DOCTOR_DB_USER", "valueFrom": "$DB_SECRET_ARN:username::"},
                {"name": "DOCTOR_DB_NAME", "valueFrom": "$DB_SECRET_ARN:doctor_db::"},
                {"name": "COGNITO_USER_POOL_ID", "valueFrom": "$COGNITO_SECRET_ARN:user_pool_id::"},
                {"name": "COGNITO_CLIENT_ID", "valueFrom": "$COGNITO_SECRET_ARN:client_id::"}
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/$PROJECT_NAME-doctor-api",
                    "awslogs-region": "$AWS_REGION",
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
EOFDOCTOR
    
    aws ecs register-task-definition --cli-input-json file://doctor-task-def.json > /dev/null
    rm -f ./doctor-task-def.json
    log_success "Doctor API Task Definition registered"
}

# =============================================================================
# STEP 15: CREATE ECS SERVICES
# =============================================================================

create_ecs_services() {
    log_step "STEP 15: Creating ECS Services"
    
    CLUSTER_NAME="$PROJECT_NAME-$ENVIRONMENT"
    NETWORK_CONFIG="awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_1,$PRIVATE_SUBNET_2],securityGroups=[$SG_ECS],assignPublicIp=DISABLED}"
    
    # -------------------------------------------------------------------------
    # Patient API Service - Check if exists first
    # -------------------------------------------------------------------------
    log_info "Creating Patient API Service..."
    PATIENT_SERVICE_STATUS=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services "patient-api-service" \
        --query 'services[0].status' \
        --output text 2>/dev/null || echo "")
    
    if [ "$PATIENT_SERVICE_STATUS" = "ACTIVE" ]; then
        log_info "Patient API Service exists, updating..."
        aws ecs update-service \
            --cluster $CLUSTER_NAME \
            --service "patient-api-service" \
            --task-definition "$PROJECT_NAME-patient-api" \
            --desired-count $DESIRED_COUNT \
            --force-new-deployment > /dev/null
        log_success "Patient API Service updated"
    else
        # Delete inactive service if exists
        if [ -n "$PATIENT_SERVICE_STATUS" ] && [ "$PATIENT_SERVICE_STATUS" != "None" ]; then
            log_info "Removing inactive Patient API Service..."
            aws ecs delete-service --cluster $CLUSTER_NAME --service "patient-api-service" --force 2>/dev/null || true
            sleep 5
        fi
        
        aws ecs create-service \
            --cluster $CLUSTER_NAME \
            --service-name "patient-api-service" \
            --task-definition "$PROJECT_NAME-patient-api" \
            --desired-count $DESIRED_COUNT \
            --launch-type FARGATE \
            --network-configuration "$NETWORK_CONFIG" \
            --load-balancers "targetGroupArn=$PATIENT_TG_ARN,containerName=patient-api,containerPort=8000" \
            --health-check-grace-period-seconds 120 > /dev/null
        log_success "Patient API Service created"
    fi
    
    # -------------------------------------------------------------------------
    # Doctor API Service - Check if exists first
    # -------------------------------------------------------------------------
    log_info "Creating Doctor API Service..."
    DOCTOR_SERVICE_STATUS=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services "doctor-api-service" \
        --query 'services[0].status' \
        --output text 2>/dev/null || echo "")
    
    if [ "$DOCTOR_SERVICE_STATUS" = "ACTIVE" ]; then
        log_info "Doctor API Service exists, updating..."
        aws ecs update-service \
            --cluster $CLUSTER_NAME \
            --service "doctor-api-service" \
            --task-definition "$PROJECT_NAME-doctor-api" \
            --desired-count $DESIRED_COUNT \
            --force-new-deployment > /dev/null
        log_success "Doctor API Service updated"
    else
        # Delete inactive service if exists
        if [ -n "$DOCTOR_SERVICE_STATUS" ] && [ "$DOCTOR_SERVICE_STATUS" != "None" ]; then
            log_info "Removing inactive Doctor API Service..."
            aws ecs delete-service --cluster $CLUSTER_NAME --service "doctor-api-service" --force 2>/dev/null || true
            sleep 5
        fi
        
        aws ecs create-service \
            --cluster $CLUSTER_NAME \
            --service-name "doctor-api-service" \
            --task-definition "$PROJECT_NAME-doctor-api" \
            --desired-count $DESIRED_COUNT \
            --launch-type FARGATE \
            --network-configuration "$NETWORK_CONFIG" \
            --load-balancers "targetGroupArn=$DOCTOR_TG_ARN,containerName=doctor-api,containerPort=8001" \
            --health-check-grace-period-seconds 120 > /dev/null
        log_success "Doctor API Service created"
    fi
}

# =============================================================================
# STEP 16: VERIFY DEPLOYMENT
# =============================================================================

verify_deployment() {
    log_step "STEP 16: Verifying Deployment"
    
    CLUSTER_NAME="$PROJECT_NAME-$ENVIRONMENT"
    
    log_info "Waiting for services to stabilize (this may take 2-5 minutes)..."
    
    local attempts=0
    local max_attempts=20
    
    while [ $attempts -lt $max_attempts ]; do
        PATIENT_RUNNING=$(aws ecs describe-services \
            --cluster $CLUSTER_NAME \
            --services "patient-api-service" \
            --query 'services[0].runningCount' \
            --output text 2>/dev/null || echo "0")
        
        DOCTOR_RUNNING=$(aws ecs describe-services \
            --cluster $CLUSTER_NAME \
            --services "doctor-api-service" \
            --query 'services[0].runningCount' \
            --output text 2>/dev/null || echo "0")
        
        echo "  Patient API: $PATIENT_RUNNING running, Doctor API: $DOCTOR_RUNNING running"
        
        if [ "$PATIENT_RUNNING" -ge 1 ] 2>/dev/null && [ "$DOCTOR_RUNNING" -ge 1 ] 2>/dev/null; then
            log_success "Services are running!"
            break
        fi
        
        attempts=$((attempts + 1))
        sleep 15
    done
    
    # Test health endpoints
    if command -v curl &> /dev/null; then
        log_info "Testing health endpoints..."
        
        sleep 30  # Give ALB time to register targets
        
        if curl -sf "http://$PATIENT_ALB_DNS/health" > /dev/null 2>&1; then
            log_success "Patient API is healthy"
        else
            log_warning "Patient API not responding yet (may still be starting)"
        fi
        
        if curl -sf "http://$DOCTOR_ALB_DNS/health" > /dev/null 2>&1; then
            log_success "Doctor API is healthy"
        else
            log_warning "Doctor API not responding yet (may still be starting)"
        fi
    else
        log_warning "curl not found - skipping health check tests"
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    START_TIME=$(date +%s)
    
    echo ""
    echo -e "${MAGENTA}+==============================================================+${NC}"
    echo -e "${MAGENTA}|       ONCOLIFE COMPLETE AWS DEPLOYMENT SCRIPT (BASH)         |${NC}"
    echo -e "${MAGENTA}|                                                              |${NC}"
    echo -e "${MAGENTA}|  This script will deploy the complete OncoLife platform     |${NC}"
    echo -e "${MAGENTA}|  to AWS. Estimated time: 20-30 minutes                       |${NC}"
    echo -e "${MAGENTA}+==============================================================+${NC}"
    echo ""
    
    # Execute all steps
    check_prerequisites
    create_ecs_service_role
    create_vpc_infrastructure
    create_security_groups
    create_rds_database
    create_cognito_user_pool
    create_s3_buckets
    upload_education_pdfs
    create_secrets
    create_ecr_repositories
    create_cloudwatch_log_groups
    build_docker_images
    create_iam_roles
    create_ecs_cluster
    create_alb_infrastructure
    register_task_definitions
    create_ecs_services
    verify_deployment
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    DURATION_MIN=$((DURATION / 60))
    DURATION_SEC=$((DURATION % 60))
    
    # Save configuration
    CONFIG_FILE="deployment-config-$(date +%Y%m%d-%H%M%S).json"
    cat > $CONFIG_FILE <<EOFCONFIG
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "region": "$AWS_REGION",
    "account_id": "$ACCOUNT_ID",
    "vpc_id": "$VPC_ID",
    "public_subnets": ["$PUBLIC_SUBNET_1", "$PUBLIC_SUBNET_2"],
    "private_subnets": ["$PRIVATE_SUBNET_1", "$PRIVATE_SUBNET_2"],
    "rds_endpoint": "$RDS_ENDPOINT",
    "cognito_pool_id": "$COGNITO_POOL_ID",
    "patient_alb_dns": "$PATIENT_ALB_DNS",
    "doctor_alb_dns": "$DOCTOR_ALB_DNS",
    "s3_buckets": {
        "education": "$PROJECT_NAME-education-$ACCOUNT_ID",
        "referrals": "$PROJECT_NAME-referrals-$ACCOUNT_ID"
    },
    "environment_variables": {
        "S3_EDUCATION_BUCKET": "$PROJECT_NAME-education-$ACCOUNT_ID",
        "S3_REFERRAL_BUCKET": "$PROJECT_NAME-referrals-$ACCOUNT_ID",
        "AWS_REGION": "$AWS_REGION"
    }
}
EOFCONFIG
    
    # Final Summary
    echo ""
    echo -e "${GREEN}+==============================================================+${NC}"
    echo -e "${GREEN}|              DEPLOYMENT COMPLETE!                            |${NC}"
    echo -e "${GREEN}+==============================================================+${NC}"
    echo ""
    echo -e "${CYAN}Duration: $DURATION_MIN minutes $DURATION_SEC seconds${NC}"
    echo ""
    echo -e "${CYAN}ACCESS URLS:${NC}"
    echo -e "  Patient API:      http://$PATIENT_ALB_DNS"
    echo -e "  Patient API Docs: http://$PATIENT_ALB_DNS/docs"
    echo -e "  Doctor API:       http://$DOCTOR_ALB_DNS"
    echo -e "  Doctor API Docs:  http://$DOCTOR_ALB_DNS/docs"
    echo ""
    echo -e "${CYAN}NEXT STEPS:${NC}"
    echo -e "  1. Create databases: Connect to RDS and run:"
    echo -e "     ${YELLOW}CREATE DATABASE oncolife_patient;${NC}"
    echo -e "     ${YELLOW}CREATE DATABASE oncolife_doctor;${NC}"
    echo ""
    echo -e "  2. Run migrations from a bastion host or ECS task:"
    echo -e "     ${YELLOW}cd apps/patient-platform/patient-api${NC}"
    echo -e "     ${YELLOW}alembic upgrade head${NC}"
    echo ""
    echo -e "  3. Seed education metadata (after migrations):"
    echo -e "     ${YELLOW}python apps/patient-platform/patient-api/scripts/seed_education_pdfs.py${NC}"
    echo ""
    echo -e "  4. (Optional) Set up custom domains with Route 53 and ACM"
    echo ""
    echo -e "${CYAN}Configuration saved to: $CONFIG_FILE${NC}"
    echo ""
}

# Run main
main
