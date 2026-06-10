"""
Base Model Classes for SQLAlchemy ORM.

This module provides:
- Base declarative class for all models
- Reusable mixins for common functionality
- Consistent timestamp handling
- UUID primary key support

All database models should inherit from Base and use
the appropriate mixins for their needs.

Usage:
    from db.base import Base, TimestampMixin, UUIDMixin
    
    class Patient(Base, UUIDMixin, TimestampMixin):
        __tablename__ = "patients"
        name = Column(String(100), nullable=False)
"""

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr, DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    Provides:
    - Automatic table naming from class name
    - Common utility methods
    - Type annotations support
    
    All models must inherit from this class.
    """
    
    @declared_attr.directive
    def __tablename__(cls) -> str:
        """
        Generate table name from class name.
        
        Converts CamelCase to snake_case and pluralizes.
        Example: PatientRecord -> patient_records
        """
        # Convert CamelCase to snake_case
        name = cls.__name__
        # Add underscore before uppercase letters and lowercase
        import re
        snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        # Simple pluralization (add 's')
        if not snake_case.endswith('s'):
            snake_case += 's'
        return snake_case
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Useful for serialization and debugging.
        Handles datetime and UUID conversion.
        
        Returns:
            Dictionary representation of the model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Convert special types
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, uuid.UUID):
                value = str(value)
            result[column.name] = value
        return result
    
    def __repr__(self) -> str:
        """
        Generate readable string representation.
        
        Shows class name and primary key value(s).
        """
        # Get primary key columns
        pk_cols = [col.name for col in self.__table__.primary_key.columns]
        pk_values = ", ".join(
            f"{col}={getattr(self, col, None)}"
            for col in pk_cols
        )
        return f"<{self.__class__.__name__}({pk_values})>"


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamps.
    
    - created_at: Set automatically when record is created
    - updated_at: Updated automatically on every modification
    
    Usage:
        class Patient(Base, TimestampMixin):
            __tablename__ = "patients"
            ...
    """
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when record was created"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when record was last updated"
    )


class UUIDMixin:
    """
    Mixin that adds UUID primary key.
    
    Uses PostgreSQL's UUID type with auto-generation.
    Provides consistent primary key handling across all models.
    
    Usage:
        class Patient(Base, UUIDMixin):
            __tablename__ = "patients"
            ...
    """
    
    uuid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier (UUID v4)"
    )


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.
    
    Instead of permanently deleting records, sets deleted_at timestamp.
    Queries should filter out soft-deleted records by default.
    
    Usage:
        class Patient(Base, SoftDeleteMixin):
            __tablename__ = "patients"
            ...
        
        # Soft delete
        patient.deleted_at = datetime.utcnow()
        
        # Query active records
        session.query(Patient).filter(Patient.deleted_at.is_(None))
    """
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        doc="Timestamp when record was soft-deleted (null = active)"
    )
    
    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None
    
    def soft_delete(self) -> None:
        """Mark record as deleted."""
        from datetime import datetime, timezone
        self.deleted_at = datetime.now(timezone.utc)
    
    def restore(self) -> None:
        """Restore soft-deleted record."""
        self.deleted_at = None





