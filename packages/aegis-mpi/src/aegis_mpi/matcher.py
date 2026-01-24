"""Probabilistic Patient Matching"""
from dataclasses import dataclass, field
import structlog
from aegis_mpi.models import PatientRecord, MatchCandidate, MatchType

logger = structlog.get_logger(__name__)


@dataclass
class MatchConfig:
    exact_threshold: float = 0.95
    probable_threshold: float = 0.80
    possible_threshold: float = 0.60


@dataclass
class MatchResult:
    input_record: PatientRecord
    candidates: list[MatchCandidate]
    best_match: MatchCandidate | None
    is_new_patient: bool


class PatientMatcher:
    def __init__(self, config: MatchConfig | None = None):
        self.config = config or MatchConfig()
        self._index: dict[str, list[PatientRecord]] = {}
    
    def index_patient(self, record: PatientRecord) -> str:
        key = f"{record.last_name[:3].upper()}" if record.last_name else "UNK"
        if key not in self._index:
            self._index[key] = []
        self._index[key].append(record)
        return record.source_id
    
    def match(self, record: PatientRecord) -> MatchResult:
        key = f"{record.last_name[:3].upper()}" if record.last_name else "UNK"
        candidates = self._index.get(key, [])
        scored = []
        for cand in candidates:
            if cand.source_id == record.source_id:
                continue
            score = self._calc_score(record, cand)
            mtype = self._get_type(score)
            scored.append(MatchCandidate(cand, score, mtype, {}))
        scored.sort(key=lambda x: x.score, reverse=True)
        best = scored[0] if scored and scored[0].score >= self.config.possible_threshold else None
        return MatchResult(record, scored[:10], best, best is None)
    
    def _calc_score(self, r1: PatientRecord, r2: PatientRecord) -> float:
        score = 0.0
        if r1.first_name and r2.first_name and r1.first_name.upper() == r2.first_name.upper():
            score += 0.2
        if r1.last_name and r2.last_name and r1.last_name.upper() == r2.last_name.upper():
            score += 0.3
        if r1.date_of_birth and r1.date_of_birth == r2.date_of_birth:
            score += 0.3
        if r1.ssn_last4 and r1.ssn_last4 == r2.ssn_last4:
            score += 0.2
        return score
    
    def _get_type(self, score: float) -> MatchType:
        if score >= self.config.exact_threshold:
            return MatchType.EXACT
        if score >= self.config.probable_threshold:
            return MatchType.PROBABLE
        if score >= self.config.possible_threshold:
            return MatchType.POSSIBLE
        return MatchType.NO_MATCH
