"""
Profile Repository - Patient API
================================

Repository for patient profile operations.

Usage:
    from db.repositories import ProfileRepository
    
    profile_repo = ProfileRepository(db)
    profile = profile_repo.get_profile(patient_uuid)
"""

from typing import Optional, Tuple
from uuid import UUID
from datetime import time
from sqlalchemy.orm import Session

from .base import BaseRepository
# Use legacy models - matches actual database tables
from db.patient_models import (
    PatientInfo as Patient,
    PatientConfigurations as PatientConfiguration,
    PatientPhysicianAssociations as PatientPhysicianAssociation,
)
from core.logging import get_logger
from core.exceptions import NotFoundError

logger = get_logger(__name__)


class ProfileRepository(BaseRepository[Patient]):
    """
    Repository for Patient profile operations.
    
    Provides operations for managing patient info
    and configurations.
    """
    
    def __init__(self, db: Session):
        """Initialize the profile repository."""
        super().__init__(Patient, db)
    
    # =========================================================================
    # Patient Info Operations
    # =========================================================================
    
    def get_by_uuid(self, patient_uuid: UUID) -> Optional[Patient]:
        """
        Get a patient by UUID.
        
        Args:
            patient_uuid: The patient's UUID
            
        Returns:
            The Patient instance, or None if not found
        """
        return self.db.query(Patient).filter(
            Patient.uuid == patient_uuid,
            Patient.is_deleted == False,
        ).first()
    
    def get_by_uuid_or_fail(self, patient_uuid: UUID) -> Patient:
        """
        Get a patient by UUID, raising error if not found.
        
        Args:
            patient_uuid: The patient's UUID
            
        Returns:
            The Patient instance
            
        Raises:
            NotFoundError: If patient not found
        """
        patient = self.get_by_uuid(patient_uuid)
        if not patient:
            raise NotFoundError(
                message="Patient not found",
                resource_type="Patient",
                resource_id=str(patient_uuid),
            )
        return patient
    
    def get_by_email(self, email: str) -> Optional[Patient]:
        """
        Get a patient by email address.
        
        Args:
            email: The patient's email
            
        Returns:
            The Patient instance, or None if not found
        """
        return self.db.query(Patient).filter(
            Patient.email_address == email,
            Patient.is_deleted == False,
        ).first()
    
    def email_exists(self, email: str) -> bool:
        """
        Check if an email is already registered.
        
        Args:
            email: The email to check
            
        Returns:
            True if email exists
        """
        return self.db.query(Patient).filter(
            Patient.email_address == email,
            Patient.is_deleted == False,
        ).first() is not None
    
    # =========================================================================
    # Configuration Operations
    # =========================================================================
    
    def get_configuration(self, patient_uuid: UUID) -> Optional[PatientConfiguration]:
        """
        Get patient configuration.
        
        Args:
            patient_uuid: The patient's UUID
            
        Returns:
            The PatientConfiguration instance, or None
        """
        return self.db.query(PatientConfiguration).filter(
            PatientConfiguration.uuid == patient_uuid,
            PatientConfiguration.is_deleted == False,
        ).first()
    
    def update_configuration(
        self,
        patient_uuid: UUID,
        reminder_method: Optional[str] = None,
        reminder_time: Optional[time] = None,
        acknowledgement_done: Optional[bool] = None,
        agreed_conditions: Optional[bool] = None,
    ) -> PatientConfiguration:
        """
        Update patient configuration.
        
        Args:
            patient_uuid: The patient's UUID
            reminder_method: New reminder method
            reminder_time: New reminder time
            acknowledgement_done: Acknowledgement status
            agreed_conditions: Terms agreement status
            
        Returns:
            The updated PatientConfiguration instance
            
        Raises:
            NotFoundError: If configuration not found
        """
        config = self.get_configuration(patient_uuid)
        if not config:
            raise NotFoundError(
                message="Patient configuration not found",
                resource_type="PatientConfiguration",
                resource_id=str(patient_uuid),
            )
        
        if reminder_method is not None:
            config.reminder_method = reminder_method
        if reminder_time is not None:
            config.reminder_time = reminder_time
        if acknowledgement_done is not None:
            config.acknowledgement_done = acknowledgement_done
        if agreed_conditions is not None:
            config.agreed_conditions = agreed_conditions
        
        self.db.commit()
        self.db.refresh(config)
        return config
    
    # =========================================================================
    # Physician Association Operations
    # =========================================================================
    
    def get_physician_association(
        self,
        patient_uuid: UUID,
    ) -> Optional[PatientPhysicianAssociation]:
        """
        Get the patient's physician association.
        
        Args:
            patient_uuid: The patient's UUID
            
        Returns:
            The PatientPhysicianAssociation instance, or None
        """
        return self.db.query(PatientPhysicianAssociation).filter(
            PatientPhysicianAssociation.patient_uuid == patient_uuid,
            PatientPhysicianAssociation.is_deleted == False,
        ).first()
    
    def create_physician_association(
        self,
        patient_uuid: UUID,
        physician_uuid: UUID,
        clinic_uuid: UUID,
    ) -> PatientPhysicianAssociation:
        """
        Create a patient-physician association.
        
        Args:
            patient_uuid: The patient's UUID
            physician_uuid: The physician's UUID
            clinic_uuid: The clinic's UUID
            
        Returns:
            The created PatientPhysicianAssociation instance
        """
        association = PatientPhysicianAssociation(
            patient_uuid=patient_uuid,
            physician_uuid=physician_uuid,
            clinic_uuid=clinic_uuid,
        )
        self.db.add(association)
        self.db.commit()
        self.db.refresh(association)
        return association
    
    # =========================================================================
    # Full Profile Operations
    # =========================================================================
    
    def get_full_profile(
        self,
        patient_uuid: UUID,
    ) -> Tuple[Patient, Optional[PatientConfiguration], Optional[PatientPhysicianAssociation]]:
        """
        Get complete patient profile data.
        
        Args:
            patient_uuid: The patient's UUID
            
        Returns:
            Tuple of (Patient, PatientConfiguration, PatientPhysicianAssociation)
            
        Raises:
            NotFoundError: If patient not found
        """
        patient = self.get_by_uuid_or_fail(patient_uuid)
        config = self.get_configuration(patient_uuid)
        association = self.get_physician_association(patient_uuid)
        
        return patient, config, association
    
    # =========================================================================
    # Soft Delete Operations
    # =========================================================================
    
    def soft_delete_patient(self, patient_uuid: UUID) -> bool:
        """
        Soft delete a patient and all related data.
        
        Args:
            patient_uuid: The patient's UUID
            
        Returns:
            True if deleted successfully
        """
        # Soft delete patient info
        patient = self.get_by_uuid(patient_uuid)
        if patient:
            patient.is_deleted = True
        
        # Soft delete configuration
        config = self.get_configuration(patient_uuid)
        if config:
            config.is_deleted = True
        
        # Soft delete physician association
        association = self.get_physician_association(patient_uuid)
        if association:
            association.is_deleted = True
        
        self.db.commit()
        return True

