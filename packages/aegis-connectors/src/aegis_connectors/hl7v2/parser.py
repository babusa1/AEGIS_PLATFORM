"""
HL7v2 Message Parser
"""

from typing import Any
from dataclasses import dataclass, field
import structlog

logger = structlog.get_logger(__name__)

try:
    from hl7apy.parser import parse_message
    HL7APY_AVAILABLE = True
except ImportError:
    HL7APY_AVAILABLE = False


@dataclass
class ParsedHL7Message:
    """Parsed HL7v2 message."""
    message_type: str
    trigger_event: str
    message_control_id: str
    sending_facility: str
    receiving_facility: str
    timestamp: str
    version: str
    patient: dict = field(default_factory=dict)
    visit: dict = field(default_factory=dict)
    observations: list = field(default_factory=list)
    diagnoses: list = field(default_factory=list)
    insurance: list = field(default_factory=list)


class HL7v2Parser:
    """Parses HL7v2 messages."""
    
    def __init__(self):
        if not HL7APY_AVAILABLE:
            raise ImportError("hl7apy required")
    
    def parse(self, message: str):
        """Parse an HL7v2 message."""
        errors = []
        
        try:
            message = message.replace("\n", "\r").replace("\r\r", "\r")
            hl7 = parse_message(message)
            
            msh = self._get_segment(hl7, "MSH")
            if not msh:
                return None, ["Missing MSH segment"]
            
            parsed = ParsedHL7Message(
                message_type=self._safe_get(msh, "msh_9.msh_9_1") or "",
                trigger_event=self._safe_get(msh, "msh_9.msh_9_2") or "",
                message_control_id=self._safe_get(msh, "msh_10") or "",
                sending_facility=self._safe_get(msh, "msh_4.msh_4_1") or "",
                receiving_facility=self._safe_get(msh, "msh_6.msh_6_1") or "",
                timestamp=self._safe_get(msh, "msh_7") or "",
                version=self._safe_get(msh, "msh_12.msh_12_1") or "2.5",
            )
            
            pid = self._get_segment(hl7, "PID")
            if pid:
                parsed.patient = self._parse_pid(pid)
            
            pv1 = self._get_segment(hl7, "PV1")
            if pv1:
                parsed.visit = self._parse_pv1(pv1)
            
            for obx in self._get_segments(hl7, "OBX"):
                parsed.observations.append(self._parse_obx(obx))
            
            for dg1 in self._get_segments(hl7, "DG1"):
                parsed.diagnoses.append(self._parse_dg1(dg1))
            
            for in1 in self._get_segments(hl7, "IN1"):
                parsed.insurance.append(self._parse_in1(in1))
            
            return parsed, errors
            
        except Exception as e:
            return None, [f"Parse error: {str(e)}"]
    
    def _get_segment(self, hl7, name: str):
        try:
            seg = getattr(hl7, name.lower(), None)
            if seg:
                return seg if not isinstance(seg, list) else seg[0]
        except Exception:
            pass
        return None
    
    def _get_segments(self, hl7, name: str) -> list:
        try:
            seg = getattr(hl7, name.lower(), None)
            if seg:
                return seg if isinstance(seg, list) else [seg]
        except Exception:
            pass
        return []
    
    def _safe_get(self, segment, path: str):
        try:
            parts = path.split(".")
            value = segment
            for part in parts:
                value = getattr(value, part, None)
                if value is None:
                    return None
            return str(value.value) if hasattr(value, "value") else str(value)
        except Exception:
            return None
    
    def _parse_pid(self, pid) -> dict:
        return {
            "patient_id": self._safe_get(pid, "pid_3.pid_3_1") or "",
            "mrn": self._safe_get(pid, "pid_3.pid_3_1") or "",
            "family_name": self._safe_get(pid, "pid_5.pid_5_1") or "",
            "given_name": self._safe_get(pid, "pid_5.pid_5_2") or "",
            "birth_date": self._safe_get(pid, "pid_7") or "",
            "gender": self._safe_get(pid, "pid_8") or "",
            "city": self._safe_get(pid, "pid_11.pid_11_3") or "",
            "state": self._safe_get(pid, "pid_11.pid_11_4") or "",
            "postal_code": self._safe_get(pid, "pid_11.pid_11_5") or "",
            "phone": self._safe_get(pid, "pid_13.pid_13_1") or "",
        }
    
    def _parse_pv1(self, pv1) -> dict:
        return {
            "visit_number": self._safe_get(pv1, "pv1_19.pv1_19_1") or "",
            "patient_class": self._safe_get(pv1, "pv1_2") or "",
            "assigned_location": self._safe_get(pv1, "pv1_3.pv1_3_1") or "",
            "admit_date": self._safe_get(pv1, "pv1_44") or "",
            "discharge_date": self._safe_get(pv1, "pv1_45") or "",
        }
    
    def _parse_obx(self, obx) -> dict:
        return {
            "observation_id": self._safe_get(obx, "obx_3.obx_3_1") or "",
            "observation_name": self._safe_get(obx, "obx_3.obx_3_2") or "",
            "observation_value": self._safe_get(obx, "obx_5") or "",
            "units": self._safe_get(obx, "obx_6.obx_6_1") or "",
            "abnormal_flag": self._safe_get(obx, "obx_8") or "",
            "observation_date": self._safe_get(obx, "obx_14") or "",
        }
    
    def _parse_dg1(self, dg1) -> dict:
        return {
            "diagnosis_code": self._safe_get(dg1, "dg1_3.dg1_3_1") or "",
            "diagnosis_description": self._safe_get(dg1, "dg1_3.dg1_3_2") or "",
            "coding_system": self._safe_get(dg1, "dg1_3.dg1_3_3") or "",
        }
    
    def _parse_in1(self, in1) -> dict:
        return {
            "plan_id": self._safe_get(in1, "in1_2.in1_2_1") or "",
            "company_id": self._safe_get(in1, "in1_3.in1_3_1") or "",
            "company_name": self._safe_get(in1, "in1_4.in1_4_1") or "",
        }
    
    def validate(self, message: str) -> list:
        errors = []
        try:
            message = message.replace("\n", "\r").replace("\r\r", "\r")
            if not message.startswith("MSH"):
                errors.append("Message must start with MSH")
            parse_message(message)
        except Exception as e:
            errors.append(str(e))
        return errors
