"""Consent Data Models - FHIR Consent aligned"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ConsentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    REJECTED = "rejected"
    PENDING = "pending"


class ConsentScope(str, Enum):
    TREATMENT = "treatment"
    PAYMENT = "payment"
    OPERATIONS = "operations"
    RESEARCH = "research"
    MARKETING = "marketing"
    DISCLOSURE = "disclosure"
    HIE = "hie"  # Health Information Exchange


class ConsentAction(str, Enum):
    ACCESS = "access"
    COLLECT = "collect"
    USE = "use"
    DISCLOSE = "disclose"
    CORRECT = "correct"
    DELETE = "delete"


class DataCategory(str, Enum):
    GENERAL = "general"
    SENSITIVE = "sensitive"
    MENTAL_HEALTH = "mental_health"
    SUBSTANCE_ABUSE = "substance_abuse"
    HIV = "hiv"
    GENETIC = "genetic"
    REPRODUCTIVE = "reproductive"


@dataclass
class ConsentProvision:
    """A specific provision within a consent."""
    type: str  # permit or deny
    action: list[ConsentAction]
    data_categories: list[DataCategory]
    actors: list[str] = field(default_factory=list)
    purpose: list[ConsentScope] = field(default_factory=list)
    period_start: datetime | None = None
    period_end: datetime | None = None


@dataclass
class Consent:
    """Patient consent record - FHIR R4 aligned."""
    id: str
    patient_id: str
    status: ConsentStatus
    scope: ConsentScope
    provisions: list[ConsentProvision] = field(default_factory=list)
    grantor: str | None = None  # Who gave consent
    grantee: str | None = None  # Who receives consent
    source_document: str | None = None  # Reference to signed document
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    tenant_id: str | None = None


@dataclass
class ConsentDecision:
    """Result of consent check."""
    allowed: bool
    consent_id: str | None
    reason: str
    provisions_applied: list[str] = field(default_factory=list)
    restrictions: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=datetime.utcnow)
