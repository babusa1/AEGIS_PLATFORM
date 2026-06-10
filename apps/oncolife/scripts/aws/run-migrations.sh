#!/bin/bash
# =============================================================================
# OncoLife Database Migration Script
# =============================================================================
# This script runs Alembic migrations on AWS RDS or local Docker.
#
# Usage:
#   ./scripts/aws/run-migrations.sh local           # Run on local Docker DB
#   ./scripts/aws/run-migrations.sh patient         # Run patient-api migrations on AWS
#   ./scripts/aws/run-migrations.sh doctor          # Run doctor-api migrations on AWS
#   ./scripts/aws/run-migrations.sh all             # Run all migrations on AWS
#   ./scripts/aws/run-migrations.sh sql             # Apply SQL script directly
#   ./scripts/aws/run-migrations.sh status          # Check migration status
#
# Prerequisites:
#   - For local: Docker must be running with postgres container
#   - For AWS: AWS CLI configured, SSM Session Manager plugin installed
#   - Python with alembic installed in the API virtual environment
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
PROJECT_NAME="oncolife"
AWS_REGION="${AWS_REGION:-us-east-1}"
PATIENT_API_DIR="apps/patient-platform/patient-api"
DOCTOR_API_DIR="apps/doctor-platform/doctor-api"
SQL_SCRIPT="scripts/db/schema_patient_diary_doctor_dashboard.sql"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}=============================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}=============================================${NC}"
}

# =============================================================================
# Local Docker Migrations
# =============================================================================

run_local_migrations() {
    log_step "Running Migrations on Local Docker"
    
    # Check if Docker is running
    if ! docker info &> /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check if postgres container is running
    if ! docker ps | grep -q "postgres"; then
        log_error "PostgreSQL container is not running."
        log_info "Start it with: docker-compose up -d postgres"
        exit 1
    fi
    
    # Get container name
    POSTGRES_CONTAINER=$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -1)
    log_info "Found PostgreSQL container: $POSTGRES_CONTAINER"
    
    # Run Patient API migrations
    log_info "Running Patient API Alembic migrations..."
    if [ -d "$PATIENT_API_DIR" ]; then
        cd "$PATIENT_API_DIR"
        
        # Activate virtual environment if it exists
        if [ -d ".venv" ]; then
            source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null || true
        fi
        
        # Run alembic
        if command -v alembic &> /dev/null; then
            alembic upgrade head
            log_success "Patient API migrations completed"
        else
            log_warning "Alembic not found. Install with: pip install alembic"
        fi
        
        cd - > /dev/null
    else
        log_warning "Patient API directory not found: $PATIENT_API_DIR"
    fi
    
    # Run Doctor API migrations
    log_info "Running Doctor API Alembic migrations..."
    if [ -d "$DOCTOR_API_DIR" ]; then
        cd "$DOCTOR_API_DIR"
        
        # Activate virtual environment if it exists
        if [ -d ".venv" ]; then
            source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null || true
        fi
        
        # Run alembic
        if command -v alembic &> /dev/null; then
            alembic upgrade head
            log_success "Doctor API migrations completed"
        else
            log_warning "Alembic not found. Install with: pip install alembic"
        fi
        
        cd - > /dev/null
    else
        log_warning "Doctor API directory not found: $DOCTOR_API_DIR"
    fi
    
    log_success "Local migrations completed!"
}

# =============================================================================
# Apply SQL Script Directly
# =============================================================================

