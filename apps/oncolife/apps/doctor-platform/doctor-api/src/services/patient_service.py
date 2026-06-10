"""
================================================================================
Patient Service - Doctor API
================================================================================

Module:         patient_service.py
Description:    Service for accessing patient data from the patient database.
                Provides read-only access for doctors/staff to view their
                associated patients, conversations, and diary entries.

Created:        2025-12-22
Modified:       2026-01-16
Author:         Naveen Babu S A
Version:        2.1.0

Features:
    - Patient listing with physician association checks
    - Patient details retrieval with demographics
    - Conversation and alert access
    - Diary entry access (shared entries only)
    - Cross-database queries with SQLAlchemy text() wrapper

Usage:
    from services import PatientService
    
    patient_service = PatientService(patient_db, doctor_db)
    patients = patient_service.get_associated_patients(staff_uuid)

Security:
    - All operations are read-only
    - Authorization checks on every query
    - Uses patient_physician_associations table for access control

Copyright:
    (c) 2026 OncoLife Health Technologies. All rights reserved.
================================================================================
"""

from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_, and_, text

from .base import BaseService
from core.logging import get_logger
from core.exceptions import NotFoundError, AuthorizationError

logger = get_logger(__name__)


class PatientService(BaseService):
    """
    Service for patient data access in the doctor portal.
    
    Provides:
    - Patient listing with association checks
    - Patient details retrieval
    - Alert/conversation access
    - Diary entry access
    
    All operations are read-only and require proper authorization.
    """
    
    def __init__(self, patient_db: Session, doctor_db: Session):
        """
        Initialize the patient service.
        
        Args:
            patient_db: Database session for patient database
            doctor_db: Database session for doctor database
        """
        super().__init__(doctor_db)
        self.patient_db = patient_db
        self.doctor_db = doctor_db
    
    # =========================================================================
    # Patient Listing
    # =========================================================================
    
    def get_associated_patients(
        self,
        staff_uuid: UUID,
        search_query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get patients associated with a staff member.
        
        For physicians: Returns directly assigned patients.
        For other staff: Returns patients via clinic association.
        
        Args:
            staff_uuid: The staff member's UUID
            search_query: Optional search filter
            skip: Pagination offset
            limit: Maximum results to return
            
        Returns:
            Tuple of (list of patients, total count)
        """
        logger.info(f"Getting associated patients for staff {staff_uuid}")
        
        # Get patient UUIDs from associations
        associations_result = self.patient_db.execute(
            text("""
            SELECT patient_uuid 
            FROM patient_physician_associations 
            WHERE physician_uuid = :physician_uuid 
            AND is_deleted = false
            """),
            {"physician_uuid": str(staff_uuid)}
        )
        patient_uuids = [str(row[0]) for row in associations_result.fetchall()]
        
        if not patient_uuids:
            logger.info(f"No patients found for staff {staff_uuid}")
            return [], 0
        
        # Build the query with parameterized UUID list
        uuid_list = ",".join([f"'{uuid}'" for uuid in patient_uuids])
        
        # Add search filter if provided
        where_clause = f"uuid IN ({uuid_list}) AND is_deleted = false"
        if search_query:
            search_term = search_query.lower().replace("'", "''")  # Escape single quotes
            where_clause += f"""
                AND (
                    LOWER(first_name) LIKE '%{search_term}%'
                    OR LOWER(last_name) LIKE '%{search_term}%'
                    OR LOWER(email_address) LIKE '%{search_term}%'
                )
            """
        
        # Get patients
        patients_result = self.patient_db.execute(
            text(f"""
            SELECT uuid, email_address, first_name, last_name, 
                   phone_number, created_at
            FROM patient_info 
            WHERE {where_clause}
            ORDER BY created_at DESC
            OFFSET {skip} LIMIT {limit}
            """)
        )
        
        patients = []
        for row in patients_result.fetchall():
            patients.append({
                "uuid": str(row[0]),
                "email_address": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "phone_number": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
            })
        
        # Get total count
        count_result = self.patient_db.execute(
            text(f"""
            SELECT COUNT(*) FROM patient_info 
            WHERE {where_clause}
            """)
        )
        total = count_result.fetchone()[0]
        
        logger.info(f"Found {len(patients)} patients (total: {total}) for staff {staff_uuid}")
        return patients, total
    
    # =========================================================================
    # Patient Details
    # =========================================================================
    
    def get_patient_details(
        self,
        patient_uuid: UUID,
        staff_uuid: UUID,
    ) -> Dict[str, Any]:
        """
        Get detailed patient information.
        
        Args:
            patient_uuid: The patient's UUID
            staff_uuid: The requesting staff member's UUID (for auth)
            
        Returns:
            Patient details dictionary
            
        Raises:
            NotFoundError: If patient not found
            AuthorizationError: If staff not authorized to view patient
        """
        logger.info(f"Getting patient {patient_uuid} for staff {staff_uuid}")
        
        # Verify authorization
        if not self._is_authorized_for_patient(patient_uuid, staff_uuid):
            raise AuthorizationError(
                f"Staff {staff_uuid} not authorized to view patient {patient_uuid}"
            )
        
        # Get patient details
        result = self.patient_db.execute(
            text("""
            SELECT uuid, email_address, first_name, last_name, phone_number, 
                   dob, sex, disease_type, treatment_type, created_at, mrn
            FROM patient_info 
            WHERE uuid = :patient_uuid AND is_deleted = false
            """),
            {"patient_uuid": str(patient_uuid)}
        )
        
        row = result.fetchone()
        if not row:
            raise NotFoundError(f"Patient {patient_uuid} not found")
        
        return {
            "uuid": str(row[0]),
            "email_address": row[1],
            "first_name": row[2],
            "last_name": row[3],
            "phone_number": row[4],
            "dob": str(row[5]) if row[5] else None,
            "sex": row[6],
            "disease_type": row[7],
            "treatment_type": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "mrn": row[10],
        }
    
    # =========================================================================
    # Patient Alerts
    # =========================================================================
    
    def get_patient_alerts(
        self,
        patient_uuid: UUID,
        staff_uuid: UUID,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get symptom alerts for a patient.
        
        Alerts are conversations with concerning triage levels.
        
        Args:
            patient_uuid: The patient's UUID
            staff_uuid: The requesting staff member's UUID
            limit: Maximum alerts to return
            
        Returns:
            List of alert dictionaries
        """
        logger.info(f"Getting alerts for patient {patient_uuid}")
        
        # Verify authorization
        if not self._is_authorized_for_patient(patient_uuid, staff_uuid):
            raise AuthorizationError(
                f"Staff {staff_uuid} not authorized to view patient {patient_uuid}"
            )
        
        result = self.patient_db.execute(
            text("""
            SELECT uuid, conversation_state, symptom_list, created_at
            FROM conversations 
            WHERE patient_uuid = :patient_uuid
            AND (conversation_state = 'EMERGENCY' OR conversation_state = 'COMPLETED')
            ORDER BY created_at DESC
            LIMIT :limit
            """),
            {"patient_uuid": str(patient_uuid), "limit": limit}
        )
        
        alerts = []
        for row in result.fetchall():
            symptom_list = row[2] if row[2] else []
            if symptom_list:  # Only include if there are symptoms
                triage_level = "call_911" if row[1] == "EMERGENCY" else "notify_care_team"
                alerts.append({
                    "conversation_uuid": str(row[0]),
                    "triage_level": triage_level,
                    "symptom_list": symptom_list,
                    "created_at": row[3].isoformat() if row[3] else "",
                    "conversation_state": row[1],
                })
        
        return alerts
    
    # =========================================================================
    # Patient Conversations
    # =========================================================================
    
    def get_patient_conversations(
        self,
        patient_uuid: UUID,
        staff_uuid: UUID,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a patient.
        
        Args:
            patient_uuid: The patient's UUID
            staff_uuid: The requesting staff member's UUID
            limit: Maximum conversations to return
            
        Returns:
            List of conversation dictionaries
        """
        logger.info(f"Getting conversations for patient {patient_uuid}")
        
        # Verify authorization
        if not self._is_authorized_for_patient(patient_uuid, staff_uuid):
            raise AuthorizationError(
                f"Staff {staff_uuid} not authorized to view patient {patient_uuid}"
            )
        
        result = self.patient_db.execute(
            text("""
            SELECT uuid, created_at, conversation_state, symptom_list, 
                   overall_feeling, bulleted_summary
            FROM conversations 
            WHERE patient_uuid = :patient_uuid
            ORDER BY created_at DESC
            LIMIT :limit
            """),
            {"patient_uuid": str(patient_uuid), "limit": limit}
        )
        
        conversations = []
        for row in result.fetchall():
            conversations.append({
                "uuid": str(row[0]),
                "created_at": row[1].isoformat() if row[1] else "",
                "conversation_state": row[2],
                "symptom_list": row[3] if row[3] else [],
                "overall_feeling": row[4],
                "bulleted_summary": row[5],
            })
        
        return conversations
    
    # =========================================================================
    # Patient Diary
    # =========================================================================
    
    def get_patient_diary(
        self,
        patient_uuid: UUID,
        staff_uuid: UUID,
        for_doctor_only: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get diary entries for a patient.
        
        Args:
            patient_uuid: The patient's UUID
            staff_uuid: The requesting staff member's UUID
            for_doctor_only: Only return entries marked for doctor
            limit: Maximum entries to return
            
        Returns:
            List of diary entry dictionaries
        """
        logger.info(f"Getting diary for patient {patient_uuid}")
        
        # Verify authorization
        if not self._is_authorized_for_patient(patient_uuid, staff_uuid):
            raise AuthorizationError(
                f"Staff {staff_uuid} not authorized to view patient {patient_uuid}"
            )
        
        where_clause = "patient_uuid = :patient_uuid AND is_deleted = false"
        if for_doctor_only:
            where_clause += " AND marked_for_doctor = true"
        
        result = self.patient_db.execute(
            text(f"""
            SELECT id, entry_uuid, created_at, title, diary_entry, marked_for_doctor
            FROM patient_diary_entries 
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit
            """),
            {"patient_uuid": str(patient_uuid), "limit": limit}
        )
        
        entries = []
        for row in result.fetchall():
            entries.append({
                "id": row[0],
                "entry_uuid": str(row[1]),
                "created_at": row[2].isoformat() if row[2] else "",
                "title": row[3],
                "diary_entry": row[4],
                "marked_for_doctor": row[5],
            })
        
        return entries
    
    # =========================================================================
    # Authorization Helpers
    # =========================================================================
    
    def _is_authorized_for_patient(
        self,
        patient_uuid: UUID,
        staff_uuid: UUID,
    ) -> bool:
        """
        Check if staff member is authorized to access patient data.
        
        Args:
            patient_uuid: The patient's UUID
            staff_uuid: The staff member's UUID
            
        Returns:
            True if authorized, False otherwise
        """
        result = self.patient_db.execute(
            text("""
            SELECT COUNT(*) FROM patient_physician_associations
            WHERE patient_uuid = :patient_uuid
            AND physician_uuid = :staff_uuid
            AND is_deleted = false
            """),
            {"patient_uuid": str(patient_uuid), "staff_uuid": str(staff_uuid)}
        )
        
        count = result.fetchone()[0]
        return count > 0
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_patient_statistics(
        self,
        patient_uuid: UUID,
        staff_uuid: UUID,
    ) -> Dict[str, Any]:
        """
        Get statistics for a patient.
        
        Args:
            patient_uuid: The patient's UUID
            staff_uuid: The requesting staff member's UUID
            
        Returns:
            Statistics dictionary
        """
        if not self._is_authorized_for_patient(patient_uuid, staff_uuid):
            raise AuthorizationError(
                f"Staff {staff_uuid} not authorized to view patient {patient_uuid}"
            )
        
        # Count conversations
        conv_result = self.patient_db.execute(
            text("""
            SELECT COUNT(*) FROM conversations
            WHERE patient_uuid = :patient_uuid
            """),
            {"patient_uuid": str(patient_uuid)}
        )
        total_conversations = conv_result.fetchone()[0]
        
        # Count alerts (emergency + completed with symptoms)
        alert_result = self.patient_db.execute(
            text("""
            SELECT COUNT(*) FROM conversations
            WHERE patient_uuid = :patient_uuid
            AND conversation_state IN ('EMERGENCY', 'COMPLETED')
            AND symptom_list IS NOT NULL
            """),
            {"patient_uuid": str(patient_uuid)}
        )
        total_alerts = alert_result.fetchone()[0]
        
        # Count diary entries
        diary_result = self.patient_db.execute(
            text("""
            SELECT COUNT(*) FROM patient_diary_entries
            WHERE patient_uuid = :patient_uuid
            AND is_deleted = false
            """),
            {"patient_uuid": str(patient_uuid)}
        )
        total_diary_entries = diary_result.fetchone()[0]
        
        return {
            "total_conversations": total_conversations,
            "total_alerts": total_alerts,
            "total_diary_entries": total_diary_entries,
        }

    # =========================================================================
    # PATIENT QUESTIONS - Shared questions for doctor review
    # =========================================================================
    
    def get_patient_questions(
        self,
        patient_uuid: UUID,
        staff_uuid: UUID,
        include_answered: bool = True,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get shared questions from a patient.
        
        Only returns questions where share_with_physician=True.
        These are questions the patient wants to discuss with their doctor.
        
        Args:
            patient_uuid: The patient's UUID
            staff_uuid: The requesting staff member's UUID
            include_answered: Whether to include answered questions
            limit: Maximum questions to return
            
        Returns:
            List of question dictionaries
            
        Raises:
            AuthorizationError: If not authorized
        """
        if not self._is_authorized_for_patient(patient_uuid, staff_uuid):
            raise AuthorizationError(
                f"Staff {staff_uuid} not authorized to view patient {patient_uuid}"
            )
        
        # Query shared questions only
        query = """
            SELECT id, question_text, category, is_answered, created_at
            FROM patient_questions
            WHERE patient_uuid = :patient_uuid
            AND share_with_physician = true
            AND is_deleted = false
        """
        
        if not include_answered:
            query += " AND is_answered = false"
        
        query += " ORDER BY created_at DESC LIMIT :limit"
        
        result = self.patient_db.execute(
            text(query),
            {"patient_uuid": str(patient_uuid), "limit": limit}
        )
        
        questions = []
        for row in result:
            questions.append({
                "id": str(row[0]),
                "question_text": row[1],
                "category": row[2],
                "is_answered": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
            })
        
        return questions

    def mark_question_answered(
        self,
        patient_uuid: UUID,
        question_id: UUID,
        staff_uuid: UUID,
    ) -> Dict[str, Any]:
        """
        Mark a patient's question as answered.
        
        Doctors can mark questions as answered after discussing with the patient.
        
        Args:
            patient_uuid: The patient's UUID
            question_id: The question's UUID
            staff_uuid: The requesting staff member's UUID
            
        Returns:
            Updated question dictionary
            
        Raises:
            AuthorizationError: If not authorized
            NotFoundError: If question not found
        """
        if not self._is_authorized_for_patient(patient_uuid, staff_uuid):
            raise AuthorizationError(
                f"Staff {staff_uuid} not authorized to view patient {patient_uuid}"
            )
        
        # Get the question
        result = self.patient_db.execute(
            text("""
            SELECT id, question_text, category, is_answered, created_at
            FROM patient_questions
            WHERE id = :question_id
            AND patient_uuid = :patient_uuid
            AND share_with_physician = true
            AND is_deleted = false
            """),
            {"question_id": str(question_id), "patient_uuid": str(patient_uuid)}
        )
        
        row = result.fetchone()
        if not row:
            raise NotFoundError(f"Question {question_id} not found")
        
        # Mark as answered
        self.patient_db.execute(
            text("""
            UPDATE patient_questions
            SET is_answered = true, updated_at = NOW()
            WHERE id = :question_id
            """),
            {"question_id": str(question_id)}
        )
        self.patient_db.commit()
        
        return {
            "id": str(row[0]),
            "question_text": row[1],
            "category": row[2],
            "is_answered": True,  # Updated value
            "created_at": row[4].isoformat() if row[4] else None,
        }



