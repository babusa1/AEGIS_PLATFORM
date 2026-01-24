"""
PRO Forms Connector

Ingests Patient-Reported Outcomes data.
"""

from datetime import datetime
from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult
from aegis_connectors.pro.parser import PROParser, PROResponse, PROInstrument

logger = structlog.get_logger(__name__)


class PROConnector(BaseConnector):
    """
    PRO Connector for Patient-Reported Outcomes.
    
    Supports:
    - FHIR QuestionnaireResponse
    - PHQ-9 (depression)
    - GAD-7 (anxiety)
    - ESAS (symptom assessment)
    - PROMIS instruments
    - Custom questionnaires
    
    Usage:
        connector = PROConnector(tenant_id="hospital-a")
        result = await connector.parse(questionnaire_response)
    """
    
    def __init__(self, tenant_id: str, source_system: str = "pro"):
        super().__init__(tenant_id, source_system)
        self.parser = PROParser()
    
    @property
    def connector_type(self) -> str:
        return "pro"
    
    async def parse(self, data: Any) -> ConnectorResult:
        """Parse PRO questionnaire response."""
        errors = []
        
        if not isinstance(data, dict):
            return ConnectorResult(success=False, errors=["Data must be a dict"])
        
        # Parse the response
        response = self.parser.parse(data)
        if not response:
            return ConnectorResult(success=False, errors=["Failed to parse PRO response"])
        
        # Transform to vertices/edges
        try:
            vertices, edges = self._transform(response)
        except Exception as e:
            errors.append(f"Transform error: {str(e)}")
            return ConnectorResult(success=False, errors=errors)
        
        logger.info(
            "PRO parse complete",
            response_id=response.response_id,
            instrument=response.instrument.value,
            answers=len(response.answers),
            score=response.total_score,
        )
        
        return ConnectorResult(
            success=True,
            vertices=vertices,
            edges=edges,
            errors=errors,
            metadata={
                "response_id": response.response_id,
                "instrument": response.instrument.value,
                "total_score": response.total_score,
                "severity": response.severity,
            },
        )
    
    async def validate(self, data: Any) -> list[str]:
        """Validate PRO data."""
        errors = []
        if not isinstance(data, dict):
            errors.append("Data must be a dict")
            return errors
        
        if data.get("resourceType") != "QuestionnaireResponse":
            errors.append("resourceType must be QuestionnaireResponse")
        
        if not data.get("subject"):
            errors.append("Missing subject (patient) reference")
        
        return errors
    
    def _transform(self, response: PROResponse) -> tuple[list[dict], list[dict]]:
        """Transform PRO response to vertices/edges."""
        vertices = []
        edges = []
        
        # Create QuestionnaireResponse vertex
        response_id = f"QuestionnaireResponse/{response.response_id}"
        patient_id = f"Patient/{response.patient_id}"
        
        response_vertex = self._create_vertex(
            label="QuestionnaireResponse",
            id=response_id,
            properties={
                "response_id": response.response_id,
                "questionnaire_id": response.questionnaire_id,
                "questionnaire_name": response.questionnaire_name,
                "instrument": response.instrument.value,
                "authored": response.authored.isoformat(),
                "status": response.status.value,
                "total_score": response.total_score,
                "severity": response.severity,
                "category": "pro",
            }
        )
        vertices.append(response_vertex)
        
        # Link to patient
        edges.append(self._create_edge(
            label="HAS_PRO_RESPONSE",
            from_label="Patient",
            from_id=patient_id,
            to_label="QuestionnaireResponse",
            to_id=response_id,
        ))
        
        # Link to encounter if present
        if response.encounter_id:
            encounter_id = f"Encounter/{response.encounter_id}"
            edges.append(self._create_edge(
                label="DOCUMENTED_IN",
                from_label="QuestionnaireResponse",
                from_id=response_id,
                to_label="Encounter",
                to_id=encounter_id,
            ))
        
        # Create Observation vertices for individual answers with scores
        for i, answer in enumerate(response.answers):
            if answer.score is not None or answer.value is not None:
                obs_id = f"Observation/{response.response_id}-{i}"
                
                obs_vertex = self._create_vertex(
                    label="Observation",
                    id=obs_id,
                    properties={
                        "category": "survey",
                        "code": answer.link_id,
                        "display": answer.question[:100] if answer.question else None,
                        "value": str(answer.value) if answer.value is not None else None,
                        "value_type": answer.value_type,
                        "score": answer.score,
                        "effective_date": response.authored.isoformat(),
                        "status": "final",
                    }
                )
                vertices.append(obs_vertex)
                
                edges.append(self._create_edge(
                    label="HAS_ANSWER",
                    from_label="QuestionnaireResponse",
                    from_id=response_id,
                    to_label="Observation",
                    to_id=obs_id,
                ))
        
        # If there's a severity score, create a summary observation
        if response.total_score is not None and response.severity:
            summary_id = f"Observation/{response.response_id}-summary"
            
            # Map instrument to LOINC code
            loinc_codes = {
                PROInstrument.PHQ9: "44261-6",
                PROInstrument.GAD7: "70274-6",
            }
            
            summary_vertex = self._create_vertex(
                label="Observation",
                id=summary_id,
                properties={
                    "category": "survey",
                    "code": loinc_codes.get(response.instrument, "survey-score"),
                    "display": f"{response.questionnaire_name} Total Score",
                    "value": response.total_score,
                    "value_type": "integer",
                    "interpretation": response.severity,
                    "effective_date": response.authored.isoformat(),
                    "status": "final",
                }
            )
            vertices.append(summary_vertex)
            
            edges.append(self._create_edge(
                label="HAS_SUMMARY_SCORE",
                from_label="QuestionnaireResponse",
                from_id=response_id,
                to_label="Observation",
                to_id=summary_id,
            ))
            
            # Also link summary to patient
            edges.append(self._create_edge(
                label="HAS_OBSERVATION",
                from_label="Patient",
                from_id=patient_id,
                to_label="Observation",
                to_id=summary_id,
            ))
        
        return vertices, edges


