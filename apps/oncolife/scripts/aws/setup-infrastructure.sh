#!/bin/bash
# =============================================================================
# OncoLife AWS Infrastructure Setup Script
# =============================================================================
# This script creates all necessary AWS resources for OncoLife deployment.
#
# Usage: ./scripts/aws/setup-infrastructure.sh
#
# Prerequisites:
# - AWS CLI configured with admin-level credentials
# - Appropriate IAM permissions
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="oncolife"
ENVIRONMENT="${ENVIRONMENT:-production}"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# 1. Create ECR Repositories
# =============================================================================

create_ecr_repos() {
    log_info "Creating ECR repositories..."
    
    for repo in "oncolife-patient-api" "oncolife-doctor-api"; do
        if aws ecr describe-repositories --repository-names $repo --region $AWS_REGION 2>/dev/null; then
            log_warning "Repository $repo already exists, skipping..."
        else
            aws ecr create-repository \
                --repository-name $repo \
                --region $AWS_REGION \
                --image-scanning-configuration scanOnPush=true \
                --encryption-configuration encryptionType=AES256
            log_success "Created ECR repository: $repo"
        fi
    done
}

# =============================================================================
# 2. Create CloudWatch Log Groups
# =============================================================================

create_log_groups() {
    log_info "Creating CloudWatch log groups..."
    
    for log_group in "/ecs/oncolife-patient-api" "/ecs/oncolife-doctor-api"; do
        if aws logs describe-log-groups --log-group-name-prefix $log_group --region $AWS_REGION 2>/dev/null | grep -q $log_group; then
            log_warning "Log group $log_group already exists, skipping..."
        else
            aws logs create-log-group \
                --log-group-name $log_group \
                --region $AWS_REGION
            
            aws logs put-retention-policy \
                --log-group-name $log_group \
                --retention-in-days 30 \
                --region $AWS_REGION
            
            log_success "Created log group: $log_group"
        fi
    done
}

# =============================================================================
# 3. Create ECS Cluster
# =============================================================================

create_ecs_cluster() {
    log_info "Creating ECS cluster..."
    
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    
    if aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION 2>/dev/null | grep -q "ACTIVE"; then
        log_warning "Cluster $CLUSTER_NAME already exists, skipping..."
    else
        aws ecs create-cluster \
            --cluster-name $CLUSTER_NAME \
            --capacity-providers FARGATE FARGATE_SPOT \
            --default-capacity-provider-strategy \
                capacityProvider=FARGATE,weight=1 \
                capacityProvider=FARGATE_SPOT,weight=1 \
            --settings name=containerInsights,value=enabled \
            --region $AWS_REGION
        
        log_success "Created ECS cluster: $CLUSTER_NAME"
    fi
}

# =============================================================================
# 4. Create Secrets in Secrets Manager
# =============================================================================

create_secrets() {
    log_info "Creating Secrets Manager secrets..."
    
    # Database secret template
    DB_SECRET='{
        "host": "REPLACE_WITH_RDS_ENDPOINT",
        "port": "5432",
        "username": "oncolife_admin",
        "password": "REPLACE_WITH_SECURE_PASSWORD",
        "patient_db": "oncolife_patient",
        "doctor_db": "oncolife_doctor"
    }'
    
    # Cognito secret template
    COGNITO_SECRET='{
        "user_pool_id": "REPLACE_WITH_USER_POOL_ID",
        "client_id": "REPLACE_WITH_CLIENT_ID",
        "client_secret": "REPLACE_WITH_CLIENT_SECRET"
    }'
    
    for secret_name in "oncolife/db" "oncolife/cognito"; do
        if aws secretsmanager describe-secret --secret-id $secret_name --region $AWS_REGION 2>/dev/null; then
            log_warning "Secret $secret_name already exists, skipping..."
        else
            if [ "$secret_name" == "oncolife/db" ]; then
                SECRET_VALUE="$DB_SECRET"
            else
                SECRET_VALUE="$COGNITO_SECRET"
            fi
            
            aws secretsmanager create-secret \
                --name $secret_name \
                --secret-string "$SECRET_VALUE" \
                --region $AWS_REGION
            
            log_success "Created secret: $secret_name (update with real values!)"
        fi
    done
}

