"""
Clinic Models - Doctor API
==========================

This module defines SQLAlchemy models for clinic/location data.

Tables:
- all_clinics: Healthcare facility information

Usage:
    from db.models import Clinic
    
    clinic = Clinic(
        clinic_name="Main Oncology Center",
        address="123 Medical Way",
        phone_number="555-0100"
    )
"""

import uuid
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.base import DoctorBase, TimestampMixin


class Clinic(DoctorBase, TimestampMixin):
    """
    Represents a healthcare clinic or facility.
    
    This is the central location entity that staff members
    and physicians are associated with.
    
    Attributes:
        uuid: Unique identifier for the clinic
        clinic_name: Official name of the clinic
        address: Physical address
        phone_number: Contact phone number
        fax_number: Fax number for medical documents
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last modified
    """
    
    __tablename__ = 'all_clinics'
    __table_args__ = {
        'comment': 'Healthcare clinics and facilities'
    }
    
    # Primary key
    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the clinic"
    )
    
    # Clinic information
    clinic_name = Column(
        String(255),
        nullable=False,
        comment="Official name of the clinic"
    )
    address = Column(
        String(500),
        nullable=True,
        comment="Physical address of the clinic"
    )
    phone_number = Column(
        String(20),
        nullable=True,
        comment="Contact phone number"
    )
    fax_number = Column(
        String(20),
        nullable=True,
        comment="Fax number for medical documents"
    )
    
    # Relationships
    # staff_associations = relationship(
    #     "StaffAssociation",
    #     back_populates="clinic",
    #     lazy="dynamic"
    # )
    
    def __repr__(self) -> str:
        """String representation of the clinic."""
        return f"<Clinic(uuid={self.uuid}, name='{self.clinic_name}')>"
    
    def to_dict(self) -> dict:
        """
        Convert the clinic to a dictionary.
        
        Returns:
            Dictionary representation of the clinic
        """
        return {
            "uuid": str(self.uuid),
            "clinic_name": self.clinic_name,
            "address": self.address,
            "phone_number": self.phone_number,
            "fax_number": self.fax_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }





