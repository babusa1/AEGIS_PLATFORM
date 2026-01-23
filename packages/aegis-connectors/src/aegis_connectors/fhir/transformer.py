"""
FHIR to Graph Transformer

Transforms FHIR resources into graph vertices and edges.
"""

from datetime import datetime
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class FHIRTransformer:
    """
    Transforms FHIR resources to graph vertices/edges.
    
    Maps FHIR resource types to AEGIS ontology vertices.
    """
    
    def __init__(self, tenant_id: str, source_system: str = "fhir"):
        self.tenant_id = tenant_id
        self.source_system = source_system
    
    def transform(self, resource: Any) -> tuple[list[dict], list[dict]]:
        """
        Transform a FHIR resource to vertices and edges.
        
        Returns:
            Tuple of (vertices, edges)
        """
        resource_type = self._get_resource_type(resource)
        
        transformer_method = getattr(self, f"_transform_{resource_type.lower()}", None)
        
        if transformer_method:
            return transformer_method(resource)
        else:
            logger.warning(f"No transformer for {resource_type}")
            return [], []
    
    def _get_resource_type(self, resource: Any) -> str:
        if hasattr(resource, "resource_type"):
            return resource.resource_type
        elif isinstance(resource, dict):
            return resource.get("resourceType", "Unknown")
        return "Unknown"
    
    def _base_vertex(self, label: str, resource: Any) -> dict:
        """Create base vertex with common properties."""
        fhir_id = resource.id if hasattr(resource, "id") else resource.get("id")
        return {
            "label": label,
            "id": f"{label}/{fhir_id}",
            "fhir_id": fhir_id,
            "tenant_id": self.tenant_id,
            "source_system": self.source_system,
            "created_at": datetime.utcnow().isoformat(),
        }
    
    # ==================== PATIENT ====================
    
    def _transform_patient(self, patient: Any) -> tuple[list[dict], list[dict]]:
        vertex = self._base_vertex("Patient", patient)
        
        # Name
        if patient.name:
            name = patient.name[0]
            vertex["given_name"] = name.given[0] if name.given else None
            vertex["family_name"] = name.family
        
        # Demographics
        vertex["birth_date"] = str(patient.birthDate) if patient.birthDate else None
        vertex["gender"] = patient.gender
        vertex["deceased"] = patient.deceasedBoolean if hasattr(patient, "deceasedBoolean") else False
        
        # Identifiers (MRN)
        if patient.identifier:
            for ident in patient.identifier:
                if ident.type and ident.type.coding:
                    for coding in ident.type.coding:
                        if coding.code == "MR":
                            vertex["mrn"] = ident.value
                            break
        
        # Contact
        if patient.telecom:
            for telecom in patient.telecom:
                if telecom.system == "phone":
                    vertex["phone"] = telecom.value
                elif telecom.system == "email":
                    vertex["email"] = telecom.value
        
        # Address
        if patient.address:
            addr = patient.address[0]
            vertex["address_line"] = addr.line[0] if addr.line else None
            vertex["city"] = addr.city
            vertex["state"] = addr.state
            vertex["postal_code"] = addr.postalCode
            vertex["country"] = addr.country
        
        return [vertex], []
    
    # ==================== ENCOUNTER ====================
    
    def _transform_encounter(self, encounter: Any) -> tuple[list[dict], list[dict]]:
        vertex = self._base_vertex("Encounter", encounter)
        edges = []
        
        vertex["status"] = encounter.status
        vertex["encounter_class"] = encounter.class_fhir.code if encounter.class_fhir else None
        
        if encounter.period:
            vertex["start_date"] = str(encounter.period.start) if encounter.period.start else None
            vertex["end_date"] = str(encounter.period.end) if encounter.period.end else None
        
        if encounter.type:
            vertex["service_type"] = encounter.type[0].text if encounter.type[0].text else None
        
        # Edge to patient
        if encounter.subject and encounter.subject.reference:
            patient_ref = encounter.subject.reference
            edges.append({
                "label": "HAS_ENCOUNTER",
                "from_label": "Patient",
                "from_id": patient_ref,
                "to_label": "Encounter",
                "to_id": vertex["id"],
                "tenant_id": self.tenant_id,
            })
        
        return [vertex], edges
    
    # ==================== CONDITION ====================
    
    def _transform_condition(self, condition: Any) -> tuple[list[dict], list[dict]]:
        vertex = self._base_vertex("Condition", condition)
        edges = []
        
        # Code
        if condition.code and condition.code.coding:
            coding = condition.code.coding[0]
            vertex["code"] = coding.code
            vertex["code_system"] = coding.system
            vertex["display"] = coding.display
        
        vertex["clinical_status"] = condition.clinicalStatus.coding[0].code if condition.clinicalStatus else None
        vertex["verification_status"] = condition.verificationStatus.coding[0].code if condition.verificationStatus else None
        
        if condition.onsetDateTime:
            vertex["onset_date"] = str(condition.onsetDateTime)
        
        # Edge to patient
        if condition.subject and condition.subject.reference:
            edges.append({
                "label": "HAS_CONDITION",
                "from_label": "Patient",
                "from_id": condition.subject.reference,
                "to_label": "Condition",
                "to_id": vertex["id"],
                "tenant_id": self.tenant_id,
            })
        
        return [vertex], edges
    
    # ==================== OBSERVATION ====================
    
    def _transform_observation(self, obs: Any) -> tuple[list[dict], list[dict]]:
        vertex = self._base_vertex("Observation", obs)
        edges = []
        
        # Code
        if obs.code and obs.code.coding:
            coding = obs.code.coding[0]
            vertex["code"] = coding.code
            vertex["code_system"] = coding.system
            vertex["display"] = coding.display
        
        vertex["status"] = obs.status
        
        # Value
        if hasattr(obs, "valueQuantity") and obs.valueQuantity:
            vertex["value_numeric"] = obs.valueQuantity.value
            vertex["value_unit"] = obs.valueQuantity.unit
        elif hasattr(obs, "valueString") and obs.valueString:
            vertex["value_string"] = obs.valueString
        
        # Effective date
        if obs.effectiveDateTime:
            vertex["effective_date"] = str(obs.effectiveDateTime)
        
        # Edge to patient
        if obs.subject and obs.subject.reference:
            edges.append({
                "label": "HAS_OBSERVATION",
                "from_label": "Patient",
                "from_id": obs.subject.reference,
                "to_label": "Observation",
                "to_id": vertex["id"],
                "tenant_id": self.tenant_id,
            })
        
        return [vertex], edges
    
    # ==================== MEDICATION REQUEST ====================
    
    def _transform_medicationrequest(self, med: Any) -> tuple[list[dict], list[dict]]:
        vertex = self._base_vertex("MedicationRequest", med)
        edges = []
        
        vertex["status"] = med.status
        vertex["intent"] = med.intent
        
        # Medication code
        if med.medicationCodeableConcept and med.medicationCodeableConcept.coding:
            coding = med.medicationCodeableConcept.coding[0]
            vertex["medication_code"] = coding.code
            vertex["medication_name"] = coding.display
        
        # Dosage
        if med.dosageInstruction:
            dosage = med.dosageInstruction[0]
            if dosage.text:
                vertex["dosage"] = dosage.text
        
        # Authored date
        if med.authoredOn:
            vertex["start_date"] = str(med.authoredOn)
        
        # Edge to patient
        if med.subject and med.subject.reference:
            edges.append({
                "label": "HAS_MEDICATION",
                "from_label": "Patient",
                "from_id": med.subject.reference,
                "to_label": "MedicationRequest",
                "to_id": vertex["id"],
                "tenant_id": self.tenant_id,
            })
        
        return [vertex], edges
    
    # ==================== PROCEDURE ====================
    
    def _transform_procedure(self, proc: Any) -> tuple[list[dict], list[dict]]:
        vertex = self._base_vertex("Procedure", proc)
        edges = []
        
        vertex["status"] = proc.status
        
        # Code
        if proc.code and proc.code.coding:
            coding = proc.code.coding[0]
            vertex["procedure_code"] = coding.code
            vertex["code_system"] = coding.system
            vertex["display"] = coding.display
        
        # Performed date
        if proc.performedDateTime:
            vertex["procedure_date"] = str(proc.performedDateTime)
        elif proc.performedPeriod:
            vertex["procedure_date"] = str(proc.performedPeriod.start) if proc.performedPeriod.start else None
        
        # Edge to patient
        if proc.subject and proc.subject.reference:
            edges.append({
                "label": "HAS_PROCEDURE",
                "from_label": "Patient",
                "from_id": proc.subject.reference,
                "to_label": "Procedure",
                "to_id": vertex["id"],
                "tenant_id": self.tenant_id,
            })
        
        return [vertex], edges
    
    # ==================== CLAIM ====================
    
    def _transform_claim(self, claim: Any) -> tuple[list[dict], list[dict]]:
        vertex = self._base_vertex("Claim", claim)
        edges = []
        
        vertex["status"] = claim.status
        vertex["claim_type"] = claim.type.coding[0].code if claim.type and claim.type.coding else None
        
        if claim.created:
            vertex["service_date"] = str(claim.created)
        
        if claim.total:
            vertex["billed_amount"] = float(claim.total.value) if claim.total.value else None
        
        # Edge to patient
        if claim.patient and claim.patient.reference:
            edges.append({
                "label": "HAS_CLAIM",
                "from_label": "Patient",
                "from_id": claim.patient.reference,
                "to_label": "Claim",
                "to_id": vertex["id"],
                "tenant_id": self.tenant_id,
            })
        
        return [vertex], edges
    
    # ==================== PRACTITIONER ====================
    
    def _transform_practitioner(self, prac: Any) -> tuple[list[dict], list[dict]]:
        vertex = self._base_vertex("Provider", prac)
        
        # Name
        if prac.name:
            name = prac.name[0]
            vertex["given_name"] = name.given[0] if name.given else None
            vertex["family_name"] = name.family
            vertex["name"] = f"{vertex.get('given_name', '')} {vertex.get('family_name', '')}".strip()
        
        # NPI
        if prac.identifier:
            for ident in prac.identifier:
                if ident.system and "npi" in ident.system.lower():
                    vertex["npi"] = ident.value
                    break
        
        return [vertex], []
    
    # ==================== ORGANIZATION ====================
    
    def _transform_organization(self, org: Any) -> tuple[list[dict], list[dict]]:
        vertex = self._base_vertex("Organization", org)
        
        vertex["name"] = org.name
        
        if org.type:
            vertex["org_type"] = org.type[0].coding[0].code if org.type[0].coding else None
        
        return [vertex], []
