"""
Synthetic Healthcare Data Generator

Generates realistic synthetic healthcare data for testing and demos.
Includes patients, encounters, claims, and denial patterns.
"""

import random
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Iterator

import structlog

from aegis.models.core import Patient, Provider, Organization, Address
from aegis.models.clinical import Encounter, Diagnosis, Procedure, Observation, Medication
from aegis.models.financial import Claim, ClaimLine, Denial, Payer, Coverage

logger = structlog.get_logger(__name__)


# =============================================================================
# Reference Data
# =============================================================================

FIRST_NAMES_MALE = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
    "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark",
]

FIRST_NAMES_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
    "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Betty", "Margaret", "Sandra",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
]

CITIES = [
    ("New York", "NY", "10001"),
    ("Los Angeles", "CA", "90001"),
    ("Chicago", "IL", "60601"),
    ("Houston", "TX", "77001"),
    ("Phoenix", "AZ", "85001"),
    ("Philadelphia", "PA", "19101"),
    ("San Antonio", "TX", "78201"),
    ("San Diego", "CA", "92101"),
    ("Dallas", "TX", "75201"),
    ("Austin", "TX", "78701"),
]

SPECIALTIES = [
    "Internal Medicine", "Family Medicine", "Cardiology", "Orthopedics",
    "Neurology", "Oncology", "Pulmonology", "Gastroenterology",
    "Emergency Medicine", "General Surgery",
]

# ICD-10 codes with descriptions
ICD10_CODES = [
    ("I50.9", "Heart failure, unspecified"),
    ("J44.1", "COPD with acute exacerbation"),
    ("E11.9", "Type 2 diabetes mellitus without complications"),
    ("I10", "Essential hypertension"),
    ("J18.9", "Pneumonia, unspecified organism"),
    ("N17.9", "Acute kidney failure, unspecified"),
    ("A41.9", "Sepsis, unspecified organism"),
    ("K92.2", "Gastrointestinal hemorrhage, unspecified"),
    ("I21.9", "Acute myocardial infarction, unspecified"),
    ("J96.00", "Acute respiratory failure, unspecified"),
    ("G40.909", "Epilepsy, unspecified, not intractable"),
    ("F32.9", "Major depressive disorder, single episode, unspecified"),
    ("M54.5", "Low back pain"),
    ("J06.9", "Acute upper respiratory infection, unspecified"),
    ("R50.9", "Fever, unspecified"),
]

# CPT codes with descriptions and typical charges
CPT_CODES = [
    ("99213", "Office visit, established patient, low complexity", 150),
    ("99214", "Office visit, established patient, moderate complexity", 200),
    ("99223", "Initial hospital care, high complexity", 450),
    ("99232", "Subsequent hospital care, moderate complexity", 175),
    ("99291", "Critical care, first 30-74 minutes", 550),
    ("93000", "Electrocardiogram (ECG)", 75),
    ("71046", "Chest X-ray, 2 views", 125),
    ("80053", "Comprehensive metabolic panel", 85),
    ("85025", "Complete blood count (CBC)", 45),
    ("36415", "Venipuncture", 25),
    ("93306", "Echocardiogram", 650),
    ("93458", "Cardiac catheterization", 2500),
    ("43239", "Upper GI endoscopy with biopsy", 1200),
    ("27447", "Total knee replacement", 15000),
    ("33533", "Coronary artery bypass graft", 35000),
]

# Payers
PAYERS = [
    ("PAYER001", "UnitedHealthcare", "commercial"),
    ("PAYER002", "Anthem Blue Cross", "commercial"),
    ("PAYER003", "Aetna", "commercial"),
    ("PAYER004", "Cigna", "commercial"),
    ("PAYER005", "Medicare Part A", "medicare"),
    ("PAYER006", "Medicare Part B", "medicare"),
    ("PAYER007", "Medicaid", "medicaid"),
]

