"""
Order Generator

Generates common order sets for clinical scenarios.
"""

from typing import List, Dict, Any, Optional
import structlog

from aegis.ehr.request_group import RequestGroupBuilder

logger = structlog.get_logger(__name__)


class OrderGenerator:
    """
    Generates common order sets for clinical scenarios.
    
    Provides pre-configured order sets for:
    - Basic metabolic panel
    - Complete blood count
    - Imaging studies
    - Common medications
    """
    
    @staticmethod
    def generate_basic_metabolic_panel(
        patient_id: str,
        encounter_id: Optional[str] = None,
    ) -> RequestGroupBuilder:
        """Generate basic metabolic panel order set."""
        builder = RequestGroupBuilder(patient_id, encounter_id)
        
        builder.add_lab_order(
            loinc_code="24323-8",  # Comprehensive Metabolic Panel
            display_name="Comprehensive Metabolic Panel",
            priority="routine",
        )
        
        return builder
    
    @staticmethod
    def generate_complete_blood_count(
        patient_id: str,
        encounter_id: Optional[str] = None,
    ) -> RequestGroupBuilder:
        """Generate complete blood count order set."""
        builder = RequestGroupBuilder(patient_id, encounter_id)
        
        builder.add_lab_order(
            loinc_code="58410-2",  # Complete Blood Count
            display_name="Complete Blood Count with Differential",
            priority="routine",
        )
        
        return builder
    
    @staticmethod
    def generate_chemo_monitoring_labs(
        patient_id: str,
        encounter_id: Optional[str] = None,
    ) -> RequestGroupBuilder:
        """Generate chemotherapy monitoring lab order set."""
        builder = RequestGroupBuilder(patient_id, encounter_id)
        
        # CBC
        builder.add_lab_order(
            loinc_code="58410-2",
            display_name="Complete Blood Count",
            priority="routine",
        )
        
        # Comprehensive Metabolic Panel
        builder.add_lab_order(
            loinc_code="24323-8",
            display_name="Comprehensive Metabolic Panel",
            priority="routine",
        )
        
        # Liver function tests
        builder.add_lab_order(
            loinc_code="24325-3",  # Comprehensive Metabolic Panel with Liver
            display_name="Liver Function Tests",
            priority="routine",
        )
        
        return builder
    
    @staticmethod
    def generate_ckd_monitoring_labs(
        patient_id: str,
        encounter_id: Optional[str] = None,
    ) -> RequestGroupBuilder:
        """Generate CKD monitoring lab order set."""
        builder = RequestGroupBuilder(patient_id, encounter_id)
        
        # Basic metabolic panel (includes creatinine, K+)
        builder.add_lab_order(
            loinc_code="24323-8",
            display_name="Comprehensive Metabolic Panel",
            priority="routine",
            notes="Monitor creatinine and potassium",
        )
        
        # Urine albumin-to-creatinine ratio
        builder.add_lab_order(
            loinc_code="9318-7",  # ACR
            display_name="Urine Albumin-to-Creatinine Ratio",
            priority="routine",
        )
        
        # Hemoglobin A1C (if diabetic)
        builder.add_lab_order(
            loinc_code="4548-4",  # HbA1c
            display_name="Hemoglobin A1C",
            priority="routine",
        )
        
        return builder
