"""
User Authentication and Profile Models.

This module defines models for:
- User: Base authentication entity
- PatientProfile: Extended patient information
- StaffProfile: Medical staff information

These models handle authentication, authorization, and user profiles.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    Base user model for authentication.
    
    Represents any user that can authenticate with the system,
    including patients and staff members.
    
    Attributes:
        uuid: Unique identifier
        email: User's email address (unique)
        hashed_password: Bcrypt-hashed password
        is_active: Whether the account is active
        is_verified: Whether email has been verified
        user_type: 'patient' or 'staff'
        last_login: Timestamp of last successful login
    """
    
    __tablename__ = "users"
    
    # Primary key
    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique user identifier"
    )
    
    # Authentication fields
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User's email address (used for login)"
    )
    hashed_password = Column(
        String(255),
        nullable=False,
        doc="Bcrypt-hashed password"
    )
    
    # Account status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the account is active"
    )
    is_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether email has been verified"
    )
    
    # User type for role-based access
    user_type = Column(
        String(20),
        nullable=False,
        default="patient",
        doc="User type: 'patient' or 'staff'"
    )
    
    # Login tracking
    last_login = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last successful login"
    )
    
    # Relationships
    patient_profile = relationship(
        "PatientProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    staff_profile = relationship(
        "StaffProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(uuid={self.uuid}, email='{self.email}', type='{self.user_type}')>"
    
    @property
    def is_patient(self) -> bool:
        """Check if user is a patient."""
        return self.user_type == "patient"
    
    @property
    def is_staff(self) -> bool:
        """Check if user is a staff member."""
        return self.user_type == "staff"


class PatientProfile(Base, TimestampMixin):
    """
    Extended profile information for patients.
    
    Contains medical and personal information specific to patients.
    Linked to User model via foreign key.
    
    Attributes:
        uuid: Unique identifier
        user_uuid: Link to User model
        first_name: Patient's first name
        last_name: Patient's last name
        date_of_birth: Patient's date of birth
        phone: Contact phone number
        diagnosis: Primary diagnosis
        treatment_status: Current treatment status
        preferences: JSON object for user preferences
    """
    
    __tablename__ = "patient_profiles"
    
    # Primary key
    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Link to User
    user_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Personal information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Medical information
    diagnosis = Column(String(255), nullable=True)
    diagnosis_date = Column(DateTime, nullable=True)
    treatment_status = Column(
        String(50),
        nullable=True,
        doc="active, completed, on_hold, etc."
    )
    primary_oncologist = Column(String(255), nullable=True)
    
    # Care team reference
    care_team_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="Reference to assigned care team"
    )
    
    # Preferences stored as JSON
    preferences = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="User preferences (notifications, display, etc.)"
    )
    
    # Relationships
    user = relationship("User", back_populates="patient_profile")
    
    @property
    def full_name(self) -> str:
        """Get patient's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or "Unknown"
    
    def __repr__(self) -> str:
        return f"<PatientProfile(uuid={self.uuid}, name='{self.full_name}')>"


class StaffProfile(Base, TimestampMixin):
    """
    Profile information for medical staff.
    
    Contains professional information for doctors, nurses,
    and other care team members.
    
    Attributes:
        uuid: Unique identifier
        user_uuid: Link to User model
        first_name: Staff member's first name
        last_name: Staff member's last name
        role: Medical role (doctor, nurse, etc.)
        department: Department assignment
        license_number: Professional license number
    """
    
    __tablename__ = "staff_profiles"
    
    # Primary key
    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Link to User
    user_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Personal information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Professional information
    role = Column(
        String(50),
        nullable=False,
        default="nurse",
        doc="Medical role: doctor, nurse, care_coordinator, admin"
    )
    department = Column(String(100), nullable=True)
    specialty = Column(String(100), nullable=True)
    license_number = Column(String(50), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="staff_profile")
    
    @property
    def full_name(self) -> str:
        """Get staff member's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or "Unknown"
    
    def __repr__(self) -> str:
        return f"<StaffProfile(uuid={self.uuid}, name='{self.full_name}', role='{self.role}')>"