# Denial reasons with CARC codes
DENIAL_REASONS = [
    ("CO-4", "coding", "The procedure code is inconsistent with the modifier used"),
    ("CO-16", "authorization", "Claim lacks information needed for adjudication"),
    ("CO-29", "timely_filing", "The time limit for filing has expired"),
    ("CO-45", "other", "Charge exceeds fee schedule/maximum allowable"),
    ("CO-50", "coding", "These are non-covered services because this is not deemed a medical necessity"),
    ("PR-96", "eligibility", "Non-covered charge(s)"),
    ("PR-204", "medical_necessity", "This service is not covered when performed with this procedure"),
    ("CO-97", "bundling", "Payment adjusted because this service was bundled"),
    ("CO-167", "authorization", "This service requires prior authorization"),
    ("CO-197", "authorization", "Precertification/authorization/notification absent"),
]


class SyntheticDataGenerator:
    """
    Generator for synthetic healthcare data.
    
    Usage:
        generator = SyntheticDataGenerator(tenant_id="demo", seed=42)
        
        # Generate a batch of patients
        patients = generator.generate_patients(100)
        
        # Generate encounters for patients
        encounters = generator.generate_encounters(patients, encounters_per_patient=3)
        
        # Generate claims with some denials
        claims, denials = generator.generate_claims_with_denials(encounters, denial_rate=0.15)
    """
    
    def __init__(
        self, 
        tenant_id: str = "default",
        source_system: str = "synthetic",
        seed: int | None = None
    ):
        """
        Initialize the generator.
        
        Args:
            tenant_id: Multi-tenant identifier
            source_system: Source system name
            seed: Random seed for reproducibility
        """
        self.tenant_id = tenant_id
        self.source_system = source_system
        
        if seed is not None:
            random.seed(seed)
        
        # Generate reference data
        self.payers = self._generate_payers()
        self.providers = []
        self.organizations = []
    
    def _generate_payers(self) -> list[Payer]:
        """Generate standard payers."""
        return [
            Payer(
                tenant_id=self.tenant_id,
                source_system=self.source_system,
                source_id=p[0],
                payer_id=p[0],
                name=p[1],
                type=p[2],
            )
            for p in PAYERS
        ]
    
    def generate_providers(self, count: int = 20) -> list[Provider]:
        """Generate synthetic providers."""
        providers = []
        for i in range(count):
            gender = random.choice(["male", "female"])
            first_name = random.choice(FIRST_NAMES_MALE if gender == "male" else FIRST_NAMES_FEMALE)
            last_name = random.choice(LAST_NAMES)
            
            provider = Provider(
                tenant_id=self.tenant_id,
                source_system=self.source_system,
                source_id=f"PROV-{i+1:04d}",
                npi=f"1{random.randint(100000000, 999999999)}",
                given_name=first_name,
                family_name=last_name,
                specialty=random.choice(SPECIALTIES),
                credentials=random.choice(["MD", "DO", "MD", "MD"]),
            )
            providers.append(provider)
        
        self.providers = providers
        logger.info(f"Generated {count} synthetic providers")
        return providers
    
    def generate_organizations(self, count: int = 5) -> list[Organization]:
        """Generate synthetic healthcare organizations."""
        org_names = [
            "General Hospital", "Regional Medical Center", "University Hospital",
            "Community Health Center", "Memorial Hospital", "St. Mary's Medical Center",
        ]
        
        organizations = []
        for i in range(min(count, len(org_names))):
            city, state, zip_code = random.choice(CITIES)
            org = Organization(
                tenant_id=self.tenant_id,
                source_system=self.source_system,
                source_id=f"ORG-{i+1:04d}",
                name=org_names[i],
                type="hospital",
                tax_id=f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
            )
            organizations.append(org)
        
        self.organizations = organizations
        logger.info(f"Generated {len(organizations)} synthetic organizations")
        return organizations
    
    def generate_patients(self, count: int = 100) -> list[Patient]:
        """Generate synthetic patients."""
        patients = []
        
        for i in range(count):
            gender = random.choice(["male", "female"])
            first_name = random.choice(FIRST_NAMES_MALE if gender == "male" else FIRST_NAMES_FEMALE)
            last_name = random.choice(LAST_NAMES)
            city, state, zip_code = random.choice(CITIES)
            
            # Generate birth date (18-90 years old)
            age = random.randint(18, 90)
            birth_year = date.today().year - age
            birth_date = date(birth_year, random.randint(1, 12), random.randint(1, 28))
            
            patient = Patient(
                tenant_id=self.tenant_id,
                source_system=self.source_system,
                source_id=f"PAT-{i+1:06d}",
                mrn=f"MRN{random.randint(100000, 999999)}",
                given_name=first_name,
                family_name=last_name,
                birth_date=birth_date,
                gender=gender,
                phone_number=f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}",
                email=f"{first_name.lower()}.{last_name.lower()}@email.com",
                address=Address(
                    line=f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Maple', 'Cedar', 'Pine'])} St",
                    city=city,
                    state=state,
                    postal_code=zip_code,
                ),
            )
            patients.append(patient)
        
        logger.info(f"Generated {count} synthetic patients")
        return patients
    
    def generate_encounters(
        self, 
        patients: list[Patient],
        encounters_per_patient: int | tuple[int, int] = (1, 5),
        date_range_days: int = 365
    ) -> list[Encounter]:
        """
        Generate synthetic encounters for patients.
        
        Args:
            patients: List of patients to create encounters for
            encounters_per_patient: Number of encounters per patient (int or range tuple)
            date_range_days: How far back to generate encounters
            
        Returns:
            List of generated encounters
        """
        if not self.providers:
            self.generate_providers()
        
        encounters = []
        enc_types = ["inpatient", "outpatient", "emergency", "observation"]
        
        for patient in patients:
            if isinstance(encounters_per_patient, tuple):
                num_encounters = random.randint(*encounters_per_patient)
            else:
                num_encounters = encounters_per_patient
            
            for j in range(num_encounters):
                # Random admit date within range
                days_ago = random.randint(1, date_range_days)
                admit_date = datetime.now() - timedelta(days=days_ago)
                
                # Encounter type affects length of stay
                enc_type = random.choice(enc_types)
                if enc_type == "inpatient":
                    los = random.randint(1, 14)
                elif enc_type == "observation":
                    los = random.randint(0, 2)
                else:
                    los = 0
                
                discharge_date = admit_date + timedelta(days=los) if los > 0 else None
                
                encounter = Encounter(
                    tenant_id=self.tenant_id,
                    source_system=self.source_system,
                    source_id=f"ENC-{patient.source_id}-{j+1:03d}",
                    type=enc_type,
                    encounter_class="IMP" if enc_type == "inpatient" else "AMB",
                    status="finished",
                    admit_date=admit_date,
                    discharge_date=discharge_date,
                    patient_id=patient.source_id,
                    attending_provider_id=random.choice(self.providers).source_id if self.providers else None,
                )
                encounters.append(encounter)
        
        logger.info(f"Generated {len(encounters)} synthetic encounters")
        return encounters
    
    def generate_diagnoses(
        self,
        encounters: list[Encounter],
        diagnoses_per_encounter: int | tuple[int, int] = (1, 4)
    ) -> list[Diagnosis]:
        """Generate diagnoses for encounters."""
        diagnoses = []
        
        for encounter in encounters:
            if isinstance(diagnoses_per_encounter, tuple):
                num_dx = random.randint(*diagnoses_per_encounter)
            else:
                num_dx = diagnoses_per_encounter
            
            # Select random ICD-10 codes
            selected_codes = random.sample(ICD10_CODES, min(num_dx, len(ICD10_CODES)))
            
            for rank, (code, desc) in enumerate(selected_codes, 1):
                dx = Diagnosis(
                    tenant_id=self.tenant_id,
                    source_system=self.source_system,
                    source_id=f"DX-{encounter.source_id}-{rank}",
                    icd10_code=code,
                    description=desc,
                    type="principal" if rank == 1 else "secondary",
                    rank=rank,
                    present_on_admission="Y" if random.random() > 0.3 else "N",
                    encounter_id=encounter.source_id,
                )
                diagnoses.append(dx)
        
        logger.info(f"Generated {len(diagnoses)} synthetic diagnoses")
        return diagnoses
    
    def generate_procedures(
        self,
        encounters: list[Encounter],
        procedures_per_encounter: int | tuple[int, int] = (0, 3)
    ) -> list[Procedure]:
        """Generate procedures for encounters."""
        procedures = []
        
        for encounter in encounters:
            if isinstance(procedures_per_encounter, tuple):
                num_proc = random.randint(*procedures_per_encounter)
            else:
                num_proc = procedures_per_encounter
            
            if num_proc == 0:
                continue
            
            # Select random CPT codes
            selected_codes = random.sample(CPT_CODES, min(num_proc, len(CPT_CODES)))
            
            for idx, (code, desc, _) in enumerate(selected_codes, 1):
                proc = Procedure(
                    tenant_id=self.tenant_id,
                    source_system=self.source_system,
                    source_id=f"PROC-{encounter.source_id}-{idx}",
                    cpt_code=code,
                    description=desc,
                    procedure_date=encounter.admit_date,
                    status="completed",
                    encounter_id=encounter.source_id,
                    performed_by_id=encounter.attending_provider_id,
                )
                procedures.append(proc)
        
        logger.info(f"Generated {len(procedures)} synthetic procedures")
        return procedures
    
    def generate_claims_with_denials(
        self,
        encounters: list[Encounter],
        denial_rate: float = 0.15,
        partial_denial_rate: float = 0.10
    ) -> tuple[list[Claim], list[Denial]]:
        """
        Generate claims for encounters with realistic denial patterns.
        
        Args:
            encounters: List of encounters to create claims for
            denial_rate: Percentage of claims that are fully denied
            partial_denial_rate: Percentage of claims with partial denials
            
        Returns:
            Tuple of (claims, denials)
        """
        claims = []
        denials = []
        
        for encounter in encounters:
            # Generate claim lines based on encounter type
            lines = []
            total_billed = Decimal("0")
            
            if encounter.type == "inpatient":
                # Room and board
                los = (encounter.discharge_date - encounter.admit_date).days if encounter.discharge_date else 1
                lines.append(ClaimLine(
                    tenant_id=self.tenant_id,
                    source_system=self.source_system,
                    source_id=f"LINE-{encounter.source_id}-1",
                    line_number=1,
                    revenue_code="0120",
                    description="Room and Board",
                    service_date=encounter.admit_date.date() if isinstance(encounter.admit_date, datetime) else encounter.admit_date,
                    units=los,
                    billed_amount=Decimal("1500"),
                    claim_id=f"CLM-{encounter.source_id}",
                ))
                total_billed += Decimal("1500") * los
            
            # Add random procedures
            num_services = random.randint(1, 4)
            selected_services = random.sample(CPT_CODES, min(num_services, len(CPT_CODES)))
            
            for idx, (code, desc, charge) in enumerate(selected_services, len(lines) + 1):
                lines.append(ClaimLine(
                    tenant_id=self.tenant_id,
                    source_system=self.source_system,
                    source_id=f"LINE-{encounter.source_id}-{idx}",
                    line_number=idx,
                    cpt_code=code,
                    description=desc,
                    service_date=encounter.admit_date.date() if isinstance(encounter.admit_date, datetime) else encounter.admit_date,
                    units=1,
                    billed_amount=Decimal(str(charge)),
                    claim_id=f"CLM-{encounter.source_id}",
                ))
                total_billed += Decimal(str(charge))
            
            # Select a payer
            payer = random.choice(self.payers)
            
            # Determine claim status and create denial if applicable
            rand_val = random.random()
            if rand_val < denial_rate:
                # Fully denied
                status = "denied"
                paid_amount = Decimal("0")
                
                # Create denial record
                denial_reason = random.choice(DENIAL_REASONS)
                denial = Denial(
                    tenant_id=self.tenant_id,
                    source_system=self.source_system,
                    source_id=f"DEN-{encounter.source_id}",
                    reason_code=denial_reason[0],
                    category=denial_reason[1],
                    description=denial_reason[2],
                    denied_amount=total_billed,
                    denial_date=encounter.admit_date.date() + timedelta(days=random.randint(14, 45)) if isinstance(encounter.admit_date, datetime) else encounter.admit_date + timedelta(days=random.randint(14, 45)),
                    appeal_deadline=encounter.admit_date.date() + timedelta(days=random.randint(60, 180)) if isinstance(encounter.admit_date, datetime) else encounter.admit_date + timedelta(days=random.randint(60, 180)),
                    claim_id=f"CLM-{encounter.source_id}",
                    payer_id=payer.source_id,
                )
                denials.append(denial)
                
            elif rand_val < denial_rate + partial_denial_rate:
                # Partial denial
                status = "paid"
                paid_amount = total_billed * Decimal(str(random.uniform(0.5, 0.85)))
                
                # Create partial denial
                denial_reason = random.choice(DENIAL_REASONS)
                denial = Denial(
                    tenant_id=self.tenant_id,
                    source_system=self.source_system,
                    source_id=f"DEN-{encounter.source_id}",
                    reason_code=denial_reason[0],
                    category=denial_reason[1],
                    description=denial_reason[2],
                    denied_amount=total_billed - paid_amount,
                    denial_date=encounter.admit_date.date() + timedelta(days=random.randint(14, 45)) if isinstance(encounter.admit_date, datetime) else encounter.admit_date + timedelta(days=random.randint(14, 45)),
                    appeal_deadline=encounter.admit_date.date() + timedelta(days=random.randint(60, 180)) if isinstance(encounter.admit_date, datetime) else encounter.admit_date + timedelta(days=random.randint(60, 180)),
                    claim_id=f"CLM-{encounter.source_id}",
                    payer_id=payer.source_id,
                )
                denials.append(denial)
            else:
                # Paid normally
                status = "paid"
                # Allowed amount is typically 60-90% of billed
                paid_amount = total_billed * Decimal(str(random.uniform(0.6, 0.9)))
            
            # Create claim
            claim = Claim(
                tenant_id=self.tenant_id,
                source_system=self.source_system,
                source_id=f"CLM-{encounter.source_id}",
                claim_number=f"CLM{random.randint(1000000, 9999999)}",
                type="institutional" if encounter.type == "inpatient" else "professional",
                status=status,
                service_date_start=encounter.admit_date.date() if isinstance(encounter.admit_date, datetime) else encounter.admit_date,
                service_date_end=encounter.discharge_date.date() if encounter.discharge_date and isinstance(encounter.discharge_date, datetime) else encounter.discharge_date,
                submission_date=encounter.admit_date.date() + timedelta(days=random.randint(1, 7)) if isinstance(encounter.admit_date, datetime) else encounter.admit_date + timedelta(days=random.randint(1, 7)),
                billed_amount=total_billed,
                allowed_amount=paid_amount / Decimal("0.8") if status == "paid" else None,
                paid_amount=paid_amount if status == "paid" else None,
                patient_id=encounter.patient_id,
                encounter_id=encounter.source_id,
                payer_id=payer.source_id,
                lines=lines,
            )
            claims.append(claim)
        
        logger.info(
            f"Generated {len(claims)} claims with {len(denials)} denials "
            f"({len([d for d in denials if d.denied_amount == claims[denials.index(d) if d in [Denial(**{k: getattr(d, k) for k in ['tenant_id', 'source_id']}) for d in denials] else 0].billed_amount])} full, "
            f"{len(denials) - len([d for d in denials])} partial)"
        )
        return claims, denials
    
    def generate_complete_dataset(
        self,
        num_patients: int = 100,
        encounters_per_patient: tuple[int, int] = (1, 5),
        denial_rate: float = 0.15
    ) -> dict:
        """
        Generate a complete synthetic dataset.
        
        Returns:
            Dictionary with all generated entities
        """
        logger.info(f"Generating complete synthetic dataset with {num_patients} patients")
        
        # Generate reference data
        organizations = self.generate_organizations(5)
        providers = self.generate_providers(20)
        
        # Generate patients
        patients = self.generate_patients(num_patients)
        
        # Generate encounters
        encounters = self.generate_encounters(patients, encounters_per_patient)
        
        # Generate clinical data
        diagnoses = self.generate_diagnoses(encounters)
        procedures = self.generate_procedures(encounters)
        
        # Generate financial data
        claims, denials = self.generate_claims_with_denials(encounters, denial_rate)
        
        result = {
            "organizations": organizations,
            "providers": providers,
            "payers": self.payers,
            "patients": patients,
            "encounters": encounters,
            "diagnoses": diagnoses,
            "procedures": procedures,
            "claims": claims,
            "denials": denials,
        }
        
        logger.info(
            "Generated complete dataset",
            organizations=len(organizations),
            providers=len(providers),
            patients=len(patients),
            encounters=len(encounters),
            diagnoses=len(diagnoses),
            procedures=len(procedures),
            claims=len(claims),
            denials=len(denials),
        )
        
        return result
