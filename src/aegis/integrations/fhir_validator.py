"""
FHIR Profile and Resource Validation

Validates FHIR resources against:
- Base FHIR R4 specifications
- US Core profiles
- Custom StructureDefinitions
- ValueSets and CodeSystems
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from enum import Enum
import re
import structlog

logger = structlog.get_logger(__name__)


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"


class ValidationCategory(str, Enum):
    """Categories of validation issues."""
    STRUCTURE = "structure"
    CARDINALITY = "cardinality"
    TYPE = "type"
    REFERENCE = "reference"
    BINDING = "binding"
    INVARIANT = "invariant"
    PROFILE = "profile"


@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: ValidationSeverity
    category: ValidationCategory
    location: str  # FHIRPath to the element
    message: str
    code: str | None = None  # Issue code
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of validating a FHIR resource."""
    valid: bool
    resource_type: str
    profile: str | None = None
    issues: list[ValidationIssue] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
    
    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
    
    def to_operation_outcome(self) -> dict:
        """Convert to FHIR OperationOutcome resource."""
        return {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "severity": issue.severity.value,
                    "code": issue.code or "invalid",
                    "details": {"text": issue.message},
                    "diagnostics": issue.location,
                }
                for issue in self.issues
            ]
        }


# =============================================================================
# Profile Definitions
# =============================================================================

# US Core Profile URLs
US_CORE_PROFILES = {
    "Patient": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient",
    "Practitioner": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-practitioner",
    "Organization": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-organization",
    "Condition": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition",
    "Observation": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab",
    "MedicationRequest": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-medicationrequest",
    "DiagnosticReport": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-diagnosticreport-lab",
    "Encounter": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-encounter",
    "Procedure": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-procedure",
    "AllergyIntolerance": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-allergyintolerance",
    "Immunization": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-immunization",
    "CarePlan": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-careplan",
    "Goal": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-goal",
    "DocumentReference": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-documentreference",
}

# US Core required elements by resource type
US_CORE_REQUIRED = {
    "Patient": {
        "must_have": ["identifier", "name", "gender"],
        "must_support": ["birthDate", "address", "telecom", "communication"],
    },
    "Condition": {
        "must_have": ["clinicalStatus", "verificationStatus", "category", "code", "subject"],
        "must_support": ["onset[x]", "abatement[x]", "recordedDate"],
    },
    "Observation": {
        "must_have": ["status", "category", "code", "subject"],
        "must_support": ["effective[x]", "value[x]", "dataAbsentReason"],
    },
    "MedicationRequest": {
        "must_have": ["status", "intent", "medication[x]", "subject"],
        "must_support": ["authoredOn", "requester", "dosageInstruction"],
    },
    "Encounter": {
        "must_have": ["status", "class", "type", "subject"],
        "must_support": ["period", "reasonCode", "hospitalization"],
    },
}

# ValueSet bindings
REQUIRED_BINDINGS = {
    "Patient.gender": {
        "valueSet": "http://hl7.org/fhir/ValueSet/administrative-gender",
        "strength": "required",
        "codes": ["male", "female", "other", "unknown"],
    },
    "Condition.clinicalStatus": {
        "valueSet": "http://hl7.org/fhir/ValueSet/condition-clinical",
        "strength": "required",
        "codes": ["active", "recurrence", "relapse", "inactive", "remission", "resolved"],
    },
    "Condition.verificationStatus": {
        "valueSet": "http://hl7.org/fhir/ValueSet/condition-ver-status",
        "strength": "required",
        "codes": ["unconfirmed", "provisional", "differential", "confirmed", "refuted", "entered-in-error"],
    },
    "Observation.status": {
        "valueSet": "http://hl7.org/fhir/ValueSet/observation-status",
        "strength": "required",
        "codes": ["registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"],
    },
    "MedicationRequest.status": {
        "valueSet": "http://hl7.org/fhir/ValueSet/medicationrequest-status",
        "strength": "required",
        "codes": ["active", "on-hold", "cancelled", "completed", "entered-in-error", "stopped", "draft", "unknown"],
    },
    "Encounter.status": {
        "valueSet": "http://hl7.org/fhir/ValueSet/encounter-status",
        "strength": "required",
        "codes": ["planned", "arrived", "triaged", "in-progress", "onleave", "finished", "cancelled", "entered-in-error", "unknown"],
    },
}


