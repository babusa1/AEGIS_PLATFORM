"""AEGIS Ontology Models - 19+ Data Sources Unified."""

# Base
from aegis_ontology.models.base import BaseVertex, BaseEdge, TenantMixin

# Clinical - Core
from aegis_ontology.models.clinical import (
    Patient, Provider, Organization, Location,
    Encounter, Diagnosis, Procedure, Observation,
    Medication, AllergyIntolerance,
)

# Financial (RCM)
from aegis_ontology.models.financial import (
    Claim, ClaimLine, Denial, Authorization, Coverage,
)

# Genomics (Oncolife)
from aegis_ontology.models.genomics import (
    MolecularSequence, GeneticVariant, GenomicReport, Specimen,
)

# Imaging
from aegis_ontology.models.imaging import (
    ImagingStudy, ImagingReport,
)

# Devices & Wearables
from aegis_ontology.models.devices import (
    Device, DeviceMetric, WearableData, DeviceAssociation,
)

# Care Planning
from aegis_ontology.models.careplan import (
    CarePlan, Goal, CareTeam, CareTeamMember,
    Task, ServiceRequest, Referral,
)

# SDOH
from aegis_ontology.models.sdoh import (
    SocialHistory, SDOHAssessment, SDOHCondition, CommunityResource,
)

# Communication & Scheduling
from aegis_ontology.models.communication import (
    Communication, Appointment, Schedule, Slot, PatientEngagement,
)

# Documents & Consent
from aegis_ontology.models.documents import (
    DocumentReference, Consent, QuestionnaireResponse, AdvanceDirective,
)

# Analytics & AI
from aegis_ontology.models.analytics import (
    RiskScore, CareGap, AIRecommendation, CohortMembership, QualityMeasure,
)

__all__ = [
    # Base
    "BaseVertex", "BaseEdge", "TenantMixin",
    # Clinical Core
    "Patient", "Provider", "Organization", "Location",
    # Clinical Events
    "Encounter", "Diagnosis", "Procedure", "Observation", "Medication", "AllergyIntolerance",
    # Financial
    "Claim", "ClaimLine", "Denial", "Authorization", "Coverage",
    # Genomics
    "MolecularSequence", "GeneticVariant", "GenomicReport", "Specimen",
    # Imaging
    "ImagingStudy", "ImagingReport",
    # Devices
    "Device", "DeviceMetric", "WearableData", "DeviceAssociation",
    # Care Planning
    "CarePlan", "Goal", "CareTeam", "CareTeamMember", "Task", "ServiceRequest", "Referral",
    # SDOH
    "SocialHistory", "SDOHAssessment", "SDOHCondition", "CommunityResource",
    # Communication
    "Communication", "Appointment", "Schedule", "Slot", "PatientEngagement",
    # Documents
    "DocumentReference", "Consent", "QuestionnaireResponse", "AdvanceDirective",
    # Analytics
    "RiskScore", "CareGap", "AIRecommendation", "CohortMembership", "QualityMeasure",
]
