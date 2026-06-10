from pydantic import BaseModel, EmailStr, Field
from typing import List
import uuid

class ClinicAssociationResponse(BaseModel):
    physician_uuid: uuid.UUID
    clinic_uuid: uuid.UUID

class AddPhysicianRequest(BaseModel):
    email_address: EmailStr
    first_name: str
    last_name: str
    npi_number: str
    clinic_uuid: uuid.UUID

class AddStaffRequest(BaseModel):
    email_address: EmailStr
    first_name: str
    last_name: str
    role: str = Field(..., pattern="^(staff|admin)$")
    physician_uuids: List[uuid.UUID]
    clinic_uuid: uuid.UUID

class AddClinicRequest(BaseModel):
    clinic_name: str
    address: str
    phone_number: str
    fax_number: str 