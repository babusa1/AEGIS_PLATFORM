"""
OCR Service - AWS Textract Integration with Per-Field Confidence.

This service processes referral documents using AWS Textract to extract
patient and treatment information from clinic fax referrals.

Features:
- Asynchronous document processing (for large multi-page faxes)
- Synchronous processing (for single-page documents)
- Form and table extraction
- PER-FIELD confidence scoring with thresholds
- Automatic REQUIRES_MANUAL_REVIEW flagging
- Medical field parsing (dates, names, medications, etc.)

Confidence Thresholds (per spec):
    Patient Name: ≥ 0.95
    DOB: ≥ 0.98
    Phone: ≥ 0.95
    Email: ≥ 0.95
    Cancer Type: ≥ 0.90
    Chemo Plan Name: ≥ 0.90
    Start/End Dates: ≥ 0.95
    Medications: ≥ 0.90

Usage:
    from services import OCRService
    
    ocr_service = OCRService()
    result = await ocr_service.process_document(s3_bucket, s3_key)
"""

import re
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
import asyncio

import boto3
from botocore.exceptions import ClientError

from core.config import settings
from core.logging import get_logger
from core.exceptions import ExternalServiceError, ValidationError

logger = get_logger(__name__)


# =============================================================================
# CONFIDENCE THRESHOLDS (Per Spec)
# =============================================================================

OCR_CONFIDENCE_THRESHOLDS = {
    # Patient Identifiers (Visible to Patient) - HIGH THRESHOLD
    "patient_name": 0.95,
    "patient_first_name": 0.95,
    "patient_last_name": 0.95,
    "patient_dob": 0.98,  # DOB requires highest confidence
    "patient_phone": 0.95,
    "patient_email": 0.95,
    
    # Provider Information
    "attending_physician_name": 0.90,
    "clinic_name": 0.90,
    
    # Cancer & Treatment (Patient-Facing)
    "cancer_type": 0.90,
    "cancer_staging": 0.85,  # Optional field, lower threshold OK
    "line_of_treatment": 0.90,
    "chemo_plan_name": 0.90,
    "chemo_start_date": 0.95,
    "chemo_end_date": 0.95,
    
    # Medications
    "medication_name": 0.90,
    "medication_dose": 0.85,
    
    # Clinical Context (NOT Displayed to Patient) - Lower thresholds OK
    "history_of_cancer": 0.75,
    "past_medical_history": 0.75,
    "past_surgical_history": 0.75,
    "bmi": 0.90,
    "height": 0.85,
    "weight": 0.85,
    "blood_pressure": 0.85,
    "pulse": 0.85,
    "spo2": 0.85,
}


@dataclass
class ExtractedField:
    """
    Represents a single extracted field with confidence tracking.
    
    Attributes:
        field_name: Name of the field (e.g., "patient_first_name")
        field_category: Category (patient, provider, diagnosis, treatment, etc.)
        extracted_value: Raw extracted value
        normalized_value: Cleaned/formatted value
        confidence_score: OCR confidence (0.0 to 1.0)
        confidence_threshold: Required threshold for this field
        is_acceptable: True if confidence >= threshold
        requires_review: True if confidence < threshold
        source_page: Which page of the document
        source_location: Bounding box coordinates (optional)
    """
    field_name: str
    field_category: str
    extracted_value: str
    normalized_value: Optional[str] = None
    confidence_score: float = 0.0
    confidence_threshold: float = 0.85
    is_acceptable: bool = False
    requires_review: bool = True
    source_page: int = 1
    source_location: Optional[Dict] = None
    
    def __post_init__(self):
        """Calculate acceptability based on confidence."""
        self.confidence_threshold = OCR_CONFIDENCE_THRESHOLDS.get(
            self.field_name, 0.85
        )
        self.is_acceptable = self.confidence_score >= self.confidence_threshold
        self.requires_review = not self.is_acceptable
        
        # Set normalized value if not provided
        if self.normalized_value is None:
            self.normalized_value = self.extracted_value
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return asdict(self)


