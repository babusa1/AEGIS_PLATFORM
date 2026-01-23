"""
Core Domain Models

Pydantic models for Patient, Provider, Organization, Location.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class BaseEntity(BaseModel):
    """Base class for all graph entities."""
    
    id: str | None = Field(default=None, description="Graph vertex ID")
    tenant_id: str = Field(default="default", description="Multi-tenant isolation ID")
    source_system: str | None = Field(default=None, description="Origin system (Epic, Cerner, etc.)")
    source_id: str | None = Field(default=None, description="ID in source system")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class Address(BaseModel):
    """Address component."""
    
    line: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = "US"


class Patient(BaseEntity):
    """
    Patient entity.
    
    Represents a person receiving healthcare services.
    Maps to FHIR Patient resource.
    """
    
    # Identifiers
    mrn: str = Field(..., description="Medical Record Number")
    ssn: str | None = Field(default=None, description="Social Security Number (encrypted)")
    
    # Demographics
    given_name: str = Field(..., description="First/given name")
    family_name: str = Field(..., description="Last/family name")
    birth_date: date = Field(..., description="Date of birth")
    gender: Literal["male", "female", "other", "unknown"] = Field(..., description="Administrative gender")
    
    # Contact
    phone_number: str | None = Field(default=None, description="Primary phone")
    email: str | None = Field(default=None, description="Email address")
    address: Address | None = Field(default=None, description="Home address")
    
    # Relationships (vertex IDs)
    primary_provider_id: str | None = Field(default=None, description="Primary care provider")
    
    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.given_name} {self.family_name}"
    
    @property
    def age(self) -> int:
        """Calculate current age."""
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )


class Provider(BaseEntity):
    """
    Provider entity.
    
    Represents a healthcare provider (physician, nurse, etc.).
    Maps to FHIR Practitioner resource.
    """
    
    # Identifiers
    npi: str = Field(..., description="National Provider Identifier")
    
    # Demographics
    given_name: str = Field(..., description="First name")
    family_name: str = Field(..., description="Last name")
    
    # Professional
    specialty: str | None = Field(default=None, description="Medical specialty")
    credentials: str | None = Field(default=None, description="Credentials (MD, DO, NP, etc.)")
    
    # Contact
    phone_number: str | None = None
    email: str | None = None
    
    # Relationships
    organization_id: str | None = Field(default=None, description="Affiliated organization")
    
    @property
    def display_name(self) -> str:
        """Get display name with credentials."""
        name = f"{self.given_name} {self.family_name}"
        if self.credentials:
            name += f", {self.credentials}"
        return name


class Organization(BaseEntity):
    """
    Organization entity.
    
    Represents a healthcare organization (hospital, clinic, etc.).
    Maps to FHIR Organization resource.
    """
    
    name: str = Field(..., description="Organization name")
    type: Literal["hospital", "clinic", "payer", "pharmacy", "lab", "other"] = Field(
        ..., description="Organization type"
    )
    tax_id: str | None = Field(default=None, description="Tax ID / EIN")
    
    # Contact
    phone_number: str | None = None
    address: Address | None = None
    
    # Relationships
    parent_organization_id: str | None = Field(default=None, description="Parent organization")


class Location(BaseEntity):
    """
    Location entity.
    
    Represents a physical location (facility, unit, room, bed).
    Maps to FHIR Location resource.
    """
    
    name: str = Field(..., description="Location name")
    type: Literal["facility", "building", "floor", "unit", "room", "bed"] = Field(
        ..., description="Location type"
    )
    
    # Status (for beds)
    status: Literal["available", "occupied", "cleaning", "blocked"] | None = Field(
        default=None, description="Current status"
    )
    
    # Hierarchy
    parent_location_id: str | None = Field(default=None, description="Parent location")
    organization_id: str | None = Field(default=None, description="Owning organization")
    
    # Physical
    address: Address | None = None