run_sql_script() {
    log_step "Applying SQL Script Directly"
    
    local target="${1:-local}"
    
    if [ ! -f "$SQL_SCRIPT" ]; then
        log_error "SQL script not found: $SQL_SCRIPT"
        exit 1
    fi
    
    if [ "$target" = "local" ]; then
        # Local Docker execution
        POSTGRES_CONTAINER=$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -1)
        
        if [ -z "$POSTGRES_CONTAINER" ]; then
            log_error "PostgreSQL container not found"
            exit 1
        fi
        
        log_info "Running SQL script on local Docker..."
        
        # Copy script to container and execute
        docker cp "$SQL_SCRIPT" "$POSTGRES_CONTAINER:/tmp/schema.sql"
        
        # Run on patient database
        log_info "Applying to oncolife_patient database..."
        docker exec -i "$POSTGRES_CONTAINER" psql -U oncolife -d oncolife_patient -f /tmp/schema.sql
        log_success "Applied to oncolife_patient"
        
        # Run on doctor database (for doctor-specific tables)
        log_info "Applying to oncolife_doctor database..."
        docker exec -i "$POSTGRES_CONTAINER" psql -U oncolife -d oncolife_doctor -f /tmp/schema.sql 2>/dev/null || true
        log_success "Applied to oncolife_doctor"
        
        # Cleanup
        docker exec "$POSTGRES_CONTAINER" rm /tmp/schema.sql
        
    else
        # AWS RDS execution
        log_info "For AWS RDS, use the AWS console or a bastion host:"
        echo ""
        echo "  1. Connect to RDS via bastion or VPN:"
        echo "     psql -h <RDS_ENDPOINT> -U oncolife_admin -d oncolife_patient"
        echo ""
        echo "  2. Run the SQL script:"
        echo "     \\i $SQL_SCRIPT"
        echo ""
        echo "  Or use AWS RDS Query Editor in the console."
        echo ""
    fi
}

# =============================================================================
# AWS RDS Migrations (via ECS Exec or Bastion)
# =============================================================================

run_aws_migrations() {
    local api_type="$1"
    
    log_step "Running Migrations on AWS RDS ($api_type)"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install it first."
        exit 1
    fi
    
    # Get RDS endpoint from Secrets Manager
    log_info "Fetching RDS endpoint from Secrets Manager..."
    RDS_SECRET=$(aws secretsmanager get-secret-value \
        --secret-id "$PROJECT_NAME/db" \
        --query 'SecretString' \
        --output text \
        --region $AWS_REGION 2>/dev/null || echo "")
    
    if [ -z "$RDS_SECRET" ]; then
        log_error "Could not fetch database secret. Is AWS configured correctly?"
        exit 1
    fi
    
    RDS_HOST=$(echo "$RDS_SECRET" | python3 -c "import sys, json; print(json.load(sys.stdin)['host'])" 2>/dev/null || echo "")
    RDS_USER=$(echo "$RDS_SECRET" | python3 -c "import sys, json; print(json.load(sys.stdin)['username'])" 2>/dev/null || echo "")
    
    if [ -z "$RDS_HOST" ]; then
        log_error "Could not parse RDS endpoint from secret"
        exit 1
    fi
    
    log_success "RDS Endpoint: $RDS_HOST"
    log_success "RDS User: $RDS_USER"
    
    echo ""
    log_warning "AWS RDS migrations require one of these methods:"
    echo ""
    echo "  ${CYAN}OPTION 1: Run from Bastion Host or VPN${NC}"
    echo "  ─────────────────────────────────────────"
    echo "  1. SSH to bastion or connect via VPN"
    echo "  2. Clone the repo and install dependencies"
    echo "  3. Run:"
    
    if [ "$api_type" = "patient" ] || [ "$api_type" = "all" ]; then
        echo "     cd $PATIENT_API_DIR"
        echo "     export PATIENT_DB_HOST=$RDS_HOST"
        echo "     export PATIENT_DB_USER=$RDS_USER"
        echo "     export PATIENT_DB_PASSWORD=<from-secrets-manager>"
        echo "     export PATIENT_DB_NAME=oncolife_patient"
        echo "     alembic upgrade head"
        echo ""
    fi
    
    if [ "$api_type" = "doctor" ] || [ "$api_type" = "all" ]; then
        echo "     cd $DOCTOR_API_DIR"
        echo "     export DOCTOR_DB_HOST=$RDS_HOST"
        echo "     export DOCTOR_DB_USER=$RDS_USER"
        echo "     export DOCTOR_DB_PASSWORD=<from-secrets-manager>"
        echo "     export DOCTOR_DB_NAME=oncolife_doctor"
        echo "     alembic upgrade head"
        echo ""
    fi
    
    echo "  ${CYAN}OPTION 2: Run SQL Script via RDS Query Editor${NC}"
    echo "  ──────────────────────────────────────────────"
    echo "  1. Open AWS Console → RDS → Query Editor"
    echo "  2. Connect to $RDS_HOST"
    echo "  3. Copy contents of: $SQL_SCRIPT"
    echo "  4. Execute on both databases"
    echo ""
    
    echo "  ${CYAN}OPTION 3: Use ECS Exec (if enabled)${NC}"
    echo "  ────────────────────────────────────"
    echo "  aws ecs execute-command \\"
    echo "    --cluster $PROJECT_NAME-production \\"
    echo "    --task <TASK_ID> \\"
    echo "    --container patient-api \\"
    echo "    --interactive \\"
    echo "    --command \"/bin/bash\""
    echo ""
    echo "  Then run: alembic upgrade head"
    echo ""
}

