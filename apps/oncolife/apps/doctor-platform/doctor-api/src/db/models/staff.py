"""
Staff Models - Doctor API
=========================

This module defines SQLAlchemy models for staff/personnel data.

Tables:
- staff_profiles: Healthcare staff member information
- staff_associations: Links between staff, physicians, and clinics

Staff Roles:
- physician: Treating physician (can have patients assigned)
- staff: General staff member (assists physicians)
- admin: Administrative user with elevated permissions

Usage:
    from db.models import StaffProfile, StaffAssociation
    
    physician = StaffProfile(
        email_address="doctor@clinic.com",
        first_name="Jane",
        last_name="Smith",
        role="physician",
        npi_number="1234567890"
    )
"""

import uuid
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.base import DoctorBase, TimestampMixin


class StaffProfile(DoctorBase, TimestampMixin):
    """
    Represents a staff member's profile.
    
    Staff members can be physicians, general staff, or administrators.
    Each staff member has a unique email address and UUID.
    
    Attributes:
        id: Auto-increment ID (internal use)
        staff_uuid: Unique identifier for external use
        email_address: Unique email address (login identifier)
        first_name: Staff member's first name
        last_name: Staff member's last name
        role: Role type (physician, staff, admin)
        npi_number: National Provider Identifier (physicians only)
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last modified
    """
    
    __tablename__ = 'staff_profiles'
    __table_args__ = (
        Index('ix_staff_profiles_email', 'email_address'),
        Index('ix_staff_profiles_role', 'role'),
        {'comment': 'Healthcare staff member profiles'}
    )
    
    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Auto-increment internal ID"
    )
    
    # Unique identifiers
    staff_uuid = Column(
        UUID(as_uuid=True),
        unique=True,
        default=uuid.uuid4,
        nullable=False,
        comment="Unique identifier for external use"
    )
    email_address = Column(
        String(255),
        unique=True,
        nullable=False,
        comment="Unique email address (login identifier)"
    )
    
    # Personal information
    first_name = Column(
        String(100),
        nullable=True,
        comment="Staff member's first name"
    )
    last_name = Column(
        String(100),
        nullable=True,
        comment="Staff member's last name"
    )
    
    # Role and credentials
    role = Column(
        String(50),
        nullable=False,
        default='staff',
        comment="Role type: physician, staff, or admin"
    )
    npi_number = Column(
        String(20),
        nullable=True,
        comment="National Provider Identifier (physicians only)"
    )
    
    # Relationships
    # associations = relationship(
    #     "StaffAssociation",
    #     foreign_keys="StaffAssociation.staff_uuid",
    #     back_populates="staff",
    #     lazy="dynamic"
    # )
    
    def __repr__(self) -> str:
        """String representation of the staff profile."""
        return (
            f"<StaffProfile(uuid={self.staff_uuid}, "
            f"email='{self.email_address}', role='{self.role}')>"
        )
    
    @property
    def full_name(self) -> str:
        """Get the full name of the staff member."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or "Unknown"
    
    @property
    def is_physician(self) -> bool:
        """Check if this staff member is a physician."""
        return self.role == 'physician'
    
    @property
    def is_admin(self) -> bool:
        """Check if this staff member is an admin."""
        return self.role == 'admin'
    
    def to_dict(self) -> dict:
        """
        Convert the staff profile to a dictionary.
        
        Returns:
            Dictionary representation of the staff profile
        """
        return {
            "staff_uuid": str(self.staff_uuid),
            "email_address": self.email_address,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "role": self.role,
            "npi_number": self.npi_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class StaffAssociation(DoctorBase, TimestampMixin):
    """
    Represents the association between staff, physicians, and clinics.
    
    This is a junction table that links:
    - Staff members to the physicians they work with
    - Both staff and physicians to their clinic
    
    For physicians, staff_uuid == physician_uuid (self-association).
    For staff members, they are linked to one or more physicians.
    
    Attributes:
        id: Auto-increment ID (internal use)
        staff_uuid: The staff member being associated
        physician_uuid: The physician the staff works with
        clinic_uuid: The clinic where this association applies
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last modified
    """
    
    __tablename__ = 'staff_associations'
    __table_args__ = (
        Index('ix_staff_assoc_staff', 'staff_uuid'),
        Index('ix_staff_assoc_physician', 'physician_uuid'),
        Index('ix_staff_assoc_clinic', 'clinic_uuid'),
        {'comment': 'Links staff members to physicians and clinics'}
    )
    
    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Auto-increment internal ID"
    )
    
    # Foreign keys (UUIDs)
    staff_uuid = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of the staff member"
    )
    physician_uuid = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of the associated physician"
    )
    clinic_uuid = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of the clinic"
    )
    
    # Relationships
    # staff = relationship(
    #     "StaffProfile",
    #     foreign_keys=[staff_uuid],
    #     back_populates="associations"
    # )
    # clinic = relationship(
    #     "Clinic",
    #     back_populates="staff_associations"
    # )
    
    def __repr__(self) -> str:
        """String representation of the association."""
        return (
            f"<StaffAssociation(staff={self.staff_uuid}, "
            f"physician={self.physician_uuid}, clinic={self.clinic_uuid})>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert the association to a dictionary.
        
        Returns:
            Dictionary representation of the association
        """
        return {
            "id": self.id,
            "staff_uuid": str(self.staff_uuid),
            "physician_uuid": str(self.physician_uuid),
            "clinic_uuid": str(self.clinic_uuid),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }





