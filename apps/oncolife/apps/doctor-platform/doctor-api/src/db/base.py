"""
Base Model Classes - Doctor API
===============================

This module defines base classes and mixins for SQLAlchemy models:
- DoctorBase: Declarative base for doctor database models
- PatientBase: Declarative base for patient database models (read-only)
- TimestampMixin: Adds created_at/updated_at fields

Usage:
    from db.base import DoctorBase, TimestampMixin
    
    class StaffProfile(DoctorBase, TimestampMixin):
        __tablename__ = 'staff_profiles'
        id = Column(Integer, primary_key=True)
        ...
"""

from datetime import datetime
from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import declarative_base, declared_attr


# =============================================================================
# Declarative Bases
# =============================================================================

# Base class for doctor database models
DoctorBase = declarative_base()

# Base class for patient database models (used for read-only access)
PatientBase = declarative_base()


# =============================================================================
# Mixins
# =============================================================================

class TimestampMixin:
    """
    Mixin that adds automatic timestamp fields to models.
    
    Provides:
    - created_at: Set automatically when record is created
    - updated_at: Updated automatically when record is modified
    
    Usage:
        class MyModel(Base, TimestampMixin):
            __tablename__ = 'my_table'
            id = Column(Integer, primary_key=True)
    """
    
    @declared_attr
    def created_at(cls):
        """Timestamp when the record was created."""
        return Column(
            DateTime,
            server_default=func.now(),
            nullable=False,
            comment="Timestamp when record was created"
        )
    
    @declared_attr
    def updated_at(cls):
        """Timestamp when the record was last updated."""
        return Column(
            DateTime,
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
            comment="Timestamp when record was last updated"
        )


class SoftDeleteMixin:
    """
    Mixin that adds soft delete capability to models.
    
    Instead of physically deleting records, marks them as deleted.
    This preserves data for auditing and recovery purposes.
    
    Usage:
        class MyModel(Base, SoftDeleteMixin):
            __tablename__ = 'my_table'
            id = Column(Integer, primary_key=True)
    """
    
    @declared_attr
    def is_deleted(cls):
        """Flag indicating if record is soft-deleted."""
        return Column(
            "is_deleted",
            DateTime,
            nullable=True,
            default=None,
            comment="Timestamp when record was soft-deleted, NULL if active"
        )
    
    def soft_delete(self) -> None:
        """Mark this record as deleted."""
        self.is_deleted = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.is_deleted = None
    
    @property
    def is_active(self) -> bool:
        """Check if the record is active (not deleted)."""
        return self.is_deleted is None





