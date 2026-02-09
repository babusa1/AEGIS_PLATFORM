"""
NCCN Guidelines

National Comprehensive Cancer Network (NCCN) oncology guidelines.
"""

from typing import Dict, Any, List
from datetime import datetime

import structlog

from aegis.guidelines.base import BaseGuideline, GuidelineSection, GuidelineType

logger = structlog.get_logger(__name__)


class NCCNGuideline(BaseGuideline):
    """
    NCCN Oncology Guidelines.
    
    Provides structured access to NCCN guidelines for:
    - Chemotherapy dosing
    - Toxicity management
    - Supportive care
    - Surveillance
    """
    
    def __init__(self, version: str = "2024"):
        super().__init__(
            guideline_id=f"nccn-{version}",
            name="NCCN Clinical Practice Guidelines in Oncology",
            specialty="oncology",
            guideline_type=GuidelineType.NCCN,
            version=version,
        )
        
        # Load common NCCN sections
        self._load_common_sections()
    
    def _load_common_sections(self):
        """Load common NCCN guideline sections."""
        
        # Anemia Management
        self.add_section(GuidelineSection(
            section_id="nccn-anemia-management",
            title="Anemia Management in Cancer Patients",
            content="""
NCCN Guidelines for Anemia Management:

1. Hemoglobin Thresholds:
   - < 9.0 g/dL: Dose hold required, consider Epoetin Alpha evaluation
   - 9.0-10.0 g/dL: Monitor closely, consider dose reduction
   - > 10.0 g/dL: Continue treatment with monitoring

2. Evaluation:
   - Complete blood count (CBC)
   - Iron studies (ferritin, TIBC, transferrin saturation)
   - B12 and folate levels
   - Consider bone marrow evaluation if persistent

3. Treatment Options:
   - Erythropoiesis-stimulating agents (ESA)
   - Iron supplementation (if iron deficient)
   - Blood transfusion (if severe or symptomatic)

4. Monitoring:
   - Weekly CBC during treatment
   - Monitor for thrombosis risk with ESA use
            """,
            specialty="oncology",
            guideline_type=GuidelineType.NCCN,
            version=self.version,
            citations=[{
                "title": "NCCN Guidelines for Supportive Care - Anemia",
                "link": "https://www.nccn.org/guidelines/guidelines-detail",
                "year": 2024,
            }],
            keywords=["anemia", "hemoglobin", "HGB", "dose hold", "epoetin", "ESA"],
        ))
        
        # Neutropenia Management
        self.add_section(GuidelineSection(
            section_id="nccn-neutropenia-management",
            title="Neutropenia and Febrile Neutropenia Management",
            content="""
NCCN Guidelines for Neutropenia:

1. Absolute Neutrophil Count (ANC) Thresholds:
   - < 500/μL: High risk of infection
   - < 1000/μL: Moderate risk
   - Febrile neutropenia: Temperature ≥38.3°C or ≥38.0°C for >1 hour with ANC <500

2. Prophylaxis:
   - G-CSF (filgrastim, pegfilgrastim) for high-risk regimens
   - Antibiotic prophylaxis in select cases

3. Treatment of Febrile Neutropenia:
   - Immediate evaluation
   - Blood cultures and imaging
   - Broad-spectrum antibiotics
   - Consider antifungal if persistent fever

4. Dose Modifications:
   - Hold chemotherapy if ANC < 1000
   - Reduce dose by 25% for recurrent neutropenia
            """,
            specialty="oncology",
            guideline_type=GuidelineType.NCCN,
            version=self.version,
            citations=[{
                "title": "NCCN Guidelines for Supportive Care - Neutropenia",
                "link": "https://www.nccn.org/guidelines/guidelines-detail",
                "year": 2024,
            }],
            keywords=["neutropenia", "ANC", "febrile neutropenia", "G-CSF", "filgrastim"],
        ))
        
        # CTCAE Toxicity Grading
        self.add_section(GuidelineSection(
            section_id="nccn-ctcae-grading",
            title="CTCAE v5.0 Toxicity Grading",
            content="""
NCCN uses CTCAE v5.0 for toxicity grading:

Grade 1: Mild; asymptomatic or mild symptoms
Grade 2: Moderate; minimal, local or noninvasive intervention indicated
Grade 3: Severe or medically significant but not immediately life-threatening
Grade 4: Life-threatening consequences; urgent intervention indicated
Grade 5: Death related to AE

Common Toxicities:
- Nausea: Grade 3-4 requires dose modification
- Fatigue: Grade 3-4 may require dose hold
- Diarrhea: Grade 3-4 requires immediate intervention
- Neuropathy: Grade 2-3 may require dose reduction
            """,
            specialty="oncology",
            guideline_type=GuidelineType.NCCN,
            version=self.version,
            citations=[{
                "title": "CTCAE v5.0",
                "link": "https://ctep.cancer.gov/protocoldevelopment/electronic_applications/ctc.htm",
                "year": 2017,
            }],
            keywords=["CTCAE", "toxicity", "grading", "adverse events"],
        ))
    
    def check_dose_hold_criteria(
        self,
        lab_values: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Check if dose hold is required per NCCN guidelines.
        
        Args:
            lab_values: Dict of lab values (e.g., {"HGB": 8.5, "ANC": 800})
            
        Returns:
            Dict with dose hold recommendation
        """
        recommendations = []
        requires_hold = False
        
        # Check hemoglobin
        hgb = lab_values.get("HGB") or lab_values.get("hemoglobin")
        if hgb and hgb < 9.0:
            recommendations.append({
                "reason": "Hemoglobin < 9.0 g/dL",
                "guideline": "NCCN Anemia Management",
                "action": "hold_dose",
                "alternative": "Consider Epoetin Alpha evaluation",
            })
            requires_hold = True
        
        # Check ANC
        anc = lab_values.get("ANC") or lab_values.get("absolute_neutrophil_count")
        if anc and anc < 1000:
            recommendations.append({
                "reason": "ANC < 1000/μL",
                "guideline": "NCCN Neutropenia Management",
                "action": "hold_dose",
                "alternative": "Consider G-CSF support",
            })
            requires_hold = True
        
        return {
            "requires_hold": requires_hold,
            "recommendations": recommendations,
            "guideline": "NCCN",
            "version": self.version,
        }
