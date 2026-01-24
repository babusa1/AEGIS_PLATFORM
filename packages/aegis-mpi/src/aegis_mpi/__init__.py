"""AEGIS Master Patient Index - Entity resolution and matching"""
from aegis_mpi.matcher import PatientMatcher, MatchResult
from aegis_mpi.models import PatientRecord, MatchCandidate

__version__ = "0.1.0"
__all__ = ["PatientMatcher", "MatchResult", "PatientRecord", "MatchCandidate"]
