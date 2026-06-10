"""
Chemo Repository - Patient API
==============================

Repository for chemotherapy date operations.

Usage:
    from db.repositories import ChemoRepository
    
    chemo_repo = ChemoRepository(db)
    chemo_repo.log_chemo_date(patient_uuid, chemo_date)
"""

from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import extract
import pytz

from .base import BaseRepository
# Use legacy model - matches actual database table
from db.patient_models import PatientChemoDates as ChemoDate
from core.logging import get_logger

logger = get_logger(__name__)


class ChemoRepository(BaseRepository[ChemoDate]):
    """
    Repository for ChemoDate model operations.
    
    Provides CRUD operations for managing patient
    chemotherapy treatment dates.
    """
    
    def __init__(self, db: Session):
        """Initialize the chemo repository."""
        super().__init__(ChemoDate, db)
    
    def log_chemo_date(
        self,
        patient_uuid: UUID,
        chemo_date: date,
    ) -> ChemoDate:
        """
        Log a new chemotherapy date for a patient.
        
        Args:
            patient_uuid: The patient's UUID
            chemo_date: The date of chemotherapy
            
        Returns:
            The created ChemoDate instance
        """
        utc_now = datetime.utcnow()
        if utc_now.tzinfo is None:
            utc_now = pytz.UTC.localize(utc_now)
        
        return self.create(
            patient_uuid=patient_uuid,
            chemo_date=chemo_date,
            created_at=utc_now,
        )
    
    def get_by_patient(
        self,
        patient_uuid: UUID,
        limit: int = 100,
    ) -> List[ChemoDate]:
        """
        Get all chemo dates for a patient.
        
        Args:
            patient_uuid: The patient's UUID
            limit: Maximum records to return
            
        Returns:
            List of ChemoDate instances
        """
        return self.db.query(ChemoDate).filter(
            ChemoDate.patient_uuid == patient_uuid
        ).order_by(ChemoDate.chemo_date.desc()).limit(limit).all()
    
    def get_by_month(
        self,
        patient_uuid: UUID,
        year: int,
        month: int,
    ) -> List[ChemoDate]:
        """
        Get chemo dates for a specific month.
        
        Args:
            patient_uuid: The patient's UUID
            year: The year
            month: The month (1-12)
            
        Returns:
            List of ChemoDate instances
        """
        return self.db.query(ChemoDate).filter(
            ChemoDate.patient_uuid == patient_uuid,
            extract('year', ChemoDate.chemo_date) == year,
            extract('month', ChemoDate.chemo_date) == month,
        ).order_by(ChemoDate.chemo_date).all()
    
    def get_upcoming(
        self,
        patient_uuid: UUID,
        from_date: Optional[date] = None,
        limit: int = 10,
    ) -> List[ChemoDate]:
        """
        Get upcoming chemo dates.
        
        Args:
            patient_uuid: The patient's UUID
            from_date: Start date (defaults to today)
            limit: Maximum records to return
            
        Returns:
            List of upcoming ChemoDate instances
        """
        if from_date is None:
            from_date = date.today()
        
        return self.db.query(ChemoDate).filter(
            ChemoDate.patient_uuid == patient_uuid,
            ChemoDate.chemo_date >= from_date,
        ).order_by(ChemoDate.chemo_date).limit(limit).all()
    
    def delete_by_date(
        self,
        patient_uuid: UUID,
        chemo_date: date,
    ) -> bool:
        """
        Delete a chemo date entry.
        
        Args:
            patient_uuid: The patient's UUID
            chemo_date: The date to delete
            
        Returns:
            True if deleted, False if not found
        """
        entry = self.db.query(ChemoDate).filter(
            ChemoDate.patient_uuid == patient_uuid,
            ChemoDate.chemo_date == chemo_date,
        ).first()
        
        if entry:
            return self.delete(entry)
        return False

