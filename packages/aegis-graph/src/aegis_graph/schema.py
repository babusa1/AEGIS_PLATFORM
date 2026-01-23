"""
Graph Schema Definition for AEGIS Healthcare Ontology
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class PropertyType(str, Enum):
    STRING = "String"
    INTEGER = "Integer"
    LONG = "Long"
    DOUBLE = "Double"
    BOOLEAN = "Boolean"
    DATE = "Date"


class Cardinality(str, Enum):
    SINGLE = "SINGLE"
    LIST = "LIST"
    SET = "SET"


@dataclass
class PropertyKeyDef:
    name: str
    data_type: PropertyType
    cardinality: Cardinality = Cardinality.SINGLE


@dataclass
class VertexLabelDef:
    name: str
    properties: list[str] = field(default_factory=list)


@dataclass
class EdgeLabelDef:
    name: str
    multiplicity: str = "MULTI"


class AegisGraphSchema:
    """AEGIS Graph Schema - defines vertices, edges, and properties."""
    
    PROPERTY_KEYS = [
        # Common
        PropertyKeyDef("id", PropertyType.STRING),
        PropertyKeyDef("tenant_id", PropertyType.STRING),
        PropertyKeyDef("source_system", PropertyType.STRING),
        PropertyKeyDef("created_at", PropertyType.DATE),
        PropertyKeyDef("updated_at", PropertyType.DATE),
        
        # Patient
        PropertyKeyDef("mrn", PropertyType.STRING),
        PropertyKeyDef("given_name", PropertyType.STRING),
        PropertyKeyDef("family_name", PropertyType.STRING),
        PropertyKeyDef("birth_date", PropertyType.DATE),
        PropertyKeyDef("gender", PropertyType.STRING),
        PropertyKeyDef("deceased", PropertyType.BOOLEAN),
        PropertyKeyDef("phone", PropertyType.STRING),
        PropertyKeyDef("email", PropertyType.STRING),
        PropertyKeyDef("address_line", PropertyType.STRING),
        PropertyKeyDef("city", PropertyType.STRING),
        PropertyKeyDef("state", PropertyType.STRING),
        PropertyKeyDef("postal_code", PropertyType.STRING),
        
        # Provider
        PropertyKeyDef("npi", PropertyType.STRING),
        PropertyKeyDef("credentials", PropertyType.STRING),
        PropertyKeyDef("specialty", PropertyType.STRING),
        PropertyKeyDef("name", PropertyType.STRING),
        
        # Clinical
        PropertyKeyDef("code", PropertyType.STRING),
        PropertyKeyDef("code_system", PropertyType.STRING),
        PropertyKeyDef("display", PropertyType.STRING),
        PropertyKeyDef("status", PropertyType.STRING),
        PropertyKeyDef("category", PropertyType.STRING),
        PropertyKeyDef("start_date", PropertyType.DATE),
        PropertyKeyDef("end_date", PropertyType.DATE),
        PropertyKeyDef("effective_date", PropertyType.DATE),
        PropertyKeyDef("value_numeric", PropertyType.DOUBLE),
        PropertyKeyDef("value_string", PropertyType.STRING),
        PropertyKeyDef("value_unit", PropertyType.STRING),
        
        # Financial
        PropertyKeyDef("claim_type", PropertyType.STRING),
        PropertyKeyDef("billed_amount", PropertyType.DOUBLE),
        PropertyKeyDef("paid_amount", PropertyType.DOUBLE),
        PropertyKeyDef("denial_code", PropertyType.STRING),
        PropertyKeyDef("denial_reason", PropertyType.STRING),
        
        # Genomics
        PropertyKeyDef("gene", PropertyType.STRING),
        PropertyKeyDef("chromosome", PropertyType.STRING),
        PropertyKeyDef("position", PropertyType.LONG),
        PropertyKeyDef("clinical_significance", PropertyType.STRING),
        
        # Risk/Analytics
        PropertyKeyDef("score_type", PropertyType.STRING),
        PropertyKeyDef("score_value", PropertyType.DOUBLE),
        PropertyKeyDef("risk_level", PropertyType.STRING),
        PropertyKeyDef("gap_type", PropertyType.STRING),
        PropertyKeyDef("due_date", PropertyType.DATE),
        PropertyKeyDef("priority", PropertyType.STRING),
        
        # Edge properties
        PropertyKeyDef("role", PropertyType.STRING),
        PropertyKeyDef("rank", PropertyType.INTEGER),
        PropertyKeyDef("period_start", PropertyType.DATE),
        PropertyKeyDef("period_end", PropertyType.DATE),
    ]
    
    VERTEX_LABELS = [
        VertexLabelDef("Patient"),
        VertexLabelDef("Provider"),
        VertexLabelDef("Organization"),
        VertexLabelDef("Location"),
        VertexLabelDef("Encounter"),
        VertexLabelDef("Diagnosis"),
        VertexLabelDef("Condition"),
        VertexLabelDef("Observation"),
        VertexLabelDef("DiagnosticReport"),
        VertexLabelDef("Medication"),
        VertexLabelDef("MedicationRequest"),
        VertexLabelDef("Procedure"),
        VertexLabelDef("Claim"),
        VertexLabelDef("ClaimLine"),
        VertexLabelDef("Denial"),
        VertexLabelDef("Coverage"),
        VertexLabelDef("Authorization"),
        VertexLabelDef("GeneticVariant"),
        VertexLabelDef("GenomicReport"),
        VertexLabelDef("Device"),
        VertexLabelDef("DeviceMetric"),
        VertexLabelDef("WearableData"),
        VertexLabelDef("CarePlan"),
        VertexLabelDef("Goal"),
        VertexLabelDef("CareTeam"),
        VertexLabelDef("Task"),
        VertexLabelDef("SDOHAssessment"),
        VertexLabelDef("DocumentReference"),
        VertexLabelDef("Consent"),
        VertexLabelDef("RiskScore"),
        VertexLabelDef("CareGap"),
        VertexLabelDef("Appointment"),
        VertexLabelDef("Communication"),
    ]
    
    EDGE_LABELS = [
        EdgeLabelDef("HAS_ENCOUNTER"),
        EdgeLabelDef("HAS_CONDITION"),
        EdgeLabelDef("HAS_OBSERVATION"),
        EdgeLabelDef("HAS_MEDICATION"),
        EdgeLabelDef("HAS_PROCEDURE"),
        EdgeLabelDef("HAS_CLAIM"),
        EdgeLabelDef("HAS_COVERAGE"),
        EdgeLabelDef("HAS_CARE_PLAN"),
        EdgeLabelDef("HAS_CARE_TEAM"),
        EdgeLabelDef("HAS_DEVICE"),
        EdgeLabelDef("HAS_VARIANT"),
        EdgeLabelDef("HAS_RISK_SCORE"),
        EdgeLabelDef("HAS_CARE_GAP"),
        EdgeLabelDef("HAS_DOCUMENT"),
        EdgeLabelDef("HAS_DIAGNOSIS"),
        EdgeLabelDef("HAS_LINE"),
        EdgeLabelDef("HAS_DENIAL"),
        EdgeLabelDef("FOR_ENCOUNTER"),
        EdgeLabelDef("AT_LOCATION"),
        EdgeLabelDef("WITH_PROVIDER"),
        EdgeLabelDef("MEMBER_OF"),
        EdgeLabelDef("PART_OF"),
        EdgeLabelDef("RELATED_TO"),
    ]


SCHEMA = AegisGraphSchema()
