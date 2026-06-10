#!/bin/bash
# =============================================================================
# OncoLife Monitoring Setup Script
# =============================================================================
# 
# This script sets up:
# 1. SNS Topics for alert notifications
# 2. Email subscriptions for alerts
# 3. CloudWatch Log Groups
# 4. CloudWatch Dashboard
#
# Usage:
#   ./scripts/aws/setup-monitoring.sh email@example.com
#   ./scripts/aws/setup-monitoring.sh email@example.com --region us-east-1
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Run full-deploy.sh first to create the base infrastructure
# =============================================================================

# Prevent Git Bash from converting Unix paths to Windows paths
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"

set -e

# Parse arguments
ALERT_EMAIL=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [email@example.com] [--region REGION]"
            echo ""
            echo "Arguments:"
            echo "  email              Email address for alert notifications"
            echo ""
            echo "Options:"
            echo "  --region REGION    AWS region (default: us-east-1)"
            echo "  --help             Show this help"
            exit 0
            ;;
        *)
            if [ -z "$ALERT_EMAIL" ]; then
                ALERT_EMAIL="$1"
            else
                echo "Unknown option: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="oncolife"
ENVIRONMENT="production"

# Colors (with fallback for terminals without color support)
if [[ "$TERM" == "dumb" ]] || [[ -z "$TERM" ]]; then
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    NC=''
else
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    NC='\033[0m'
fi

echo ""
echo -e "${CYAN}+==============================================================+${NC}"
echo -e "${CYAN}|     OncoLife Monitoring Setup                                |${NC}"
echo -e "${CYAN}|     Environment: ${ENVIRONMENT}                                       |${NC}"
echo -e "${CYAN}|     Region: ${AWS_REGION}                                       |${NC}"
echo -e "${CYAN}+==============================================================+${NC}"
echo ""

# Get Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
if [ -z "$ACCOUNT_ID" ]; then
    echo -e "${RED}[ERROR] Could not get AWS account ID. Run 'aws configure' first.${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] AWS Account: $ACCOUNT_ID${NC}"

# =============================================================================
# SNS Topics Setup
# =============================================================================

echo ""
echo -e "${YELLOW}=== Setting up SNS Topics ===${NC}"

# Create main alerts topic
ALERTS_TOPIC_ARN=$(aws sns create-topic \
    --name "${PROJECT_NAME}-${ENVIRONMENT}-alerts" \
    --region "$AWS_REGION" \
    --query 'TopicArn' \
    --output text 2>/dev/null || echo "")

if [ -n "$ALERTS_TOPIC_ARN" ]; then
    aws sns tag-resource \
        --resource-arn "$ALERTS_TOPIC_ARN" \
        --tags "Key=Environment,Value=${ENVIRONMENT}" "Key=Project,Value=${PROJECT_NAME}" \
        --region "$AWS_REGION" 2>/dev/null || true
    echo -e "${GREEN}[OK] Created SNS topic: ${ALERTS_TOPIC_ARN}${NC}"
else
    ALERTS_TOPIC_ARN=$(aws sns list-topics --region "$AWS_REGION" --query "Topics[?contains(TopicArn, '${PROJECT_NAME}-${ENVIRONMENT}-alerts')].TopicArn" --output text 2>/dev/null)
    echo -e "${YELLOW}[WARN] SNS topic already exists: ${ALERTS_TOPIC_ARN}${NC}"
fi

# Create critical alerts topic (for immediate attention)
CRITICAL_TOPIC_ARN=$(aws sns create-topic \
    --name "${PROJECT_NAME}-${ENVIRONMENT}-critical-alerts" \
    --region "$AWS_REGION" \
    --query 'TopicArn' \
    --output text 2>/dev/null || echo "")

if [ -n "$CRITICAL_TOPIC_ARN" ]; then
    aws sns tag-resource \
        --resource-arn "$CRITICAL_TOPIC_ARN" \
        --tags "Key=Environment,Value=${ENVIRONMENT}" "Key=Project,Value=${PROJECT_NAME}" "Key=Severity,Value=critical" \
        --region "$AWS_REGION" 2>/dev/null || true
    echo -e "${GREEN}[OK] Created critical alerts topic: ${CRITICAL_TOPIC_ARN}${NC}"
fi

# Subscribe email if provided
if [ -n "$ALERT_EMAIL" ]; then
    echo ""
    echo -e "${YELLOW}=== Subscribing email to alerts ===${NC}"
    
    aws sns subscribe \
        --topic-arn "$ALERTS_TOPIC_ARN" \
        --protocol email \
        --notification-endpoint "$ALERT_EMAIL" \
        --region "$AWS_REGION" \
        --return-subscription-arn 2>/dev/null || true
    
    echo -e "${GREEN}[OK] Subscription request sent to ${ALERT_EMAIL}${NC}"
    echo -e "${YELLOW}[INFO] Please check your email and confirm the subscription!${NC}"
    
    # Also subscribe to critical alerts
    aws sns subscribe \
        --topic-arn "$CRITICAL_TOPIC_ARN" \
        --protocol email \
        --notification-endpoint "$ALERT_EMAIL" \
        --region "$AWS_REGION" \
        --return-subscription-arn 2>/dev/null || true