@dataclass
class OCRResult:
    """
    Complete result of OCR processing.
    
    Contains all extracted fields, overall statistics, and
    flags for manual review requirements.
    """
    raw_text: str
    forms: Dict[str, str]
    tables: List[List[str]]
    page_count: int
    overall_confidence: float
    
    # Per-field extracted data
    extracted_fields: List[ExtractedField] = field(default_factory=list)
    
    # Grouped data for easy access
    patient_data: Dict[str, Any] = field(default_factory=dict)
    provider_data: Dict[str, Any] = field(default_factory=dict)
    diagnosis_data: Dict[str, Any] = field(default_factory=dict)
    treatment_data: Dict[str, Any] = field(default_factory=dict)
    vitals_data: Dict[str, Any] = field(default_factory=dict)
    medications_data: List[Dict] = field(default_factory=list)
    
    # Review tracking
    requires_manual_review: bool = False
    fields_needing_review: List[str] = field(default_factory=list)
    
    def add_field(self, extracted_field: ExtractedField):
        """Add an extracted field and update review status."""
        self.extracted_fields.append(extracted_field)
        
        if extracted_field.requires_review:
            self.requires_manual_review = True
            self.fields_needing_review.append(extracted_field.field_name)
    
    def get_field(self, field_name: str) -> Optional[ExtractedField]:
        """Get a specific field by name."""
        for f in self.extracted_fields:
            if f.field_name == field_name:
                return f
        return None
    
    def get_acceptable_fields(self) -> List[ExtractedField]:
        """Get all fields that meet confidence threshold."""
        return [f for f in self.extracted_fields if f.is_acceptable]
    
    def get_review_fields(self) -> List[ExtractedField]:
        """Get all fields that need review."""
        return [f for f in self.extracted_fields if f.requires_review]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "raw_text": self.raw_text,
            "forms": self.forms,
            "tables": self.tables,
            "page_count": self.page_count,
            "overall_confidence": self.overall_confidence,
            "extracted_fields": [f.to_dict() for f in self.extracted_fields],
            "patient_data": self.patient_data,
            "provider_data": self.provider_data,
            "diagnosis_data": self.diagnosis_data,
            "treatment_data": self.treatment_data,
            "vitals_data": self.vitals_data,
            "medications_data": self.medications_data,
            "requires_manual_review": self.requires_manual_review,
            "fields_needing_review": self.fields_needing_review,
        }


