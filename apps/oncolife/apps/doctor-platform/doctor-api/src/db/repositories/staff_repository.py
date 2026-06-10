"""
Staff Repository - Doctor API
=============================

Repository for staff-related database operations.
Handles both StaffProfile and StaffAssociation models.

Usage:
    from db.repositories import StaffRepository
    
    staff_repo = StaffRepository(db)
    physician = staff_repo.get_physician_by_email("doctor@clinic.com")
    staff_list = staff_repo.get_staff_for_physician(physician_uuid)
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .base import BaseRepository
from db.models import StaffProfile, StaffAssociation
from core.logging import get_logger
from core.exceptions import NotFoundError, ConflictError

logger = get_logger(__name__)


class StaffRepository(BaseRepository[StaffProfile]):
    """
    Repository for StaffProfile model operations.
    
    Provides CRUD operations and staff-specific queries
    for managing healthcare personnel data.
    
    Also handles StaffAssociation operations since they're
    closely related to staff management.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the staff repository.
        
        Args:
            db: The database session
        """
        super().__init__(StaffProfile, db)
    
    # =========================================================================
    # Staff Profile Queries
    # =========================================================================
    
    def get_by_staff_uuid(self, staff_uuid: UUID) -> Optional[StaffProfile]:
        """
        Get a staff profile by their UUID.
        
        Args:
            staff_uuid: The staff member's unique identifier
            
        Returns:
            The StaffProfile instance, or None if not found
        """
        return self.db.query(StaffProfile).filter(
            StaffProfile.staff_uuid == staff_uuid
        ).first()
    
    def get_by_staff_uuid_or_fail(self, staff_uuid: UUID) -> StaffProfile:
        """
        Get a staff profile by UUID, raising error if not found.
        
        Args:
            staff_uuid: The staff member's unique identifier
            
        Returns:
            The StaffProfile instance
            
        Raises:
            NotFoundError: If the staff member doesn't exist
        """
        profile = self.get_by_staff_uuid(staff_uuid)
        if not profile:
            raise NotFoundError(
                message="Staff member not found",
                resource_type="StaffProfile",
                resource_id=str(staff_uuid)
            )
        return profile
    
    def get_by_email(self, email: str) -> Optional[StaffProfile]:
        """
        Get a staff profile by email address.
        
        Args:
            email: The staff member's email address
            
        Returns:
            The StaffProfile instance, or None if not found
        """
        return self.db.query(StaffProfile).filter(
            StaffProfile.email_address == email
        ).first()
    
    def get_by_email_or_fail(self, email: str) -> StaffProfile:
        """
        Get a staff profile by email, raising error if not found.
        
        Args:
            email: The staff member's email address
            
        Returns:
            The StaffProfile instance
            
        Raises:
            NotFoundError: If the staff member doesn't exist
        """
        profile = self.get_by_email(email)
        if not profile:
            raise NotFoundError(
                message="Staff member not found",
                resource_type="StaffProfile",
                details={"email": email}
            )
        return profile
    
    def get_physician_by_email(self, email: str) -> Optional[StaffProfile]:
        """
        Get a physician profile by email address.
        
        Args:
            email: The physician's email address
            
        Returns:
            The StaffProfile instance if it's a physician, or None
        """
        return self.db.query(StaffProfile).filter(
            and_(
                StaffProfile.email_address == email,
                StaffProfile.role == 'physician'
            )
        ).first()
    
    def get_all_physicians(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[StaffProfile]:
        """
        Get all physicians with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of physician profiles
        """
        return self.db.query(StaffProfile).filter(
            StaffProfile.role == 'physician'
        ).order_by(
            StaffProfile.last_name, StaffProfile.first_name
        ).offset(skip).limit(limit).all()
    
    def get_staff_by_role(
        self,
        role: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[StaffProfile]:
        """
        Get all staff members with a specific role.
        
        Args:
            role: The role to filter by (physician, staff, admin)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of staff profiles with the specified role
        """
        return self.db.query(StaffProfile).filter(
            StaffProfile.role == role
        ).order_by(
            StaffProfile.last_name, StaffProfile.first_name
        ).offset(skip).limit(limit).all()
    
    def count_staff(self, role: Optional[str] = None) -> int:
        """
        Count total staff members with optional role filter.
        
        Args:
            role: Optional role to filter by (physician, staff, admin)
            
        Returns:
            Total count of matching staff members
        """
        query = self.db.query(StaffProfile)
        if role:
            query = query.filter(StaffProfile.role == role)
        return query.count()
    
    def search_by_name(
        self,
        search_term: str,
        role: Optional[str] = None,
        limit: int = 20
    ) -> List[StaffProfile]:
        """
        Search staff by name (first or last name, case-insensitive).
        
        Args:
            search_term: The search term to match
            role: Optional role filter
            limit: Maximum number of results
            
        Returns:
            List of matching staff profiles
        """
        query = self.db.query(StaffProfile).filter(
            (StaffProfile.first_name.ilike(f"%{search_term}%")) |
            (StaffProfile.last_name.ilike(f"%{search_term}%"))
        )
        
        if role:
            query = query.filter(StaffProfile.role == role)
        
        return query.limit(limit).all()
    
    def email_exists(self, email: str) -> bool:
        """
        Check if an email address is already in use.
        
        Args:
            email: The email address to check
            
        Returns:
            True if the email is already registered
        """
        return self.exists(email_address=email)
    
    # =========================================================================
    # Staff Creation
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
        Create a new physician profile with self-association.
        
        Physicians are self-associated (staff_uuid == physician_uuid)
        in the StaffAssociation table.
        
        Args:
            email_address: Physician's email
            first_name: Physician's first name
            last_name: Physician's last name
            npi_number: National Provider Identifier
            clinic_uuid: UUID of the clinic
            
        Returns:
            The created StaffProfile instance
            
        Raises:
            ConflictError: If email already exists
        """
        if self.email_exists(email_address):
            raise ConflictError(
                message="A staff member with this email already exists",
                details={"email": email_address}
            )
        
        # Create the physician profile
        physician = self.create(
            email_address=email_address,
            first_name=first_name,
            last_name=last_name,
            role='physician',
            npi_number=npi_number,
        )
        
        # Create self-association (physician associated with themselves)
        self.create_association(
            staff_uuid=physician.staff_uuid,
            physician_uuid=physician.staff_uuid,  # Self-association
            clinic_uuid=clinic_uuid,
        )
        
        logger.info(f"Created physician: {physician.full_name} ({email_address})")
        return physician
    
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
        Create a new staff member with physician associations.
        
        Staff members are associated with one or more physicians
        in the StaffAssociation table.
        
        Args:
            email_address: Staff member's email
            first_name: Staff member's first name
            last_name: Staff member's last name
            role: Role (staff or admin)
            physician_uuids: List of physician UUIDs to associate with
            clinic_uuid: UUID of the clinic
            
        Returns:
            The created StaffProfile instance
            
        Raises:
            ConflictError: If email already exists
        """
        if self.email_exists(email_address):
            raise ConflictError(
                message="A staff member with this email already exists",
                details={"email": email_address}
            )
        
        # Create the staff profile
        staff = self.create(
            email_address=email_address,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )
        
        # Create associations with each physician
        for physician_uuid in physician_uuids:
            self.create_association(
                staff_uuid=staff.staff_uuid,
                physician_uuid=physician_uuid,
                clinic_uuid=clinic_uuid,
            )
        
        logger.info(
            f"Created {role}: {staff.full_name} ({email_address}), "
            f"associated with {len(physician_uuids)} physician(s)"
        )
        return staff
    
    # =========================================================================
    # Staff Association Operations
    # =========================================================================
    
    def create_association(
        self,
        staff_uuid: UUID,
        physician_uuid: UUID,
        clinic_uuid: UUID,
    ) -> StaffAssociation:
        """
        Create a staff-physician-clinic association.
        
        Args:
            staff_uuid: UUID of the staff member
            physician_uuid: UUID of the physician
            clinic_uuid: UUID of the clinic
            
        Returns:
            The created StaffAssociation instance
        """
        association = StaffAssociation(
            staff_uuid=staff_uuid,
            physician_uuid=physician_uuid,
            clinic_uuid=clinic_uuid,
        )
        self.db.add(association)
        self.db.commit()
        self.db.refresh(association)
        return association
    
    def get_associations_for_staff(
        self,
        staff_uuid: UUID
    ) -> List[StaffAssociation]:
        """
        Get all associations for a staff member.
        
        Args:
            staff_uuid: UUID of the staff member
            
        Returns:
            List of StaffAssociation instances
        """
        return self.db.query(StaffAssociation).filter(
            StaffAssociation.staff_uuid == staff_uuid
        ).all()
    
    def get_associations_for_physician(
        self,
        physician_uuid: UUID
    ) -> List[StaffAssociation]:
        """
        Get all staff associations for a physician.
        
        Args:
            physician_uuid: UUID of the physician
            
        Returns:
            List of StaffAssociation instances
        """
        return self.db.query(StaffAssociation).filter(
            StaffAssociation.physician_uuid == physician_uuid
        ).all()
    
    def get_clinic_for_physician(
        self,
        physician_uuid: UUID
    ) -> Optional[UUID]:
        """
        Get the clinic UUID for a physician.
        
        Args:
            physician_uuid: UUID of the physician
            
        Returns:
            The clinic UUID, or None if not found
        """
        association = self.db.query(StaffAssociation).filter(
            StaffAssociation.physician_uuid == physician_uuid
        ).first()
        
        if association:
            return association.clinic_uuid
        return None
    
    def get_staff_for_physician(
        self,
        physician_uuid: UUID
    ) -> List[StaffProfile]:
        """
        Get all staff members associated with a physician.
        
        Args:
            physician_uuid: UUID of the physician
            
        Returns:
            List of StaffProfile instances
        """
        # Get all staff UUIDs associated with this physician
        associations = self.db.query(StaffAssociation).filter(
            StaffAssociation.physician_uuid == physician_uuid
        ).all()
        
        staff_uuids = [a.staff_uuid for a in associations]
        
        if not staff_uuids:
            return []
        
        # Get the staff profiles (excluding the physician themselves)
        return self.db.query(StaffProfile).filter(
            and_(
                StaffProfile.staff_uuid.in_(staff_uuids),
                StaffProfile.staff_uuid != physician_uuid  # Exclude self
            )
        ).all()