# =============================================================================
# Check Migration Status
# =============================================================================

check_migration_status() {
    log_step "Checking Migration Status"
    
    # Check if Docker is running for local
    if docker info &> /dev/null 2>&1; then
        POSTGRES_CONTAINER=$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -1)
        
        if [ -n "$POSTGRES_CONTAINER" ]; then
            log_info "Local Docker PostgreSQL detected"
            
            echo ""
            echo "Patient Database Tables:"
            docker exec -i "$POSTGRES_CONTAINER" psql -U oncolife -d oncolife_patient -c "\dt" 2>/dev/null || echo "  Database not accessible"
            
            echo ""
            echo "Alembic Version (Patient):"
            docker exec -i "$POSTGRES_CONTAINER" psql -U oncolife -d oncolife_patient -c "SELECT * FROM alembic_version;" 2>/dev/null || echo "  No alembic_version table"
            
            echo ""
            echo "New Onboarding Tables Check:"
            for table in providers oncology_profiles medications chemo_schedule fax_ingestion_log ocr_field_confidence; do
                if docker exec -i "$POSTGRES_CONTAINER" psql -U oncolife -d oncolife_patient -c "\dt $table" 2>/dev/null | grep -q "$table"; then
                    echo "  ✅ $table"
                else
                    echo "  ❌ $table (missing)"
                fi
            done
            echo ""
        fi
    fi
    
    # Check patient-api alembic status
    if [ -d "$PATIENT_API_DIR" ]; then
        cd "$PATIENT_API_DIR"
        if [ -d ".venv" ]; then
            source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null || true
        fi
        
        if command -v alembic &> /dev/null; then
            log_info "Patient API Alembic Status:"
            alembic current 2>/dev/null || echo "  Could not get alembic status"
            echo ""
            log_info "Pending Migrations:"
            alembic history 2>/dev/null | head -10 || echo "  Could not get history"
        fi
        cd - > /dev/null
    fi
}

# =============================================================================
# Print Usage
# =============================================================================

print_usage() {
    echo ""
    echo "OncoLife Database Migration Script"
    echo "==================================="
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  local       Run Alembic migrations on local Docker PostgreSQL"
    echo "  patient     Show instructions for Patient API migrations on AWS"
    echo "  doctor      Show instructions for Doctor API migrations on AWS"
    echo "  all         Show instructions for all migrations on AWS"
    echo "  sql         Apply SQL script directly to local Docker"
    echo "  sql-aws     Show instructions for SQL on AWS RDS"
    echo "  status      Check current migration status"
    echo ""
    echo "Examples:"
    echo "  $0 local           # Run all migrations locally"
    echo "  $0 sql             # Apply SQL schema script locally"
    echo "  $0 status          # Check which migrations have been applied"
    echo ""
    echo "For AWS deployments, this script provides instructions."
    echo "Migrations must be run from a bastion host or via VPN."
    echo ""
}

# =============================================================================
# Main
# =============================================================================

case "${1:-}" in
    local)
        run_local_migrations
        ;;
    patient)
        run_aws_migrations "patient"
        ;;
    doctor)
        run_aws_migrations "doctor"
        ;;
    all)
        run_aws_migrations "all"
        ;;
    sql)
        run_sql_script "local"
        ;;
    sql-aws)
        run_sql_script "aws"
        ;;
    status)
        check_migration_status
        ;;
    -h|--help)
        print_usage
        ;;
    *)
        if [ -n "$1" ]; then
            log_error "Unknown command: $1"
        fi
        print_usage
        exit 1
        ;;
esac
