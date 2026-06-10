"""
================================================================================
Dashboard Service - Doctor API
================================================================================

Module:         dashboard_service.py
Description:    Analytics-driven clinical monitoring dashboard service.
                Provides severity-ranked patient lists, symptom timelines,
                treatment overlays, and weekly report generation.

Created:        2025-12-20
Modified:       2026-01-16
Author:         Naveen Babu S A
Version:        2.1.0

Features:
    - Ranked patient list based on severity (urgent/severe/moderate/mild)
    - Patient symptom timeline data for zigzag visualization
    - Treatment event overlays (chemo dates, medication changes)
    - Weekly report generation with severity breakdown
    - HIPAA-compliant physician-scoped data access
    - Audit logging for all data access

Dependencies:
    - patient_db: Cross-database access to patient platform
    - doctor_db: Doctor platform database access

Copyright:
    (c) 2026 OncoLife Health Technologies. All rights reserved.
================================================================================
"""

from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, date, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import text, desc, func

from .base import BaseService
from core.logging import get_logger
from core.exceptions import NotFoundError, AuthorizationError

logger = get_logger(__name__)


class DashboardService(BaseService):
    """
    Service for doctor dashboard analytics.
    
    All queries enforce physician-level access control.
    No cross-physician data access is permitted.
    """
    
    def __init__(self, patient_db: Session, doctor_db: Session):
        """
        Initialize the dashboard service.
        
        Args:
            patient_db: Database session for patient database
            doctor_db: Database session for doctor database
        """
        super().__init__(doctor_db)
        self.patient_db = patient_db
        self.doctor_db = doctor_db
    
    # =========================================================================
    # Dashboard Landing View
    # =========================================================================
    
    def get_ranked_patient_list(
        self,
        physician_id: UUID,
        days: int = 7,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get ranked list of patients for dashboard landing view.
        
        Patients are sorted by:
        1. Has escalation (urgent symptoms) - highest priority
        2. Maximum severity in the period
        3. Most recent activity
        
        Args:
            physician_id: The physician's UUID
            days: Number of days to look back (default: 7)
            limit: Maximum patients to return
            
        Returns:
            List of patient summaries with severity info
        """
        logger.info(f"Getting ranked patient list for physician {physician_id}")
        
        # Get patient UUIDs associated with this physician
        patient_uuids = self._get_physician_patients(physician_id)
        
        if not patient_uuids:
            return []
        
        # Query for each patient's severity summary
        results = []
        for patient_uuid in patient_uuids[:limit]:
            patient_summary = self._get_patient_severity_summary(
                patient_uuid, 
                days
            )
            if patient_summary:
                results.append(patient_summary)
        
        # Sort by: has_escalation DESC, max_severity DESC, last_checkin DESC
        severity_order = {'urgent': 4, 'severe': 3, 'moderate': 2, 'mild': 1, None: 0}
        results.sort(
            key=lambda x: (
                x.get('has_escalation', False),
                severity_order.get(x.get('max_severity'), 0),
                x.get('last_checkin') or ''
            ),
            reverse=True
        )
        
        return results
    
    def _get_patient_severity_summary(
        self,
        patient_uuid: UUID,
        days: int = 7,
    ) -> Optional[Dict[str, Any]]:
        """
        Get severity summary for a patient.
        
        Returns:
            Patient summary with severity data, or None if no data
        """
        # Get patient info
        patient_result = self.patient_db.execute(
            text("""
                SELECT uuid, first_name, last_name, email_address
                FROM patient_info
                WHERE uuid = :patient_uuid AND is_deleted = false
            """),
            {"patient_uuid": str(patient_uuid)}
        )
        patient_row = patient_result.fetchone()
        
        if not patient_row:
            return None
        
        # Get severity data from conversations
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        severity_result = self.patient_db.execute(
            text("""
                SELECT 
                    MAX(created_at) as last_checkin,
                    MAX(CASE 
                        WHEN conversation_state = 'EMERGENCY' THEN 'urgent'
                        WHEN severity_list IS NOT NULL AND severity_list::text LIKE '%severe%' THEN 'severe'
                        WHEN severity_list IS NOT NULL AND severity_list::text LIKE '%moderate%' THEN 'moderate'
                        ELSE 'mild'
                    END) as max_severity,
                    BOOL_OR(conversation_state = 'EMERGENCY') as has_escalation
                FROM conversations
                WHERE patient_uuid = :patient_uuid
                AND created_at >= :cutoff_date
            """),
            {"patient_uuid": str(patient_uuid), "cutoff_date": cutoff_date}
        )
        severity_row = severity_result.fetchone()
        
        last_checkin = severity_row[0] if severity_row else None
        max_severity = severity_row[1] if severity_row and severity_row[1] else None
        has_escalation = severity_row[2] if severity_row else False
        
        return {
            "patient_uuid": str(patient_uuid),
            "first_name": patient_row[1],
            "last_name": patient_row[2],
            "email_address": patient_row[3],
            "last_checkin": last_checkin.isoformat() if last_checkin else None,
            "max_severity": max_severity,
            "has_escalation": has_escalation or False,
            "severity_badge": self._get_severity_color(max_severity),
        }
    
    def _get_severity_color(self, severity: Optional[str]) -> str:
        """Map severity to color for UI."""
        colors = {
            'urgent': 'red',
            'severe': 'orange',
            'moderate': 'yellow',
            'mild': 'green',
        }
        return colors.get(severity, 'gray')
    
    # =========================================================================
    # Patient Detail View - Timeline
    # =========================================================================
    
    def get_patient_symptom_timeline(
        self,
        patient_uuid: UUID,
        physician_id: UUID,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get symptom timeline data for a patient.
        
        Returns data for multi-line time series chart:
        - Each symptom = one line
        - X-axis = time (days)
        - Y-axis = severity (1-4 ordinal scale)
        
        Args:
            patient_uuid: The patient's UUID
            physician_id: The requesting physician's UUID (for auth)
            days: Number of days to look back
            
        Returns:
            Timeline data with symptom series and treatment overlays
        """
        logger.info(f"Getting symptom timeline for patient {patient_uuid}")
        
        # Verify authorization
        if not self._is_authorized_for_patient(patient_uuid, physician_id):
            raise AuthorizationError(
                f"Physician {physician_id} not authorized to view patient {patient_uuid}"
            )
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get symptom data from conversations
        symptom_result = self.patient_db.execute(
            text("""
                SELECT 
                    symptom_list,
                    severity_list,
                    created_at,
                    uuid as session_id
                FROM conversations
                WHERE patient_uuid = :patient_uuid
                AND created_at >= :cutoff_date
                AND symptom_list IS NOT NULL
                ORDER BY created_at ASC
            """),
            {"patient_uuid": str(patient_uuid), "cutoff_date": cutoff_date}
        )
        
        # Process into timeline format
        symptom_series = {}
        for row in symptom_result.fetchall():
            symptom_list = row[0] if row[0] else []
            severity_list = row[1] if row[1] else []
            recorded_at = row[2]
            
            for i, symptom in enumerate(symptom_list):
                if symptom not in symptom_series:
                    symptom_series[symptom] = []
                
                severity = severity_list[i] if i < len(severity_list) else 'mild'
                severity_numeric = {'mild': 1, 'moderate': 2, 'severe': 3, 'urgent': 4}.get(severity, 1)
                
                symptom_series[symptom].append({
                    "date": recorded_at.isoformat() if recorded_at else None,
                    "severity": severity,
                    "severity_numeric": severity_numeric,
                })
        
        # Get treatment events
        treatment_events = self._get_treatment_events(patient_uuid, days)
        
        return {
            "patient_uuid": str(patient_uuid),
            "period_days": days,
            "symptom_series": symptom_series,
            "treatment_events": treatment_events,
        }
    
    def _get_treatment_events(
        self,
        patient_uuid: UUID,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get treatment events for timeline overlay.
        
        Falls back to chemo_dates table if treatment_events doesn't exist.
        """
        cutoff_date = date.today() - timedelta(days=days)
        
        # Try chemo_dates first (existing table)
        try:
            chemo_result = self.patient_db.execute(
                text("""
                    SELECT chemo_date, created_at
                    FROM patient_chemo_dates
                    WHERE patient_uuid = :patient_uuid
                    AND chemo_date >= :cutoff_date
                    ORDER BY chemo_date ASC
                """),
                {"patient_uuid": str(patient_uuid), "cutoff_date": cutoff_date}
            )
            
            events = []
            for row in chemo_result.fetchall():
                events.append({
                    "event_type": "chemo_date",
                    "event_date": row[0].isoformat() if row[0] else None,
                    "metadata": {},
                })
            
            return events
        except Exception as e:
            logger.warning(f"Error getting treatment events: {e}")
            return []
    
    # =========================================================================
    # Patient Questions (Shared Only)
    # =========================================================================
    
    def get_patient_shared_questions(
        self,
        patient_uuid: UUID,
        physician_id: UUID,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get shared questions for a patient (physician view).
        
        Only returns questions where share_with_physician = true.
        
        Args:
            patient_uuid: The patient's UUID
            physician_id: The requesting physician's UUID
            limit: Maximum questions to return
            
        Returns:
            List of shared questions
        """
        logger.info(f"Getting shared questions for patient {patient_uuid}")
        
        # Verify authorization
        if not self._is_authorized_for_patient(patient_uuid, physician_id):
            raise AuthorizationError(
                f"Physician {physician_id} not authorized to view patient {patient_uuid}"
            )
        
        try:
            result = self.patient_db.execute(
                text("""
                    SELECT id, question_text, category, is_answered, created_at
                    FROM patient_questions
                    WHERE patient_uuid = :patient_uuid
                    AND share_with_physician = true
                    AND is_deleted = false
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"patient_uuid": str(patient_uuid), "limit": limit}
            )
            
            questions = []
            for row in result.fetchall():
                questions.append({
                    "id": str(row[0]),
                    "question_text": row[1],
                    "category": row[2],
                    "is_answered": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                })
            
            return questions
        except Exception as e:
            logger.warning(f"Error getting patient questions: {e}")
            return []
    
    # =========================================================================
    # Weekly Reports
    # =========================================================================
    
    def get_weekly_report_data(
        self,
        physician_id: UUID,
        week_start: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Get data for weekly physician report.
        
        Args:
            physician_id: The physician's UUID
            week_start: Start of the report week (default: last Monday)
            
        Returns:
            Report data including patient summaries, alerts, questions
        """
        logger.info(f"Generating weekly report data for physician {physician_id}")
        
        if not week_start:
            # Default to last Monday
            today = date.today()
            week_start = today - timedelta(days=today.weekday() + 7)
        
        week_end = week_start + timedelta(days=6)
        
        # Get all patients for this physician
        patient_uuids = self._get_physician_patients(physician_id)
        
        # Compile report data
        patient_summaries = []
        total_alerts = 0
        total_questions = 0
        
        for patient_uuid in patient_uuids:
            # Get patient info
            patient_info = self._get_patient_info(patient_uuid)
            if not patient_info:
                continue
            
            # Get symptom data for the week
            symptom_data = self._get_weekly_symptoms(patient_uuid, week_start, week_end)
            
            # Get alerts
            alerts = self._get_weekly_alerts(patient_uuid, week_start, week_end)
            total_alerts += len(alerts)
            
            # Get shared questions
            questions = self.get_patient_shared_questions(
                patient_uuid, 
                physician_id,
                limit=10
            )
            total_questions += len(questions)
            
            patient_summaries.append({
                "patient": patient_info,
                "symptoms": symptom_data,
                "alerts": alerts,
                "questions": questions,
            })
        
        return {
            "physician_id": str(physician_id),
            "report_week_start": week_start.isoformat(),
            "report_week_end": week_end.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "patient_count": len(patient_summaries),
            "total_alerts": total_alerts,
            "total_questions": total_questions,
            "patients": patient_summaries,
        }
    
    def _get_weekly_symptoms(
        self,
        patient_uuid: UUID,
        week_start: date,
        week_end: date,
    ) -> Dict[str, Any]:
        """Get symptom summary for the week."""
        result = self.patient_db.execute(
            text("""
                SELECT symptom_list, severity_list
                FROM conversations
                WHERE patient_uuid = :patient_uuid
                AND DATE(created_at) BETWEEN :week_start AND :week_end
            """),
            {
                "patient_uuid": str(patient_uuid),
                "week_start": week_start,
                "week_end": week_end,
            }
        )
        
        all_symptoms = []
        max_severity = 'mild'
        severity_order = {'mild': 1, 'moderate': 2, 'severe': 3, 'urgent': 4}
        
        for row in result.fetchall():
            symptoms = row[0] if row[0] else []
            severities = row[1] if row[1] else []
            
            all_symptoms.extend(symptoms)
            for sev in severities:
                if severity_order.get(sev, 0) > severity_order.get(max_severity, 0):
                    max_severity = sev
        
        return {
            "symptom_count": len(all_symptoms),
            "unique_symptoms": list(set(all_symptoms)),
            "max_severity": max_severity,
        }
    
    def _get_weekly_alerts(
        self,
        patient_uuid: UUID,
        week_start: date,
        week_end: date,
    ) -> List[Dict[str, Any]]:
        """Get alerts for the week."""
        result = self.patient_db.execute(
            text("""
                SELECT uuid, conversation_state, symptom_list, created_at
                FROM conversations
                WHERE patient_uuid = :patient_uuid
                AND DATE(created_at) BETWEEN :week_start AND :week_end
                AND conversation_state IN ('EMERGENCY', 'COMPLETED')
            """),
            {
                "patient_uuid": str(patient_uuid),
                "week_start": week_start,
                "week_end": week_end,
            }
        )
        
        alerts = []
        for row in result.fetchall():
            if row[2]:  # Has symptoms
                alerts.append({
                    "conversation_uuid": str(row[0]),
                    "triage_level": "call_911" if row[1] == "EMERGENCY" else "notify_care_team",
                    "symptoms": row[2],
                    "date": row[3].isoformat() if row[3] else None,
                })
        
        return alerts
    
    # =========================================================================
    # Authorization & Helpers
    # =========================================================================
    
    def _get_physician_patients(self, physician_id: UUID) -> List[UUID]:
        """Get all patient UUIDs for a physician."""
        result = self.patient_db.execute(
            text("""
                SELECT patient_uuid
                FROM patient_physician_associations
                WHERE physician_uuid = :physician_id
                AND is_deleted = false
            """),
            {"physician_id": str(physician_id)}
        )
        
        # PostgreSQL may return UUID objects directly, so convert to string first
        return [UUID(str(row[0])) for row in result.fetchall()]
    
    def _is_authorized_for_patient(
        self,
        patient_uuid: UUID,
        physician_id: UUID,
    ) -> bool:
        """Check if physician is authorized to access patient data."""
        result = self.patient_db.execute(
            text("""
                SELECT COUNT(*) FROM patient_physician_associations
                WHERE patient_uuid = :patient_uuid
                AND physician_uuid = :physician_id
                AND is_deleted = false
            """),
            {"patient_uuid": str(patient_uuid), "physician_id": str(physician_id)}
        )
        
        count = result.fetchone()[0]
        return count > 0
    
    def _get_patient_info(self, patient_uuid: UUID) -> Optional[Dict[str, Any]]:
        """Get basic patient info."""
        result = self.patient_db.execute(
            text("""
                SELECT uuid, first_name, last_name, email_address, dob
                FROM patient_info
                WHERE uuid = :patient_uuid AND is_deleted = false
            """),
            {"patient_uuid": str(patient_uuid)}
        )
        
        row = result.fetchone()
        if not row:
            return None
        
        return {
            "uuid": str(row[0]),
            "first_name": row[1],
            "last_name": row[2],
            "email_address": row[3],
            "dob": str(row[4]) if row[4] else None,
        }



