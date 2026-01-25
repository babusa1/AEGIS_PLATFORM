"""Repositories - Data access for each entity type"""
from aegis_data.repositories.base import BaseRepository
from aegis_data.repositories.patient import PatientRepository
from aegis_data.repositories.condition import ConditionRepository
from aegis_data.repositories.medication import MedicationRepository
from aegis_data.repositories.encounter import EncounterRepository
from aegis_data.repositories.observation import ObservationRepository

__all__ = [
    "BaseRepository",
    "PatientRepository", 
    "ConditionRepository",
    "MedicationRepository",
    "EncounterRepository",
    "ObservationRepository",
]
