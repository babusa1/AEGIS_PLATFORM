"""
Chemo Service - Patient API
============================

Service for chemotherapy date management.

Usage:
    from services import ChemoService
    
    chemo_service = ChemoService(db)
    result = chemo_service.log_chemo_date(patient_uuid, chemo_date)
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import date, datetime
import pytz

from sqlalchemy.orm import Session

from db.repositories import ChemoRepository
from core.logging import get_logger
from core.exceptions import ValidationError

logger = get_logger(__name__)


class ChemoService:
    """
    Service for chemotherapy date operations.
    
    Provides:
    - Log chemotherapy treatment dates
    - Retrieve chemo history
    - Get upcoming treatments
    """
    
    def __init__(self, db: Session):
        """
        Initialize the chemo service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.chemo_repo = ChemoRepository(db)
    
    def log_chemo_date(
        self,
        patient_uuid: UUID,
        chemo_date: date,
        timezone: str = "America/Los_Angeles",
    ) -> Dict[str, Any]:
        """
        Log a new chemotherapy date.
        
        Args:
            patient_uuid: The patient's UUID
            chemo_date: The date of chemotherapy
            timezone: User's timezone for logging
            
        Returns:
            Success response with chemo date info
        """
        logger.info(
            f"Log chemo date: patient={patient_uuid} "
            f"date={chemo_date} tz={timezone}"
        )
        
        try:
            entry = self.chemo_repo.log_chemo_date(
                patient_uuid=patient_uuid,
                chemo_date=chemo_date,
            )
            
            logger.info(f"Chemo date logged: id={entry.id}")
            
            return {
                "success": True,
                "message": "Chemotherapy date successfully logged.",
                "chemo_date": chemo_date,
                "id": entry.id,
            }
            
        except Exception as e:
            logger.error(f"Failed to log chemo date: {e}")
            raise
    
    def get_chemo_history(
        self,
        patient_uuid: UUID,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get chemotherapy history for a patient.
        
        Args:
            patient_uuid: The patient's UUID
            limit: Maximum records to return
            
        Returns:
            List of chemo date records
        """
        logger.info(f"Get chemo history: patient={patient_uuid}")
        
        entries = self.chemo_repo.get_by_patient(patient_uuid, limit)
        
        return [
            {
                "id": entry.id,
                "chemo_date": entry.chemo_date,
                "created_at": entry.created_at,
            }
            for entry in entries
        ]
    
    def get_chemo_by_month(
        self,
        patient_uuid: UUID,
        year: int,
        month: int,
    ) -> List[Dict[str, Any]]:
        """
        Get chemo dates for a specific month.
        
        Args:
            patient_uuid: The patient's UUID
            year: The year
            month: The month (1-12)
            
        Returns:
            List of chemo date records
        """
        if month < 1 or month > 12:
            raise ValidationError(
                message="Month must be between 1 and 12",
                field="month",
            )
        
        logger.info(f"Get chemo by month: patient={patient_uuid} {year}/{month}")
        
        entries = self.chemo_repo.get_by_month(patient_uuid, year, month)
        
        return [
            {
                "id": entry.id,
                "chemo_date": entry.chemo_date,
                "created_at": entry.created_at,
            }
            for entry in entries
        ]
    
    def get_upcoming_chemo(
        self,
        patient_uuid: UUID,
        from_date: Optional[date] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming chemotherapy dates.
        
        Args:
            patient_uuid: The patient's UUID
            from_date: Start date (defaults to today)
            limit: Maximum records to return
            
        Returns:
            List of upcoming chemo date records
        """
        logger.info(f"Get upcoming chemo: patient={patient_uuid}")
        
        entries = self.chemo_repo.get_upcoming(patient_uuid, from_date, limit)
        
        return [
            {
                "id": entry.id,
                "chemo_date": entry.chemo_date,
                "created_at": entry.created_at,
            }
            for entry in entries
        ]
    
    def delete_chemo_date(
        self,
        patient_uuid: UUID,
        chemo_date: date,
    ) -> Dict[str, Any]:
        """
        Delete a chemo date entry.
        
        Args:
            patient_uuid: The patient's UUID
            chemo_date: The date to delete
            
        Returns:
            Success/failure response
        """
        logger.info(f"Delete chemo date: patient={patient_uuid} date={chemo_date}")
        
        deleted = self.chemo_repo.delete_by_date(patient_uuid, chemo_date)
        
        if deleted:
            logger.info(f"Chemo date deleted: date={chemo_date}")
            return {
                "success": True,
                "message": "Chemotherapy date successfully deleted.",
            }
        else:
            logger.warning(f"Chemo date not found: date={chemo_date}")
            return {
                "success": False,
                "message": "Chemotherapy date not found.",
            }





