"""
================================================================================
Diary Service - Patient API
================================================================================

Module:         diary_service.py
Description:    Service for patient diary entry management. Handles CRUD
                operations for patient health journal entries with support
                for sharing entries with doctors.

Created:        2025-12-18
Modified:       2026-01-16
Author:         Naveen Babu S A
Version:        2.1.0

Features:
    - Create, read, update diary entries
    - Soft delete entries
    - Get entries by month for calendar view
    - Mark entries to share with doctor
    - Timezone conversion for user display

Usage:
    from services import DiaryService
    
    diary_service = DiaryService(db)
    entries = diary_service.get_entries_by_month(patient_uuid, 2024, 1)

Copyright:
    (c) 2026 OncoLife Health Technologies. All rights reserved.
================================================================================
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session

from db.repositories import DiaryRepository
from core.logging import get_logger
from core.exceptions import ValidationError, NotFoundError
from utils.timezone_utils import utc_to_user_timezone

logger = get_logger(__name__)


class DiaryService:
    """
    Service for diary entry operations.
    
    Provides:
    - Create, read, update diary entries
    - Soft delete entries
    - Get entries by month
    - Get entries marked for doctor
    """
    
    def __init__(self, db: Session):
        """
        Initialize the diary service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.diary_repo = DiaryRepository(db)
    
    def _convert_to_timezone(
        self,
        entry: Any,
        timezone: str,
    ) -> Dict[str, Any]:
        """Convert diary entry to dict with timezone-adjusted timestamps."""
        return {
            "id": entry.id,
            "created_at": utc_to_user_timezone(entry.created_at, timezone) if entry.created_at else None,
            "last_updated_at": utc_to_user_timezone(entry.last_updated_at, timezone) if entry.last_updated_at else None,
            "patient_uuid": str(entry.patient_uuid),
            "title": entry.title,
            "diary_entry": entry.diary_entry,
            "entry_uuid": str(entry.entry_uuid),
            "marked_for_doctor": entry.marked_for_doctor,
            "is_deleted": entry.is_deleted,
        }
    
    # =========================================================================
    # Create
    # =========================================================================
    
    def create_entry(
        self,
        patient_uuid: UUID,
        diary_entry: str,
        title: Optional[str] = None,
        marked_for_doctor: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new diary entry.
        
        Args:
            patient_uuid: The patient's UUID
            diary_entry: The diary entry text
            title: Optional title
            marked_for_doctor: Whether to flag for doctor
            
        Returns:
            The created entry as a dict
        """
        logger.info(f"Create diary entry: patient={patient_uuid}")
        
        if not diary_entry or not diary_entry.strip():
            raise ValidationError(
                message="Diary entry cannot be empty",
                field="diary_entry",
            )
        
        entry = self.diary_repo.create_entry(
            patient_uuid=patient_uuid,
            diary_entry=diary_entry,
            title=title,
            marked_for_doctor=marked_for_doctor,
        )
        
        logger.info(f"Diary entry created: id={entry.id}")
        
        return {
            "id": entry.id,
            "created_at": entry.created_at,
            "last_updated_at": entry.last_updated_at,
            "patient_uuid": str(entry.patient_uuid),
            "title": entry.title,
            "diary_entry": entry.diary_entry,
            "entry_uuid": str(entry.entry_uuid),
            "marked_for_doctor": entry.marked_for_doctor,
            "is_deleted": entry.is_deleted,
        }
    
    # =========================================================================
    # Read
    # =========================================================================
    
    def get_all_entries(
        self,
        patient_uuid: UUID,
        timezone: str = "America/Los_Angeles",
    ) -> List[Dict[str, Any]]:
        """
        Get all diary entries for a patient.
        
        Args:
            patient_uuid: The patient's UUID
            timezone: User's timezone
            
        Returns:
            List of diary entries
        """
        logger.info(f"Get all diary entries: patient={patient_uuid}")
        
        entries = self.diary_repo.get_by_patient(patient_uuid)
        
        return [self._convert_to_timezone(e, timezone) for e in entries]
    
    def get_entries_by_month(
        self,
        patient_uuid: UUID,
        year: int,
        month: int,
        timezone: str = "America/Los_Angeles",
    ) -> List[Dict[str, Any]]:
        """
        Get diary entries for a specific month.
        
        Args:
            patient_uuid: The patient's UUID
            year: The year
            month: The month (1-12)
            timezone: User's timezone
            
        Returns:
            List of diary entries
        """
        if month < 1 or month > 12:
            raise ValidationError(
                message="Month must be between 1 and 12",
                field="month",
            )
        
        logger.info(f"Get diary entries by month: patient={patient_uuid} {year}/{month}")
        
        entries = self.diary_repo.get_by_month(patient_uuid, year, month)
        
        return [self._convert_to_timezone(e, timezone) for e in entries]
    
    def get_entry_by_uuid(
        self,
        entry_uuid: UUID,
        patient_uuid: UUID,
        timezone: str = "America/Los_Angeles",
    ) -> Dict[str, Any]:
        """
        Get a specific diary entry.
        
        Args:
            entry_uuid: The entry's UUID
            patient_uuid: The patient's UUID (for authorization)
            timezone: User's timezone
            
        Returns:
            The diary entry
            
        Raises:
            NotFoundError: If entry not found
        """
        entry = self.diary_repo.get_by_entry_uuid(entry_uuid)
        
        if not entry or str(entry.patient_uuid) != str(patient_uuid):
            raise NotFoundError(
                message="Diary entry not found",
                resource_type="DiaryEntry",
                resource_id=str(entry_uuid),
            )
        
        return self._convert_to_timezone(entry, timezone)
    
    def get_entries_for_doctor(
        self,
        patient_uuid: UUID,
        timezone: str = "America/Los_Angeles",
    ) -> List[Dict[str, Any]]:
        """
        Get entries marked for doctor review.
        
        Args:
            patient_uuid: The patient's UUID
            timezone: User's timezone
            
        Returns:
            List of diary entries marked for doctor
        """
        logger.info(f"Get entries for doctor: patient={patient_uuid}")
        
        entries = self.diary_repo.get_for_doctor(patient_uuid)
        
        return [self._convert_to_timezone(e, timezone) for e in entries]
    
    # =========================================================================
    # Update
    # =========================================================================
    
    def update_entry(
        self,
        entry_uuid: UUID,
        patient_uuid: UUID,
        title: Optional[str] = None,
        diary_entry: Optional[str] = None,
        marked_for_doctor: Optional[bool] = None,
        timezone: str = "America/Los_Angeles",
    ) -> Dict[str, Any]:
        """
        Update a diary entry.
        
        Args:
            entry_uuid: The entry's UUID
            patient_uuid: The patient's UUID (for authorization)
            title: New title (optional)
            diary_entry: New entry text (optional)
            marked_for_doctor: New flag value (optional)
            timezone: User's timezone
            
        Returns:
            The updated entry
        """
        # Check if any updates provided
        if title is None and diary_entry is None and marked_for_doctor is None:
            raise ValidationError(
                message="No update data provided",
                field="update_data",
            )
        
        logger.info(f"Update diary entry: entry_uuid={entry_uuid} patient={patient_uuid}")
        
        entry = self.diary_repo.update_entry(
            entry_uuid=entry_uuid,
            patient_uuid=patient_uuid,
            title=title,
            diary_entry=diary_entry,
            marked_for_doctor=marked_for_doctor,
        )
        
        logger.info(f"Diary entry updated: id={entry.id}")
        
        return self._convert_to_timezone(entry, timezone)
    
    # =========================================================================
    # Delete
    # =========================================================================
    
    def soft_delete_entry(
        self,
        entry_uuid: UUID,
        patient_uuid: UUID,
    ) -> Dict[str, Any]:
        """
        Soft delete a diary entry.
        
        Args:
            entry_uuid: The entry's UUID
            patient_uuid: The patient's UUID (for authorization)
            
        Returns:
            Success response
        """
        logger.info(f"Soft delete diary entry: entry_uuid={entry_uuid} patient={patient_uuid}")
        
        deleted = self.diary_repo.soft_delete(entry_uuid, patient_uuid)
        
        if deleted:
            logger.info(f"Diary entry deleted: entry_uuid={entry_uuid}")
            return {"success": True, "message": "Diary entry deleted"}
        else:
            logger.info(f"Diary entry already deleted: entry_uuid={entry_uuid}")
            return {"success": True, "message": "Diary entry was already deleted"}
    
    # =========================================================================
    # Auto-populate from Symptom Checker
    # =========================================================================
    
    def create_from_symptom_session(
        self,
        patient_uuid: UUID,
        conversation_uuid: UUID,
        symptoms: List[Dict[str, Any]],
        triage_level: str,
        overall_feeling: Optional[str] = None,
        summary_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Auto-populate a diary entry from a symptom checker session.
        
        Called automatically when a symptom checker conversation completes.
        Creates a system-generated summary entry that patients can reference.
        
        Args:
            patient_uuid: The patient's UUID
            conversation_uuid: The conversation UUID for reference
            symptoms: List of symptoms with severity
            triage_level: The triage outcome (call_911, notify_care_team, none)
            overall_feeling: Patient's reported feeling
            summary_text: Optional pre-generated summary
            
        Returns:
            The created diary entry
        """
        logger.info(f"Auto-populating diary from symptom session: patient={patient_uuid}")
        
        # Build the diary entry content
        today = datetime.utcnow().strftime("%B %d, %Y")
        
        # Format symptoms
        symptom_lines = []
        max_severity = "mild"
        severity_order = {"mild": 1, "moderate": 2, "severe": 3, "urgent": 4}
        
        for symptom in symptoms:
            name = symptom.get("name", symptom.get("code", "Unknown"))
            severity = symptom.get("severity", "mild")
            symptom_lines.append(f"• {name}: {severity}")
            
            if severity_order.get(severity, 0) > severity_order.get(max_severity, 0):
                max_severity = severity
        
        # Build entry text
        parts = [f"Daily Check-in Summary - {today}"]
        
        if overall_feeling:
            parts.append(f"\nOverall feeling: {overall_feeling}")
        
        if symptom_lines:
            parts.append("\nSymptoms reported:")
            parts.extend(symptom_lines)
        
        # Add triage outcome (if concerning)
        if triage_level == "call_911":
            parts.append("\n⚠️ Urgent: Emergency care recommended")
        elif triage_level == "notify_care_team":
            parts.append("\n📞 Care team notification sent")
        
        # Add custom summary if provided
        if summary_text:
            parts.append(f"\n\n{summary_text}")
        
        parts.append(f"\n\n[Auto-generated from symptom check session]")
        
        diary_entry = "\n".join(parts)
        title = f"Symptom Check - {today}"
        
        # Create the entry (marked for doctor if concerning)
        marked_for_doctor = triage_level in ["call_911", "notify_care_team"]
        
        entry = self.diary_repo.create_entry(
            patient_uuid=patient_uuid,
            diary_entry=diary_entry,
            title=title,
            marked_for_doctor=marked_for_doctor,
        )
        
        logger.info(
            f"Auto-populated diary entry created: id={entry.id} "
            f"marked_for_doctor={marked_for_doctor}"
        )
        
        return {
            "id": entry.id,
            "created_at": entry.created_at,
            "last_updated_at": entry.last_updated_at,
            "patient_uuid": str(entry.patient_uuid),
            "title": entry.title,
            "diary_entry": entry.diary_entry,
            "entry_uuid": str(entry.entry_uuid),
            "marked_for_doctor": entry.marked_for_doctor,
            "is_deleted": entry.is_deleted,
            "auto_generated": True,
        }



