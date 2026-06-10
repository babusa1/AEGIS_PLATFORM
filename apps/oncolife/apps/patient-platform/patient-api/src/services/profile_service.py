"""
Profile Service - Patient API
==============================

Service for patient profile operations.

Usage:
    from services import ProfileService
    
    profile_service = ProfileService(patient_db, doctor_db)
    profile = profile_service.get_profile(patient_uuid)
"""

from typing import Dict, Any, Optional
from uuid import UUID
from datetime import time, date

from sqlalchemy.orm import Session

from db.repositories import ProfileRepository
from db.doctor_models import StaffProfiles, AllClinics, StaffAssociations
from db.models.onboarding_schema import OncologyProfile
from db.patient_models import PatientInfo
from core.logging import get_logger
from core.exceptions import NotFoundError

logger = get_logger(__name__)


class ProfileService:
    """
    Service for patient profile operations.
    
    Provides:
    - Get complete patient profile
    - Update patient configuration
    - Get physician/clinic information
    """
    
    def __init__(
        self,
        patient_db: Session,
        doctor_db: Optional[Session] = None,
    ):
        """
        Initialize the profile service.
        
        Args:
            patient_db: Patient database session
            doctor_db: Doctor database session (optional)
        """
        self.patient_db = patient_db
        self.doctor_db = doctor_db
        self.profile_repo = ProfileRepository(patient_db)
    
    def get_profile(
        self,
        patient_uuid: UUID,
    ) -> Dict[str, Any]:
        """
        Get complete patient profile.
        
        Combines data from patient database and doctor database
        to create a comprehensive profile view including oncology data.
        
        Args:
            patient_uuid: The patient's UUID
            
        Returns:
            Complete patient profile with oncology data
            
        Raises:
            NotFoundError: If patient not found
        """
        logger.info(f"Get profile: patient={patient_uuid}")
        
        # Get patient data
        patient, config, association = self.profile_repo.get_full_profile(patient_uuid)
        
        # Get physician and clinic info from doctor database
        doctor_name = None
        clinic_name = None
        
        if association and self.doctor_db:
            doctor_name, clinic_name = self._get_physician_info(association.physician_uuid)
        
        # Get oncology profile data
        oncology_data = self._get_oncology_profile(patient_uuid)
        
        logger.info(f"Profile fetched: patient={patient_uuid} doctor={doctor_name}")
        
        return {
            # Basic info
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "email_address": patient.email_address,
            "phone_number": patient.phone_number,
            "date_of_birth": patient.dob,
            "reminder_time": config.reminder_time if config else None,
            "doctor_name": doctor_name or oncology_data.get("provider_name"),
            "clinic_name": clinic_name or oncology_data.get("clinic_name"),
            # Treatment info from oncology profile
            "diagnosis": oncology_data.get("cancer_type"),
            "treatment_type": oncology_data.get("line_of_treatment"),
            "chemo_plan_name": oncology_data.get("chemo_plan_name"),
            "chemo_start_date": oncology_data.get("chemo_start_date"),
            "chemo_end_date": oncology_data.get("chemo_end_date"),
            "current_cycle": oncology_data.get("current_cycle"),
            "total_cycles": oncology_data.get("total_cycles"),
            "last_chemo_date": oncology_data.get("last_chemo_date"),
            "next_physician_visit": oncology_data.get("next_clinic_visit"),
            # Emergency contact
            "emergency_contact_name": getattr(patient, 'emergency_contact_name', None),
            "emergency_contact_phone": getattr(patient, 'emergency_contact_phone', None),
        }
    
    def _get_oncology_profile(
        self,
        patient_uuid: UUID,
    ) -> Dict[str, Any]:
        """Get oncology profile data for a patient."""
        try:
            oncology = self.patient_db.query(OncologyProfile).filter(
                OncologyProfile.patient_id == patient_uuid,
                OncologyProfile.is_active == True,
                OncologyProfile.is_deleted == False,
            ).order_by(OncologyProfile.created_at.desc()).first()
            
            if oncology:
                return {
                    "cancer_type": oncology.cancer_type,
                    "cancer_stage": oncology.cancer_stage,
                    "line_of_treatment": oncology.line_of_treatment,
                    "treatment_goal": oncology.treatment_goal,
                    "chemo_plan_name": oncology.chemo_plan_name,
                    "chemo_start_date": oncology.chemo_start_date,
                    "chemo_end_date": oncology.chemo_end_date,
                    "current_cycle": oncology.current_cycle,
                    "total_cycles": oncology.total_cycles,
                    "next_clinic_visit": oncology.next_clinic_visit,
                    "last_chemo_date": oncology.last_chemo_date,
                    "treatment_department": oncology.treatment_department,
                }
        except Exception as e:
            logger.warning(f"Could not fetch oncology profile: {e}")
        
        return {}
    
    def _get_physician_info(
        self,
        physician_uuid: UUID,
    ) -> tuple:
        """Get physician name and clinic name."""
        doctor_name = None
        clinic_name = None
        
        try:
            physician = self.doctor_db.query(StaffProfiles).filter(
                StaffProfiles.staff_uuid == physician_uuid
            ).first()
            
            if physician:
                doctor_name = f"{physician.first_name} {physician.last_name}"
                
                # Get clinic association
                staff_assoc = self.doctor_db.query(StaffAssociations).filter(
                    StaffAssociations.physician_uuid == physician_uuid
                ).first()
                
                if staff_assoc:
                    clinic = self.doctor_db.query(AllClinics).filter(
                        AllClinics.uuid == staff_assoc.clinic_uuid
                    ).first()
                    
                    if clinic:
                        clinic_name = clinic.clinic_name
                        
        except Exception as e:
            logger.error(f"Error fetching physician info: {e}")
        
        return doctor_name, clinic_name
    
    def update_configuration(
        self,
        patient_uuid: UUID,
        reminder_method: Optional[str] = None,
        reminder_time: Optional[time] = None,
        acknowledgement_done: Optional[bool] = None,
        agreed_conditions: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Update patient configuration.
        
        Args:
            patient_uuid: The patient's UUID
            reminder_method: New reminder method
            reminder_time: New reminder time
            acknowledgement_done: Acknowledgement status
            agreed_conditions: Terms agreement status
            
        Returns:
            Updated configuration
        """
        logger.info(f"Update configuration: patient={patient_uuid}")
        
        config = self.profile_repo.update_configuration(
            patient_uuid=patient_uuid,
            reminder_method=reminder_method,
            reminder_time=reminder_time,
            acknowledgement_done=acknowledgement_done,
            agreed_conditions=agreed_conditions,
        )
        
        logger.info(f"Configuration updated: patient={patient_uuid}")
        
        return {
            "uuid": str(config.uuid),
            "reminder_method": config.reminder_method,
            "reminder_time": config.reminder_time,
            "acknowledgement_done": config.acknowledgement_done,
            "agreed_conditions": config.agreed_conditions,
        }
    
    def update_consent(
        self,
        patient_uuid: UUID,
        acknowledgement_done: Optional[bool] = None,
        agreed_conditions: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Update patient consent status.
        
        Args:
            patient_uuid: The patient's UUID
            acknowledgement_done: Acknowledgement status
            agreed_conditions: Terms agreement status
            
        Returns:
            Updated consent status
        """
        logger.info(f"Update consent: patient={patient_uuid}")
        
        return self.update_configuration(
            patient_uuid=patient_uuid,
            acknowledgement_done=acknowledgement_done,
            agreed_conditions=agreed_conditions,
        )
    
    def get_patient_info(
        self,
        patient_uuid: UUID,
    ) -> Dict[str, Any]:
        """
        Get detailed patient info.
        
        Args:
            patient_uuid: The patient's UUID
            
        Returns:
            Patient information
            
        Raises:
            NotFoundError: If patient not found
        """
        patient = self.profile_repo.get_by_uuid_or_fail(patient_uuid)
        
        return {
            "uuid": str(patient.uuid),
            "created_at": patient.created_at.isoformat() if patient.created_at else None,
            "email_address": patient.email_address,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "sex": patient.sex,
            "dob": patient.dob,
            "mrn": patient.mrn,
            "ethnicity": patient.ethnicity,
            "phone_number": patient.phone_number,
            "disease_type": patient.disease_type,
            "treatment_type": patient.treatment_type,
            "is_deleted": patient.is_deleted,
        }
    
    def update_profile(
        self,
        patient_uuid: UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        reminder_time: Optional[time] = None,
        diagnosis: Optional[str] = None,
        treatment_type: Optional[str] = None,
        last_chemo_date: Optional[date] = None,
        next_physician_visit: Optional[date] = None,
        emergency_contact_name: Optional[str] = None,
        emergency_contact_phone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update patient profile including oncology data.
        
        Args:
            patient_uuid: The patient's UUID
            first_name: Updated first name
            last_name: Updated last name
            phone_number: Updated phone number
            date_of_birth: Updated date of birth
            reminder_time: Updated reminder time
            diagnosis: Updated diagnosis/cancer type
            treatment_type: Updated treatment type
            last_chemo_date: Last chemotherapy date
            next_physician_visit: Next scheduled clinic visit
            emergency_contact_name: Emergency contact name
            emergency_contact_phone: Emergency contact phone
            
        Returns:
            Updated profile data
            
        Raises:
            NotFoundError: If patient not found
        """
        logger.info(f"Update profile: patient={patient_uuid}")
        
        # Update patient info
        patient = self.profile_repo.get_by_uuid_or_fail(patient_uuid)
        
        if first_name is not None:
            patient.first_name = first_name
        if last_name is not None:
            patient.last_name = last_name
        if phone_number is not None:
            patient.phone_number = phone_number
        if date_of_birth is not None:
            patient.dob = date_of_birth
        if emergency_contact_name is not None:
            patient.emergency_contact_name = emergency_contact_name
        if emergency_contact_phone is not None:
            patient.emergency_contact_phone = emergency_contact_phone
        
        # Update config if reminder time provided
        if reminder_time is not None:
            self.profile_repo.update_configuration(
                patient_uuid=patient_uuid,
                reminder_time=reminder_time,
            )
        
        # Update or create oncology profile
        self._update_oncology_profile(
            patient_uuid=patient_uuid,
            cancer_type=diagnosis,
            line_of_treatment=treatment_type,
            last_chemo_date=last_chemo_date,
            next_clinic_visit=next_physician_visit,
        )
        
        self.patient_db.commit()
        
        logger.info(f"Profile updated: patient={patient_uuid}")
        
        return self.get_profile(patient_uuid)
    
    def _update_oncology_profile(
        self,
        patient_uuid: UUID,
        cancer_type: Optional[str] = None,
        line_of_treatment: Optional[str] = None,
        last_chemo_date: Optional[date] = None,
        next_clinic_visit: Optional[date] = None,
    ) -> None:
        """Update or create oncology profile for a patient."""
        try:
            oncology = self.patient_db.query(OncologyProfile).filter(
                OncologyProfile.patient_id == patient_uuid,
                OncologyProfile.is_active == True,
                OncologyProfile.is_deleted == False,
            ).order_by(OncologyProfile.created_at.desc()).first()
            
            if oncology:
                # Update existing profile
                if cancer_type is not None:
                    oncology.cancer_type = cancer_type
                if line_of_treatment is not None:
                    oncology.line_of_treatment = line_of_treatment
                if last_chemo_date is not None:
                    oncology.last_chemo_date = last_chemo_date
                if next_clinic_visit is not None:
                    oncology.next_clinic_visit = next_clinic_visit
            else:
                # Create new profile if we have data to save
                if any([cancer_type, line_of_treatment, last_chemo_date, next_clinic_visit]):
                    new_oncology = OncologyProfile(
                        patient_id=patient_uuid,
                        cancer_type=cancer_type or "Not specified",
                        line_of_treatment=line_of_treatment,
                        last_chemo_date=last_chemo_date,
                        next_clinic_visit=next_clinic_visit,
                        is_active=True,
                        is_deleted=False,
                    )
                    self.patient_db.add(new_oncology)
                    
        except Exception as e:
            logger.error(f"Error updating oncology profile: {e}")