# Sample PHQ-9 response for testing
SAMPLE_PRO = {
    "resourceType": "QuestionnaireResponse",
    "id": "phq9-response-001",
    "questionnaire": "Questionnaire/phq-9",
    "status": "completed",
    "subject": {"reference": "Patient/PAT12345"},
    "encounter": {"reference": "Encounter/ENC001"},
    "authored": "2024-01-15T10:30:00Z",
    "item": [
        {
            "linkId": "phq9-1",
            "text": "Little interest or pleasure in doing things",
            "answer": [{"valueInteger": 2}]
        },
        {
            "linkId": "phq9-2",
            "text": "Feeling down, depressed, or hopeless",
            "answer": [{"valueInteger": 2}]
        },
        {
            "linkId": "phq9-3",
            "text": "Trouble falling or staying asleep, or sleeping too much",
            "answer": [{"valueInteger": 1}]
        },
        {
            "linkId": "phq9-4",
            "text": "Feeling tired or having little energy",
            "answer": [{"valueInteger": 2}]
        },
        {
            "linkId": "phq9-5",
            "text": "Poor appetite or overeating",
            "answer": [{"valueInteger": 1}]
        },
        {
            "linkId": "phq9-6",
            "text": "Feeling bad about yourself",
            "answer": [{"valueInteger": 1}]
        },
        {
            "linkId": "phq9-7",
            "text": "Trouble concentrating on things",
            "answer": [{"valueInteger": 1}]
        },
        {
            "linkId": "phq9-8",
            "text": "Moving or speaking slowly or being fidgety",
            "answer": [{"valueInteger": 0}]
        },
        {
            "linkId": "phq9-9",
            "text": "Thoughts of self-harm",
            "answer": [{"valueInteger": 0}]
        },
    ],
}
