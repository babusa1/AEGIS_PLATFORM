"""
Financial Domain Models

Pydantic models for Claim, Denial, Appeal, Payment, Payer, Coverage.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from aegis.models.core import BaseEntity


class Payer(BaseEntity):
    """
    Payer entity.
    
    Represents an insurance payer organization.
    """
    
    payer_id: str = Field(..., description="Payer identifier")
    name: str = Field(..., description="Payer name")
    type: Literal["commercial", "medicare", "medicaid", "tricare", "self-pay", "workers-comp"] = Field(
        ..., description="Payer type"
    )
    
    # Contact
    phone_number: str | None = None
    portal_url: str | None = Field(default=None, description="Provider portal URL")


class Coverage(BaseEntity):
    """
    Coverage entity.
    
    Represents patient insurance coverage.
    Maps to FHIR Coverage resource.
    """
    
    # Identifiers
    member_id: str = Field(..., description="Member ID on insurance card")
    group_number: str | None = Field(default=None, description="Group number")
    
    # Classification
    type: Literal["primary", "secondary", "tertiary"] = Field(
        default="primary", description="Coverage order"
    )
    
    # Dates
    effective_date: date = Field(..., description="Coverage start date")
    termination_date: date | None = Field(default=None, description="Coverage end date")
    
    # Relationships
    patient_id: str = Field(..., description="Patient ID")
    payer_id: str = Field(..., description="Payer ID")
    
    @property
    def is_active(self) -> bool:
        """Check if coverage is currently active."""
        today = date.today()
        if self.termination_date:
            return self.effective_date <= today <= self.termination_date
        return self.effective_date <= today


class ClaimLine(BaseEntity):
    """
    Claim Line entity.
    
    Represents an individual service line on a claim.
    """
    
    line_number: int = Field(..., description="Line number on claim")
    
    # Coding
    cpt_code: str | None = Field(default=None, description="CPT code")
    hcpcs_code: str | None = Field(default=None, description="HCPCS code")
    revenue_code: str | None = Field(default=None, description="Revenue code (UB-04)")
    modifier: str | None = Field(default=None, description="Procedure modifiers")
    
    # Service
    service_date: date = Field(..., description="Date of service")
    units: int = Field(default=1, description="Service units")
    description: str | None = Field(default=None, description="Service description")
    
    # Amounts
    billed_amount: Decimal = Field(..., description="Billed charge")
    allowed_amount: Decimal | None = Field(default=None, description="Allowed amount")
    paid_amount: Decimal | None = Field(default=None, description="Paid amount")
    
    # Relationships
    claim_id: str = Field(..., description="Parent claim ID")


class Claim(BaseEntity):
    """
    Claim entity.
    
    Represents a healthcare claim (professional or institutional).
    Maps to FHIR Claim resource.
    """
    
    # Identifiers
    claim_number: str = Field(..., description="Claim number")
    
    # Classification
    type: Literal["professional", "institutional", "dental", "pharmacy"] = Field(
        ..., description="Claim type"
    )
    status: Literal["draft", "submitted", "pending", "paid", "denied", "appealed", "adjusted"] = Field(
        default="submitted", description="Claim status"
    )
    
    # Dates
    service_date_start: date = Field(..., description="First date of service")
    service_date_end: date | None = Field(default=None, description="Last date of service")
    submission_date: date | None = Field(default=None, description="Submission date")
    
    # Amounts
    billed_amount: Decimal = Field(..., description="Total billed amount")
    allowed_amount: Decimal | None = Field(default=None, description="Total allowed amount")
    paid_amount: Decimal | None = Field(default=None, description="Total paid amount")
    patient_responsibility: Decimal | None = Field(default=None, description="Patient owes")
    
    # Diagnosis codes (for claim-level)
    primary_diagnosis: str | None = Field(default=None, description="Primary ICD-10")
    secondary_diagnoses: list[str] = Field(default_factory=list, description="Secondary ICD-10 codes")
    
    # Relationships
    patient_id: str = Field(..., description="Patient ID")
    encounter_id: str | None = Field(default=None, description="Associated encounter")
    payer_id: str = Field(..., description="Submitted to payer")
    provider_id: str | None = Field(default=None, description="Billing provider")
    
    # Nested
    lines: list[ClaimLine] = Field(default_factory=list, description="Claim lines")
    
    @property
    def is_denied(self) -> bool:
        """Check if claim is denied."""
        return self.status == "denied"
    
    @property
    def denial_amount(self) -> Decimal:
        """Calculate denied amount."""
        if self.paid_amount is not None:
            return self.billed_amount - self.paid_amount
        return Decimal("0")


class Denial(BaseEntity):
    """
    Denial entity.
    
    Represents a claim denial from a payer.
    """
    
    # Reason
    reason_code: str = Field(..., description="CARC/RARC code (e.g., CO-4, PR-204)")
    category: Literal[
        "medical_necessity", 
        "authorization", 
        "coding", 
        "eligibility", 
        "duplicate",
        "timely_filing",
        "bundling",
        "other"
    ] = Field(..., description="Denial category")
    description: str = Field(..., description="Denial description")
    
    # Amounts
    denied_amount: Decimal = Field(..., description="Denied amount")
    
    # Dates
    denial_date: date = Field(..., description="Date denial received")
    appeal_deadline: date | None = Field(default=None, description="Deadline to appeal")
    
    # Relationships
    claim_id: str = Field(..., description="Denied claim ID")
    payer_id: str = Field(..., description="Denying payer")
    
    @property
    def days_until_deadline(self) -> int | None:
        """Calculate days until appeal deadline."""
        if self.appeal_deadline:
            delta = self.appeal_deadline - date.today()
            return delta.days
        return None
    
    @property
    def is_past_deadline(self) -> bool:
        """Check if appeal deadline has passed."""
        if self.appeal_deadline:
            return date.today() > self.appeal_deadline
        return False


class Appeal(BaseEntity):
    """
    Appeal entity.
    
    Represents an appeal against a denial.
    """
    
    # Identifiers
    appeal_number: str | None = Field(default=None, description="Appeal reference number")
    
    # Classification
    level: Literal["first_level", "second_level", "external_review", "administrative"] = Field(
        default="first_level", description="Appeal level"
    )
    status: Literal["draft", "pending_approval", "submitted", "pending", "won", "lost", "withdrawn"] = Field(
        default="draft", description="Appeal status"
    )
    
    # Dates
    created_date: date = Field(..., description="Date appeal created")
    submission_date: date | None = Field(default=None, description="Date submitted to payer")
    resolution_date: date | None = Field(default=None, description="Date resolved")
    
    # Outcome
    outcome: str | None = Field(default=None, description="Outcome description")
    recovered_amount: Decimal | None = Field(default=None, description="Amount recovered")
    
    # Content
    letter_content: str | None = Field(default=None, description="Appeal letter text")
    evidence_summary: str | None = Field(default=None, description="Summary of evidence")
    
    # AI metadata
    confidence_score: float | None = Field(default=None, description="AI confidence score")
    ai_generated: bool = Field(default=False, description="Whether AI-generated")
    
    # Relationships
    denial_id: str = Field(..., description="Appealed denial ID")
    claim_id: str = Field(..., description="Original claim ID")
    created_by: str | None = Field(default=None, description="User who created")
    approved_by: str | None = Field(default=None, description="User who approved")
    
    @property
    def is_successful(self) -> bool:
        """Check if appeal was successful."""
        return self.status == "won"
    
    @property
    def is_pending(self) -> bool:
        """Check if appeal is still pending."""
        return self.status in ("submitted", "pending")


class Payment(BaseEntity):
    """
    Payment entity.
    
    Represents a payment from payer to provider.
    """
    
    # Amount
    amount: Decimal = Field(..., description="Payment amount")
    
    # Dates
    payment_date: date = Field(..., description="Payment date")
    
    # Reference
    check_number: str | None = Field(default=None, description="Check/EFT number")
    trace_number: str | None = Field(default=None, description="835 trace number")
    
    # Adjustments
    adjustment_codes: list[str] = Field(default_factory=list, description="Adjustment reason codes")
    adjustment_amount: Decimal | None = Field(default=None, description="Total adjustments")
    
    # Relationships
    claim_id: str = Field(..., description="Paid claim ID")
    payer_id: str = Field(..., description="Paying payer")


class Authorization(BaseEntity):
    """
    Authorization entity.
    
    Represents a prior authorization for a service.
    """
    
    # Identifiers
    authorization_number: str = Field(..., description="Auth number from payer")
    
    # Status
    status: Literal["requested", "approved", "denied", "expired", "cancelled"] = Field(
        default="requested", description="Authorization status"
    )
    
    # Service
    service_code: str | None = Field(default=None, description="Authorized service code")
    service_description: str | None = Field(default=None, description="Service description")
    authorized_units: int | None = Field(default=None, description="Authorized units")
    
    # Dates
    request_date: date = Field(..., description="Date requested")
    decision_date: date | None = Field(default=None, description="Date of decision")
    effective_date: date | None = Field(default=None, description="Auth effective date")
    expiry_date: date | None = Field(default=None, description="Auth expiration date")
    
    # Relationships
    patient_id: str = Field(..., description="Patient ID")
    payer_id: str = Field(..., description="Payer ID")
    provider_id: str | None = Field(default=None, description="Requesting provider")
    
    @property
    def is_valid(self) -> bool:
        """Check if authorization is currently valid."""
        if self.status != "approved":
            return False
        today = date.today()
        if self.effective_date and today < self.effective_date:
            return False
        if self.expiry_date and today > self.expiry_date:
            return False
        return True
