"""
HL7v2 Parser and Handler

Supports:
- ADT (Admit/Discharge/Transfer)
- ORM (Orders)
- ORU (Results)
- SIU (Scheduling)
- MDM (Medical Documents)
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import re

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# HL7v2 Constants
# =============================================================================

class HL7MessageType(str, Enum):
    """HL7v2 message types."""
    ADT = "ADT"  # Admit/Discharge/Transfer
    ORM = "ORM"  # Order Message
    ORU = "ORU"  # Observation Result
    SIU = "SIU"  # Scheduling
    MDM = "MDM"  # Medical Document
    DFT = "DFT"  # Detailed Financial Transaction
    BAR = "BAR"  # Billing Account Record
    RDE = "RDE"  # Pharmacy/Treatment Encoded Order


class HL7TriggerEvent(str, Enum):
    """Common HL7v2 trigger events."""
    # ADT Events
    A01 = "A01"  # Admit
    A02 = "A02"  # Transfer
    A03 = "A03"  # Discharge
    A04 = "A04"  # Register
    A08 = "A08"  # Update Patient Info
    A11 = "A11"  # Cancel Admit
    A13 = "A13"  # Cancel Discharge
    
    # ORM Events
    O01 = "O01"  # Order
    
    # ORU Events
    R01 = "R01"  # Unsolicited Result


# =============================================================================
# HL7v2 Models
# =============================================================================

class HL7v2Field(BaseModel):
    """An HL7v2 field with components."""
    value: str
    components: List[str] = Field(default_factory=list)
    subcomponents: List[List[str]] = Field(default_factory=list)
    
    def __str__(self):
        return self.value
    
    def get_component(self, index: int) -> str:
        """Get component by index (1-based)."""
        if 0 < index <= len(self.components):
            return self.components[index - 1]
        return ""


class HL7v2Segment(BaseModel):
    """An HL7v2 segment."""
    segment_id: str
    fields: List[HL7v2Field] = Field(default_factory=list)
    raw: str = ""
    
    def get_field(self, index: int) -> Optional[HL7v2Field]:
        """Get field by index (1-based, 0 is segment ID)."""
        if index == 0:
            return HL7v2Field(value=self.segment_id)
        if 0 < index <= len(self.fields):
            return self.fields[index - 1]
        return None
    
    def get_value(self, index: int, component: int = 0) -> str:
        """Get field value, optionally a specific component."""
        field = self.get_field(index)
        if not field:
            return ""
        if component > 0:
            return field.get_component(component)
        return field.value
    
    def __getitem__(self, index: int) -> str:
        """Allow segment[index] access."""
        field = self.get_field(index)
        return field.value if field else ""


class HL7v2Message(BaseModel):
    """An HL7v2 message."""
    message_type: str = ""
    trigger_event: str = ""
    control_id: str = ""
    
    # Delimiters
    field_separator: str = "|"
    component_separator: str = "^"
    repetition_separator: str = "~"
    escape_char: str = "\\"
    subcomponent_separator: str = "&"
    
    # Segments
    segments: List[HL7v2Segment] = Field(default_factory=list)
    
    # Raw message
    raw: str = ""
    
    # Timestamps
    timestamp: Optional[datetime] = None
    
    def get_segment(self, segment_id: str, index: int = 0) -> Optional[HL7v2Segment]:
        """Get segment by ID. Index for repeated segments."""
        matches = [s for s in self.segments if s.segment_id == segment_id]
        if index < len(matches):
            return matches[index]
        return None
    
    def get_segments(self, segment_id: str) -> List[HL7v2Segment]:
        """Get all segments with ID."""
        return [s for s in self.segments if s.segment_id == segment_id]
    
    def get_value(self, segment_id: str, field: int, component: int = 0) -> str:
        """Get value from segment.field.component."""
        seg = self.get_segment(segment_id)
        if seg:
            return seg.get_value(field, component)
        return ""
    
    @property
    def patient_id(self) -> str:
        """Get patient ID from PID-3."""
        return self.get_value("PID", 3, 1)
    
    @property
    def patient_name(self) -> Tuple[str, str]:
        """Get patient name from PID-5 (family, given)."""
        family = self.get_value("PID", 5, 1)
        given = self.get_value("PID", 5, 2)
        return (family, given)
    
    @property
    def patient_dob(self) -> str:
        """Get patient DOB from PID-7."""
        return self.get_value("PID", 7)
    
    @property
    def attending_physician(self) -> str:
        """Get attending physician from PV1-7."""
        return self.get_value("PV1", 7, 2)


# =============================================================================
# HL7v2 Parser
# =============================================================================

class HL7v2Parser:
    """
    HL7v2 message parser.
    
    Features:
    - Parse HL7v2 messages
    - Handle encoding characters
    - Extract common fields
    - Convert to FHIR
    """
    
    @staticmethod
    def parse(message: str) -> HL7v2Message:
        """Parse an HL7v2 message string."""
        # Clean message
        message = message.strip()
        
        # Split into segments
        lines = re.split(r'\r\n|\r|\n', message)
        lines = [l for l in lines if l.strip()]
        
        if not lines:
            raise ValueError("Empty HL7v2 message")
        
        # Parse MSH (first segment) to get delimiters
        msh_line = lines[0]
        if not msh_line.startswith("MSH"):
            raise ValueError("Message must start with MSH segment")
        
        # Extract encoding characters
        field_sep = msh_line[3]
        encoding_chars = msh_line[4:8] if len(msh_line) > 7 else "^~\\&"
        
        component_sep = encoding_chars[0] if len(encoding_chars) > 0 else "^"
        repetition_sep = encoding_chars[1] if len(encoding_chars) > 1 else "~"
        escape_char = encoding_chars[2] if len(encoding_chars) > 2 else "\\"
        subcomponent_sep = encoding_chars[3] if len(encoding_chars) > 3 else "&"
        
        # Create message object
        msg = HL7v2Message(
            field_separator=field_sep,
            component_separator=component_sep,
            repetition_separator=repetition_sep,
            escape_char=escape_char,
            subcomponent_separator=subcomponent_sep,
            raw=message,
        )
        
        # Parse each segment
        for line in lines:
            segment = HL7v2Parser._parse_segment(
                line,
                field_sep,
                component_sep,
                subcomponent_sep,
            )
            msg.segments.append(segment)
        
        # Extract message info from MSH
        msh = msg.get_segment("MSH")
        if msh:
            msg.message_type = msh.get_value(9, 1)
            msg.trigger_event = msh.get_value(9, 2)
            msg.control_id = msh.get_value(10)
            
            # Parse timestamp
            ts_str = msh.get_value(7)
            if ts_str:
                msg.timestamp = HL7v2Parser._parse_datetime(ts_str)
        
        return msg
    
    @staticmethod
    def _parse_segment(
        line: str,
        field_sep: str,
        component_sep: str,
        subcomponent_sep: str,
    ) -> HL7v2Segment:
        """Parse a single segment."""
        parts = line.split(field_sep)
        segment_id = parts[0]
        
        fields = []
        
        # MSH is special - field 1 is the separator itself
        start_index = 2 if segment_id == "MSH" else 1
        
        if segment_id == "MSH" and len(parts) > 1:
            # MSH-1 is field separator, MSH-2 is encoding chars
            fields.append(HL7v2Field(value=field_sep, components=[field_sep]))
            if len(parts) > 1:
                fields.append(HL7v2Field(value=parts[1], components=[parts[1]]))
            start_index = 2
        
        for part in parts[start_index:]:
            components = part.split(component_sep)
            subcomponents = [c.split(subcomponent_sep) for c in components]
            
            fields.append(HL7v2Field(
                value=part,
                components=components,
                subcomponents=subcomponents,
            ))
        
        return HL7v2Segment(
            segment_id=segment_id,
            fields=fields,
            raw=line,
        )
    
    @staticmethod
    def _parse_datetime(value: str) -> Optional[datetime]:
        """Parse HL7v2 datetime format."""
        formats = [
            "%Y%m%d%H%M%S",
            "%Y%m%d%H%M",
            "%Y%m%d",
        ]
        
        # Remove timezone if present
        value = value.split("+")[0].split("-")[0]
        
        for fmt in formats:
            try:
                return datetime.strptime(value[:len(fmt.replace("%", ""))], fmt)
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def to_fhir_patient(message: HL7v2Message) -> dict:
        """Convert PID segment to FHIR Patient resource."""
        pid = message.get_segment("PID")
        if not pid:
            return {}
        
        family, given = message.patient_name
        
        return {
            "resourceType": "Patient",
            "identifier": [
                {
                    "system": "urn:oid:medical-record-number",
                    "value": message.patient_id,
                }
            ],
            "name": [
                {
                    "family": family,
                    "given": [given] if given else [],
                }
            ],
            "birthDate": HL7v2Parser._format_fhir_date(message.patient_dob),
            "gender": HL7v2Parser._map_gender(pid.get_value(8)),
        }
    
    @staticmethod
    def to_fhir_encounter(message: HL7v2Message) -> dict:
        """Convert PV1 segment to FHIR Encounter resource."""
        pv1 = message.get_segment("PV1")
        if not pv1:
            return {}
        
        status_map = {
            "A01": "in-progress",
            "A03": "finished",
            "A04": "arrived",
        }
        
        return {
            "resourceType": "Encounter",
            "status": status_map.get(message.trigger_event, "unknown"),
            "class": {
                "code": pv1.get_value(2),
            },
            "subject": {
                "reference": f"Patient/{message.patient_id}",
            },
            "participant": [
                {
                    "individual": {
                        "display": message.attending_physician,
                    },
                }
            ] if message.attending_physician else [],
        }
    
    @staticmethod
    def _format_fhir_date(hl7_date: str) -> str:
        """Format HL7 date to FHIR format."""
        if len(hl7_date) >= 8:
            return f"{hl7_date[:4]}-{hl7_date[4:6]}-{hl7_date[6:8]}"
        return ""
    
    @staticmethod
    def _map_gender(hl7_gender: str) -> str:
        """Map HL7 gender to FHIR."""
        mapping = {
            "M": "male",
            "F": "female",
            "O": "other",
            "U": "unknown",
        }
        return mapping.get(hl7_gender.upper(), "unknown")


# =============================================================================
# HL7v2 Message Builder
# =============================================================================

class HL7v2Builder:
    """Build HL7v2 messages."""
    
    def __init__(self):
        self.segments: List[str] = []
        self.field_sep = "|"
        self.encoding = "^~\\&"
    
    def add_msh(
        self,
        sending_app: str,
        sending_facility: str,
        receiving_app: str,
        receiving_facility: str,
        message_type: str,
        trigger_event: str,
        control_id: str,
    ) -> "HL7v2Builder":
        """Add MSH segment."""
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        
        msh = f"MSH|{self.encoding}|{sending_app}|{sending_facility}|" \
              f"{receiving_app}|{receiving_facility}|{now}||" \
              f"{message_type}^{trigger_event}|{control_id}|P|2.5.1"
        
        self.segments.append(msh)
        return self
    
    def add_pid(
        self,
        patient_id: str,
        family_name: str,
        given_name: str,
        dob: str,
        gender: str,
    ) -> "HL7v2Builder":
        """Add PID segment."""
        pid = f"PID|||{patient_id}||{family_name}^{given_name}||{dob}|{gender}"
        self.segments.append(pid)
        return self
    
    def add_pv1(
        self,
        patient_class: str,
        location: str = "",
        attending_doctor: str = "",
    ) -> "HL7v2Builder":
        """Add PV1 segment."""
        pv1 = f"PV1||{patient_class}|{location}||||{attending_doctor}"
        self.segments.append(pv1)
        return self
    
    def add_segment(self, segment: str) -> "HL7v2Builder":
        """Add a raw segment."""
        self.segments.append(segment)
        return self
    
    def build(self) -> str:
        """Build the HL7v2 message."""
        return "\r".join(self.segments)
