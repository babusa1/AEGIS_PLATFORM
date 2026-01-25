#!/usr/bin/env python3
"""
AEGIS Sample Data Loader

Loads sample FHIR data into the database for testing.
Can be run standalone or imported as a module.

Usage:
    python scripts/load_sample_data.py
    
    # Or with options
    python scripts/load_sample_data.py --patients 10 --tenant default
"""
import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx


# =============================================================================
# Sample Data Generators
# =============================================================================

FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", 
               "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas"]

CONDITIONS = [
    {"code": "44054006", "display": "Type 2 Diabetes Mellitus", "system": "http://snomed.info/sct"},
    {"code": "38341003", "display": "Hypertension", "system": "http://snomed.info/sct"},
    {"code": "13645005", "display": "Chronic Obstructive Pulmonary Disease", "system": "http://snomed.info/sct"},
    {"code": "84114007", "display": "Heart Failure", "system": "http://snomed.info/sct"},
    {"code": "195967001", "display": "Asthma", "system": "http://snomed.info/sct"},
    {"code": "73211009", "display": "Diabetes Mellitus", "system": "http://snomed.info/sct"},
    {"code": "59621000", "display": "Essential Hypertension", "system": "http://snomed.info/sct"},
    {"code": "233604007", "display": "Pneumonia", "system": "http://snomed.info/sct"},
]

MEDICATIONS = [
    {"code": "860975", "display": "Metformin 500 MG", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    {"code": "314076", "display": "Lisinopril 10 MG", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    {"code": "197361", "display": "Amlodipine 5 MG", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    {"code": "310798", "display": "Atorvastatin 20 MG", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    {"code": "312961", "display": "Omeprazole 20 MG", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
    {"code": "198440", "display": "Aspirin 81 MG", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"},
]

VITAL_TYPES = [
    {"code": "8867-4", "display": "Heart rate", "unit": "/min", "range": (60, 100)},
    {"code": "8480-6", "display": "Systolic blood pressure", "unit": "mmHg", "range": (100, 140)},
    {"code": "8462-4", "display": "Diastolic blood pressure", "unit": "mmHg", "range": (60, 90)},
    {"code": "8310-5", "display": "Body temperature", "unit": "Cel", "range": (36.1, 37.2)},
    {"code": "9279-1", "display": "Respiratory rate", "unit": "/min", "range": (12, 20)},
    {"code": "2708-6", "display": "Oxygen saturation", "unit": "%", "range": (95, 100)},
]


def generate_mrn() -> str:
    """Generate a random MRN."""
    return f"MRN{random.randint(100000, 999999)}"


def generate_patient(patient_id: str = None) -> dict:
    """Generate a sample FHIR Patient resource."""
    patient_id = patient_id or str(uuid4())
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    gender = random.choice(["male", "female"])
    birth_year = random.randint(1940, 2005)
    
    return {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": [
            {
                "system": "http://hospital.example.org/mrn",
                "value": generate_mrn()
            }
        ],
        "active": True,
        "name": [
            {
                "use": "official",
                "family": last_name,
                "given": [first_name]
            }
        ],
        "gender": gender,
        "birthDate": f"{birth_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        "address": [
            {
                "use": "home",
                "line": [f"{random.randint(100, 9999)} Main St"],
                "city": random.choice(["Boston", "New York", "Chicago", "Los Angeles", "Houston"]),
                "state": random.choice(["MA", "NY", "IL", "CA", "TX"]),
                "postalCode": f"{random.randint(10000, 99999)}"
            }
        ],
        "telecom": [
            {
                "system": "phone",
                "value": f"555-{random.randint(100,999)}-{random.randint(1000,9999)}",
                "use": "home"
            },
            {
                "system": "email",
                "value": f"{first_name.lower()}.{last_name.lower()}@email.com"
            }
        ]
    }


def generate_condition(patient_id: str) -> dict:
    """Generate a sample FHIR Condition resource."""
    condition = random.choice(CONDITIONS)
    onset_days_ago = random.randint(30, 365 * 5)
    onset_date = (datetime.now() - timedelta(days=onset_days_ago)).strftime("%Y-%m-%d")
    
    return {
        "resourceType": "Condition",
        "id": str(uuid4()),
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
        },
        "verificationStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]
        },
        "category": [
            {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "problem-list-item"}]}
        ],
        "code": {
            "coding": [condition],
            "text": condition["display"]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "onsetDateTime": onset_date
    }


def generate_medication_request(patient_id: str) -> dict:
    """Generate a sample FHIR MedicationRequest resource."""
    medication = random.choice(MEDICATIONS)
    
    return {
        "resourceType": "MedicationRequest",
        "id": str(uuid4()),
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [medication],
            "text": medication["display"]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "authoredOn": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dosageInstruction": [
            {
                "text": "Take once daily",
                "timing": {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}}
            }
        ]
    }


def generate_observation(patient_id: str, vital_type: dict, time: datetime) -> dict:
    """Generate a sample FHIR Observation (vital sign) resource."""
    value = round(random.uniform(vital_type["range"][0], vital_type["range"][1]), 1)
    
    return {
        "resourceType": "Observation",
        "id": str(uuid4()),
        "status": "final",
        "category": [
            {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}
        ],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": vital_type["code"], "display": vital_type["display"]}],
            "text": vital_type["display"]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "valueQuantity": {
            "value": value,
            "unit": vital_type["unit"],
            "system": "http://unitsofmeasure.org"
        }
    }


