"""
FHIR R4 Parser

Parses FHIR R4 Bundles and extracts healthcare resources
into AEGIS data models.
"""

import json
from datetime import date, datetime
from typing import Any
from decimal import Decimal

import structlog
from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.patient import Patient as FHIRPatient
from fhir.resources.R4B.encounter import Encounter as FHIREncounter
from fhir.resources.R4B.condition import Condition as FHIRCondition
from fhir.resources.R4B.procedure import Procedure as FHIRProcedure
from fhir.resources.R4B.observation import Observation as FHIRObservation
from fhir.resources.R4B.medicationrequest import MedicationRequest as FHIRMedicationRequest
from fhir.resources.R4B.claim import Claim as FHIRClaim
from fhir.resources.R4B.practitioner import Practitioner as FHIRPractitioner
from fhir.resources.R4B.organization import Organization as FHIROrganization

from aegis.models.core import Patient, Provider, Organization
from aegis.models.clinical import Encounter, Diagnosis, Procedure, Observation, Medication
from aegis.models.financial import Claim, ClaimLine

logger = structlog.get_logger(__name__)


class FHIRParser:
    """
    Parser for FHIR R4 Bundles.
    
    Extracts resources and converts them to AEGIS data models.
    
    Usage:
        parser = FHIRParser(tenant_id="hospital_a")
        result = parser.parse_bundle(fhir_json)
        
        # Access parsed resources
        patients = result["patients"]
        encounters = result["encounters"]
    """
    
    def __init__(self, tenant_id: str = "default", source_system: str = "fhir"):
        """
        Initialize the FHIR parser.
        
        Args:
            tenant_id: Multi-tenant identifier
            source_system: Name of the source system (e.g., "epic", "cerner")
        """
        self.tenant_id = tenant_id
        self.source_system = source_system
        
        # Reference maps for linking resources
        self._patient_map: dict[str, Patient] = {}
        self._encounter_map: dict[str, Encounter] = {}
        self._practitioner_map: dict[str, Provider] = {}
        self._organization_map: dict[str, Organization] = {}
    
    def parse_bundle(self, fhir_data: str | dict) -> dict[str, list]:
        """
        Parse a FHIR Bundle and extract all resources.
        
        Args:
            fhir_data: FHIR Bundle as JSON string or dict
            
        Returns:
            Dictionary with lists of parsed resources by type
        """
        # Parse JSON if string
        if isinstance(fhir_data, str):
            fhir_data = json.loads(fhir_data)
        
        # Create Bundle object
        bundle = Bundle.parse_obj(fhir_data)
        
        logger.info(
            "Parsing FHIR Bundle",
            bundle_type=bundle.type,
            entry_count=len(bundle.entry) if bundle.entry else 0,
            tenant_id=self.tenant_id,
        )
        
        # Initialize result containers
        result = {
            "patients": [],
            "providers": [],
            "organizations": [],
            "encounters": [],
            "diagnoses": [],
            "procedures": [],
            "observations": [],
            "medications": [],
            "claims": [],
        }
        
        if not bundle.entry:
            return result
        
        # First pass: Parse reference resources (Patient, Practitioner, Organization)
        for entry in bundle.entry:
            resource = entry.resource
            resource_type = resource.resource_type
            
            if resource_type == "Patient":
                patient = self._parse_patient(resource)
                result["patients"].append(patient)
                self._patient_map[f"Patient/{resource.id}"] = patient
                
            elif resource_type == "Practitioner":
                provider = self._parse_practitioner(resource)
                result["providers"].append(provider)
                self._practitioner_map[f"Practitioner/{resource.id}"] = provider
                
            elif resource_type == "Organization":
                org = self._parse_organization(resource)
                result["organizations"].append(org)
                self._organization_map[f"Organization/{resource.id}"] = org
        
        # Second pass: Parse clinical resources
        for entry in bundle.entry:
            resource = entry.resource
            resource_type = resource.resource_type
            
            if resource_type == "Encounter":
                encounter = self._parse_encounter(resource)
                result["encounters"].append(encounter)
                self._encounter_map[f"Encounter/{resource.id}"] = encounter
                
            elif resource_type == "Condition":
                diagnosis = self._parse_condition(resource)
                result["diagnoses"].append(diagnosis)
                
            elif resource_type == "Procedure":
                procedure = self._parse_procedure(resource)
                result["procedures"].append(procedure)
                
            elif resource_type == "Observation":
                observation = self._parse_observation(resource)
                result["observations"].append(observation)
                
            elif resource_type == "MedicationRequest":
                medication = self._parse_medication_request(resource)
                result["medications"].append(medication)
                
            elif resource_type == "Claim":
                claim = self._parse_claim(resource)
                result["claims"].append(claim)
        
        logger.info(
            "FHIR Bundle parsed",
            patients=len(result["patients"]),
            encounters=len(result["encounters"]),
            diagnoses=len(result["diagnoses"]),
            procedures=len(result["procedures"]),
            observations=len(result["observations"]),
            claims=len(result["claims"]),
        )
        
        return result
    
    def _parse_patient(self, fhir_patient: FHIRPatient) -> Patient:
        """Parse FHIR Patient to AEGIS Patient model."""
        # Extract MRN from identifiers
        mrn = None
        ssn = None
        for identifier in fhir_patient.identifier or []:
            if identifier.type and identifier.type.coding:
                for coding in identifier.type.coding:
                    if coding.code == "MR":
                        mrn = identifier.value
                    elif coding.code == "SS":
                        ssn = identifier.value
            elif identifier.system == "http://hl7.org/fhir/sid/us-ssn":
                ssn = identifier.value
        
        # Use first identifier as MRN if not found
        if not mrn and fhir_patient.identifier:
            mrn = fhir_patient.identifier[0].value
        
        # Extract name
        given_name = ""
        family_name = ""
        if fhir_patient.name:
            name = fhir_patient.name[0]
            given_name = name.given[0] if name.given else ""
            family_name = name.family or ""
        
        # Extract contact info
        phone = None
        email = None
        for telecom in fhir_patient.telecom or []:
            if telecom.system == "phone" and not phone:
                phone = telecom.value
            elif telecom.system == "email" and not email:
                email = telecom.value
        
        # Extract address
        address = None
        if fhir_patient.address:
            addr = fhir_patient.address[0]
            from aegis.models.core import Address
            address = Address(
                line=addr.line[0] if addr.line else None,
                city=addr.city,
                state=addr.state,
                postal_code=addr.postalCode,
            )
        
        return Patient(
            tenant_id=self.tenant_id,
            source_system=self.source_system,
            source_id=fhir_patient.id,
            mrn=mrn or fhir_patient.id,
            ssn=ssn,
            given_name=given_name,
            family_name=family_name,
            birth_date=fhir_patient.birthDate,
            gender=fhir_patient.gender or "unknown",
            phone_number=phone,
            email=email,
            address=address,
        )
    
    def _parse_practitioner(self, fhir_prac: FHIRPractitioner) -> Provider:
        """Parse FHIR Practitioner to AEGIS Provider model."""
        # Extract NPI
        npi = None
        for identifier in fhir_prac.identifier or []:
            if identifier.system == "http://hl7.org/fhir/sid/us-npi":
                npi = identifier.value
                break
        
        # Extract name
        given_name = ""
        family_name = ""
        if fhir_prac.name:
            name = fhir_prac.name[0]
            given_name = name.given[0] if name.given else ""
            family_name = name.family or ""
        
        return Provider(
            tenant_id=self.tenant_id,
            source_system=self.source_system,
            source_id=fhir_prac.id,
            npi=npi or fhir_prac.id,
            given_name=given_name,
            family_name=family_name,
        )
    
    def _parse_organization(self, fhir_org: FHIROrganization) -> Organization:
        """Parse FHIR Organization to AEGIS Organization model."""
        # Determine type
        org_type = "other"
        if fhir_org.type:
            for type_cc in fhir_org.type:
                if type_cc.coding:
                    code = type_cc.coding[0].code
                    if code in ("prov", "hosp"):
                        org_type = "hospital"
                    elif code == "ins":
                        org_type = "payer"
                    elif code == "pharm":
                        org_type = "pharmacy"
        
        return Organization(
            tenant_id=self.tenant_id,
            source_system=self.source_system,
            source_id=fhir_org.id,
            name=fhir_org.name or "Unknown",
            type=org_type,
        )
    
    def _parse_encounter(self, fhir_enc: FHIREncounter) -> Encounter:
        """Parse FHIR Encounter to AEGIS Encounter model."""
        # Get patient reference
        patient_id = None
        if fhir_enc.subject and fhir_enc.subject.reference:
            patient_ref = fhir_enc.subject.reference
            if patient_ref in self._patient_map:
                patient_id = self._patient_map[patient_ref].source_id
        
        # Determine encounter type
        enc_type = "outpatient"
        if fhir_enc.class_fhir:
            code = fhir_enc.class_fhir.code
            if code == "IMP":
                enc_type = "inpatient"
            elif code == "EMER":
                enc_type = "emergency"
            elif code == "OBSENC":
                enc_type = "observation"
        
        # Get dates
        admit_date = datetime.now()
        discharge_date = None
        if fhir_enc.period:
            if fhir_enc.period.start:
                admit_date = fhir_enc.period.start
            if fhir_enc.period.end:
                discharge_date = fhir_enc.period.end
        
        # Get attending provider
        attending_id = None
        for participant in fhir_enc.participant or []:
            if participant.individual and participant.individual.reference:
                ref = participant.individual.reference
                if ref in self._practitioner_map:
                    attending_id = self._practitioner_map[ref].source_id
                    break
        
        return Encounter(
            tenant_id=self.tenant_id,
            source_system=self.source_system,
            source_id=fhir_enc.id,
            type=enc_type,
            encounter_class=fhir_enc.class_fhir.code if fhir_enc.class_fhir else "AMB",
            status=fhir_enc.status or "finished",
            admit_date=admit_date,
            discharge_date=discharge_date,
            patient_id=patient_id or "unknown",
            attending_provider_id=attending_id,
        )
    
    def _parse_condition(self, fhir_cond: FHIRCondition) -> Diagnosis:
        """Parse FHIR Condition to AEGIS Diagnosis model."""
        # Get ICD-10 code
        icd10_code = "unknown"
        description = "Unknown condition"
        if fhir_cond.code and fhir_cond.code.coding:
            for coding in fhir_cond.code.coding:
                if coding.system and "icd-10" in coding.system.lower():
                    icd10_code = coding.code
                    description = coding.display or description
                    break
            # Fallback to first coding
            if icd10_code == "unknown" and fhir_cond.code.coding:
                icd10_code = fhir_cond.code.coding[0].code or "unknown"
                description = fhir_cond.code.coding[0].display or description
        
        # Get encounter reference
        encounter_id = None
        if fhir_cond.encounter and fhir_cond.encounter.reference:
            ref = fhir_cond.encounter.reference
            if ref in self._encounter_map:
                encounter_id = self._encounter_map[ref].source_id
        
        return Diagnosis(
            tenant_id=self.tenant_id,
            source_system=self.source_system,
            source_id=fhir_cond.id,
            icd10_code=icd10_code,
            description=description,
            type="secondary",
            rank=1,
            encounter_id=encounter_id or "unknown",
        )
    
    def _parse_procedure(self, fhir_proc: FHIRProcedure) -> Procedure:
        """Parse FHIR Procedure to AEGIS Procedure model."""
        # Get CPT code
        cpt_code = None
        description = "Unknown procedure"
        if fhir_proc.code and fhir_proc.code.coding:
            for coding in fhir_proc.code.coding:
                if coding.system and "cpt" in coding.system.lower():
                    cpt_code = coding.code
                    description = coding.display or description
                    break
            # Fallback
            if not cpt_code and fhir_proc.code.coding:
                cpt_code = fhir_proc.code.coding[0].code
                description = fhir_proc.code.coding[0].display or description
        
        # Get encounter reference
        encounter_id = None
        if fhir_proc.encounter and fhir_proc.encounter.reference:
            ref = fhir_proc.encounter.reference
            if ref in self._encounter_map:
                encounter_id = self._encounter_map[ref].source_id
        
        # Get date
        proc_date = datetime.now()
        if fhir_proc.performedDateTime:
            proc_date = fhir_proc.performedDateTime
        elif fhir_proc.performedPeriod and fhir_proc.performedPeriod.start:
            proc_date = fhir_proc.performedPeriod.start
        
        return Procedure(
            tenant_id=self.tenant_id,
            source_system=self.source_system,
            source_id=fhir_proc.id,
            cpt_code=cpt_code,
            description=description,
            procedure_date=proc_date,
            status=fhir_proc.status or "completed",
            encounter_id=encounter_id or "unknown",
        )
    
    def _parse_observation(self, fhir_obs: FHIRObservation) -> Observation:
        """Parse FHIR Observation to AEGIS Observation model."""
        # Get LOINC code
        loinc_code = None
        if fhir_obs.code and fhir_obs.code.coding:
            for coding in fhir_obs.code.coding:
                if coding.system and "loinc" in coding.system.lower():
                    loinc_code = coding.code
                    break
        
        # Determine observation type
        obs_type = "laboratory"
        if fhir_obs.category:
            for cat in fhir_obs.category:
                if cat.coding:
                    code = cat.coding[0].code
                    if code == "vital-signs":
                        obs_type = "vital-signs"
                    elif code == "imaging":
                        obs_type = "imaging"
        
        # Get value
        value = ""
        value_numeric = None
        unit = None
        if fhir_obs.valueQuantity:
            value = str(fhir_obs.valueQuantity.value)
            value_numeric = float(fhir_obs.valueQuantity.value)
            unit = fhir_obs.valueQuantity.unit
        elif fhir_obs.valueString:
            value = fhir_obs.valueString
        elif fhir_obs.valueCodeableConcept:
            value = fhir_obs.valueCodeableConcept.text or ""
        
        # Get patient reference
        patient_id = None
        if fhir_obs.subject and fhir_obs.subject.reference:
            ref = fhir_obs.subject.reference
            if ref in self._patient_map:
                patient_id = self._patient_map[ref].source_id
        
        # Get encounter reference
        encounter_id = None
        if fhir_obs.encounter and fhir_obs.encounter.reference:
            ref = fhir_obs.encounter.reference
            if ref in self._encounter_map:
                encounter_id = self._encounter_map[ref].source_id
        
        return Observation(
            tenant_id=self.tenant_id,
            source_system=self.source_system,
            source_id=fhir_obs.id,
            loinc_code=loinc_code,
            type=obs_type,
            value=value or "N/A",
            value_numeric=value_numeric,
            unit=unit,
            observation_date=fhir_obs.effectiveDateTime or datetime.now(),
            patient_id=patient_id or "unknown",
            encounter_id=encounter_id,
        )
    
    def _parse_medication_request(self, fhir_med: FHIRMedicationRequest) -> Medication:
        """Parse FHIR MedicationRequest to AEGIS Medication model."""
        # Get medication name and codes
        med_name = "Unknown medication"
        rxnorm_code = None
        
        if fhir_med.medicationCodeableConcept:
            med_name = fhir_med.medicationCodeableConcept.text or med_name
            for coding in fhir_med.medicationCodeableConcept.coding or []:
                if coding.system and "rxnorm" in coding.system.lower():
                    rxnorm_code = coding.code
                if coding.display:
                    med_name = coding.display
        
        # Get patient reference
        patient_id = None
        if fhir_med.subject and fhir_med.subject.reference:
            ref = fhir_med.subject.reference
            if ref in self._patient_map:
                patient_id = self._patient_map[ref].source_id
        
        # Get dosage
        dosage = None
        route = None
        frequency = None
        if fhir_med.dosageInstruction:
            instr = fhir_med.dosageInstruction[0]
            if instr.doseAndRate and instr.doseAndRate[0].doseQuantity:
                dose = instr.doseAndRate[0].doseQuantity
                dosage = f"{dose.value} {dose.unit}"
            if instr.route and instr.route.coding:
                route = instr.route.coding[0].display
            if instr.timing and instr.timing.code:
                frequency = instr.timing.code.text
        
        return Medication(
            tenant_id=self.tenant_id,
            source_system=self.source_system,
            source_id=fhir_med.id,
            rxnorm_code=rxnorm_code,
            name=med_name,
            dosage=dosage,
            route=route,
            frequency=frequency,
            status=fhir_med.status or "active",
            patient_id=patient_id or "unknown",
        )
    
    def _parse_claim(self, fhir_claim: FHIRClaim) -> Claim:
        """Parse FHIR Claim to AEGIS Claim model."""
        # Get claim number
        claim_number = fhir_claim.id
        for identifier in fhir_claim.identifier or []:
            if identifier.value:
                claim_number = identifier.value
                break
        
        # Get claim type
        claim_type = "professional"
        if fhir_claim.type and fhir_claim.type.coding:
            code = fhir_claim.type.coding[0].code
            if code == "institutional":
                claim_type = "institutional"
            elif code == "pharmacy":
                claim_type = "pharmacy"
        
        # Get patient reference
        patient_id = None
        if fhir_claim.patient and fhir_claim.patient.reference:
            ref = fhir_claim.patient.reference
            if ref in self._patient_map:
                patient_id = self._patient_map[ref].source_id
        
        # Get payer reference
        payer_id = None
        if fhir_claim.insurer and fhir_claim.insurer.reference:
            ref = fhir_claim.insurer.reference
            if ref in self._organization_map:
                payer_id = self._organization_map[ref].source_id
        
        # Get dates
        service_date = date.today()
        if fhir_claim.billablePeriod:
            if fhir_claim.billablePeriod.start:
                service_date = fhir_claim.billablePeriod.start.date() if hasattr(fhir_claim.billablePeriod.start, 'date') else fhir_claim.billablePeriod.start
        
        # Get total
        billed_amount = Decimal("0")
        if fhir_claim.total and fhir_claim.total.value:
            billed_amount = Decimal(str(fhir_claim.total.value))
        
        # Parse claim lines
        lines = []
        for idx, item in enumerate(fhir_claim.item or []):
            line = ClaimLine(
                tenant_id=self.tenant_id,
                source_system=self.source_system,
                source_id=f"{fhir_claim.id}-{idx+1}",
                line_number=item.sequence or idx + 1,
                cpt_code=item.productOrService.coding[0].code if item.productOrService and item.productOrService.coding else None,
                service_date=service_date,
                units=int(item.quantity.value) if item.quantity else 1,
                billed_amount=Decimal(str(item.unitPrice.value)) if item.unitPrice else Decimal("0"),
                claim_id=claim_number,
            )
            lines.append(line)
            billed_amount += line.billed_amount * line.units
        
        return Claim(
            tenant_id=self.tenant_id,
            source_system=self.source_system,
            source_id=fhir_claim.id,
            claim_number=claim_number,
            type=claim_type,
            status="submitted",
            service_date_start=service_date,
            billed_amount=billed_amount,
            patient_id=patient_id or "unknown",
            payer_id=payer_id or "unknown",
            lines=lines,
        )
