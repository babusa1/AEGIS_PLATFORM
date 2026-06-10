from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

# Absolute imports
from database import get_doctor_db
from routers.db.doctor_models import StaffAssociations, StaffProfiles, AllClinics
from routers.auth.dependencies import get_current_user, TokenData
from .models import ClinicAssociationResponse, AddPhysicianRequest, AddStaffRequest, AddClinicRequest

router = APIRouter(prefix="/staff", tags=["Staff and Clinic Data"])

@router.post(
    "/add-clinic",
    status_code=status.HTTP_201_CREATED,
    summary="Add a new clinic"
)
async def add_clinic(
    request: AddClinicRequest,
    db: Session = Depends(get_doctor_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Creates a new clinic in the AllClinics table.
    """
    new_clinic = AllClinics(
        clinic_name=request.clinic_name,
        address=request.address,
        phone_number=request.phone_number,
        fax_number=request.fax_number
    )
    db.add(new_clinic)
    db.commit()
    db.refresh(new_clinic)

    return {"message": "Clinic added successfully", "clinic_uuid": new_clinic.uuid}


@router.post(
    "/add-physician",
    status_code=status.HTTP_201_CREATED,
    summary="Add a new physician"
)
async def add_physician(
    request: AddPhysicianRequest,
    db: Session = Depends(get_doctor_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Creates a new physician profile and self-associates them in the StaffAssociations table.
    """
    # Create the profile first to get the generated staff_uuid
    new_physician_profile = StaffProfiles(
        email_address=request.email_address,
        first_name=request.first_name,
        last_name=request.last_name,
        npi_number=request.npi_number,
        role='physician'
    )
    db.add(new_physician_profile)
    db.commit()
    db.refresh(new_physician_profile)

    # Now create the self-association
    new_association = StaffAssociations(
        staff_uuid=new_physician_profile.staff_uuid,
        physician_uuid=new_physician_profile.staff_uuid, # Self-association
        clinic_uuid=request.clinic_uuid
    )
    db.add(new_association)
    db.commit()

    return {"message": "Physician added successfully", "staff_uuid": new_physician_profile.staff_uuid}

@router.post(
    "/add-staff",
    status_code=status.HTTP_201_CREATED,
    summary="Add a new staff or admin member"
)
async def add_staff(
    request: AddStaffRequest,
    db: Session = Depends(get_doctor_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Creates a new staff/admin profile and associates them with one or more physicians.
    """
    # Create the staff profile
    new_staff_profile = StaffProfiles(
        email_address=request.email_address,
        first_name=request.first_name,
        last_name=request.last_name,
        role=request.role
    )
    db.add(new_staff_profile)
    db.commit()
    db.refresh(new_staff_profile)

    # Create associations for each physician UUID provided
    for physician_uuid in request.physician_uuids:
        new_association = StaffAssociations(
            staff_uuid=new_staff_profile.staff_uuid,
            physician_uuid=physician_uuid,
            clinic_uuid=request.clinic_uuid
        )
        db.add(new_association)
    
    db.commit()

    return {"message": f"{request.role.capitalize()} added successfully", "staff_uuid": new_staff_profile.staff_uuid}


@router.get(
    "/clinic-from-physician/{physician_uuid}",
    response_model=ClinicAssociationResponse,
    summary="Get a clinic UUID from a physician UUID"
)
async def get_clinic_from_physician(
    physician_uuid: uuid.UUID,
    db: Session = Depends(get_doctor_db),
    current_user: TokenData = Depends(get_current_user) # Add authentication
):
    """
    Finds the clinic associated with a given physician by looking up their
    association in the Staff_Associations table.
    """
    association = db.query(StaffAssociations).filter(
        StaffAssociations.physician_uuid == physician_uuid
    ).first()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No clinic association found for physician UUID: {physician_uuid}"
        )

    return ClinicAssociationResponse(
        physician_uuid=association.physician_uuid,
        clinic_uuid=association.clinic_uuid
    ) 