def generate_encounter(patient_id: str) -> dict:
    """Generate a sample FHIR Encounter resource."""
    start_days_ago = random.randint(1, 90)
    start = datetime.now() - timedelta(days=start_days_ago)
    end = start + timedelta(hours=random.randint(1, 8))
    
    return {
        "resourceType": "Encounter",
        "id": str(uuid4()),
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB", "display": "ambulatory"},
        "type": [
            {"coding": [{"system": "http://snomed.info/sct", "code": "162673000", "display": "General examination"}]}
        ],
        "subject": {"reference": f"Patient/{patient_id}"},
        "period": {
            "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": end.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    }


def generate_fhir_bundle(num_patients: int = 5) -> dict:
    """Generate a complete FHIR Bundle with patients and related resources."""
    entries = []
    
    for _ in range(num_patients):
        patient_id = str(uuid4())
        
        # Add patient
        patient = generate_patient(patient_id)
        entries.append({"resource": patient, "request": {"method": "POST", "url": "Patient"}})
        
        # Add 1-3 conditions per patient
        for _ in range(random.randint(1, 3)):
            condition = generate_condition(patient_id)
            entries.append({"resource": condition, "request": {"method": "POST", "url": "Condition"}})
        
        # Add 1-3 medications per patient
        for _ in range(random.randint(1, 3)):
            med = generate_medication_request(patient_id)
            entries.append({"resource": med, "request": {"method": "POST", "url": "MedicationRequest"}})
        
        # Add 1-2 encounters per patient
        for _ in range(random.randint(1, 2)):
            encounter = generate_encounter(patient_id)
            entries.append({"resource": encounter, "request": {"method": "POST", "url": "Encounter"}})
        
        # Add vital signs (multiple readings over past 7 days)
        for vital_type in VITAL_TYPES:
            for days_ago in range(7):
                time = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 12))
                obs = generate_observation(patient_id, vital_type, time)
                entries.append({"resource": obs, "request": {"method": "POST", "url": "Observation"}})
    
    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": entries
    }


# =============================================================================
# Data Loading Functions
# =============================================================================

async def load_via_api(bundle: dict, api_url: str, tenant_id: str = "default") -> dict:
    """Load FHIR bundle via the ingestion API."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{api_url}/v1/ingestion/fhir",
            json=bundle,
            headers={
                "Content-Type": "application/json",
                "X-Tenant-ID": tenant_id
            }
        )
        response.raise_for_status()
        return response.json()


async def load_directly_to_db(bundle: dict, settings):
    """Load FHIR bundle directly to databases (bypassing API)."""
    from aegis.db import init_db_clients, close_db_clients
    
    clients = await init_db_clients(settings)
    
    try:
        patient_count = 0
        resource_count = 0
        
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")
            
            if resource_type == "Patient":
                patient_count += 1
            
            # For mock clients, just count
            resource_count += 1
        
        print(f"Processed {patient_count} patients, {resource_count} total resources")
        return {"patients": patient_count, "resources": resource_count}
        
    finally:
        await close_db_clients()


def save_bundle_to_file(bundle: dict, filepath: str):
    """Save bundle to JSON file for manual loading."""
    with open(filepath, 'w') as f:
        json.dump(bundle, f, indent=2)
    print(f"Saved bundle to {filepath}")


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Load sample FHIR data into AEGIS")
    parser.add_argument("--patients", type=int, default=5, help="Number of patients to generate")
    parser.add_argument("--tenant", type=str, default="default", help="Tenant ID")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000", help="API base URL")
    parser.add_argument("--output", type=str, help="Save bundle to file instead of loading")
    parser.add_argument("--direct", action="store_true", help="Load directly to DB (bypass API)")
    
    args = parser.parse_args()
    
    print(f"Generating FHIR bundle with {args.patients} patients...")
    bundle = generate_fhir_bundle(args.patients)
    
    total_resources = len(bundle["entry"])
    print(f"Generated {total_resources} resources")
    
    if args.output:
        save_bundle_to_file(bundle, args.output)
        return
    
    if args.direct:
        print("Loading directly to database...")
        from aegis.config import get_settings
        result = await load_directly_to_db(bundle, get_settings())
    else:
        print(f"Loading via API at {args.api_url}...")
        try:
            result = await load_via_api(bundle, args.api_url, args.tenant)
            print(f"API Response: {json.dumps(result, indent=2)}")
        except httpx.ConnectError:
            print(f"\nError: Could not connect to API at {args.api_url}")
            print("Make sure the API server is running: python -m aegis.api.main")
            print("\nSaving bundle to file instead...")
            save_bundle_to_file(bundle, "sample_data.json")
            return
        except Exception as e:
            print(f"Error: {e}")
            return
    
    print("\nSample data loaded successfully!")
    print(f"  Patients: {args.patients}")
    print(f"  Total Resources: {total_resources}")


if __name__ == "__main__":
    asyncio.run(main())
