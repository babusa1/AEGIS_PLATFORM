"""
Patient Service for Patient-Related Business Logic.

This service handles:
- Patient CRUD operations
- Patient search and filtering
- Patient profile management
- Business rules for patient data

Usage:
    from services import PatientService
    
    service = PatientService(db)
    patient = service.get_patient(patient_id)
    patients = service.search_patients("John")
"""

from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from db.models import Patient
from db.repositories import PatientRepository
from services.base import BaseService
from core.exceptions import (
    NotFoundException,
    ValidationException,
    ConflictException,
)
from core.logging import get_logger

logger = get_logger(__name__)


class PatientService(BaseService):
    """
    Service for patient-related operations.
    
    Provides business logic for patient management,
    including validation, search, and profile operations.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the patient service.
        
        Args:
            db: Database session
        """
        super().__init__(db)
        self.patient_repo = PatientRepository(db)
    
    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================
    
    def get_patient(self, patient_id: UUID) -> Patient:
        """
        Get a patient by ID.
        
        Args:
            patient_id: Patient UUID
        
        Returns:
            Patient model instance
        
        Raises:
            NotFoundException: If patient doesn't exist
        """
        patient = self.patient_repo.get_by_id(patient_id)
        if not patient:
            raise NotFoundException(f"Patient with ID {patient_id} not found")
        return patient
    
    def get_patient_by_email(self, email: str) -> Optional[Patient]:
        """
        Get a patient by email address.
        
        Args:
            email: Email address
        
        Returns:
            Patient or None
        """
        return self.patient_repo.find_by_email(email)
    
    def get_patient_by_mrn(self, mrn: str) -> Optional[Patient]:
        """
        Get a patient by Medical Record Number.
        
        Args:
            mrn: Medical Record Number
        
        Returns:
            Patient or None
        """
        return self.patient_repo.find_by_mrn(mrn)
    
    def create_patient(self, data: Dict[str, Any]) -> Patient:
        """
        Create a new patient.
        
        Validates:
        - Required fields (first_name, last_name)
        - Unique email (if provided)
        - Unique MRN (if provided)
        
        Args:
            data: Patient data dictionary
        
        Returns:
            Created patient
        
        Raises:
            ValidationException: If validation fails
            ConflictException: If email or MRN already exists
        """
        # Validate required fields
        if not data.get("first_name"):
            raise ValidationException(
                "First name is required",
                details={"field": "first_name"}
            )
        if not data.get("last_name"):
            raise ValidationException(
                "Last name is required",
                details={"field": "last_name"}
            )
        
        # Check for duplicate email
        if data.get("email"):
            existing = self.patient_repo.find_by_email(data["email"])
            if existing:
                raise ConflictException(
                    "A patient with this email already exists",
                    details={"field": "email", "email": data["email"]}
                )
        
        # Check for duplicate MRN
        if data.get("mrn"):
            existing = self.patient_repo.find_by_mrn(data["mrn"])
            if existing:
                raise ConflictException(
                    "A patient with this MRN already exists",
                    details={"field": "mrn", "mrn": data["mrn"]}
                )
        
        # Create patient
        patient = self.patient_repo.create(data)
        
        logger.info(
            f"Created patient: {patient.full_name}",
            extra={"patient_id": str(patient.uuid)}
        )
        
        return patient
    
    def update_patient(
        self,
        patient_id: UUID,
        data: Dict[str, Any]
    ) -> Patient:
        """
        Update an existing patient.
        
        Args:
            patient_id: Patient UUID
            data: Updated data
        
        Returns:
            Updated patient
        
        Raises:
            NotFoundException: If patient doesn't exist
            ConflictException: If email/MRN conflicts
        """
        patient = self.get_patient(patient_id)
        
        # Check for email conflict
        if data.get("email") and data["email"] != patient.email:
            existing = self.patient_repo.find_by_email(data["email"])
            if existing and existing.uuid != patient_id:
                raise ConflictException(
                    "A patient with this email already exists"
                )
        
        # Check for MRN conflict
        if data.get("mrn") and data["mrn"] != patient.mrn:
            existing = self.patient_repo.find_by_mrn(data["mrn"])
            if existing and existing.uuid != patient_id:
                raise ConflictException(
                    "A patient with this MRN already exists"
                )
        
        # Update patient
        updated = self.patient_repo.update(patient_id, data)
        
        logger.info(
            f"Updated patient: {updated.full_name}",
            extra={"patient_id": str(patient_id)}
        )
        
        return updated
    
    def delete_patient(self, patient_id: UUID) -> None:
        """
        Delete a patient (soft delete - deactivate).
        
        Args:
            patient_id: Patient UUID
        
        Raises:
            NotFoundException: If patient doesn't exist
        """
        patient = self.get_patient(patient_id)
        self.patient_repo.deactivate_patient(patient_id)
        
        logger.info(
            f"Deactivated patient: {patient.full_name}",
            extra={"patient_id": str(patient_id)}
        )
    
    # =========================================================================
    # SEARCH AND FILTERING
    # =========================================================================
    
    def list_patients(
        self,
        skip: int = 0,
        limit: int = 20,
        active_only: bool = True
    ) -> List[Patient]:
        """
        List patients with pagination.
        
        Args:
            skip: Offset for pagination
            limit: Maximum results
            active_only: Only return active patients
        
        Returns:
            List of patients
        """
        if active_only:
            return self.patient_repo.get_active_patients(skip=skip, limit=limit)
        return self.patient_repo.get_all(skip=skip, limit=limit)
    
    def search_patients(
        self,
        query: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Patient]:
        """
        Search patients by name, email, or MRN.
        
        Args:
            query: Search query
            skip: Offset for pagination
            limit: Maximum results
        
        Returns:
            List of matching patients
        """
        if not query or len(query) < 2:
            raise ValidationException(
                "Search query must be at least 2 characters"
            )
        
        return self.patient_repo.search(query, skip=skip, limit=limit)
    
    def get_patients_by_care_team(
        self,
        care_team_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[Patient]:
        """
        Get patients assigned to a care team.
        
        Args:
            care_team_id: Care team UUID
            skip: Offset for pagination
            limit: Maximum results
        
        Returns:
            List of patients
        """
        return self.patient_repo.get_by_care_team(
            care_team_id, skip=skip, limit=limit
        )
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_patient_count(self, active_only: bool = True) -> int:
        """
        Get total patient count.
        
        Args:
            active_only: Only count active patients
        
        Returns:
            Patient count
        """
        if active_only:
            return self.patient_repo.count_active()
        return self.patient_repo.count()





