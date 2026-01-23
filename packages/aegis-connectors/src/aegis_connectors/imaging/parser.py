"""
DICOM Parser

Parses DICOM metadata without requiring pydicom.
Supports JSON DICOM format and basic tag extraction.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import json
import structlog

logger = structlog.get_logger(__name__)


# Common DICOM tags
DICOM_TAGS = {
    "00080005": "specific_character_set",
    "00080008": "image_type",
    "00080016": "sop_class_uid",
    "00080018": "sop_instance_uid",
    "00080020": "study_date",
    "00080021": "series_date",
    "00080030": "study_time",
    "00080050": "accession_number",
    "00080060": "modality",
    "00080070": "manufacturer",
    "00080080": "institution_name",
    "00080090": "referring_physician",
    "00081030": "study_description",
    "0008103E": "series_description",
    "00100010": "patient_name",
    "00100020": "patient_id",
    "00100030": "patient_birth_date",
    "00100040": "patient_sex",
    "0020000D": "study_instance_uid",
    "0020000E": "series_instance_uid",
    "00200010": "study_id",
    "00200011": "series_number",
    "00200013": "instance_number",
    "00280010": "rows",
    "00280011": "columns",
    "00280030": "pixel_spacing",
    "00180050": "slice_thickness",
    "00180088": "spacing_between_slices",
}


@dataclass
class DICOMStudy:
    """DICOM Study metadata."""
    study_instance_uid: str
    study_id: str | None
    study_date: str | None
    study_time: str | None
    study_description: str | None
    accession_number: str | None
    referring_physician: str | None
    institution_name: str | None
    patient_id: str | None
    patient_name: str | None
    modalities: list[str] = field(default_factory=list)
    series: list["DICOMSeries"] = field(default_factory=list)


@dataclass
class DICOMSeries:
    """DICOM Series metadata."""
    series_instance_uid: str
    series_number: int | None
    series_description: str | None
    modality: str
    manufacturer: str | None
    instance_count: int = 0


@dataclass
class DICOMInstance:
    """DICOM Instance (image) metadata."""
    sop_instance_uid: str
    sop_class_uid: str
    instance_number: int | None
    rows: int | None
    columns: int | None


class DICOMParser:
    """
    Parses DICOM metadata.
    
    Supports:
    - DICOM JSON format
    - Extracted tag dictionaries
    """
    
    def parse_json(self, data: str | dict) -> tuple[DICOMStudy | None, list[str]]:
        """Parse DICOM JSON format."""
        errors = []
        
        try:
            if isinstance(data, str):
                data = json.loads(data)
            
            study = self._extract_study(data)
            return study, errors
            
        except Exception as e:
            errors.append(f"Parse error: {str(e)}")
            return None, errors
    
    def parse_tags(self, tags: dict) -> tuple[DICOMStudy | None, list[str]]:
        """Parse from extracted DICOM tags."""
        errors = []
        
        try:
            study_uid = tags.get("study_instance_uid") or tags.get("0020000D")
            
            if not study_uid:
                errors.append("Missing StudyInstanceUID")
                return None, errors
            
            study = DICOMStudy(
                study_instance_uid=study_uid,
                study_id=tags.get("study_id") or tags.get("00200010"),
                study_date=self._format_date(tags.get("study_date") or tags.get("00080020")),
                study_time=tags.get("study_time") or tags.get("00080030"),
                study_description=tags.get("study_description") or tags.get("00081030"),
                accession_number=tags.get("accession_number") or tags.get("00080050"),
                referring_physician=tags.get("referring_physician") or tags.get("00080090"),
                institution_name=tags.get("institution_name") or tags.get("00080080"),
                patient_id=tags.get("patient_id") or tags.get("00100020"),
                patient_name=tags.get("patient_name") or tags.get("00100010"),
            )
            
            modality = tags.get("modality") or tags.get("00080060")
            if modality:
                study.modalities = [modality]
            
            return study, errors
            
        except Exception as e:
            errors.append(f"Parse error: {str(e)}")
            return None, errors
    
    def _extract_study(self, data: dict) -> DICOMStudy:
        """Extract study from DICOM JSON."""
        def get_value(tag: str) -> Any:
            tag_data = data.get(tag, {})
            if isinstance(tag_data, dict):
                value = tag_data.get("Value", [])
                if value:
                    return value[0] if len(value) == 1 else value
            return None
        
        study = DICOMStudy(
            study_instance_uid=get_value("0020000D") or "",
            study_id=get_value("00200010"),
            study_date=self._format_date(get_value("00080020")),
            study_time=get_value("00080030"),
            study_description=get_value("00081030"),
            accession_number=get_value("00080050"),
            referring_physician=self._extract_name(get_value("00080090")),
            institution_name=get_value("00080080"),
            patient_id=get_value("00100020"),
            patient_name=self._extract_name(get_value("00100010")),
        )
        
        modality = get_value("00080060")
        if modality:
            study.modalities = [modality] if isinstance(modality, str) else modality
        
        return study
    
    def _extract_name(self, name_data: Any) -> str | None:
        """Extract name from DICOM PersonName."""
        if not name_data:
            return None
        if isinstance(name_data, str):
            return name_data
        if isinstance(name_data, dict):
            return name_data.get("Alphabetic", "")
        return str(name_data)
    
    def _format_date(self, date_str: str | None) -> str | None:
        """Format DICOM date (YYYYMMDD) to ISO."""
        if not date_str or len(date_str) < 8:
            return date_str
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except Exception:
            return date_str
    
    def validate(self, data: Any) -> list[str]:
        """Validate DICOM data."""
        errors = []
        
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                errors.append("Invalid JSON")
                return errors
        
        if not isinstance(data, dict):
            errors.append("Data must be dict or JSON string")
        
        return errors
