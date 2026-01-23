"""
Financial Domain Models

Models for Revenue Cycle Management (RCM):
- Claim, ClaimLine (billing)
- Denial, DenialReason (denial management)
- Authorization (prior auth)
- Coverage (insurance)

These support the RCM/Denial Management use case.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from aegis_ontology.models.base import BaseVertex


class Coverage(BaseVertex):
    """
    Insurance coverage.
    
    FHIR: Coverage
    """
    
    _label = "Coverage"
    _fhir_resource_type = "Coverage"
    _omop_table = "payer_plan_period"
    
    # Identifiers
    member_id: str = Field(..., description="Member/subscriber ID")
    group_id: str | None = Field(default=None, description="Group/employer ID")
    policy_number: str | None = None
    
    # Payer
    payer_name: str = Field(..., description="Insurance company name")
    payer_id: str | None = Field(default=None, description="Payer vertex ID")
    
    # Plan
    plan_name: str | None = None
    plan_type: Literal["HMO", "PPO", "EPO", "POS", "HDHP", "Medicare", "Medicaid", "Other"] | None = None
    
    # Coverage details
    type: Literal["primary", "secondary", "tertiary"] = "primary"
    relationship: Literal["self", "spouse", "child", "other"] = "self"
    
    # Period
    period_start: date = Field(..., description="Coverage start date")
    period_end: date | None = Field(default=None, description="Coverage end date")
    
    # Status
    status: Literal["active", "cancelled", "draft", "entered-in-error"] = "active"
    
    # Relationships
    patient_id: str = Field(..., description="Patient/beneficiary vertex ID")
    subscriber_id: str | None = Field(default=None, description="Subscriber if different")
    
    @property
    def is_active(self) -> bool:
        if self.status != "active":
            return False
        today = date.today()
        if self.period_end and today > self.period_end:
            return False
        return today >= self.period_start


class Claim(BaseVertex):
    """
    Healthcare claim.
    
    FHIR: Claim
    """
    
    _label = "Claim"
    _fhir_resource_type = "Claim"
    _omop_table = None  # Custom
    
    # Identifiers
    claim_number: str = Field(..., description="Claim/ICN number")
    patient_control_number: str | None = Field(default=None, description="PCN")
    
    # Type
    type: Literal["institutional", "professional", "pharmacy", "dental", "vision"] = Field(
        ..., description="Claim type"
    )
    use: Literal["claim", "preauthorization", "predetermination"] = "claim"
    
    # Facility (for institutional)
    bill_type: str | None = Field(default=None, description="3-digit bill type (e.g., 111)")
    facility_type: str | None = None
    
    # Amounts
    total_charge: Decimal = Field(..., description="Total billed amount")
    total_allowed: Decimal | None = Field(default=None, description="Allowed amount")
    total_paid: Decimal | None = Field(default=None, description="Paid amount")
    patient_responsibility: Decimal | None = Field(default=None, description="Patient owes")
    
    # Status
    status: Literal[
        "active", "cancelled", "draft", "entered-in-error"
    ] = "active"
    outcome: Literal[
        "queued", "complete", "error", "partial"
    ] | None = None
    
    # Dates
    service_date_start: date = Field(..., description="Service from date")
    service_date_end: date | None = Field(default=None, description="Service to date")
    created_date: datetime = Field(..., description="Claim creation date")
    submitted_date: datetime | None = None
    adjudicated_date: datetime | None = None
    
    # DRG (for inpatient)
    drg_code: str | None = Field(default=None, description="MS-DRG code")
    drg_description: str | None = None
    drg_weight: Decimal | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = Field(default=None, description="Encounter vertex ID")
    coverage_id: str | None = Field(default=None, description="Coverage vertex ID")
    billing_provider_id: str | None = None
    attending_provider_id: str | None = None
    facility_id: str | None = None
    
    @property
    def is_denied(self) -> bool:
        # A claim is denied if paid is 0 and it was adjudicated
        if self.adjudicated_date and self.total_paid == 0:
            return True
        return False
    
    @property
    def denial_rate(self) -> float | None:
        if self.total_charge and self.total_paid is not None:
            return 1 - (float(self.total_paid) / float(self.total_charge))
        return None


class ClaimLine(BaseVertex):
    """
    Individual line item on a claim.
    
    FHIR: Claim.item
    """
    
    _label = "ClaimLine"
    _fhir_resource_type = "Claim"
    _omop_table = None
    
    # Line info
    line_number: int = Field(..., description="Line sequence number")
    
    # Service
    procedure_code: str = Field(..., description="CPT/HCPCS code")
    procedure_description: str | None = None
    modifier_codes: list[str] | None = Field(default=None, description="CPT modifiers")
    
    # Revenue code (institutional)
    revenue_code: str | None = Field(default=None, description="Revenue code (e.g., 0450)")
    
    # Diagnosis pointers
    diagnosis_pointers: list[int] | None = Field(
        default=None, description="Links to claim diagnoses (1-12)"
    )
    
    # Quantity/Units
    quantity: Decimal = Field(default=Decimal("1"), description="Service units")
    unit_type: str | None = Field(default=None, description="UN, MJ, etc.")
    
    # Amounts
    charge_amount: Decimal = Field(..., description="Line charge")
    allowed_amount: Decimal | None = None
    paid_amount: Decimal | None = None
    
    # Place of service
    place_of_service: str | None = Field(default=None, description="POS code (e.g., 11)")
    
    # Service dates
    service_date: date = Field(..., description="Date of service")
    
    # Relationships
    claim_id: str = Field(..., description="Parent claim vertex ID")
    rendering_provider_id: str | None = None


class Denial(BaseVertex):
    """
    Claim denial with reason codes.
    
    Critical for RCM denial management use case.
    """
    
    _label = "Denial"
    _fhir_resource_type = None  # Custom
    _omop_table = None
    
    # Denial info
    denial_code: str = Field(..., description="CARC/RARC code")
    denial_reason: str = Field(..., description="Denial reason description")
    
    # Code classification
    code_type: Literal["CARC", "RARC", "proprietary"] = Field(
        ..., description="Code type: CARC=Claim Adjustment, RARC=Remittance Advice"
    )
    
    # Category (for analytics)
    denial_category: Literal[
        "eligibility",
        "authorization",
        "medical_necessity",
        "coding",
        "timely_filing",
        "duplicate",
        "bundling",
        "documentation",
        "contractual",
        "other"
    ] = Field(..., description="Denial category for grouping")
    
    # Amounts
    denied_amount: Decimal = Field(..., description="Amount denied")
    
    # Dates
    denial_date: datetime = Field(..., description="When denial was received")
    
    # Appeal info
    is_appealable: bool = Field(default=True, description="Can be appealed")
    appeal_deadline: date | None = Field(default=None, description="Appeal by date")
    
    # Status
    status: Literal[
        "new", "in_review", "appealing", "overturned", 
        "upheld", "written_off", "resolved"
    ] = "new"
    
    # Resolution
    resolution_date: datetime | None = None
    resolution_type: Literal[
        "overturned", "partially_overturned", "upheld", "written_off"
    ] | None = None
    recovered_amount: Decimal | None = None
    
    # Relationships
    claim_id: str = Field(..., description="Claim vertex ID")
    claim_line_id: str | None = Field(default=None, description="Specific line if line-level")
    
    # AI/Agent fields
    ai_appeal_recommendation: str | None = Field(
        default=None, description="AI-generated appeal strategy"
    )
    ai_success_probability: float | None = Field(
        default=None, description="AI-predicted overturn probability"
    )
    
    @property
    def is_open(self) -> bool:
        return self.status in ("new", "in_review", "appealing")
    
    @property
    def days_to_deadline(self) -> int | None:
        if self.appeal_deadline:
            return (self.appeal_deadline - date.today()).days
        return None


class Authorization(BaseVertex):
    """
    Prior authorization.
    
    FHIR: Claim (use=preauthorization)
    """
    
    _label = "Authorization"
    _fhir_resource_type = "Claim"
    _omop_table = None
    
    # Identifiers
    auth_number: str = Field(..., description="Authorization number")
    reference_number: str | None = Field(default=None, description="Payer reference")
    
    # Type
    type: Literal["prior_auth", "concurrent_review", "retrospective"] = "prior_auth"
    
    # Service being authorized
    service_type: str = Field(..., description="Service type")
    procedure_codes: list[str] | None = Field(default=None, description="CPT/HCPCS codes")
    diagnosis_codes: list[str] | None = Field(default=None, description="ICD-10 codes")
    
    # Quantity
    units_requested: int | None = None
    units_approved: int | None = None
    
    # Dates
    requested_date: datetime = Field(..., description="When auth was requested")
    decision_date: datetime | None = None
    effective_start: date | None = Field(default=None, description="Auth valid from")
    effective_end: date | None = Field(default=None, description="Auth valid to")
    
    # Status
    status: Literal[
        "pending", "approved", "denied", "partial",
        "cancelled", "expired"
    ] = "pending"
    
    # Decision
    decision_reason: str | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    coverage_id: str | None = Field(default=None, description="Coverage vertex ID")
    requesting_provider_id: str | None = None
    facility_id: str | None = None
    
    @property
    def is_valid(self) -> bool:
        if self.status != "approved":
            return False
        today = date.today()
        if self.effective_end and today > self.effective_end:
            return False
        if self.effective_start and today < self.effective_start:
            return False
        return True


# ==================== EDGE TYPES FOR FINANCIAL ====================
# Note: Edge types are defined in base.py, but we document them here

"""
Financial Relationships:
- Patient --HAS_COVERAGE--> Coverage
- Encounter --HAS_CLAIM--> Claim
- Claim --HAS_LINE--> ClaimLine
- Claim --HAS_DENIAL--> Denial
- ClaimLine --HAS_DENIAL--> Denial (line-level denials)
- Patient --HAS_AUTHORIZATION--> Authorization
- Authorization --FOR_SERVICE--> Procedure
"""