class FHIRProfileValidator:
    """
    Validates FHIR resources against profiles and specifications.
    
    Features:
    - Base FHIR R4 validation
    - US Core profile validation
    - Custom profile support
    - ValueSet/CodeSystem validation
    - Cardinality checking
    - Reference validation
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.
        
        Args:
            strict_mode: If True, treat warnings as errors
        """
        self.strict_mode = strict_mode
        self._loaded_profiles: dict[str, dict] = {}
        self._loaded_valuesets: dict[str, dict] = {}
    
    def validate_resource(
        self,
        resource: dict[str, Any],
        profile_url: str | None = None,
    ) -> ValidationResult:
        """
        Validate a FHIR resource.
        
        Args:
            resource: FHIR resource as dict
            profile_url: Optional profile URL to validate against
        
        Returns:
            ValidationResult
        """
        issues = []
        resource_type = resource.get("resourceType", "Unknown")
        
        # Basic structure validation
        structure_issues = self._validate_structure(resource)
        issues.extend(structure_issues)
        
        # Required elements
        required_issues = self._validate_required_elements(resource, resource_type)
        issues.extend(required_issues)
        
        # Type validation
        type_issues = self._validate_types(resource, resource_type)
        issues.extend(type_issues)
        
        # ValueSet bindings
        binding_issues = self._validate_bindings(resource, resource_type)
        issues.extend(binding_issues)
        
        # Reference validation
        reference_issues = self._validate_references(resource)
        issues.extend(reference_issues)
        
        # Profile-specific validation
        if profile_url or resource_type in US_CORE_PROFILES:
            profile = profile_url or US_CORE_PROFILES.get(resource_type)
            if profile:
                profile_issues = self._validate_profile(resource, resource_type, profile)
                issues.extend(profile_issues)
        
        # Determine if valid
        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
        
        valid = error_count == 0
        if self.strict_mode:
            valid = valid and warning_count == 0
        
        return ValidationResult(
            valid=valid,
            resource_type=resource_type,
            profile=profile_url,
            issues=issues,
        )
    
    def validate_bundle(
        self,
        bundle: dict[str, Any],
        validate_references: bool = True,
    ) -> list[ValidationResult]:
        """
        Validate a FHIR Bundle and all its entries.
        
        Returns:
            List of ValidationResults, one per entry
        """
        results = []
        
        if bundle.get("resourceType") != "Bundle":
            return [ValidationResult(
                valid=False,
                resource_type="Bundle",
                issues=[ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    location="Bundle",
                    message="Resource is not a Bundle",
                )]
            )]
        
        entries = bundle.get("entry", [])
        
        for i, entry in enumerate(entries):
            resource = entry.get("resource", {})
            if resource:
                result = self.validate_resource(resource)
                result.issues = [
                    ValidationIssue(
                        severity=issue.severity,
                        category=issue.category,
                        location=f"Bundle.entry[{i}].resource.{issue.location}",
                        message=issue.message,
                        code=issue.code,
                        details=issue.details,
                    )
                    for issue in result.issues
                ]
                results.append(result)
        
        return results
    
    def validate_valueset(
        self,
        code: str,
        system: str | None,
        valueset_url: str,
    ) -> bool:
        """
        Validate that a code is in a ValueSet.
        
        Args:
            code: The code to validate
            system: Code system URL
            valueset_url: ValueSet URL
        
        Returns:
            True if code is valid for the ValueSet
        """
        # Check predefined valuesets
        for binding_path, binding in REQUIRED_BINDINGS.items():
            if binding["valueSet"] == valueset_url:
                return code in binding["codes"]
        
        # TODO: Support external ValueSet lookup
        return True  # Default to valid for unknown ValueSets
    
    def _validate_structure(self, resource: dict) -> list[ValidationIssue]:
        """Validate basic FHIR structure."""
        issues = []
        
        # Must have resourceType
        if "resourceType" not in resource:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.STRUCTURE,
                location="",
                message="Resource must have a 'resourceType' element",
                code="invalid",
            ))
            return issues
        
        resource_type = resource["resourceType"]
        
        # Validate resourceType is known
        known_types = [
            "Patient", "Practitioner", "Organization", "Condition", "Observation",
            "MedicationRequest", "DiagnosticReport", "Encounter", "Procedure",
            "AllergyIntolerance", "Immunization", "CarePlan", "Goal", "Claim",
            "ExplanationOfBenefit", "Coverage", "DocumentReference", "Bundle",
        ]
        
        if resource_type not in known_types:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.STRUCTURE,
                location="resourceType",
                message=f"Unknown resource type: {resource_type}",
            ))
        
        return issues
    
    def _validate_required_elements(
        self,
        resource: dict,
        resource_type: str,
    ) -> list[ValidationIssue]:
        """Validate required elements are present."""
        issues = []
        
        # Common required elements
        common_required = {
            "Patient": ["identifier"],
            "Condition": ["subject", "code"],
            "Observation": ["status", "code", "subject"],
            "MedicationRequest": ["status", "intent", "subject"],
            "Encounter": ["status", "class", "subject"],
            "Procedure": ["status", "subject", "code"],
            "DiagnosticReport": ["status", "code", "subject"],
        }
        
        required = common_required.get(resource_type, [])
        
        for element in required:
            # Handle choice elements (e.g., medication[x])
            if "[x]" in element:
                base = element.replace("[x]", "")
                found = any(
                    key.startswith(base) for key in resource.keys()
                )
            else:
                found = element in resource and resource[element] is not None
            
            if not found:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.CARDINALITY,
                    location=element,
                    message=f"Required element '{element}' is missing",
                    code="required",
                ))
        
        return issues
    
    def _validate_types(
        self,
        resource: dict,
        resource_type: str,
    ) -> list[ValidationIssue]:
        """Validate element types."""
        issues = []
        
        # Type expectations for common elements
        type_expectations = {
            "id": str,
            "resourceType": str,
            "meta": dict,
            "identifier": list,
            "name": (list, dict),  # Can be list or single HumanName
            "gender": str,
            "birthDate": str,
            "address": list,
            "telecom": list,
            "status": str,
            "code": dict,
            "subject": dict,
            "patient": dict,
            "encounter": dict,
        }
        
        for element, expected_type in type_expectations.items():
            if element in resource:
                value = resource[element]
                if not isinstance(value, expected_type):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.TYPE,
                        location=element,
                        message=f"Element '{element}' has wrong type. Expected {expected_type}, got {type(value).__name__}",
                        code="invalid-type",
                    ))
        
        # Validate date formats
        date_elements = ["birthDate", "deceasedDateTime", "authoredOn", "recordedDate"]
        date_pattern = re.compile(r'^\d{4}(-\d{2}(-\d{2})?)?$')
        datetime_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
        
        for element in date_elements:
            if element in resource:
                value = resource[element]
                if isinstance(value, str):
                    if not (date_pattern.match(value) or datetime_pattern.match(value)):
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.TYPE,
                            location=element,
                            message=f"Invalid date format for '{element}': {value}",
                            code="invalid-date",
                        ))
        
        return issues
    
    def _validate_bindings(
        self,
        resource: dict,
        resource_type: str,
    ) -> list[ValidationIssue]:
        """Validate ValueSet bindings."""
        issues = []
        
        for binding_path, binding in REQUIRED_BINDINGS.items():
            # Check if this binding applies to this resource
            parts = binding_path.split(".")
            if parts[0] != resource_type:
                continue
            
            element = parts[1]
            
            if element in resource:
                value = resource[element]
                
                # Handle CodeableConcept
                if isinstance(value, dict):
                    codings = value.get("coding", [])
                    if codings:
                        code = codings[0].get("code")
                    else:
                        code = value.get("code")
                else:
                    code = value
                
                if code and code not in binding["codes"]:
                    severity = ValidationSeverity.ERROR if binding["strength"] == "required" else ValidationSeverity.WARNING
                    issues.append(ValidationIssue(
                        severity=severity,
                        category=ValidationCategory.BINDING,
                        location=element,
                        message=f"Code '{code}' is not in ValueSet {binding['valueSet']}",
                        code="code-invalid",
                        details={"allowed": binding["codes"]},
                    ))
        
        return issues
    
    def _validate_references(self, resource: dict) -> list[ValidationIssue]:
        """Validate reference elements."""
        issues = []
        
        reference_elements = ["subject", "patient", "encounter", "performer", "author", "requester"]
        
        for element in reference_elements:
            if element in resource:
                ref = resource[element]
                
                if isinstance(ref, dict):
                    reference = ref.get("reference")
                    if reference:
                        # Validate reference format
                        if not re.match(r'^[A-Za-z]+/[A-Za-z0-9\-]+$', reference):
                            # Could be a URL reference
                            if not reference.startswith("http"):
                                issues.append(ValidationIssue(
                                    severity=ValidationSeverity.WARNING,
                                    category=ValidationCategory.REFERENCE,
                                    location=element,
                                    message=f"Reference format may be invalid: {reference}",
                                ))
        
        return issues
    
    def _validate_profile(
        self,
        resource: dict,
        resource_type: str,
        profile_url: str,
    ) -> list[ValidationIssue]:
        """Validate against a specific profile."""
        issues = []
        
        # Check US Core requirements
        if "us-core" in profile_url.lower():
            us_core_req = US_CORE_REQUIRED.get(resource_type, {})
            
            # Must-have elements
            for element in us_core_req.get("must_have", []):
                if "[x]" in element:
                    base = element.replace("[x]", "")
                    found = any(key.startswith(base) for key in resource.keys())
                else:
                    found = element in resource and resource[element] is not None
                
                if not found:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.PROFILE,
                        location=element,
                        message=f"US Core profile requires element '{element}'",
                        code="profile-requirement",
                    ))
            
            # Must-support elements (warning if missing)
            for element in us_core_req.get("must_support", []):
                if "[x]" in element:
                    base = element.replace("[x]", "")
                    found = any(key.startswith(base) for key in resource.keys())
                else:
                    found = element in resource and resource[element] is not None
                
                if not found:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFORMATION,
                        category=ValidationCategory.PROFILE,
                        location=element,
                        message=f"US Core profile recommends element '{element}' (must-support)",
                        code="profile-recommendation",
                    ))
        
        return issues
    
    async def load_profile(self, profile_url: str) -> dict | None:
        """
        Load a StructureDefinition from URL.
        
        Args:
            profile_url: URL of the StructureDefinition
        
        Returns:
            StructureDefinition resource or None
        """
        if profile_url in self._loaded_profiles:
            return self._loaded_profiles[profile_url]
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                headers = {"Accept": "application/fhir+json"}
                async with session.get(profile_url, headers=headers) as response:
                    if response.status == 200:
                        profile = await response.json()
                        self._loaded_profiles[profile_url] = profile
                        return profile
        except Exception as e:
            logger.error(f"Failed to load profile: {e}")
        
        return None


# =============================================================================
# Utility Functions
# =============================================================================

def get_validator(strict_mode: bool = False) -> FHIRProfileValidator:
    """Get a FHIR validator instance."""
    return FHIRProfileValidator(strict_mode=strict_mode)


def validate_resource(resource: dict, profile: str | None = None) -> ValidationResult:
    """Convenience function to validate a resource."""
    validator = FHIRProfileValidator()
    return validator.validate_resource(resource, profile)


def validate_bundle(bundle: dict) -> list[ValidationResult]:
    """Convenience function to validate a bundle."""
    validator = FHIRProfileValidator()
    return validator.validate_bundle(bundle)
