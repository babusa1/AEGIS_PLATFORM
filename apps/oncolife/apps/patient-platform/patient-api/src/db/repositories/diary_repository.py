"""
Diary Repository - Patient API
==============================

Repository for patient diary entry operations.

Usage:
    from db.repositories import DiaryRepository
    
    diary_repo = DiaryRepository(db)
    entries = diary_repo.get_by_month(patient_uuid, 2024, 1)
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import extract, and_

from .base import BaseRepository
# Use legacy model - matches actual database table
from db.patient_models import PatientDiaryEntries as DiaryEntry
from core.logging import get_logger
from core.exceptions import NotFoundError

logger = get_logger(__name__)


class DiaryRepository(BaseRepository[DiaryEntry]):
    """
    Repository for DiaryEntry model operations.
    
    Provides CRUD operations for managing patient
    diary entries with soft delete support.
    """
    
    def __init__(self, db: Session):
        """Initialize the diary repository."""
        super().__init__(DiaryEntry, db)
    
    # =========================================================================
    # Create Operations
    # =========================================================================
    
    def create_entry(
        self,
        patient_uuid: UUID,
        diary_entry: str,
        title: Optional[str] = None,
        marked_for_doctor: bool = False,
    ) -> DiaryEntry:
        """
        Create a new diary entry.
        
        Args:
            patient_uuid: The patient's UUID
            diary_entry: The diary entry text
            title: Optional title for the entry
            marked_for_doctor: Whether to flag for doctor review
            
        Returns:
            The created DiaryEntry instance
        """
        return self.create({
            "patient_uuid": patient_uuid,
            "diary_entry": diary_entry,
            "title": title,
            "marked_for_doctor": marked_for_doctor,
        })
    
    # =========================================================================
    # Read Operations
    # =========================================================================
    
    def get_by_entry_uuid(
        self,
        entry_uuid: UUID,
        include_deleted: bool = False,
    ) -> Optional[DiaryEntry]:
        """
        Get a diary entry by its UUID.
        
        Args:
            entry_uuid: The entry's UUID
            include_deleted: Whether to include soft-deleted entries
            
        Returns:
            The DiaryEntry instance, or None if not found
        """
        query = self.db.query(DiaryEntry).filter(
            DiaryEntry.entry_uuid == entry_uuid
        )
        
        if not include_deleted:
            query = query.filter(DiaryEntry.is_deleted == False)
        
        return query.first()
    
    def get_by_patient(
        self,
        patient_uuid: UUID,
        include_deleted: bool = False,
        limit: int = 100,
    ) -> List[DiaryEntry]:
        """
        Get all diary entries for a patient.
        
        Args:
            patient_uuid: The patient's UUID
            include_deleted: Whether to include soft-deleted entries
            limit: Maximum records to return
            
        Returns:
            List of DiaryEntry instances
        """
        query = self.db.query(DiaryEntry).filter(
            DiaryEntry.patient_uuid == patient_uuid
        )
        
        if not include_deleted:
            query = query.filter(DiaryEntry.is_deleted == False)
        
        return query.order_by(
            DiaryEntry.last_updated_at.desc()
        ).limit(limit).all()
    
    def get_by_month(
        self,
        patient_uuid: UUID,
        year: int,
        month: int,
        include_deleted: bool = False,
    ) -> List[DiaryEntry]:
        """
        Get diary entries for a specific month.
        
        Args:
            patient_uuid: The patient's UUID
            year: The year
            month: The month (1-12)
            include_deleted: Whether to include soft-deleted entries
            
        Returns:
            List of DiaryEntry instances
        """
        query = self.db.query(DiaryEntry).filter(
            DiaryEntry.patient_uuid == patient_uuid,
            extract('year', DiaryEntry.created_at) == year,
            extract('month', DiaryEntry.created_at) == month,
        )
        
        if not include_deleted:
            query = query.filter(DiaryEntry.is_deleted == False)
        
        return query.order_by(
            DiaryEntry.last_updated_at.desc()
        ).all()
    
    def get_for_doctor(
        self,
        patient_uuid: UUID,
        limit: int = 50,
    ) -> List[DiaryEntry]:
        """
        Get entries marked for doctor review.
        
        Args:
            patient_uuid: The patient's UUID
            limit: Maximum records to return
            
        Returns:
            List of DiaryEntry instances marked for doctor
        """
        return self.db.query(DiaryEntry).filter(
            DiaryEntry.patient_uuid == patient_uuid,
            DiaryEntry.is_deleted == False,
            DiaryEntry.marked_for_doctor == True,
        ).order_by(
            DiaryEntry.last_updated_at.desc()
        ).limit(limit).all()
    
    # =========================================================================
    # Update Operations
    # =========================================================================
    
    def update_entry(
        self,
        entry_uuid: UUID,
        patient_uuid: UUID,
        title: Optional[str] = None,
        diary_entry: Optional[str] = None,
        marked_for_doctor: Optional[bool] = None,
    ) -> DiaryEntry:
        """
        Update a diary entry.
        
        Args:
            entry_uuid: The entry's UUID
            patient_uuid: The patient's UUID (for authorization)
            title: New title (optional)
            diary_entry: New entry text (optional)
            marked_for_doctor: New flag value (optional)
            
        Returns:
            The updated DiaryEntry instance
            
        Raises:
            NotFoundError: If entry not found or access denied
        """
        entry = self.db.query(DiaryEntry).filter(
            DiaryEntry.entry_uuid == entry_uuid,
            DiaryEntry.patient_uuid == patient_uuid,
            DiaryEntry.is_deleted == False,
        ).first()
        
        if not entry:
            raise NotFoundError(
                message="Diary entry not found",
                resource_type="DiaryEntry",
                resource_id=str(entry_uuid),
            )
        
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if diary_entry is not None:
            update_data["diary_entry"] = diary_entry
        if marked_for_doctor is not None:
            update_data["marked_for_doctor"] = marked_for_doctor
        
        if update_data:
            return self.update(entry, **update_data)
        return entry
    
    # =========================================================================
    # Delete Operations
    # =========================================================================
    
    def soft_delete(
        self,
        entry_uuid: UUID,
        patient_uuid: UUID,
    ) -> bool:
        """
        Soft delete a diary entry.
        
        Args:
            entry_uuid: The entry's UUID
            patient_uuid: The patient's UUID (for authorization)
            
        Returns:
            True if deleted, False if already deleted
            
        Raises:
            NotFoundError: If entry not found or access denied
        """
        entry = self.db.query(DiaryEntry).filter(
            DiaryEntry.entry_uuid == entry_uuid,
            DiaryEntry.patient_uuid == patient_uuid,
        ).first()
        
        if not entry:
            raise NotFoundError(
                message="Diary entry not found",
                resource_type="DiaryEntry",
                resource_id=str(entry_uuid),
            )
        
        if entry.is_deleted:
            return False
        
        entry.is_deleted = True
        self.db.commit()
        return True

