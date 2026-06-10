"""
Patient Management Endpoints.

Provides endpoints for:
- Patient CRUD operations
- Patient search
- Patient statistics

These endpoints are typically used by staff/admin users.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from uuid import UUID

from api.deps import get_patient_db, get_current_user, get_pagination, PaginationParams
from services import PatientService
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("", summary="List patients")
async def list_patients(
    pagination: PaginationParams = Depends(get_pagination),
    active_only: bool = Query(True, description="Only return active patients"),
    db: Session = Depends(get_patient_db),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    List patients with pagination.
    
    Args:
        pagination: Skip and limit parameters
        active_only: Filter to active patients only
    
    Returns:
        List of patients with pagination info
    """
    service = PatientService(db)
    patients = service.list_patients(
        skip=pagination.skip,
        limit=pagination.limit,
        active_only=active_only
    )
    
    return {
        "patients": [p.to_dict() for p in patients],
        "count": len(patients),
        "skip": pagination.skip,
        "limit": pagination.limit
    }


@router.get("/search", summary="Search patients")
async def search_patients(
    q: str = Query(..., min_length=2, description="Search query"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_patient_db),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Search patients by name, email, or MRN.
    
    Args:
        q: Search query (min 2 characters)
        pagination: Skip and limit parameters
    
    Returns:
        Matching patients
    """
    service = PatientService(db)
    patients = service.search_patients(
        query=q,
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    return {
        "patients": [p.to_dict() for p in patients],
        "count": len(patients),
        "query": q
    }


@router.get("/count", summary="Get patient count")
async def get_patient_count(
    active_only: bool = Query(True),
    db: Session = Depends(get_patient_db),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, int]:
    """
    Get total patient count.
    
    Returns:
        Patient count
    """
    service = PatientService(db)
    count = service.get_patient_count(active_only=active_only)
    
    return {"count": count}


@router.get("/{patient_id}", summary="Get patient by ID")
async def get_patient(
    patient_id: UUID,
    db: Session = Depends(get_patient_db),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get a patient by UUID.
    
    Args:
        patient_id: Patient UUID
    
    Returns:
        Patient details
    """
    service = PatientService(db)
    patient = service.get_patient(patient_id)
    
    return patient.to_dict()


@router.post("", summary="Create patient")
async def create_patient(
    # patient_data: PatientCreate,  # Define in schemas
    db: Session = Depends(get_patient_db),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new patient.
    
    Returns:
        Created patient
    """
    # TODO: Add PatientCreate schema and implement
    return {"message": "Create patient - to be implemented with schema"}


@router.put("/{patient_id}", summary="Update patient")
async def update_patient(
    patient_id: UUID,
    # patient_data: PatientUpdate,  # Define in schemas
    db: Session = Depends(get_patient_db),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update an existing patient.
    
    Args:
        patient_id: Patient UUID
    
    Returns:
        Updated patient
    """
    # TODO: Add PatientUpdate schema and implement
    return {"message": "Update patient - to be implemented with schema"}


@router.delete("/{patient_id}", summary="Deactivate patient")
async def delete_patient(
    patient_id: UUID,
    db: Session = Depends(get_patient_db),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Deactivate a patient (soft delete).
    
    Args:
        patient_id: Patient UUID
    
    Returns:
        Success message
    """
    service = PatientService(db)
    service.delete_patient(patient_id)
    
    return {"message": f"Patient {patient_id} deactivated"}





