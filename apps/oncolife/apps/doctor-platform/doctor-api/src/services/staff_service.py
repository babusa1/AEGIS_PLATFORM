"""
Staff Service - Doctor API
==========================

Service layer for staff-related business logic.
Handles staff profile management, physician registration,
and staff-clinic associations.

Usage:
    from services import StaffService
    
    staff_service = StaffService(db)
    
    # Create a physician
    physician = staff_service.create_physician(
        email_address="doctor@clinic.com",
        first_name="Jane",
        last_name="Smith",
        npi_number="1234567890",
        clinic_uuid=clinic_uuid
    )
"""

from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from .base import BaseService
from db.repositories import StaffRepository, ClinicRepository
from db.models import StaffProfile, StaffAssociation
from core.exceptions import NotFoundError, ConflictError, ValidationError
from core.logging import get_logger

logger = get_logger(__name__)


class StaffService(BaseService):
    """
    Service for staff-related operations.
    
    Provides business logic for:
    - Creating and managing staff profiles
    - Physician registration
    - Staff-clinic associations
    - Role-based queries
    """
    
    def __init__(self, db: Session):
        """
        Initialize the staff service.
        
        Args:
            db: The database session
        """
        super().__init__(db)
        self.staff_repo = StaffRepository(db)
        self.clinic_repo = ClinicRepository(db)
    
    # =========================================================================
    # Staff Profile Operations
    # =========================================================================
    
    def get_staff_by_uuid(self, staff_uuid: UUID) -> StaffProfile:
        """
        Get a staff profile by UUID.
        
        Args:
            staff_uuid: The staff member's UUID
            
        Returns:
            The StaffProfile instance
            
        Raises:
            NotFoundError: If the staff member doesn't exist
        """
        return self.staff_repo.get_by_staff_uuid_or_fail(staff_uuid)
    
    def get_staff_by_email(self, email: str) -> StaffProfile:
        """
        Get a staff profile by email.
        
        Args:
            email: The staff member's email address
            
        Returns:
            The StaffProfile instance
            
        Raises:
            NotFoundError: If the staff member doesn't exist
        """
        return self.staff_repo.get_by_email_or_fail(email)
    
    def list_staff(
        self,
        role: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[StaffProfile]:
        """
        List staff members with optional role filter.
        
        Args:
            role: Optional role to filter by (physician, staff, admin)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of staff profiles
        """
        if role:
            return self.staff_repo.get_staff_by_role(role, skip=skip, limit=limit)
        return self.staff_repo.get_all(skip=skip, limit=limit)
    
    def list_staff_with_count(
        self,
        role: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[StaffProfile], int]:
        """
        List staff members with total count for pagination.
        
        Args:
            role: Optional role to filter by (physician, staff, admin)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (list of staff profiles, total count)
        """
        staff_list = self.list_staff(role=role, skip=skip, limit=limit)
        total_count = self.staff_repo.count_staff(role=role)
        return staff_list, total_count
    
    def search_staff(
        self,
        search_term: str,
        role: Optional[str] = None,
        limit: int = 20
    ) -> List[StaffProfile]:
        """
        Search staff by name.
        
        Args:
            search_term: Name to search for
            role: Optional role filter
            limit: Maximum results
            
        Returns:
            List of matching staff profiles
        """
        if not search_term or len(search_term.strip()) < 2:
            return []
        
        return self.staff_repo.search_by_name(
            search_term=search_term.strip(),
            role=role,
            limit=limit
        )
    
    # =========================================================================
    # Physician Operations
    # =========================================================================
    
    def create_physician(
        self,
        email_address: str,
        first_name: str,
        last_name: str,
        npi_number: str,
        clinic_uuid: UUID,
    ) -> StaffProfile:
        """
        Create a new physician profile.
        
        Creates the profile and sets up self-association with the clinic.
        
        Args:
            email_address: Physician's email (unique)
            first_name: Physician's first name
            last_name: Physician's last name
            npi_number: National Provider Identifier
            clinic_uuid: UUID of the clinic
            
        Returns:
            The created StaffProfile instance
            
        Raises:
            ValidationError: If required fields are missing or invalid
            ConflictError: If email already exists
            NotFoundError: If clinic doesn't exist
        """
        # Validate inputs
        self._validate_email(email_address)
        self._validate_name(first_name, "first_name")
        self._validate_name(last_name, "last_name")
        self._validate_npi(npi_number)
        
        # Verify clinic exists
        clinic = self.clinic_repo.get_by_uuid(clinic_uuid)
        if not clinic:
            raise NotFoundError(
                message="Clinic not found",
                resource_type="Clinic",
                resource_id=str(clinic_uuid)
            )
        
        # Create physician with self-association
        physician = self.staff_repo.create_physician(
            email_address=email_address.lower().strip(),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            npi_number=npi_number.strip(),
            clinic_uuid=clinic_uuid,
        )
        
        self.logger.info(
            f"Created physician: {physician.full_name} "
            f"({physician.email_address}) at clinic {clinic.clinic_name}"
        )
        return physician
    
    def list_physicians(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[StaffProfile]:
        """
        List all physicians.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of physician profiles
        """
        return self.staff_repo.get_all_physicians(skip=skip, limit=limit)
    
    def get_clinic_for_physician(self, physician_uuid: UUID) -> Optional[UUID]:
        """
        Get the clinic UUID for a physician.
        
        Args:
            physician_uuid: The physician's UUID
            
        Returns:
            The clinic UUID, or None if not found
        """
        return self.staff_repo.get_clinic_for_physician(physician_uuid)
    
    # =========================================================================
    # Staff Member Operations
    # =========================================================================
    
    def create_staff_member(
        self,
        email_address: str,
        first_name: str,
        last_name: str,
        role: str,
        physician_uuids: List[UUID],
        clinic_uuid: UUID,
    ) -> StaffProfile:
        """
        Create a new staff member (non-physician).
        
        Creates the profile and sets up associations with physicians.
        
        Args:
            email_address: Staff member's email (unique)
            first_name: Staff member's first name
            last_name: Staff member's last name
            role: Role (must be 'staff' or 'admin')
            physician_uuids: List of physician UUIDs to associate with
            clinic_uuid: UUID of the clinic
            
        Returns:
            The created StaffProfile instance
            
        Raises:
            ValidationError: If required fields are missing or invalid
            ConflictError: If email already exists
            NotFoundError: If clinic or physicians don't exist
        """
        # Validate inputs
        self._validate_email(email_address)
        self._validate_name(first_name, "first_name")
        self._validate_name(last_name, "last_name")
        self._validate_role(role)
        
        if not physician_uuids:
            raise ValidationError(
                message="At least one physician must be specified",
                field="physician_uuids"
            )
        
        # Verify clinic exists
        clinic = self.clinic_repo.get_by_uuid(clinic_uuid)
        if not clinic:
            raise NotFoundError(
                message="Clinic not found",
                resource_type="Clinic",
                resource_id=str(clinic_uuid)
            )
        
        # Verify all physicians exist
        for physician_uuid in physician_uuids:
            physician = self.staff_repo.get_by_staff_uuid(physician_uuid)
            if not physician or not physician.is_physician:
                raise NotFoundError(
                    message=f"Physician not found: {physician_uuid}",
                    resource_type="Physician",
                    resource_id=str(physician_uuid)
                )
        
        # Create staff member with associations
        staff = self.staff_repo.create_staff_member(
            email_address=email_address.lower().strip(),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            role=role,
            physician_uuids=physician_uuids,
            clinic_uuid=clinic_uuid,
        )
        
        self.logger.info(
            f"Created {role}: {staff.full_name} ({staff.email_address}), "
            f"associated with {len(physician_uuids)} physician(s)"
        )
        return staff
    
    def get_staff_for_physician(
        self,
        physician_uuid: UUID
    ) -> List[StaffProfile]:
        """
        Get all staff members associated with a physician.
        
        Args:
            physician_uuid: The physician's UUID
            
        Returns:
            List of staff profiles
        """
        return self.staff_repo.get_staff_for_physician(physician_uuid)
    
    # =========================================================================
    # Validation Helpers
    # =========================================================================
    
    def _validate_email(self, email: str) -> None:
        """Validate email format."""
        if not email or not email.strip():
            raise ValidationError(
                message="Email address is required",
                field="email_address"
            )
        
        email = email.strip().lower()
        if "@" not in email or "." not in email:
            raise ValidationError(
                message="Invalid email address format",
                field="email_address"
            )
    
    def _validate_name(self, name: str, field: str) -> None:
        """Validate a name field."""
        if not name or not name.strip():
            raise ValidationError(
                message=f"{field.replace('_', ' ').title()} is required",
                field=field
            )
    
    def _validate_npi(self, npi: str) -> None:
        """Validate NPI number format."""
        if not npi or not npi.strip():
            raise ValidationError(
                message="NPI number is required for physicians",
                field="npi_number"
            )
        
        # NPI is a 10-digit number
        npi_clean = npi.strip()
        if not npi_clean.isdigit() or len(npi_clean) != 10:
            raise ValidationError(
                message="NPI number must be exactly 10 digits",
                field="npi_number"
            )
    
    def _validate_role(self, role: str) -> None:
        """Validate role value."""
        valid_roles = {'staff', 'admin'}
        if role not in valid_roles:
            raise ValidationError(
                message=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
                field="role"
            )





