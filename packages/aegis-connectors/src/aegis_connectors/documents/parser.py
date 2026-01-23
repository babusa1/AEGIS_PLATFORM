"""
Clinical Document Parser

Parses CDA/C-CDA documents and extracts metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import xml.etree.ElementTree as ET
import structlog

logger = structlog.get_logger(__name__)


# CDA namespaces
CDA_NS = {
    "cda": "urn:hl7-org:v3",
    "sdtc": "urn:hl7-org:sdtc",
}


@dataclass
class ClinicalDocument:
    """Parsed clinical document."""
    document_id: str
    document_type: str
    title: str | None
    effective_date: str | None
    patient_id: str | None
    patient_name: str | None
    author_name: str | None
    custodian: str | None
    sections: list[dict] = field(default_factory=list)
    problems: list[dict] = field(default_factory=list)
    medications: list[dict] = field(default_factory=list)
    allergies: list[dict] = field(default_factory=list)
    procedures: list[dict] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)


class DocumentParser:
    """
    Parses clinical documents.
    
    Supports CDA/C-CDA XML format.
    """
    
    def parse_cda(self, xml_data: str) -> tuple[ClinicalDocument | None, list[str]]:
        """Parse CDA/C-CDA document."""
        errors = []
        
        try:
            root = ET.fromstring(xml_data)
            
            # Register namespaces
            for prefix, uri in CDA_NS.items():
                ET.register_namespace(prefix, uri)
            
            doc = ClinicalDocument(
                document_id=self._get_id(root),
                document_type=self._get_document_type(root),
                title=self._get_text(root, ".//cda:title"),
                effective_date=self._get_date(root, ".//cda:effectiveTime"),
                patient_id=self._get_patient_id(root),
                patient_name=self._get_patient_name(root),
                author_name=self._get_author(root),
                custodian=self._get_custodian(root),
            )
            
            # Extract sections
            doc.sections = self._parse_sections(root)
            doc.problems = self._parse_problems(root)
            doc.medications = self._parse_medications(root)
            doc.allergies = self._parse_allergies(root)
            
            logger.info(
                "Parsed CDA document",
                type=doc.document_type,
                sections=len(doc.sections),
            )
            
            return doc, errors
            
        except ET.ParseError as e:
            errors.append(f"XML parse error: {str(e)}")
            return None, errors
        except Exception as e:
            errors.append(f"Parse error: {str(e)}")
            return None, errors
    
    def _get_id(self, root: ET.Element) -> str:
        """Get document ID."""
        id_elem = root.find(".//cda:id", CDA_NS)
        if id_elem is not None:
            return id_elem.get("root", "") + "." + id_elem.get("extension", "")
        return f"doc-{datetime.utcnow().timestamp()}"
    
    def _get_document_type(self, root: ET.Element) -> str:
        """Get document type from code."""
        code = root.find(".//cda:code", CDA_NS)
        if code is not None:
            return code.get("displayName", code.get("code", "Unknown"))
        return "Clinical Document"
    
    def _get_text(self, root: ET.Element, xpath: str) -> str | None:
        """Get text content from element."""
        elem = root.find(xpath, CDA_NS)
        return elem.text if elem is not None else None
    
    def _get_date(self, root: ET.Element, xpath: str) -> str | None:
        """Get date from element."""
        elem = root.find(xpath, CDA_NS)
        if elem is not None:
            value = elem.get("value", "")
            if len(value) >= 8:
                return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
        return None
    
    def _get_patient_id(self, root: ET.Element) -> str | None:
        """Get patient ID."""
        patient = root.find(".//cda:patientRole/cda:id", CDA_NS)
        if patient is not None:
            return patient.get("extension")
        return None
    
    def _get_patient_name(self, root: ET.Element) -> str | None:
        """Get patient name."""
        name = root.find(".//cda:patientRole/cda:patient/cda:name", CDA_NS)
        if name is not None:
            given = name.find("cda:given", CDA_NS)
            family = name.find("cda:family", CDA_NS)
            parts = []
            if given is not None and given.text:
                parts.append(given.text)
            if family is not None and family.text:
                parts.append(family.text)
            return " ".join(parts)
        return None
    
    def _get_author(self, root: ET.Element) -> str | None:
        """Get author name."""
        name = root.find(".//cda:author//cda:assignedPerson/cda:name", CDA_NS)
        if name is not None:
            given = name.find("cda:given", CDA_NS)
            family = name.find("cda:family", CDA_NS)
            parts = []
            if given is not None and given.text:
                parts.append(given.text)
            if family is not None and family.text:
                parts.append(family.text)
            return " ".join(parts)
        return None
    
    def _get_custodian(self, root: ET.Element) -> str | None:
        """Get custodian organization."""
        name = root.find(".//cda:custodian//cda:name", CDA_NS)
        return name.text if name is not None else None
    
    def _parse_sections(self, root: ET.Element) -> list[dict]:
        """Parse document sections."""
        sections = []
        
        for section in root.findall(".//cda:section", CDA_NS):
            code = section.find("cda:code", CDA_NS)
            title = section.find("cda:title", CDA_NS)
            
            sections.append({
                "code": code.get("code") if code is not None else None,
                "title": title.text if title is not None else None,
                "code_system": code.get("codeSystem") if code is not None else None,
            })
        
        return sections
    
    def _parse_problems(self, root: ET.Element) -> list[dict]:
        """Parse problem list section."""
        problems = []
        
        # Find problem section (LOINC 11450-4)
        for section in root.findall(".//cda:section", CDA_NS):
            code = section.find("cda:code", CDA_NS)
            if code is not None and code.get("code") == "11450-4":
                for entry in section.findall(".//cda:observation", CDA_NS):
                    value = entry.find("cda:value", CDA_NS)
                    if value is not None:
                        problems.append({
                            "code": value.get("code"),
                            "display": value.get("displayName"),
                            "code_system": value.get("codeSystem"),
                        })
        
        return problems
    
    def _parse_medications(self, root: ET.Element) -> list[dict]:
        """Parse medications section."""
        medications = []
        
        # Find medications section (LOINC 10160-0)
        for section in root.findall(".//cda:section", CDA_NS):
            code = section.find("cda:code", CDA_NS)
            if code is not None and code.get("code") == "10160-0":
                for entry in section.findall(".//cda:substanceAdministration", CDA_NS):
                    med_code = entry.find(".//cda:manufacturedProduct//cda:code", CDA_NS)
                    if med_code is not None:
                        medications.append({
                            "code": med_code.get("code"),
                            "display": med_code.get("displayName"),
                            "code_system": med_code.get("codeSystem"),
                        })
        
        return medications
    
    def _parse_allergies(self, root: ET.Element) -> list[dict]:
        """Parse allergies section."""
        allergies = []
        
        # Find allergies section (LOINC 48765-2)
        for section in root.findall(".//cda:section", CDA_NS):
            code = section.find("cda:code", CDA_NS)
            if code is not None and code.get("code") == "48765-2":
                for entry in section.findall(".//cda:observation", CDA_NS):
                    value = entry.find(".//cda:participant//cda:code", CDA_NS)
                    if value is not None:
                        allergies.append({
                            "code": value.get("code"),
                            "display": value.get("displayName"),
                        })
        
        return allergies
    
    def validate(self, data: str) -> list[str]:
        """Validate CDA document."""
        errors = []
        
        try:
            root = ET.fromstring(data)
            
            if root.tag != "{urn:hl7-org:v3}ClinicalDocument":
                if "ClinicalDocument" not in root.tag:
                    errors.append("Not a CDA document")
                    
        except ET.ParseError as e:
            errors.append(f"Invalid XML: {str(e)}")
        
        return errors