# =============================================================================
# 5. Create IAM Roles
# =============================================================================

create_iam_roles() {
    log_info "Creating IAM roles..."
    
    # ECS Task Execution Role
    EXECUTION_ROLE_NAME="ecsTaskExecutionRole"
    
    if aws iam get-role --role-name $EXECUTION_ROLE_NAME 2>/dev/null; then
        log_warning "Role $EXECUTION_ROLE_NAME already exists, skipping..."
    else
        # Create trust policy
        cat > /tmp/ecs-trust-policy.json << 'EOF'
{
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
}
EOF
        
        aws iam create-role \
            --role-name $EXECUTION_ROLE_NAME \
            --assume-role-policy-document file:///tmp/ecs-trust-policy.json
        
        aws iam attach-role-policy \
            --role-name $EXECUTION_ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
        
        # Add Secrets Manager access
        cat > /tmp/secrets-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:*:*:secret:oncolife/*"
        }
    ]
}
EOF
        
        aws iam put-role-policy \
            --role-name $EXECUTION_ROLE_NAME \
            --policy-name SecretsManagerAccess \
            --policy-document file:///tmp/secrets-policy.json
        
        log_success "Created IAM role: $EXECUTION_ROLE_NAME"
    fi
    
    # OncoLife Task Role (for application permissions)
    TASK_ROLE_NAME="oncolifeTaskRole"
    
    if aws iam get-role --role-name $TASK_ROLE_NAME 2>/dev/null; then
        log_warning "Role $TASK_ROLE_NAME already exists, skipping..."
    else
        aws iam create-role \
            --role-name $TASK_ROLE_NAME \
            --assume-role-policy-document file:///tmp/ecs-trust-policy.json
        
        # Add Cognito permissions
        cat > /tmp/cognito-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cognito-idp:AdminCreateUser",
                "cognito-idp:AdminDeleteUser",
                "cognito-idp:AdminInitiateAuth",
                "cognito-idp:AdminRespondToAuthChallenge",
                "cognito-idp:AdminGetUser",
                "cognito-idp:AdminSetUserPassword"
            ],
            "Resource": "*"
        }
    ]
}
EOF
        
        aws iam put-role-policy \
            --role-name $TASK_ROLE_NAME \
            --policy-name CognitoAccess \
            --policy-document file:///tmp/cognito-policy.json
        
        log_success "Created IAM role: $TASK_ROLE_NAME"
    fi
    
    # Cleanup temp files
    rm -f /tmp/ecs-trust-policy.json /tmp/secrets-policy.json /tmp/cognito-policy.json
}

# =============================================================================
# 6. Create SNS Topic for Alarms
# =============================================================================

create_sns_topic() {
    log_info "Creating SNS topic for alerts..."
    
    TOPIC_NAME="${PROJECT_NAME}-alerts"
    
    if aws sns list-topics --region $AWS_REGION | grep -q $TOPIC_NAME; then
        log_warning "SNS topic $TOPIC_NAME already exists, skipping..."
    else
        aws sns create-topic \
            --name $TOPIC_NAME \
            --region $AWS_REGION
        
        log_success "Created SNS topic: $TOPIC_NAME"
        log_warning "Remember to subscribe to the topic with your email!"
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    log_info "=========================================="
    log_info "OncoLife Infrastructure Setup"
    log_info "Region: $AWS_REGION"
    log_info "Environment: $ENVIRONMENT"
    log_info "=========================================="
    
    create_ecr_repos
    create_log_groups
    create_ecs_cluster
    create_secrets
    create_iam_roles
    create_sns_topic
    
    log_success "=========================================="
    log_success "Infrastructure setup complete!"
    log_success ""
    log_success "Next steps:"
    log_success "1. Update secrets in Secrets Manager with real values"
    log_success "2. Create RDS PostgreSQL instance"
    log_success "3. Create Cognito User Pool"
    log_success "4. Create VPC, subnets, and security groups"
    log_success "5. Create ALB and target groups"
    log_success "6. Register ECS task definitions"
    log_success "7. Create ECS services"
    log_success "=========================================="
}

main "$@"





