"""
Data Moat Entity Registry

Defines all 30+ entities available in the Data Moat and provides
generic query operations for workflows and agents.
"""

from typing import Any, Optional, Dict, List
from enum import Enum
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class EntityType(str, Enum):
    """All entity types in the Data Moat."""
    
    # Core Domain
    TENANT = "tenant"
    USER = "user"
    API_KEY = "api_key"
    DATA_SOURCE = "data_source"
    AUDIT_LOG = "audit_log"
    
    # Clinical Domain
    PATIENT = "patient"
    CONDITION = "condition"
    MEDICATION = "medication"
    ENCOUNTER = "encounter"
    PROCEDURE = "procedure"
    OBSERVATION = "observation"
    ALLERGY_INTOLERANCE = "allergy_intolerance"
    CLINICAL_NOTE = "clinical_note"
    
    # Provider Domain
    PROVIDER = "provider"
    ORGANIZATION = "organization"
    LOCATION = "location"
    
    # Financial Domain
    CLAIM = "claim"
    CLAIM_LINE = "claim_line"
    DENIAL = "denial"
    APPEAL = "appeal"
    PAYMENT = "payment"
    COVERAGE = "coverage"
    PAYER = "payer"
    AUTHORIZATION = "authorization"
    
    # Time-Series Domain
    VITAL = "vital"
    LAB_RESULT = "lab_result"
    WEARABLE_METRIC = "wearable_metric"
    
    # Workflow Domain
    WORKFLOW_DEFINITION = "workflow_definition"
    WORKFLOW_EXECUTION = "workflow_execution"
    
    # Security Domain
    CONSENT = "consent"
    BTG_SESSION = "btg_session"
    SYNC_JOB = "sync_job"
    
    # Genomics Domain
    GENOMIC_VARIANT = "genomic_variant"
    GENOMIC_REPORT = "genomic_report"
    
    # Imaging Domain
    IMAGING_STUDY = "imaging_study"
    IMAGING_SERIES = "imaging_series"
    
    # SDOH Domain
    SDOH_ASSESSMENT = "sdoh_assessment"
    
    # PRO Domain
    PRO_RESPONSE = "pro_response"
    
    # Messaging Domain
    MESSAGE = "message"
    
    # Scheduling Domain
    APPOINTMENT = "appointment"
    SCHEDULE = "schedule"


# Entity metadata: table name, primary key, tenant column
ENTITY_METADATA: Dict[EntityType, Dict[str, Any]] = {
    # Core Domain
    EntityType.TENANT: {
        "table": "tenants",
        "primary_key": "id",
        "tenant_column": None,  # Tenants don't have tenant_id
        "description": "Tenant/organization",
    },
    EntityType.USER: {
        "table": "users",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "System user",
    },
    EntityType.API_KEY: {
        "table": "api_keys",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "API key",
    },
    EntityType.DATA_SOURCE: {
        "table": "data_sources",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "Data source connection",
    },
    EntityType.AUDIT_LOG: {
        "table": "audit_log",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "Audit log entry",
    },
    
    # Clinical Domain
    EntityType.PATIENT: {
        "table": "patients",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "Patient",
    },
    EntityType.CONDITION: {
        "table": "conditions",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "Diagnosis/condition",
    },
    EntityType.MEDICATION: {
        "table": "medications",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "Medication/prescription",
    },
    EntityType.ENCOUNTER: {
        "table": "encounters",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "Healthcare encounter/visit",
    },
    
    # Financial Domain
    EntityType.CLAIM: {
        "table": "claims",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "Insurance claim",
    },
    EntityType.DENIAL: {
        "table": "denials",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "Claim denial",
    },
    
    # Time-Series Domain (TimescaleDB)
    EntityType.VITAL: {
        "table": "vitals",
        "primary_key": None,  # Time-series, no single PK
        "tenant_column": "tenant_id",
        "description": "Vital sign measurement",
        "time_column": "time",
    },
    EntityType.LAB_RESULT: {
        "table": "lab_results",
        "primary_key": None,
        "tenant_column": "tenant_id",
        "description": "Laboratory result",
        "time_column": "time",
    },
    EntityType.WEARABLE_METRIC: {
        "table": "wearable_metrics",
        "primary_key": None,
        "tenant_column": "tenant_id",
        "description": "Wearable device metric",
        "time_column": "time",
    },
    
    # Workflow Domain
    EntityType.WORKFLOW_DEFINITION: {
        "table": "workflow_definitions",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "Workflow definition",
    },
    EntityType.WORKFLOW_EXECUTION: {
        "table": "workflow_executions",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "Workflow execution instance",
    },
    
    # Security Domain
    EntityType.CONSENT: {
        "table": "consents",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "Patient consent",
    },
    EntityType.BTG_SESSION: {
        "table": "btg_sessions",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "Break-the-glass session",
    },
    EntityType.SYNC_JOB: {
        "table": "sync_jobs",
        "primary_key": "id",
        "tenant_column": "tenant_id",
        "description": "Data sync job",
    },
}


def get_entity_metadata(entity_type: EntityType) -> Dict[str, Any]:
    """Get metadata for an entity type."""
    return ENTITY_METADATA.get(entity_type, {})


def list_all_entity_types() -> List[Dict[str, Any]]:
    """List all available entity types with metadata."""
    return [
        {
            "type": entity_type.value,
            "description": metadata.get("description", ""),
            "table": metadata.get("table"),
            "has_tenant": metadata.get("tenant_column") is not None,
        }
        for entity_type, metadata in ENTITY_METADATA.items()
    ]


def get_entity_count() -> int:
    """Get total count of entity types."""
    return len(ENTITY_METADATA)
