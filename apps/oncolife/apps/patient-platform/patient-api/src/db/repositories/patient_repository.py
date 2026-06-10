"""
Patient Repository for Patient-Specific Database Operations.

This repository extends BaseRepository with patient-specific queries
and operations, including search and filtering capabilities.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from db.models import Patient
from db.repositories.base import BaseRepository
from core.logging import get_logger

logger = get_logger(__name__)


class PatientRepository(BaseRepository[Patient]):
    """
    Repository for Patient model operations.
    
    Provides patient-specific queries beyond basic CRUD,
    including search, filtering, and statistics.
    """
    
    def __init__(self, db: Session):
        """Initialize with Patient model."""
        super().__init__(Patient, db)
    
    # =========================================================================
    # SEARCH AND LOOKUP
    # =========================================================================
    
    def find_by_email(self, email: str) -> Optional[Patient]:
        """
        Find a patient by email address.
        
        Args:
            email: Email address to search
        
        Returns:
            Patient or None
        """
        return self.db.query(Patient).filter(
            func.lower(Patient.email) == email.lower()
        ).first()
    
    def find_by_mrn(self, mrn: str) -> Optional[Patient]:
        """
        Find a patient by Medical Record Number.
        
        Args:
            mrn: Medical Record Number
        
        Returns:
            Patient or None
        """
        return self.db.query(Patient).filter(
            Patient.mrn == mrn
        ).first()
    
    def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Patient]:
        """
        Search patients by name, email, or MRN.
        
        Args:
            query: Search query string
            skip: Offset for pagination
            limit: Maximum results
        
        Returns:
            List of matching patients
        """
        search_term = f"%{query.lower()}%"
        
        return self.db.query(Patient).filter(
            or_(
                func.lower(Patient.first_name).like(search_term),
                func.lower(Patient.last_name).like(search_term),
                func.lower(Patient.email).like(search_term),
                Patient.mrn.like(search_term),
            )
        ).offset(skip).limit(limit).all()
    
    # =========================================================================
    # FILTERED QUERIES
    # =========================================================================
    
    def get_active_patients(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Patient]:
        """
        Get all active patients.
        
        Args:
            skip: Offset for pagination
            limit: Maximum results
        
        Returns:
            List of active patients
        """
        return self.db.query(Patient).filter(
            Patient.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_by_care_team(
        self,
        care_team_uuid: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Patient]:
        """
        Get patients assigned to a specific care team.
        
        Args:
            care_team_uuid: Care team UUID
            skip: Offset for pagination
            limit: Maximum results
        
        Returns:
            List of patients
        """
        return self.db.query(Patient).filter(
            Patient.care_team_uuid == care_team_uuid,
            Patient.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_by_oncologist(
        self,
        oncologist_uuid: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Patient]:
        """
        Get patients under a specific oncologist.
        
        Args:
            oncologist_uuid: Primary oncologist UUID
            skip: Offset for pagination
            limit: Maximum results
        
        Returns:
            List of patients
        """
        return self.db.query(Patient).filter(
            Patient.primary_oncologist_uuid == oncologist_uuid,
            Patient.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_recently_active(
        self,
        days: int = 7,
        limit: int = 50
    ) -> List[Patient]:
        """
        Get patients with recent activity.
        
        Args:
            days: Number of days to look back
            limit: Maximum results
        
        Returns:
            List of recently active patients
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        return self.db.query(Patient).filter(
            Patient.updated_at >= cutoff,
            Patient.is_active == True
        ).order_by(
            Patient.updated_at.desc()
        ).limit(limit).all()
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def count_active(self) -> int:
        """Get count of active patients."""
        return self.db.query(Patient).filter(
            Patient.is_active == True
        ).count()
    
    def count_by_care_team(self, care_team_uuid: UUID) -> int:
        """Get count of patients in a care team."""
        return self.db.query(Patient).filter(
            Patient.care_team_uuid == care_team_uuid,
            Patient.is_active == True
        ).count()
    
    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================
    
    def deactivate_patient(self, patient_id: UUID) -> bool:
        """
        Deactivate a patient (soft delete).
        
        Args:
            patient_id: Patient UUID
        
        Returns:
            True if successful
        """
        patient = self.get_by_id(patient_id)
        if patient:
            patient.is_active = False
            self.db.flush()
            logger.info(f"Deactivated patient {patient_id}")
            return True
        return False
    
    def reactivate_patient(self, patient_id: UUID) -> bool:
        """
        Reactivate a previously deactivated patient.
        
        Args:
            patient_id: Patient UUID
        
        Returns:
            True if successful
        """
        patient = self.get_by_id(patient_id)
        if patient:
            patient.is_active = True
            self.db.flush()
            logger.info(f"Reactivated patient {patient_id}")
            return True
        return False





