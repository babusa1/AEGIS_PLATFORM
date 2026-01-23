"""
HL7v2 to Graph Transformer

Transforms parsed HL7v2 messages into graph vertices and edges.
"""

from datetime import datetime
from typing import Any
import structlog

from aegis_connectors.hl7v2.parser import ParsedHL7Message

logger = structlog.get_logger(__name__)


class HL7v2Transformer:
    """Transforms HL7v2 messages to graph vertices/edges."""
    
    ADT_EVENTS = {
        "A01": "admit",
        "A02": "transfer",
        "A03": "discharge",
        "A04": "register",
        "A08": "update",
    }
    
    def __init__(self, tenant_id: str, source_system: str = "hl7v2"):
        self.tenant_id = tenant_id
        self.source_system = source_system
    
    def transform(self, parsed: ParsedHL7Message) -> tuple[list[dict], list[dict]]:
        """Transform a parsed HL7v2 message to vertices and edges."""
        vertices = []
        edges = []
        
        if parsed.patient.get("patient_id"):
            patient_vertex = self._transform_patient(parsed)
            vertices.append(patient_vertex)
        
        if parsed.message_type == "ADT":
            v, e = self._transform_adt(parsed)
            vertices.extend(v)
            edges.extend(e)
        elif parsed.message_type == "ORU":
            v, e = self._transform_oru(parsed)
            vertices.extend(v)
            edges.extend(e)
        
        return vertices, edges
    
    def _base_vertex(self, label: str, id_value: str) -> dict:
        return {
            "label": label,
            "id": id_value,
            "tenant_id": self.tenant_id,
            "source_system": self.source_system,
            "created_at": datetime.utcnow().isoformat(),
        }
    
    def _transform_patient(self, parsed: ParsedHL7Message) -> dict:
        patient = parsed.patient
        patient_id = f"Patient/{patient['patient_id']}"
        
        vertex = self._base_vertex("Patient", patient_id)
        vertex.update({
            "mrn": patient.get("mrn"),
            "family_name": patient.get("family_name"),
            "given_name": patient.get("given_name"),
            "birth_date": self._format_hl7_date(patient.get("birth_date")),
            "gender": self._map_gender(patient.get("gender")),
            "city": patient.get("city"),
            "state": patient.get("state"),
            "postal_code": patient.get("postal_code"),
            "phone": patient.get("phone"),
        })
        return vertex
    
    def _transform_adt(self, parsed: ParsedHL7Message) -> tuple[list[dict], list[dict]]:
        vertices = []
        edges = []
        
        patient_id = f"Patient/{parsed.patient['patient_id']}"
        event_type = self.ADT_EVENTS.get(parsed.trigger_event, "unknown")
        
        if parsed.visit.get("visit_number"):
            visit = parsed.visit
            encounter_id = f"Encounter/{visit['visit_number']}"
            
            encounter = self._base_vertex("Encounter", encounter_id)
            encounter.update({
                "visit_number": visit.get("visit_number"),
                "patient_class": self._map_patient_class(visit.get("patient_class")),
                "location": visit.get("assigned_location"),
                "start_date": self._format_hl7_date(visit.get("admit_date")),
                "end_date": self._format_hl7_date(visit.get("discharge_date")),
                "adt_event": event_type,
                "status": self._encounter_status(parsed.trigger_event),
            })
            vertices.append(encounter)
            
            edges.append({
                "label": "HAS_ENCOUNTER",
                "from_label": "Patient",
                "from_id": patient_id,
                "to_label": "Encounter",
                "to_id": encounter_id,
                "tenant_id": self.tenant_id,
            })
        
        for dx in parsed.diagnoses:
            if dx.get("diagnosis_code"):
                dx_id = f"Condition/{parsed.patient['patient_id']}-{dx['diagnosis_code']}"
                
                condition = self._base_vertex("Condition", dx_id)
                condition.update({
                    "code": dx.get("diagnosis_code"),
                    "code_system": dx.get("coding_system"),
                    "display": dx.get("diagnosis_description"),
                })
                vertices.append(condition)
                
                edges.append({
                    "label": "HAS_CONDITION",
                    "from_label": "Patient",
                    "from_id": patient_id,
                    "to_label": "Condition",
                    "to_id": dx_id,
                    "tenant_id": self.tenant_id,
                })
        
        for ins in parsed.insurance:
            if ins.get("company_id") or ins.get("company_name"):
                ins_id = f"Coverage/{parsed.patient['patient_id']}-{ins.get('plan_id', 'unknown')}"
                
                coverage = self._base_vertex("Coverage", ins_id)
                coverage.update({
                    "payer_name": ins.get("company_name"),
                    "payer_id": ins.get("company_id"),
                    "plan_id": ins.get("plan_id"),
                    "group_number": ins.get("group_number"),
                    "policy_number": ins.get("policy_number"),
                })
                vertices.append(coverage)
                
                edges.append({
                    "label": "HAS_COVERAGE",
                    "from_label": "Patient",
                    "from_id": patient_id,
                    "to_label": "Coverage",
                    "to_id": ins_id,
                    "tenant_id": self.tenant_id,
                })
        
        return vertices, edges
    
    def _transform_oru(self, parsed: ParsedHL7Message) -> tuple[list[dict], list[dict]]:
        vertices = []
        edges = []
        
        patient_id = f"Patient/{parsed.patient['patient_id']}"
        
        for i, obs in enumerate(parsed.observations):
            if obs.get("observation_id"):
                obs_id = f"Observation/{parsed.message_control_id}-{i}"
                
                observation = self._base_vertex("Observation", obs_id)
                observation.update({
                    "code": obs.get("observation_id"),
                    "display": obs.get("observation_name"),
                    "value_string": obs.get("observation_value"),
                    "value_unit": obs.get("units"),
                    "reference_range": obs.get("reference_range"),
                    "abnormal_flag": obs.get("abnormal_flag"),
                    "status": obs.get("status"),
                    "effective_date": self._format_hl7_date(obs.get("observation_date")),
                })
                
                try:
                    observation["value_numeric"] = float(obs.get("observation_value", ""))
                except (ValueError, TypeError):
                    pass
                
                vertices.append(observation)
                
                edges.append({
                    "label": "HAS_OBSERVATION",
                    "from_label": "Patient",
                    "from_id": patient_id,
                    "to_label": "Observation",
                    "to_id": obs_id,
                    "tenant_id": self.tenant_id,
                })
        
        return vertices, edges
    
    def _format_hl7_date(self, hl7_date: str | None) -> str | None:
        if not hl7_date or len(hl7_date) < 8:
            return None
        try:
            year = hl7_date[0:4]
            month = hl7_date[4:6]
            day = hl7_date[6:8]
            return f"{year}-{month}-{day}"
        except Exception:
            return hl7_date
    
    def _map_gender(self, hl7_gender: str | None) -> str | None:
        mapping = {"M": "male", "F": "female", "O": "other", "U": "unknown"}
        return mapping.get(hl7_gender, hl7_gender)
    
    def _map_patient_class(self, hl7_class: str | None) -> str | None:
        mapping = {"I": "inpatient", "O": "outpatient", "E": "emergency"}
        return mapping.get(hl7_class, hl7_class)
    
    def _encounter_status(self, trigger_event: str) -> str:
        if trigger_event in ("A01", "A04"):
            return "in-progress"
        elif trigger_event == "A03":
            return "finished"
        return "unknown"
