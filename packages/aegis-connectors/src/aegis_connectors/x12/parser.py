"""
X12 EDI Parser

Parses X12 healthcare transactions without external dependencies.
"""

from dataclasses import dataclass, field
from typing import Any
import re
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class X12Segment:
    """Parsed X12 segment."""
    id: str
    elements: list[str]
    
    def get(self, index: int, default: str = "") -> str:
        if index < len(self.elements):
            return self.elements[index] or default
        return default


@dataclass
class X12Loop:
    """X12 loop containing segments."""
    id: str
    segments: list[X12Segment] = field(default_factory=list)
    children: list["X12Loop"] = field(default_factory=list)


@dataclass
class ParsedX12:
    """Parsed X12 transaction."""
    transaction_type: str  # 837, 835, 270, etc.
    sender_id: str
    receiver_id: str
    control_number: str
    date: str
    claims: list[dict] = field(default_factory=list)
    remittances: list[dict] = field(default_factory=list)
    raw_segments: list[X12Segment] = field(default_factory=list)


class X12Parser:
    """
    Parses X12 EDI files.
    
    Supports:
    - 837P Professional Claims
    - 837I Institutional Claims
    - 835 Remittance Advice
    - 270/271 Eligibility
    """
    
    def __init__(self):
        self.element_sep = "*"
        self.segment_sep = "~"
        self.sub_element_sep = ":"
    
    def parse(self, data: str) -> tuple[ParsedX12 | None, list[str]]:
        """Parse X12 EDI data."""
        errors = []
        
        try:
            # Clean and normalize
            data = data.strip().replace("\n", "").replace("\r", "")
            
            # Detect separators from ISA segment
            if data.startswith("ISA"):
                self.element_sep = data[3]
                self.sub_element_sep = data[104] if len(data) > 104 else ":"
                self.segment_sep = data[105] if len(data) > 105 else "~"
            
            # Parse segments
            segments = self._parse_segments(data)
            
            if not segments:
                errors.append("No segments found")
                return None, errors
            
            # Get transaction info from ISA/GS
            isa = self._find_segment(segments, "ISA")
            gs = self._find_segment(segments, "GS")
            st = self._find_segment(segments, "ST")
            
            if not isa:
                errors.append("Missing ISA segment")
                return None, errors
            
            parsed = ParsedX12(
                transaction_type=st.get(1) if st else "",
                sender_id=isa.get(6, "").strip(),
                receiver_id=isa.get(8, "").strip(),
                control_number=isa.get(13, ""),
                date=isa.get(9, ""),
                raw_segments=segments,
            )
            
            # Parse based on transaction type
            if parsed.transaction_type in ("837", "837P", "837I"):
                parsed.claims = self._parse_837_claims(segments)
            elif parsed.transaction_type == "835":
                parsed.remittances = self._parse_835_remittances(segments)
            
            logger.info(
                "Parsed X12",
                type=parsed.transaction_type,
                claims=len(parsed.claims),
                remittances=len(parsed.remittances),
            )
            
            return parsed, errors
            
        except Exception as e:
            errors.append(f"Parse error: {str(e)}")
            logger.error("X12 parse failed", error=str(e))
            return None, errors
    
    def _parse_segments(self, data: str) -> list[X12Segment]:
        """Parse raw data into segments."""
        segments = []
        
        for seg_str in data.split(self.segment_sep):
            seg_str = seg_str.strip()
            if not seg_str:
                continue
            
            elements = seg_str.split(self.element_sep)
            if elements:
                segments.append(X12Segment(
                    id=elements[0],
                    elements=elements[1:] if len(elements) > 1 else [],
                ))
        
        return segments
    
    def _find_segment(self, segments: list[X12Segment], seg_id: str) -> X12Segment | None:
        for seg in segments:
            if seg.id == seg_id:
                return seg
        return None
    
    def _find_segments(self, segments: list[X12Segment], seg_id: str) -> list[X12Segment]:
        return [s for s in segments if s.id == seg_id]
    
    def _parse_837_claims(self, segments: list[X12Segment]) -> list[dict]:
        """Parse 837 claim segments."""
        claims = []
        current_claim = None
        current_service = None
        
        for seg in segments:
            if seg.id == "CLM":
                # New claim
                if current_claim:
                    claims.append(current_claim)
                
                current_claim = {
                    "claim_id": seg.get(0),
                    "total_charge": self._parse_amount(seg.get(1)),
                    "facility_code": seg.get(4, "").split(self.sub_element_sep)[0] if seg.get(4) else "",
                    "frequency_code": seg.get(4, "").split(self.sub_element_sep)[1] if len(seg.get(4, "").split(self.sub_element_sep)) > 1 else "",
                    "provider_signature": seg.get(5),
                    "assignment_code": seg.get(6),
                    "services": [],
                    "diagnoses": [],
                    "patient": {},
                    "subscriber": {},
                    "provider": {},
                }
                current_service = None
                
            elif seg.id == "NM1" and current_claim:
                # Name segment
                entity_code = seg.get(0)
                name_data = {
                    "last_name": seg.get(2),
                    "first_name": seg.get(3),
                    "middle_name": seg.get(4),
                    "suffix": seg.get(5),
                    "id_qualifier": seg.get(7),
                    "id": seg.get(8),
                }
                
                if entity_code == "IL":  # Insured
                    current_claim["subscriber"] = name_data
                elif entity_code == "QC":  # Patient
                    current_claim["patient"] = name_data
                elif entity_code == "85":  # Billing Provider
                    current_claim["provider"] = name_data
                    
            elif seg.id == "HI" and current_claim:
                # Diagnosis codes
                for i, element in enumerate(seg.elements):
                    if element:
                        parts = element.split(self.sub_element_sep)
                        if len(parts) >= 2:
                            current_claim["diagnoses"].append({
                                "qualifier": parts[0],
                                "code": parts[1],
                            })
                            
            elif seg.id == "SV1" and current_claim:
                # Professional service line
                current_service = {
                    "procedure_code": "",
                    "modifiers": [],
                    "charge": 0,
                    "units": 1,
                    "place_of_service": "",
                }
                
                composite = seg.get(0, "").split(self.sub_element_sep)
                if composite:
                    current_service["procedure_code"] = composite[1] if len(composite) > 1 else ""
                    current_service["modifiers"] = composite[2:6] if len(composite) > 2 else []
                
                current_service["charge"] = self._parse_amount(seg.get(1))
                current_service["unit_code"] = seg.get(2)
                current_service["units"] = self._parse_int(seg.get(3), 1)
                current_service["place_of_service"] = seg.get(4)
                
                current_claim["services"].append(current_service)
                
            elif seg.id == "DTP" and current_claim:
                # Date
                qualifier = seg.get(0)
                date_value = seg.get(2)
                
                if qualifier == "472":  # Service date
                    if current_service:
                        current_service["service_date"] = self._format_date(date_value)
                    else:
                        current_claim["service_date"] = self._format_date(date_value)
        
        if current_claim:
            claims.append(current_claim)
        
        return claims
    
    def _parse_835_remittances(self, segments: list[X12Segment]) -> list[dict]:
        """Parse 835 remittance segments."""
        remittances = []
        current_claim = None
        
        for seg in segments:
            if seg.id == "CLP":
                # Claim payment
                if current_claim:
                    remittances.append(current_claim)
                
                current_claim = {
                    "claim_id": seg.get(0),
                    "status_code": seg.get(1),
                    "total_charge": self._parse_amount(seg.get(2)),
                    "paid_amount": self._parse_amount(seg.get(3)),
                    "patient_responsibility": self._parse_amount(seg.get(4)),
                    "claim_type": seg.get(5),
                    "payer_claim_number": seg.get(6),
                    "adjustments": [],
                    "services": [],
                }
                
            elif seg.id == "CAS" and current_claim:
                # Claim adjustment
                group_code = seg.get(0)
                i = 1
                while i < len(seg.elements) - 1:
                    reason = seg.get(i)
                    amount = self._parse_amount(seg.get(i + 1))
                    if reason:
                        current_claim["adjustments"].append({
                            "group_code": group_code,
                            "reason_code": reason,
                            "amount": amount,
                        })
                    i += 3
                    
            elif seg.id == "SVC" and current_claim:
                # Service payment
                composite = seg.get(0, "").split(self.sub_element_sep)
                service = {
                    "procedure_code": composite[1] if len(composite) > 1 else "",
                    "submitted_charge": self._parse_amount(seg.get(1)),
                    "paid_amount": self._parse_amount(seg.get(2)),
                    "units": self._parse_int(seg.get(4), 1),
                }
                current_claim["services"].append(service)
        
        if current_claim:
            remittances.append(current_claim)
        
        return remittances
    
    def _parse_amount(self, value: str) -> float:
        try:
            return float(value) if value else 0.0
        except ValueError:
            return 0.0
    
    def _parse_int(self, value: str, default: int = 0) -> int:
        try:
            return int(float(value)) if value else default
        except ValueError:
            return default
    
    def _format_date(self, date_str: str) -> str:
        """Convert CCYYMMDD to ISO format."""
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str
    
    def validate(self, data: str) -> list[str]:
        """Validate X12 data."""
        errors = []
        
        data = data.strip()
        if not data.startswith("ISA"):
            errors.append("X12 must start with ISA segment")
        
        if "IEA" not in data:
            errors.append("Missing IEA (interchange end) segment")
        
        return errors
