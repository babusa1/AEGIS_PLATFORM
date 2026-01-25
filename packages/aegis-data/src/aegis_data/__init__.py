"""
AEGIS Unified Data Layer

Provides a single interface for all data access:
- Graph DB (Neptune) - Clinical relationships
- Postgres - Operational metadata  
- TimescaleDB - Time-series vitals/labs
- Vector DB - Embeddings for RAG

Usage:
    from aegis_data import DataService
    
    service = DataService(tenant_id="tenant-1")
    patient = await service.patients.get("pat-123")
    conditions = await service.patients.get_conditions("pat-123")
    vitals = await service.vitals.get_trend("pat-123", "heart_rate", days=30)
"""
from aegis_data.service import DataService
from aegis_data.repositories import PatientRepository, ConditionRepository

__version__ = "0.1.0"
__all__ = ["DataService", "PatientRepository", "ConditionRepository"]
