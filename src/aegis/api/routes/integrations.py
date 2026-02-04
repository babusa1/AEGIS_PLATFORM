"""
Healthcare Integrations API Routes

Endpoints for:
- FHIR operations
- HL7v2 parsing
- Terminology lookups
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from aegis.integrations.fhir import FHIRClient, EpicFHIRClient, FHIRResource
from aegis.integrations.hl7v2 import HL7v2Parser, HL7v2Builder
from aegis.integrations.terminology import TerminologyService

router = APIRouter(prefix="/integrations", tags=["integrations"])

# Initialize services
_terminology = TerminologyService()
_fhir_client: Optional[FHIRClient] = None


def get_fhir_client() -> FHIRClient:
    """Get or create FHIR client."""
    global _fhir_client
    if _fhir_client is None:
        # Use Epic sandbox by default
        _fhir_client = EpicFHIRClient()
    return _fhir_client


# =============================================================================
# FHIR Endpoints
# =============================================================================

class FHIRConfig(BaseModel):
    base_url: str
    client_id: Optional[str] = None
    access_token: Optional[str] = None


@router.post("/fhir/configure")
async def configure_fhir(config: FHIRConfig):
    """Configure FHIR client."""
    global _fhir_client
    _fhir_client = FHIRClient(
        base_url=config.base_url,
        client_id=config.client_id,
        access_token=config.access_token,
    )
    return {"status": "configured", "base_url": config.base_url}


@router.get("/fhir/{resource_type}/{resource_id}")
async def read_fhir_resource(resource_type: str, resource_id: str):
    """Read a FHIR resource."""
    client = get_fhir_client()
    resource = await client.read(resource_type, resource_id)
    
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    return resource.data


@router.get("/fhir/{resource_type}")
async def search_fhir_resources(
    resource_type: str,
    count: int = Query(20, le=100),
    **params,
):
    """Search FHIR resources."""
    client = get_fhir_client()
    bundle = await client.search(resource_type, params, count)
    
    return {
        "total": bundle.total,
        "entries": [e.data for e in bundle.entries],
        "next": bundle.next_link,
    }


@router.get("/fhir/Patient/{patient_id}/$everything")
async def patient_everything(patient_id: str):
    """Get everything for a patient."""
    client = get_fhir_client()
    bundle = await client.get_patient_everything(patient_id)
    
    return {
        "total": bundle.total,
        "entries": [e.data for e in bundle.entries],
    }


# =============================================================================
# HL7v2 Endpoints
# =============================================================================

class HL7v2ParseRequest(BaseModel):
    message: str


class HL7v2ParseResponse(BaseModel):
    message_type: str
    trigger_event: str
    control_id: str
    patient_id: Optional[str]
    patient_name: Optional[dict]
    segments: List[dict]


@router.post("/hl7v2/parse")
async def parse_hl7v2(request: HL7v2ParseRequest):
    """Parse an HL7v2 message."""
    try:
        message = HL7v2Parser.parse(request.message)
        
        family, given = message.patient_name
        
        return {
            "message_type": message.message_type,
            "trigger_event": message.trigger_event,
            "control_id": message.control_id,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "patient_id": message.patient_id,
            "patient_name": {"family": family, "given": given},
            "segments": [
                {
                    "segment_id": s.segment_id,
                    "fields": [f.value for f in s.fields],
                }
                for s in message.segments
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")


@router.post("/hl7v2/to-fhir")
async def convert_hl7v2_to_fhir(request: HL7v2ParseRequest):
    """Convert HL7v2 message to FHIR resources."""
    try:
        message = HL7v2Parser.parse(request.message)
        
        patient = HL7v2Parser.to_fhir_patient(message)
        encounter = HL7v2Parser.to_fhir_encounter(message)
        
        return {
            "patient": patient,
            "encounter": encounter,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Conversion error: {str(e)}")


class HL7v2BuildRequest(BaseModel):
    message_type: str
    trigger_event: str
    patient_id: str
    patient_name: dict  # {family, given}
    patient_dob: str
    patient_gender: str


@router.post("/hl7v2/build")
async def build_hl7v2(request: HL7v2BuildRequest):
    """Build an HL7v2 message."""
    import uuid
    
    builder = HL7v2Builder()
    builder.add_msh(
        sending_app="AEGIS",
        sending_facility="AEGIS-FAC",
        receiving_app="RECEIVING",
        receiving_facility="RECV-FAC",
        message_type=request.message_type,
        trigger_event=request.trigger_event,
        control_id=str(uuid.uuid4())[:8],
    )
    builder.add_pid(
        patient_id=request.patient_id,
        family_name=request.patient_name.get("family", ""),
        given_name=request.patient_name.get("given", ""),
        dob=request.patient_dob,
        gender=request.patient_gender,
    )
    builder.add_pv1(patient_class="I")  # Inpatient
    
    return {"message": builder.build()}


# =============================================================================
# Terminology Endpoints
# =============================================================================

@router.get("/terminology/lookup/{code}")
async def lookup_code(
    code: str,
    system: Optional[str] = None,
):
    """Look up a medical code."""
    result = _terminology.lookup(code, system)
    
    if not result:
        raise HTTPException(status_code=404, detail="Code not found")
    
    return result.dict()


@router.get("/terminology/search")
async def search_terminology(
    query: str = Query(..., min_length=2),
    systems: Optional[str] = None,  # Comma-separated
    max_results: int = Query(10, le=50),
):
    """Search terminology systems."""
    system_list = systems.split(",") if systems else ["icd10", "snomed", "rxnorm"]
    
    results = await _terminology.search(query, system_list, max_results)
    
    return {
        system: {
            "total": r.total,
            "results": [c.dict() for c in r.results],
        }
        for system, r in results.items()
    }


@router.get("/terminology/validate")
async def validate_code(
    code: str = Query(...),
    system: str = Query(...),
):
    """Validate a medical code format."""
    is_valid = _terminology.validate(code, system)
    info = _terminology.lookup(code, system)
    
    return {
        "code": code,
        "system": system,
        "format_valid": is_valid,
        "exists": info is not None,
        "info": info.dict() if info else None,
    }


# =============================================================================
# ICD-10 Specific
# =============================================================================

@router.get("/terminology/icd10/{code}")
async def lookup_icd10(code: str):
    """Look up an ICD-10 code."""
    result = _terminology.icd10.lookup(code)
    if not result:
        raise HTTPException(status_code=404, detail="ICD-10 code not found")
    return result.dict()


@router.get("/terminology/icd10/search")
async def search_icd10(
    query: str = Query(..., min_length=2),
    max_results: int = Query(10, le=50),
):
    """Search ICD-10 codes."""
    result = await _terminology.icd10.search(query, max_results)
    return {
        "query": result.query,
        "total": result.total,
        "results": [c.dict() for c in result.results],
    }


# =============================================================================
# CPT Specific
# =============================================================================

@router.get("/terminology/cpt/{code}")
async def lookup_cpt(code: str):
    """Look up a CPT code."""
    result = _terminology.cpt.lookup(code)
    if not result:
        raise HTTPException(status_code=404, detail="CPT code not found")
    return result.dict()


# =============================================================================
# RxNorm Specific
# =============================================================================

@router.get("/terminology/rxnorm/{code}")
async def lookup_rxnorm(code: str):
    """Look up an RxNorm code."""
    result = _terminology.rxnorm.lookup(code)
    if not result:
        raise HTTPException(status_code=404, detail="RxNorm code not found")
    return result.dict()


@router.get("/terminology/rxnorm/search")
async def search_rxnorm(
    query: str = Query(..., min_length=2),
    max_results: int = Query(10, le=50),
):
    """Search RxNorm medications."""
    result = await _terminology.rxnorm.search(query, max_results)
    return {
        "query": result.query,
        "total": result.total,
        "results": [c.dict() for c in result.results],
    }
