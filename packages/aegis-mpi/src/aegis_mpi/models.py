"""MPI Data Models"""
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class MatchType(str, Enum):
    EXACT = "exact"
    PROBABLE = "probable"
    POSSIBLE = "possible"
    NO_MATCH = "no_match"


@dataclass
class Address:
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None


@dataclass
class PatientRecord:
    source_id: str
    source_system: str
    first_name: str
    last_name: str
    date_of_birth: date | None = None
    gender: Gender | None = None
    ssn_last4: str | None = None
    mrn: str | None = None
    phone: str | None = None
    address: Address | None = None
    tenant_id: str | None = None


@dataclass
class MatchCandidate:
    record: PatientRecord
    score: float
    match_type: MatchType
    field_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class MasterPatient:
    master_id: str
    golden_record: PatientRecord
    linked_records: list[PatientRecord] = field(default_factory=list)
