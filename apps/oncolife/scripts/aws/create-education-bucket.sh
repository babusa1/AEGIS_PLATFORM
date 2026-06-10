#!/bin/bash
# =============================================================================
# OncoLife - Create Education S3 Bucket
# =============================================================================
# This script creates and configures the S3 bucket for education content.
#
# Usage:
#   ./scripts/aws/create-education-bucket.sh
#   ./scripts/aws/create-education-bucket.sh --region us-east-1
#
# Prerequisites:
#   - AWS CLI configured with appropriate permissions
#
# Note: This is a STANDALONE script. You don't need to run this if you
#       used full-deploy.sh, as that script creates the education bucket.
# =============================================================================

# Prevent Git Bash from converting Unix paths to Windows paths
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"

set -e

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--region REGION]"
            echo ""
            echo "Options:"
            echo "  --region REGION    AWS region (default: us-east-1)"
            echo "  --help             Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set defaults
AWS_REGION="${AWS_REGION:-us-east-1}"

# Colors (with fallback for terminals without color support)
if [[ "$TERM" == "dumb" ]] || [[ -z "$TERM" ]]; then
    GREEN=''
    YELLOW=''
    CYAN=''
    RED=''
    NC=''
else
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    RED='\033[0;31m'
    NC='\033[0m'
fi

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
if [ -z "$ACCOUNT_ID" ]; then
    echo -e "${RED}[ERROR] Could not get AWS account ID. Run 'aws configure' first.${NC}"
    exit 1
fi

BUCKET_NAME="oncolife-education-${ACCOUNT_ID}"

echo ""
echo -e "${CYAN}+============================================+${NC}"
echo -e "${CYAN}|  Creating OncoLife Education Bucket       |${NC}"
echo -e "${CYAN}+============================================+${NC}"
echo ""
echo "  Bucket: $BUCKET_NAME"
echo "  Region: $AWS_REGION"
echo ""

# Check if bucket already exists
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo -e "${YELLOW}[WARN] Bucket already exists: $BUCKET_NAME${NC}"
    echo "  Continuing with configuration..."
else
    # Create bucket
    echo -e "${CYAN}Creating bucket...${NC}"
    if [ "$AWS_REGION" = "us-east-1" ]; then
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$AWS_REGION"
    else
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$AWS_REGION" \
            --create-bucket-configuration LocationConstraint="$AWS_REGION"
    fi
    echo -e "${GREEN}[OK] Bucket created${NC}"
fi

# Enable versioning
echo -e "${CYAN}Enabling versioning...${NC}"
aws s3api put-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --versioning-configuration Status=Enabled
echo -e "${GREEN}[OK] Versioning enabled${NC}"

# Enable encryption (KMS)
echo -e "${CYAN}Enabling encryption...${NC}"
aws s3api put-bucket-encryption \
    --bucket "$BUCKET_NAME" \
    --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"},"BucketKeyEnabled":true}]}'
echo -e "${GREEN}[OK] Encryption enabled${NC}"

# Block public access
echo -e "${CYAN}Blocking public access...${NC}"
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration '{"BlockPublicAcls":true,"IgnorePublicAcls":true,"BlockPublicPolicy":true,"RestrictPublicBuckets":true}'
echo -e "${GREEN}[OK] Public access blocked${NC}"

# Create folder structure
echo -e "${CYAN}Creating folder structure...${NC}"
aws s3api put-object --bucket "$BUCKET_NAME" --key "symptoms/" > /dev/null
aws s3api put-object --bucket "$BUCKET_NAME" --key "handbooks/" > /dev/null
aws s3api put-object --bucket "$BUCKET_NAME" --key "regimens/" > /dev/null
echo -e "${GREEN}[OK] Folder structure created${NC}"

# Set lifecycle policy (for cost management)
echo -e "${CYAN}Setting lifecycle policy...${NC}"
aws s3api put-bucket-lifecycle-configuration \
    --bucket "$BUCKET_NAME" \
    --lifecycle-configuration '{"Rules":[{"ID":"MoveToIAAfter90Days","Status":"Enabled","Filter":{},"Transitions":[{"Days":90,"StorageClass":"STANDARD_IA"}]}]}'
echo -e "${GREEN}[OK] Lifecycle policy set${NC}"

echo ""
echo -e "${GREEN}+============================================+${NC}"
echo -e "${GREEN}|  SUCCESS: Education bucket created!       |${NC}"
echo -e "${GREEN}+============================================+${NC}"
echo ""
echo "  Bucket Name: $BUCKET_NAME"
echo "  Bucket ARN:  arn:aws:s3:::$BUCKET_NAME"
echo ""
echo -e "${CYAN}Next Steps:${NC}"
echo "  1. Upload education PDFs: ./scripts/aws/upload-education-pdfs.sh"
echo "  2. Run seed script: python scripts/seed_education.py"
echo ""
echo -e "${YELLOW}Note: For HIPAA compliance, enable access logging to a separate log bucket.${NC}"
echo ""
