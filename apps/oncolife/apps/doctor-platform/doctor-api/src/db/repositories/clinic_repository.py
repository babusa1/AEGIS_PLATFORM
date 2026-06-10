"""
Clinic Repository - Doctor API
==============================

Repository for clinic-related database operations.
Extends BaseRepository with clinic-specific query methods.

Usage:
    from db.repositories import ClinicRepository
    
    clinic_repo = ClinicRepository(db)
    clinic = clinic_repo.get_by_uuid(clinic_uuid)
    clinics = clinic_repo.search_by_name("Oncology")
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .base import BaseRepository
from db.models import Clinic
from core.logging import get_logger

logger = get_logger(__name__)


class ClinicRepository(BaseRepository[Clinic]):
    """
    Repository for Clinic model operations.
    
    Provides CRUD operations and clinic-specific queries
    for managing healthcare facility data.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the clinic repository.
        
        Args:
            db: The database session
        """
        super().__init__(Clinic, db)
    
    # =========================================================================
    # Clinic-Specific Queries
    # =========================================================================
    
    def get_by_uuid(self, clinic_uuid: UUID) -> Optional[Clinic]:
        """
        Get a clinic by its UUID.
        
        Args:
            clinic_uuid: The clinic's unique identifier
            
        Returns:
            The Clinic instance, or None if not found
        """
        return self.db.query(Clinic).filter(
            Clinic.uuid == clinic_uuid
        ).first()
    
    def get_by_name(self, clinic_name: str) -> Optional[Clinic]:
        """
        Get a clinic by its exact name.
        
        Args:
            clinic_name: The clinic's name
            
        Returns:
            The Clinic instance, or None if not found
        """
        return self.db.query(Clinic).filter(
            Clinic.clinic_name == clinic_name
        ).first()
    
    def search_by_name(
        self,
        search_term: str,
        limit: int = 20
    ) -> List[Clinic]:
        """
        Search clinics by name (case-insensitive partial match).
        
        Args:
            search_term: The search term to match
            limit: Maximum number of results
            
        Returns:
            List of matching clinics
        """
        return self.db.query(Clinic).filter(
            Clinic.clinic_name.ilike(f"%{search_term}%")
        ).limit(limit).all()
    
    def get_all_active(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Clinic]:
        """
        Get all active clinics with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of clinic instances
        """
        return self.db.query(Clinic).order_by(
            Clinic.clinic_name
        ).offset(skip).limit(limit).all()
    
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
            clinic_name: Name of the clinic
            address: Physical address (optional)
            phone_number: Contact phone (optional)
            fax_number: Fax number (optional)
            
        Returns:
            The created Clinic instance
        """
        return self.create(
            clinic_name=clinic_name,
            address=address,
            phone_number=phone_number,
            fax_number=fax_number,
        )
    
    def update_clinic(
        self,
        clinic: Clinic,
        clinic_name: Optional[str] = None,
        address: Optional[str] = None,
        phone_number: Optional[str] = None,
        fax_number: Optional[str] = None,
    ) -> Clinic:
        """
        Update a clinic's information.
        
        Args:
            clinic: The clinic to update
            clinic_name: New name (optional)
            address: New address (optional)
            phone_number: New phone (optional)
            fax_number: New fax (optional)
            
        Returns:
            The updated Clinic instance
        """
        update_data = {}
        if clinic_name is not None:
            update_data["clinic_name"] = clinic_name
        if address is not None:
            update_data["address"] = address
        if phone_number is not None:
            update_data["phone_number"] = phone_number
        if fax_number is not None:
            update_data["fax_number"] = fax_number
        
        if update_data:
            return self.update(clinic, **update_data)
        return clinic
    
    def name_exists(self, clinic_name: str) -> bool:
        """
        Check if a clinic with the given name already exists.
        
        Args:
            clinic_name: The name to check
            
        Returns:
            True if a clinic with this name exists
        """
        return self.exists(clinic_name=clinic_name)





