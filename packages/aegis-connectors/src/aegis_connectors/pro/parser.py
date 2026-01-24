"""PRO Forms Parser"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class PROInstrument(str, Enum):
    PROMIS = "promis"
    ESAS = "esas"
    PHQ9 = "phq-9"
    GAD7 = "gad-7"
    CUSTOM = "custom"


class ResponseStatus(str, Enum):
    COMPLETED = "completed"
    IN_PROGRESS = "in-progress"


@dataclass
class PROAnswer:
    link_id: str
    question: str
    value: Any
    value_type: str
    score: int | None = None


@dataclass
class PROResponse:
    response_id: str
    questionnaire_id: str
    questionnaire_name: str
    instrument: PROInstrument
    patient_id: str
    encounter_id: str | None
    authored: datetime
    status: ResponseStatus
    answers: list[PROAnswer] = field(default_factory=list)
    total_score: int | None = None
    severity: str | None = None


class PROParser:
    PHQ9_SEVERITY = {(0, 4): "minimal", (5, 9): "mild", (10, 14): "moderate", (15, 27): "severe"}
    GAD7_SEVERITY = {(0, 4): "minimal", (5, 9): "mild", (10, 14): "moderate", (15, 21): "severe"}
    
    def parse(self, data: dict) -> PROResponse | None:
        try:
            if data.get("resourceType") != "QuestionnaireResponse":
                return None
            questionnaire = data.get("questionnaire", "")
            instrument = self._detect_instrument(questionnaire)
            subject = data.get("subject", {})
            patient_id = subject.get("reference", "").split("/")[-1] if subject.get("reference") else ""
            encounter = data.get("encounter", {})
            encounter_id = encounter.get("reference", "").split("/")[-1] if encounter.get("reference") else None
            authored_str = data.get("authored", "")
            authored = datetime.fromisoformat(authored_str.replace("Z", "+00:00")) if authored_str else datetime.utcnow()
            status = ResponseStatus.COMPLETED
            answers = self._parse_items(data.get("item", []))
            total_score = sum(a.score for a in answers if a.score) if answers else None
            severity = self._get_severity(total_score, instrument)
            return PROResponse(data.get("id", ""), questionnaire, self._get_name(instrument), instrument, patient_id, encounter_id, authored, status, answers, total_score, severity)
        except Exception as e:
            logger.error("PRO parse failed", error=str(e))
            return None
    
    def _detect_instrument(self, q: str) -> PROInstrument:
        q = q.lower()
        if "phq" in q: return PROInstrument.PHQ9
        if "gad" in q: return PROInstrument.GAD7
        if "esas" in q: return PROInstrument.ESAS
        if "promis" in q: return PROInstrument.PROMIS
        return PROInstrument.CUSTOM
    
    def _parse_items(self, items: list) -> list[PROAnswer]:
        answers = []
        for item in items:
            for ans in item.get("answer", []):
                val, vtype, score = self._get_val(ans)
                answers.append(PROAnswer(item.get("linkId", ""), item.get("text", ""), val, vtype, score))
            if "item" in item:
                answers.extend(self._parse_items(item["item"]))
        return answers
    
    def _get_val(self, ans: dict) -> tuple:
        if "valueInteger" in ans: return ans["valueInteger"], "int", ans["valueInteger"]
        if "valueString" in ans: return ans["valueString"], "str", None
        if "valueCoding" in ans:
            c = ans["valueCoding"]
            return c.get("display", ""), "coding", int(c["code"]) if c.get("code", "").isdigit() else None
        return None, "unknown", None
    
    def _get_severity(self, score: int | None, inst: PROInstrument) -> str | None:
        if not score: return None
        thresholds = self.PHQ9_SEVERITY if inst == PROInstrument.PHQ9 else self.GAD7_SEVERITY if inst == PROInstrument.GAD7 else None
        if thresholds:
            for (lo, hi), sev in thresholds.items():
                if lo <= score <= hi: return sev
        return None
    
    def _get_name(self, inst: PROInstrument) -> str:
        return {"phq-9": "PHQ-9", "gad-7": "GAD-7", "esas": "ESAS", "promis": "PROMIS"}.get(inst.value, "Custom")