else
    echo -e "${YELLOW}[INFO] No email provided - skipping subscription${NC}"
    echo "  To subscribe later: aws sns subscribe --topic-arn $ALERTS_TOPIC_ARN --protocol email --notification-endpoint YOUR_EMAIL"
fi

# =============================================================================
# CloudWatch Log Groups
# =============================================================================

echo ""
echo -e "${YELLOW}=== Setting up CloudWatch Log Groups ===${NC}"

# These match the log groups created in full-deploy.sh
LOG_GROUPS=(
    "/ecs/${PROJECT_NAME}-patient-api"
    "/ecs/${PROJECT_NAME}-doctor-api"
)

for LOG_GROUP in "${LOG_GROUPS[@]}"; do
    if aws logs create-log-group --log-group-name "$LOG_GROUP" --region "$AWS_REGION" 2>/dev/null; then
        aws logs put-retention-policy \
            --log-group-name "$LOG_GROUP" \
            --retention-in-days 30 \
            --region "$AWS_REGION" 2>/dev/null || true
        echo -e "${GREEN}[OK] Created log group: ${LOG_GROUP}${NC}"
    else
        echo -e "${YELLOW}[INFO] Log group already exists: ${LOG_GROUP}${NC}"
    fi
done

# =============================================================================
# CloudWatch Dashboard
# =============================================================================

echo ""
echo -e "${YELLOW}=== Creating CloudWatch Dashboard ===${NC}"

DASHBOARD_NAME="${PROJECT_NAME}-${ENVIRONMENT}-dashboard"

# Get ALB ARN suffixes for dashboard
PATIENT_ALB_ARN_SUFFIX=$(aws elbv2 describe-load-balancers \
    --names "${PROJECT_NAME}-patient-alb" \
    --region "$AWS_REGION" \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text 2>/dev/null | awk -F':loadbalancer/' '{print $2}' || echo "")

DOCTOR_ALB_ARN_SUFFIX=$(aws elbv2 describe-load-balancers \
    --names "${PROJECT_NAME}-doctor-alb" \
    --region "$AWS_REGION" \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text 2>/dev/null | awk -F':loadbalancer/' '{print $2}' || echo "")

# Get RDS instance ID
RDS_INSTANCE_ID=$(aws rds describe-db-instances \
    --db-instance-identifier "${PROJECT_NAME}-db" \
    --region "$AWS_REGION" \
    --query 'DBInstances[0].DBInstanceIdentifier' \
    --output text 2>/dev/null || echo "${PROJECT_NAME}-db")

