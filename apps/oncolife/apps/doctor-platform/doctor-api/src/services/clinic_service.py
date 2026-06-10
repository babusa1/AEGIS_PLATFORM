"""
Clinic Service - Doctor API
===========================

Service layer for clinic-related business logic.
Handles clinic creation, updates, and queries.

Usage:
    from services import ClinicService
    
    clinic_service = ClinicService(db)
    
    # Create a clinic
    clinic = clinic_service.create_clinic(
        clinic_name="Main Oncology Center",
        address="123 Medical Way"
    )
    
    # Get clinic by UUID
    clinic = clinic_service.get_clinic(clinic_uuid)
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from .base import BaseService
from db.repositories import ClinicRepository
from db.models import Clinic
from core.exceptions import NotFoundError, ConflictError, ValidationError
from core.logging import get_logger

logger = get_logger(__name__)


class ClinicService(BaseService):
    """
    Service for clinic-related operations.
    
    Provides business logic for:
    - Creating and updating clinics
    - Searching and listing clinics
    - Validating clinic data
    """
    
    def __init__(self, db: Session):
        """
        Initialize the clinic service.
        
        Args:
            db: The database session
        """
        super().__init__(db)
        self.clinic_repo = ClinicRepository(db)
    
    # =========================================================================
    # Clinic CRUD Operations
    # =========================================================================
    
    def create_clinic(
        self,
        clinic_name: str,
        address: Optional[str] = None,
        phone_number: Optional[str] = None,
        fax_number: Optional[str] = None,
    ) -> Clinic:
        """
        Create a new clinic.
        
        Args:
            clinic_name: Name of the clinic (required)
            address: Physical address (optional)
            phone_number: Contact phone number (optional)
            fax_number: Fax number (optional)
            
        Returns:
            The created Clinic instance
            
        Raises:
            ValidationError: If clinic_name is empty
            ConflictError: If a clinic with this name already exists
        """
        # Validate required fields
        if not clinic_name or not clinic_name.strip():
            raise ValidationError(
                message="Clinic name is required",
                field="clinic_name"
            )
        
        clinic_name = clinic_name.strip()
        
        # Check for duplicate name
        if self.clinic_repo.name_exists(clinic_name):
            raise ConflictError(
                message="A clinic with this name already exists",
                details={"clinic_name": clinic_name}
            )
        
        # Create the clinic
        clinic = self.clinic_repo.create_clinic(
            clinic_name=clinic_name,
            address=address,
            phone_number=phone_number,
            fax_number=fax_number,
        )
        
        self.logger.info(f"Created clinic: {clinic.clinic_name} ({clinic.uuid})")
        return clinic
    
    def get_clinic(self, clinic_uuid: UUID) -> Clinic:
        """
        Get a clinic by its UUID.
        
        Args:
            clinic_uuid: The clinic's unique identifier
            
        Returns:
            The Clinic instance
            
        Raises:
            NotFoundError: If the clinic doesn't exist
        """
        clinic = self.clinic_repo.get_by_uuid(clinic_uuid)
        if not clinic:
            raise NotFoundError(
                message="Clinic not found",
                resource_type="Clinic",
                resource_id=str(clinic_uuid)
            )
        return clinic
    
    def get_clinic_by_name(self, clinic_name: str) -> Optional[Clinic]:
        """
        Get a clinic by its exact name.
        
        Args:
            clinic_name: The clinic's name
            
        Returns:
            The Clinic instance, or None if not found
        """
        return self.clinic_repo.get_by_name(clinic_name)
    
    def update_clinic(
        self,
        clinic_uuid: UUID,
        clinic_name: Optional[str] = None,
        address: Optional[str] = None,
        phone_number: Optional[str] = None,
        fax_number: Optional[str] = None,
    ) -> Clinic:
        """
        Update a clinic's information.
        
        Args:
            clinic_uuid: The clinic's UUID
            clinic_name: New name (optional)
            address: New address (optional)
            phone_number: New phone (optional)
            fax_number: New fax (optional)
            
        Returns:
            The updated Clinic instance
            
        Raises:
            NotFoundError: If the clinic doesn't exist
            ConflictError: If new name conflicts with existing clinic
        """
        clinic = self.get_clinic(clinic_uuid)
        
        # Check for name conflict if changing name
        if clinic_name and clinic_name.strip() != clinic.clinic_name:
            clinic_name = clinic_name.strip()
            if self.clinic_repo.name_exists(clinic_name):
                raise ConflictError(
                    message="A clinic with this name already exists",
                    details={"clinic_name": clinic_name}
                )
        
        # Update the clinic
        updated_clinic = self.clinic_repo.update_clinic(
            clinic=clinic,
            clinic_name=clinic_name,
            address=address,
            phone_number=phone_number,
            fax_number=fax_number,
        )
        
        self.logger.info(f"Updated clinic: {updated_clinic.clinic_name} ({updated_clinic.uuid})")
        return updated_clinic
    
    def delete_clinic(self, clinic_uuid: UUID) -> bool:
        """
        Delete a clinic.
        
        Args:
            clinic_uuid: The clinic's UUID
            
        Returns:
            True if deletion was successful
            
        Raises:
            NotFoundError: If the clinic doesn't exist
        """
        clinic = self.get_clinic(clinic_uuid)
        result = self.clinic_repo.delete(clinic)
        
        self.logger.info(f"Deleted clinic: {clinic.clinic_name} ({clinic.uuid})")
        return result
    
    # =========================================================================
    # Clinic Listing and Search
    # =========================================================================
    
    def list_clinics(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Clinic]:
        """
        Get all clinics with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of clinic instances
        """
        return self.clinic_repo.get_all_active(skip=skip, limit=limit)
    
    def search_clinics(
        self,
        search_term: str,
        limit: int = 20
    ) -> List[Clinic]:
        """
        Search clinics by name.
        
        Args:
            search_term: The search term to match
            limit: Maximum number of results
            
        Returns:
            List of matching clinics
        """
        if not search_term or len(search_term.strip()) < 2:
            return []
        
        return self.clinic_repo.search_by_name(
            search_term=search_term.strip(),
            limit=limit
        )
    
    def count_clinics(self) -> int:
        """
        Get the total number of clinics.
        
        Returns:
            Total count of clinics
        """
        return self.clinic_repo.count()