class OCRService:
    """
    AWS Textract OCR service for processing referral documents.
    
    Provides:
    - Document text extraction
    - Form field extraction
    - Table extraction
    - Per-field confidence tracking
    - Smart field parsing for medical data
    - Automatic review flagging
    """
    
    # Field patterns for extracting specific data
    PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"(?:\+1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
        "date_mdy": r"\d{1,2}/\d{1,2}/\d{2,4}",
        "date_iso": r"\d{4}-\d{2}-\d{2}",
        "mrn": r"(?:MRN|Medical Record Number|Patient ID)[:\s#]*([A-Z0-9-]+)",
        "bmi": r"BMI[:\s]*(\d+\.?\d*)",
        "height": r"Height[:\s]*(\d+)['\"]?\s*(\d+)?",
        "weight": r"Weight[:\s]*(\d+\.?\d*)\s*(kg|lb|lbs)?",
        "bp": r"(?:BP|Blood Pressure)[:\s]*(\d{2,3}/\d{2,3})",
        "pulse": r"(?:Pulse|Heart Rate|HR)[:\s]*(\d{2,3})",
        "spo2": r"(?:SpO2|O2 Sat|Oxygen)[:\s]*(\d{2,3})%?",
        "temp": r"(?:Temp|Temperature)[:\s]*(\d{2,3}\.?\d*)\s*°?([FCfc])?",
    }
    
    # Keywords for section identification
    SECTION_KEYWORDS = {
        "patient_info": ["patient", "demographics", "name", "dob", "date of birth"],
        "physician": ["physician", "provider", "doctor", "attending", "referring"],
        "diagnosis": ["diagnosis", "cancer", "staging", "tumor", "malignancy"],
        "treatment": ["treatment", "chemotherapy", "regimen", "plan", "cycle"],
        "history": ["history", "medical history", "surgical history", "past medical"],
        "medications": ["medications", "meds", "current medications", "drugs"],
        "vitals": ["vitals", "height", "weight", "bmi", "blood pressure"],
        "labs": ["labs", "laboratory", "results", "cbc", "cmp"],
        "social": ["social", "tobacco", "alcohol", "drug use", "smoking"],
    }
    
    def __init__(self, textract_client: Optional[Any] = None, s3_client: Optional[Any] = None):
        """
        Initialize the OCR service.
        
        Args:
            textract_client: AWS Textract client (optional)
            s3_client: AWS S3 client (optional)
        """
        self._textract_client = textract_client
        self._s3_client = s3_client
        self.aws_region = settings.aws_region
    
    @property
    def textract_client(self):
        """Get or create Textract client."""
        if self._textract_client is None:
            self._textract_client = boto3.client(
                "textract",
                region_name=self.aws_region,
            )
        return self._textract_client
    
    @property
    def s3_client(self):
        """Get or create S3 client."""
        if self._s3_client is None:
            self._s3_client = boto3.client(
                "s3",
                region_name=self.aws_region,
            )
        return self._s3_client
    
    # =========================================================================
    # DOCUMENT PROCESSING
    # =========================================================================
    
    async def process_document(
        self,
        s3_bucket: str,
        s3_key: str,
        use_async: bool = True,
    ) -> OCRResult:
        """
        Process a document from S3 using AWS Textract.
        
        Args:
            s3_bucket: S3 bucket name
            s3_key: S3 object key
            use_async: Use async processing for large documents
            
        Returns:
            OCRResult with all extracted data and confidence scores
            
        Raises:
            ExternalServiceError: If Textract fails
        """
        logger.info(f"Processing document: s3://{s3_bucket}/{s3_key}")
        
        try:
            if use_async:
                # Start async job
                job_id = await self._start_async_job(s3_bucket, s3_key)
                textract_result = await self._wait_for_job(job_id)
            else:
                # Synchronous processing
                textract_result = await self._process_sync(s3_bucket, s3_key)
            
            # Parse the Textract result
            parsed_data = self._parse_textract_result(textract_result)
            
            # Create OCR result
            ocr_result = OCRResult(
                raw_text=parsed_data["raw_text"],
                forms=parsed_data["forms"],
                tables=parsed_data["tables"],
                page_count=parsed_data.get("page_count", 1),
                overall_confidence=parsed_data.get("avg_confidence", 0),
            )
            
            # Extract medical fields with per-field confidence
            self._extract_medical_fields_with_confidence(
                parsed_data, 
                textract_result,
                ocr_result,
            )
            
            # Log summary
            logger.info(
                f"Document processed: {s3_key} | "
                f"Confidence: {ocr_result.overall_confidence:.2f} | "
                f"Fields: {len(ocr_result.extracted_fields)} | "
                f"Review needed: {ocr_result.requires_manual_review}"
            )
            
            return ocr_result
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(f"Textract error: {error_code} - {error_message}")
            raise ExternalServiceError(
                message=f"OCR processing failed: {error_message}",
                service_name="AWS Textract",
            )
    
    async def _start_async_job(self, s3_bucket: str, s3_key: str) -> str:
        """Start an async Textract job."""
        response = self.textract_client.start_document_analysis(
            DocumentLocation={
                "S3Object": {
                    "Bucket": s3_bucket,
                    "Name": s3_key,
                }
            },
            FeatureTypes=["FORMS", "TABLES"],
        )
        
        job_id = response["JobId"]
        logger.info(f"Started Textract job: {job_id}")
        return job_id
    
    async def _wait_for_job(
        self,
        job_id: str,
        max_wait_seconds: int = 300,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """Wait for an async Textract job to complete."""
        elapsed = 0
        
        while elapsed < max_wait_seconds:
            response = self.textract_client.get_document_analysis(JobId=job_id)
            status = response["JobStatus"]
            
            if status == "SUCCEEDED":
                logger.info(f"Textract job completed: {job_id}")
                return response
            elif status == "FAILED":
                raise ExternalServiceError(
                    message=f"Textract job failed: {response.get('StatusMessage', 'Unknown error')}",
                    service_name="AWS Textract",
                )
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        raise ExternalServiceError(
            message=f"Textract job timed out after {max_wait_seconds} seconds",
            service_name="AWS Textract",
        )
    
    async def _process_sync(self, s3_bucket: str, s3_key: str) -> Dict[str, Any]:
        """Process document synchronously (for small documents)."""
        response = self.textract_client.analyze_document(
            Document={
                "S3Object": {
                    "Bucket": s3_bucket,
                    "Name": s3_key,
                }
            },
            FeatureTypes=["FORMS", "TABLES"],
        )
        return response
    
    # =========================================================================
    # RESULT PARSING
    # =========================================================================
    
    def _parse_textract_result(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Textract response into structured data."""
        blocks = response.get("Blocks", [])
        
        raw_text_lines = []
        forms = {}
        tables = []
        confidences = []
        
        # Create block lookup for relationships
        block_map = {block["Id"]: block for block in blocks}
        
        for block in blocks:
            block_type = block.get("BlockType")
            confidence = block.get("Confidence", 0)
            confidences.append(confidence)
            
            if block_type == "LINE":
                raw_text_lines.append(block.get("Text", ""))
            
            elif block_type == "KEY_VALUE_SET":
                if "KEY" in block.get("EntityTypes", []):
                    key_text = self._get_text_from_block(block, block_map)
                    value_block_id = self._get_value_block_id(block)
                    if value_block_id:
                        value_text = self._get_text_from_block(
                            block_map.get(value_block_id, {}),
                            block_map,
                        )
                        if key_text:
                            forms[key_text.strip()] = value_text.strip()
            
            elif block_type == "TABLE":
                table = self._parse_table(block, block_map)
                if table:
                    tables.append(table)
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "raw_text": "\n".join(raw_text_lines),
            "forms": forms,
            "tables": tables,
            "avg_confidence": avg_confidence / 100,  # Normalize to 0-1
            "page_count": response.get("DocumentMetadata", {}).get("Pages", 1),
            "block_map": block_map,
            "blocks": blocks,
        }
    
    def _get_text_from_block(
        self,
        block: Dict[str, Any],
        block_map: Dict[str, Dict],
    ) -> str:
        """Extract text from a block and its children."""
        text_parts = []
        
        if "Relationships" in block:
            for rel in block["Relationships"]:
                if rel["Type"] == "CHILD":
                    for child_id in rel["Ids"]:
                        child_block = block_map.get(child_id, {})
                        if child_block.get("BlockType") == "WORD":
                            text_parts.append(child_block.get("Text", ""))
        
        return " ".join(text_parts)
    
    def _get_value_block_id(self, key_block: Dict[str, Any]) -> Optional[str]:
        """Get the value block ID from a key block."""
        if "Relationships" in key_block:
            for rel in key_block["Relationships"]:
                if rel["Type"] == "VALUE":
                    return rel["Ids"][0] if rel["Ids"] else None
        return None
    
    def _get_block_confidence(
        self,
        block: Dict[str, Any],
        block_map: Dict[str, Dict],
    ) -> float:
        """Get average confidence for a block and its children."""
        confidences = [block.get("Confidence", 0)]
        
        if "Relationships" in block:
            for rel in block["Relationships"]:
                if rel["Type"] == "CHILD":
                    for child_id in rel["Ids"]:
                        child_block = block_map.get(child_id, {})
                        if "Confidence" in child_block:
                            confidences.append(child_block["Confidence"])
        
        return sum(confidences) / len(confidences) / 100 if confidences else 0
    
    def _parse_table(
        self,
        table_block: Dict[str, Any],
        block_map: Dict[str, Dict],
    ) -> List[List[str]]:
        """Parse a table block into rows and columns."""
        cells = {}
        
        if "Relationships" not in table_block:
            return []
        
        for rel in table_block["Relationships"]:
            if rel["Type"] == "CHILD":
                for cell_id in rel["Ids"]:
                    cell_block = block_map.get(cell_id, {})
                    if cell_block.get("BlockType") == "CELL":
                        row = cell_block.get("RowIndex", 0)
                        col = cell_block.get("ColumnIndex", 0)
                        text = self._get_text_from_block(cell_block, block_map)
                        cells[(row, col)] = text
        
        if not cells:
            return []
        
        # Convert to 2D array
        max_row = max(r for r, c in cells.keys())
        max_col = max(c for r, c in cells.keys())
        
        table = []
        for row in range(1, max_row + 1):
            row_data = []
            for col in range(1, max_col + 1):
                row_data.append(cells.get((row, col), ""))
            table.append(row_data)
        
        return table
    
    # =========================================================================
    # MEDICAL FIELD EXTRACTION WITH CONFIDENCE
    # =========================================================================
    
    def _extract_medical_fields_with_confidence(
        self,
        parsed_data: Dict[str, Any],
        textract_response: Dict[str, Any],
        ocr_result: OCRResult,
    ) -> None:
        """Extract medical fields with per-field confidence tracking."""
        raw_text = parsed_data.get("raw_text", "")
        forms = parsed_data.get("forms", {})
        block_map = parsed_data.get("block_map", {})
        blocks = parsed_data.get("blocks", [])
        
        # Extract patient info
        self._extract_patient_info_with_confidence(
            forms, raw_text, blocks, block_map, ocr_result
        )
        
        # Extract physician info
        self._extract_physician_info_with_confidence(
            forms, raw_text, blocks, block_map, ocr_result
        )
        
        # Extract diagnosis
        self._extract_diagnosis_with_confidence(
            forms, raw_text, blocks, block_map, ocr_result
        )
        
        # Extract treatment
        self._extract_treatment_with_confidence(
            forms, raw_text, blocks, block_map, ocr_result
        )
        
        # Extract vitals
        self._extract_vitals_with_confidence(
            forms, raw_text, blocks, block_map, ocr_result
        )
        
        # Extract medications
        self._extract_medications_with_confidence(
            raw_text, blocks, block_map, ocr_result
        )
    
    def _add_extracted_field(
        self,
        ocr_result: OCRResult,
        field_name: str,
        field_category: str,
        value: Any,
        confidence: float,
        normalized_value: Any = None,
    ) -> None:
        """Helper to add an extracted field to the result."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return
        
        str_value = str(value).strip() if value else ""
        norm_value = str(normalized_value).strip() if normalized_value else str_value
        
        field = ExtractedField(
            field_name=field_name,
            field_category=field_category,
            extracted_value=str_value,
            normalized_value=norm_value,
            confidence_score=confidence,
        )
        
        ocr_result.add_field(field)
    
    def _extract_patient_info_with_confidence(
        self,
        forms: Dict[str, str],
        raw_text: str,
        blocks: List[Dict],
        block_map: Dict,
        ocr_result: OCRResult,
    ) -> None:
        """Extract patient demographic information with confidence."""
        patient_data = {}
        
        # Look for name in forms
        for key, value in forms.items():
            key_lower = key.lower()
            # Get confidence for this form field
            confidence = 0.85  # Default if we can't find block
            
            # Try to find the matching block for confidence
            for block in blocks:
                if block.get("BlockType") == "KEY_VALUE_SET":
                    if "KEY" in block.get("EntityTypes", []):
                        block_key = self._get_text_from_block(block, block_map)
                        if block_key.lower().strip() == key.lower().strip():
                            confidence = self._get_block_confidence(block, block_map)
                            break
            
            if "name" in key_lower and "physician" not in key_lower:
                parts = value.split()
                if len(parts) >= 2:
                    self._add_extracted_field(
                        ocr_result, "patient_first_name", "patient",
                        parts[0], confidence
                    )
                    patient_data["first_name"] = parts[0]
                    
                    self._add_extracted_field(
                        ocr_result, "patient_last_name", "patient",
                        parts[-1], confidence
                    )
                    patient_data["last_name"] = parts[-1]
                    
            elif "first" in key_lower and "name" in key_lower:
                self._add_extracted_field(
                    ocr_result, "patient_first_name", "patient",
                    value, confidence
                )
                patient_data["first_name"] = value
                
            elif "last" in key_lower and "name" in key_lower:
                self._add_extracted_field(
                    ocr_result, "patient_last_name", "patient",
                    value, confidence
                )
                patient_data["last_name"] = value
                
            elif "dob" in key_lower or "date of birth" in key_lower or "birth" in key_lower:
                parsed_date = self._parse_date(value)
                self._add_extracted_field(
                    ocr_result, "patient_dob", "patient",
                    value, confidence, str(parsed_date) if parsed_date else value
                )
                patient_data["dob"] = parsed_date
                
            elif "sex" in key_lower or "gender" in key_lower:
                self._add_extracted_field(
                    ocr_result, "patient_sex", "patient",
                    value.strip().capitalize(), confidence
                )
                patient_data["sex"] = value.strip().capitalize()
        
        # Extract email from raw text
        email_match = re.search(self.PATTERNS["email"], raw_text)
        if email_match:
            email = email_match.group(0)
            # Estimate confidence based on pattern match quality
            confidence = 0.95 if "@" in email and "." in email.split("@")[1] else 0.80
            self._add_extracted_field(
                ocr_result, "patient_email", "patient",
                email, confidence
            )
            patient_data["email"] = email
        
        # Extract phone from raw text
        phone_matches = re.findall(self.PATTERNS["phone"], raw_text)
        if phone_matches:
            phone = phone_matches[0]
            # Clean phone number
            phone_clean = re.sub(r'[^\d]', '', phone)
            confidence = 0.95 if len(phone_clean) >= 10 else 0.80
            self._add_extracted_field(
                ocr_result, "patient_phone", "patient",
                phone, confidence, phone_clean
            )
            patient_data["phone"] = phone
        
        # Extract MRN
        mrn_match = re.search(self.PATTERNS["mrn"], raw_text, re.IGNORECASE)
        if mrn_match:
            self._add_extracted_field(
                ocr_result, "patient_mrn", "patient",
                mrn_match.group(1), 0.90
            )
            patient_data["mrn"] = mrn_match.group(1)
        
        ocr_result.patient_data = patient_data
    
    def _extract_physician_info_with_confidence(
        self,
        forms: Dict[str, str],
        raw_text: str,
        blocks: List[Dict],
        block_map: Dict,
        ocr_result: OCRResult,
    ) -> None:
        """Extract physician and clinic information with confidence."""
        provider_data = {}
        
        for key, value in forms.items():
            key_lower = key.lower()
            confidence = 0.85
            
            # Find matching block for confidence
            for block in blocks:
                if block.get("BlockType") == "KEY_VALUE_SET":
                    if "KEY" in block.get("EntityTypes", []):
                        block_key = self._get_text_from_block(block, block_map)
                        if block_key.lower().strip() == key.lower().strip():
                            confidence = self._get_block_confidence(block, block_map)
                            break
            
            if "physician" in key_lower or "provider" in key_lower or "doctor" in key_lower:
                self._add_extracted_field(
                    ocr_result, "attending_physician_name", "provider",
                    value.strip(), confidence
                )
                provider_data["name"] = value.strip()
                
            elif "clinic" in key_lower or "facility" in key_lower or "department" in key_lower:
                self._add_extracted_field(
                    ocr_result, "clinic_name", "provider",
                    value.strip(), confidence
                )
                provider_data["clinic"] = value.strip()
        
        # Look for physician name patterns in text
        if "name" not in provider_data:
            physician_pattern = r"(?:Dr\.|Doctor|MD|DO)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"
            match = re.search(physician_pattern, raw_text)
            if match:
                self._add_extracted_field(
                    ocr_result, "attending_physician_name", "provider",
                    match.group(0), 0.80  # Lower confidence for regex extraction
                )
                provider_data["name"] = match.group(0)
        
        ocr_result.provider_data = provider_data
    
    def _extract_diagnosis_with_confidence(
        self,
        forms: Dict[str, str],
        raw_text: str,
        blocks: List[Dict],
        block_map: Dict,
        ocr_result: OCRResult,
    ) -> None:
        """Extract cancer diagnosis and staging with confidence."""
        diagnosis_data = {}
        
        # Look for cancer type
        cancer_patterns = [
            r"(?:carcinoma|cancer|malignancy|tumor)\s+(?:of\s+)?(?:the\s+)?(\w+(?:\s+\w+)?)",
            r"(\w+(?:\s+\w+)?)\s+(?:carcinoma|cancer|malignancy)",
        ]
        
        for pattern in cancer_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                cancer_type = match.group(0).strip()
                self._add_extracted_field(
                    ocr_result, "cancer_type", "diagnosis",
                    cancer_type, 0.85  # Regex extraction gets moderate confidence
                )
                diagnosis_data["cancer_type"] = cancer_type
                break
        
        # Look for staging
        staging_pattern = r"(?:Stage|Staging)[:\s]*([IViv0-4ABC]+)"
        match = re.search(staging_pattern, raw_text)
        if match:
            staging = match.group(1).upper()
            self._add_extracted_field(
                ocr_result, "cancer_staging", "diagnosis",
                staging, 0.85
            )
            diagnosis_data["staging"] = staging
        
        # AJCC staging
        ajcc_pattern = r"AJCC\s+(?:Stage|Staging)?[:\s]*([IViv0-4ABC]+)"
        match = re.search(ajcc_pattern, raw_text)
        if match:
            staging = match.group(1).upper()
            self._add_extracted_field(
                ocr_result, "cancer_staging", "diagnosis",
                staging, 0.90  # AJCC explicitly stated gets higher confidence
            )
            diagnosis_data["ajcc_stage"] = staging
        
        ocr_result.diagnosis_data = diagnosis_data
    
    def _extract_treatment_with_confidence(
        self,
        forms: Dict[str, str],
        raw_text: str,
        blocks: List[Dict],
        block_map: Dict,
        ocr_result: OCRResult,
    ) -> None:
        """Extract treatment/chemotherapy information with confidence."""
        treatment_data = {}
        
        for key, value in forms.items():
            key_lower = key.lower()
            confidence = 0.85
            
            # Find matching block
            for block in blocks:
                if block.get("BlockType") == "KEY_VALUE_SET":
                    if "KEY" in block.get("EntityTypes", []):
                        block_key = self._get_text_from_block(block, block_map)
                        if block_key.lower().strip() == key.lower().strip():
                            confidence = self._get_block_confidence(block, block_map)
                            break
            
            if "plan name" in key_lower or "regimen" in key_lower:
                self._add_extracted_field(
                    ocr_result, "chemo_plan_name", "treatment",
                    value.strip(), confidence
                )
                treatment_data["plan_name"] = value.strip()
                
            elif "start date" in key_lower:
                parsed_date = self._parse_date(value)
                self._add_extracted_field(
                    ocr_result, "chemo_start_date", "treatment",
                    value, confidence, str(parsed_date) if parsed_date else value
                )
                treatment_data["start_date"] = parsed_date
                
            elif "end date" in key_lower:
                parsed_date = self._parse_date(value)
                self._add_extracted_field(
                    ocr_result, "chemo_end_date", "treatment",
                    value, confidence, str(parsed_date) if parsed_date else value
                )
                treatment_data["end_date"] = parsed_date
                
            elif "cycle" in key_lower:
                cycle_match = re.search(r"(\d+)\s*(?:of|/)\s*(\d+)", value)
                if cycle_match:
                    treatment_data["current_cycle"] = int(cycle_match.group(1))
                    treatment_data["total_cycles"] = int(cycle_match.group(2))
        
        # Look for treatment goal / line of treatment
        goal_pattern = r"(?:Treatment Goal|Line of Treatment)[:\s]*(\w+)"
        match = re.search(goal_pattern, raw_text)
        if match:
            self._add_extracted_field(
                ocr_result, "line_of_treatment", "treatment",
                match.group(1), 0.85
            )
            treatment_data["line_of_treatment"] = match.group(1)
        
        ocr_result.treatment_data = treatment_data
    
    def _extract_vitals_with_confidence(
        self,
        forms: Dict[str, str],
        raw_text: str,
        blocks: List[Dict],
        block_map: Dict,
        ocr_result: OCRResult,
    ) -> None:
        """Extract vital signs with confidence."""
        vitals_data = {}
        
        # BMI
        bmi_match = re.search(self.PATTERNS["bmi"], raw_text)
        if bmi_match:
            bmi = float(bmi_match.group(1))
            self._add_extracted_field(
                ocr_result, "bmi", "vitals",
                bmi_match.group(1), 0.90, str(bmi)
            )
            vitals_data["bmi"] = bmi
        
        # Blood Pressure
        bp_match = re.search(self.PATTERNS["bp"], raw_text)
        if bp_match:
            self._add_extracted_field(
                ocr_result, "blood_pressure", "vitals",
                bp_match.group(1), 0.90
            )
            vitals_data["blood_pressure"] = bp_match.group(1)
        
        # Pulse
        pulse_match = re.search(self.PATTERNS["pulse"], raw_text)
        if pulse_match:
            pulse = int(pulse_match.group(1))
            self._add_extracted_field(
                ocr_result, "pulse", "vitals",
                pulse_match.group(1), 0.90, str(pulse)
            )
            vitals_data["pulse"] = pulse
        
        # SpO2
        spo2_match = re.search(self.PATTERNS["spo2"], raw_text)
        if spo2_match:
            spo2 = int(spo2_match.group(1))
            self._add_extracted_field(
                ocr_result, "spo2", "vitals",
                spo2_match.group(1), 0.90, str(spo2)
            )
            vitals_data["spo2"] = spo2
        
        # Height
        height_pattern = r"Height[:\s]*(\d+)['\s]?(?:ft)?\s*(\d+)?[\"']?\s*(?:in)?"
        height_match = re.search(height_pattern, raw_text, re.IGNORECASE)
        if height_match:
            feet = int(height_match.group(1))
            inches = int(height_match.group(2) or 0)
            height_cm = round((feet * 12 + inches) * 2.54, 1)
            self._add_extracted_field(
                ocr_result, "height", "vitals",
                f"{feet}'{inches}\"", 0.85, str(height_cm)
            )
            vitals_data["height_cm"] = height_cm
        
        # Weight
        weight_match = re.search(self.PATTERNS["weight"], raw_text, re.IGNORECASE)
        if weight_match:
            weight = float(weight_match.group(1))
            unit = (weight_match.group(2) or "").lower()
            if unit in ["lb", "lbs", "pounds"]:
                weight_kg = round(weight * 0.453592, 1)
            else:
                weight_kg = weight
            self._add_extracted_field(
                ocr_result, "weight", "vitals",
                f"{weight_match.group(1)} {unit}", 0.85, str(weight_kg)
            )
            vitals_data["weight_kg"] = weight_kg
        
        ocr_result.vitals_data = vitals_data
    
    def _extract_medications_with_confidence(
        self,
        raw_text: str,
        blocks: List[Dict],
        block_map: Dict,
        ocr_result: OCRResult,
    ) -> None:
        """Extract medications with confidence and categorization."""
        from services.medication_categorizer import categorize_medication
        
        medications = []
        
        # Look for medications section
        meds_pattern = r"(?:Current\s+)?(?:Outpatient\s+)?Medications[:\s]*(.+?)(?=Allergies|Past|Review|$)"
        meds_match = re.search(meds_pattern, raw_text, re.IGNORECASE | re.DOTALL)
        
        if meds_match:
            meds_text = meds_match.group(1)
            # Split by common patterns (bullets, newlines)
            med_lines = re.split(r"[•\n\r]+", meds_text)
            
            for line in med_lines:
                line = line.strip()
                if line and len(line) > 3:
                    # Try to parse medication name and dosage
                    med_match = re.match(r"([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s*(.+)?", line)
                    if med_match:
                        med_name = med_match.group(1).strip()
                        details = (med_match.group(2) or "").strip()
                        
                        # Categorize the medication
                        category, metadata = categorize_medication(med_name)
                        
                        # Add field for tracking
                        self._add_extracted_field(
                            ocr_result, "medication_name", "medication",
                            med_name, 0.85
                        )
                        
                        medications.append({
                            "name": med_name,
                            "details": details,
                            "category": category.value,
                            "confidence": 0.85,
                        })
        
        ocr_result.medications_data = medications[:20]  # Limit to 20
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string into a date object."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Try various formats
        formats = [
            "%m/%d/%Y",
            "%m/%d/%y",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    async def upload_document(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str = "application/pdf",
    ) -> Tuple[str, str]:
        """
        Upload a document to S3 for processing.
        
        Args:
            file_content: File bytes
            file_name: Original file name
            content_type: MIME type
            
        Returns:
            Tuple of (bucket, key)
        """
        bucket = settings.s3_referral_bucket
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")
        key = f"referrals/{timestamp}/{file_name}"
        
        try:
            self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=file_content,
                ContentType=content_type,
            )
            
            logger.info(f"Uploaded document: s3://{bucket}/{key}")
            return bucket, key
            
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            raise ExternalServiceError(
                message="Failed to upload document",
                service_name="AWS S3",
            )