# Create dashboard JSON
DASHBOARD_BODY=$(cat <<EOF
{
    "widgets": [
        {
            "type": "text",
            "x": 0,
            "y": 0,
            "width": 24,
            "height": 1,
            "properties": {
                "markdown": "# OncoLife ${ENVIRONMENT} Dashboard\\n**Region:** ${AWS_REGION} | **Account:** ${ACCOUNT_ID}"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 1,
            "width": 12,
            "height": 6,
            "properties": {
                "title": "ECS Service Health",
                "metrics": [
                    [ "AWS/ECS", "CPUUtilization", "ClusterName", "${PROJECT_NAME}-${ENVIRONMENT}", "ServiceName", "patient-api-service", { "label": "Patient API CPU" } ],
                    [ ".", "MemoryUtilization", ".", ".", ".", ".", { "label": "Patient API Memory" } ],
                    [ ".", "CPUUtilization", ".", ".", ".", "doctor-api-service", { "label": "Doctor API CPU" } ],
                    [ ".", "MemoryUtilization", ".", ".", ".", ".", { "label": "Doctor API Memory" } ]
                ],
                "period": 300,
                "region": "${AWS_REGION}",
                "stat": "Average"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 1,
            "width": 12,
            "height": 6,
            "properties": {
                "title": "ALB Request Metrics",
                "metrics": [
                    [ "AWS/ApplicationELB", "RequestCount", "LoadBalancer", "${PATIENT_ALB_ARN_SUFFIX:-app/oncolife-patient-alb/placeholder}", { "label": "Patient API Requests", "stat": "Sum" } ],
                    [ ".", "HTTPCode_Target_5XX_Count", ".", ".", { "label": "Patient API 5XX", "stat": "Sum", "color": "#d62728" } ],
                    [ ".", "RequestCount", ".", "${DOCTOR_ALB_ARN_SUFFIX:-app/oncolife-doctor-alb/placeholder}", { "label": "Doctor API Requests", "stat": "Sum" } ],
                    [ ".", "HTTPCode_Target_5XX_Count", ".", ".", { "label": "Doctor API 5XX", "stat": "Sum", "color": "#ff7f0e" } ]
                ],
                "period": 300,
                "region": "${AWS_REGION}"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 7,
            "width": 12,
            "height": 6,
            "properties": {
                "title": "ALB Response Time (P95)",
                "metrics": [
                    [ "AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "${PATIENT_ALB_ARN_SUFFIX:-app/oncolife-patient-alb/placeholder}", { "label": "Patient API", "stat": "p95" } ],
                    [ ".", ".", ".", "${DOCTOR_ALB_ARN_SUFFIX:-app/oncolife-doctor-alb/placeholder}", { "label": "Doctor API", "stat": "p95" } ]
                ],
                "period": 300,
                "region": "${AWS_REGION}"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 7,
            "width": 12,
            "height": 6,
            "properties": {
                "title": "RDS Database Metrics",
                "metrics": [
                    [ "AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "${RDS_INSTANCE_ID}", { "label": "CPU %" } ],
                    [ ".", "DatabaseConnections", ".", ".", { "label": "Connections", "yAxis": "right" } ],
                    [ ".", "FreeStorageSpace", ".", ".", { "label": "Free Storage (bytes)", "yAxis": "right" } ]
                ],
                "period": 300,
                "region": "${AWS_REGION}"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 13,
            "width": 12,
            "height": 6,
            "properties": {
                "title": "ALB Healthy/Unhealthy Hosts",
                "metrics": [
                    [ "AWS/ApplicationELB", "HealthyHostCount", "LoadBalancer", "${PATIENT_ALB_ARN_SUFFIX:-app/oncolife-patient-alb/placeholder}", "TargetGroup", "targetgroup/patient-api-tg/placeholder", { "label": "Patient Healthy" } ],
                    [ ".", "UnHealthyHostCount", ".", ".", ".", ".", { "label": "Patient Unhealthy", "color": "#d62728" } ],
                    [ ".", "HealthyHostCount", ".", "${DOCTOR_ALB_ARN_SUFFIX:-app/oncolife-doctor-alb/placeholder}", ".", "targetgroup/doctor-api-tg/placeholder", { "label": "Doctor Healthy" } ],
                    [ ".", "UnHealthyHostCount", ".", ".", ".", ".", { "label": "Doctor Unhealthy", "color": "#ff7f0e" } ]
                ],
                "period": 60,
                "region": "${AWS_REGION}"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 13,
            "width": 12,
            "height": 6,
            "properties": {
                "title": "ECS Running Task Count",
                "metrics": [
                    [ "AWS/ECS", "RunningTaskCount", "ClusterName", "${PROJECT_NAME}-${ENVIRONMENT}", "ServiceName", "patient-api-service", { "label": "Patient API Tasks" } ],
                    [ ".", ".", ".", ".", ".", "doctor-api-service", { "label": "Doctor API Tasks" } ]
                ],
                "period": 60,
                "region": "${AWS_REGION}",
                "stat": "Average"
            }
        }
    ]
}
EOF
)

aws cloudwatch put-dashboard \
    --dashboard-name "$DASHBOARD_NAME" \
    --dashboard-body "$DASHBOARD_BODY" \
    --region "$AWS_REGION" 2>/dev/null || true

echo -e "${GREEN}[OK] Dashboard created: ${DASHBOARD_NAME}${NC}"

# =============================================================================
# Summary
# =============================================================================

echo ""
echo -e "${GREEN}+==============================================================+${NC}"
echo -e "${GREEN}|                 Monitoring Setup Complete!                   |${NC}"
echo -e "${GREEN}+==============================================================+${NC}"

echo ""
echo -e "${CYAN}Created Resources:${NC}"
echo "  - SNS Alerts Topic: ${ALERTS_TOPIC_ARN}"
echo "  - SNS Critical Topic: ${CRITICAL_TOPIC_ARN}"
echo "  - Log Groups: ${#LOG_GROUPS[@]} created/verified"
echo "  - Dashboard: ${DASHBOARD_NAME}"

echo ""
echo -e "${CYAN}View Dashboard:${NC}"
echo "  https://${AWS_REGION}.console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:name=${DASHBOARD_NAME}"

if [ -n "$ALERT_EMAIL" ]; then
    echo ""
    echo -e "${YELLOW}IMPORTANT: Check your email ($ALERT_EMAIL) and confirm the subscription!${NC}"
fi

echo ""
echo -e "${CYAN}Environment Variables to Set:${NC}"
echo "  export SNS_ALERT_TOPIC_ARN=\"${ALERTS_TOPIC_ARN}\""
echo "  export CLOUDWATCH_NAMESPACE=\"OncoLife/PatientAPI\""
echo ""
