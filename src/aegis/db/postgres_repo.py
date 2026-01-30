"""
PostgreSQL Repository Layer

Provides data access for patients, conditions, medications, encounters, claims.
Used when PostgreSQL is available, falls back to mock otherwise.
"""

from typing import Any
from datetime import date
import structlog

logger = structlog.get_logger(__name__)


class PostgresPatientRepository:
    """
    Patient repository backed by PostgreSQL.
    
    Usage:
        repo = PostgresPatientRepository(pool)
        patients = await repo.list_patients(tenant_id="default")
        patient_360 = await repo.get_patient_360("patient-001")
    """
    
    def __init__(self, pool):
        """
        Initialize with an asyncpg connection pool.
        
        Args:
            pool: asyncpg.Pool instance
        """
        self.pool = pool
    
    async def list_patients(
        self,
        tenant_id: str = "default",
        limit: int = 20,
        offset: int = 0,
        search: str | None = None
    ) -> tuple[list[dict], int]:
        """
        List patients with pagination and optional search.
        
        Returns:
            Tuple of (patients list, total count)
        """
        async with self.pool.acquire() as conn:
            # Build query
            if search:
                query = """
                    SELECT id, mrn, given_name, family_name, birth_date, gender,
                           phone, email, address_city, address_state, status
                    FROM patients
                    WHERE tenant_id = $1
                      AND (given_name ILIKE $4 OR family_name ILIKE $4 OR mrn ILIKE $4)
                    ORDER BY family_name, given_name
                    LIMIT $2 OFFSET $3
                """
                count_query = """
                    SELECT COUNT(*) FROM patients
                    WHERE tenant_id = $1
                      AND (given_name ILIKE $2 OR family_name ILIKE $2 OR mrn ILIKE $2)
                """
                search_pattern = f"%{search}%"
                rows = await conn.fetch(query, tenant_id, limit, offset, search_pattern)
                total = await conn.fetchval(count_query, tenant_id, search_pattern)
            else:
                query = """
                    SELECT id, mrn, given_name, family_name, birth_date, gender,
                           phone, email, address_city, address_state, status
                    FROM patients
                    WHERE tenant_id = $1
                    ORDER BY family_name, given_name
                    LIMIT $2 OFFSET $3
                """
                count_query = "SELECT COUNT(*) FROM patients WHERE tenant_id = $1"
                rows = await conn.fetch(query, tenant_id, limit, offset)
                total = await conn.fetchval(count_query, tenant_id)
            
            patients = [dict(row) for row in rows]
            return patients, total
    
    async def get_patient(self, patient_id: str, tenant_id: str = "default") -> dict | None:
        """Get a single patient by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, mrn, given_name, family_name, birth_date, gender,
                       phone, email, address_city, address_state, status,
                       created_at, updated_at
                FROM patients
                WHERE id = $1 AND tenant_id = $2
            """, patient_id, tenant_id)
            
            return dict(row) if row else None
    
    async def get_patient_conditions(self, patient_id: str) -> list[dict]:
        """Get all conditions for a patient."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, code, code_system, display, status, onset_date, severity
                FROM conditions
                WHERE patient_id = $1
                ORDER BY onset_date DESC
            """, patient_id)
            return [dict(row) for row in rows]
    
    async def get_patient_medications(self, patient_id: str) -> list[dict]:
        """Get all medications for a patient."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, code, display, dosage, frequency, route, status, start_date
                FROM medications
                WHERE patient_id = $1 AND status = 'active'
                ORDER BY start_date DESC
            """, patient_id)
            return [dict(row) for row in rows]
    
    async def get_patient_encounters(self, patient_id: str, limit: int = 10) -> list[dict]:
        """Get recent encounters for a patient."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, encounter_type, status, admit_date, discharge_date,
                       facility, provider, reason
                FROM encounters
                WHERE patient_id = $1
                ORDER BY admit_date DESC
                LIMIT $2
            """, patient_id, limit)
            return [dict(row) for row in rows]
    
    async def get_patient_claims(self, patient_id: str) -> list[dict]:
        """Get all claims for a patient."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, claim_number, claim_type, status, billed_amount,
                       paid_amount, payer_name, service_date, denial_reason
                FROM claims
                WHERE patient_id = $1
                ORDER BY service_date DESC
            """, patient_id)
            return [dict(row) for row in rows]
    
    async def get_patient_vitals(self, patient_id: str, limit: int = 10) -> list[dict]:
        """Get recent vitals for a patient."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT time, vital_type, value, unit, source
                FROM vitals
                WHERE patient_id = $1
                ORDER BY time DESC
                LIMIT $2
            """, patient_id, limit)
            return [dict(row) for row in rows]
    
    async def get_patient_labs(self, patient_id: str, limit: int = 20) -> list[dict]:
        """Get recent lab results for a patient."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT time, test_code, test_name, value, value_string, unit,
                       reference_low, reference_high, interpretation, abnormal, critical
                FROM lab_results
                WHERE patient_id = $1
                ORDER BY time DESC
                LIMIT $2
            """, patient_id, limit)
            return [dict(row) for row in rows]
    
    async def get_patient_360(self, patient_id: str, tenant_id: str = "default") -> dict:
        """
        Get complete 360-degree view of a patient.
        
        Includes: demographics, conditions, medications, encounters, claims, vitals, labs
        """
        patient = await self.get_patient(patient_id, tenant_id)
        if not patient:
            return {}
        
        # Fetch all related data in parallel would be ideal, but for simplicity:
        conditions = await self.get_patient_conditions(patient_id)
        medications = await self.get_patient_medications(patient_id)
        encounters = await self.get_patient_encounters(patient_id)
        claims = await self.get_patient_claims(patient_id)
        vitals = await self.get_patient_vitals(patient_id)
        labs = await self.get_patient_labs(patient_id)
        
        # Calculate risk scores
        risk_scores = self._calculate_risk_scores(patient, conditions, medications)
        patient_status = self._calculate_patient_status(risk_scores)
        
        # Calculate financial summary
        total_billed = sum(c.get("billed_amount", 0) or 0 for c in claims)
        total_paid = sum(c.get("paid_amount", 0) or 0 for c in claims)
        total_denied = sum(
            c.get("billed_amount", 0) or 0 
            for c in claims 
            if c.get("status") == "denied"
        )
        
        return {
            "patient": patient,
            "conditions": conditions,
            "medications": medications,
            "encounters": encounters,
            "claims": claims,
            "vitals": self._format_vitals(vitals),
            "labs": labs,
            "risk_scores": risk_scores,
            "patient_status": patient_status,
            "financial_summary": {
                "total_billed": float(total_billed),
                "total_paid": float(total_paid),
                "total_denied": float(total_denied),
                "collection_rate": round(total_paid / total_billed, 2) if total_billed > 0 else 0,
            }
        }
    
    def _format_vitals(self, vitals: list[dict]) -> list[dict]:
        """Format vitals into a cleaner structure."""
        formatted = []
        seen_types = set()
        
        for v in vitals:
            vtype = v.get("vital_type")
            if vtype and vtype not in seen_types:
                seen_types.add(vtype)
                formatted.append({
                    "type": vtype,
                    "value": v.get("value"),
                    "unit": v.get("unit"),
                    "timestamp": v.get("time").isoformat() if v.get("time") else None
                })
        
        return formatted
    
    def _calculate_risk_scores(
        self, 
        patient: dict, 
        conditions: list[dict], 
        medications: list[dict]
    ) -> dict:
        """Calculate risk scores based on patient data."""
        risk_score = 0.0
        risk_factors = []
        
        # High-risk condition codes (ICD-10 prefixes)
        high_risk_codes = {
            "E11": ("Diabetes", 0.15),
            "I10": ("Hypertension", 0.10),
            "I50": ("Heart Failure", 0.25),
            "J44": ("COPD", 0.20),
            "N18": ("Chronic Kidney Disease", 0.20),
            "E78": ("Hyperlipidemia", 0.05),
        }
        
        for cond in conditions:
            code = (cond.get("code") or "")[:3]
            if code in high_risk_codes:
                name, score = high_risk_codes[code]
                risk_score += score
                if name not in risk_factors:
                    risk_factors.append(name)
        
        # Age factor
        birth_date = patient.get("birth_date")
        if birth_date:
            if isinstance(birth_date, date):
                age = (date.today() - birth_date).days // 365
            else:
                try:
                    age = (date.today() - date.fromisoformat(str(birth_date))).days // 365
                except:
                    age = 0
            
            if age > 65:
                risk_score += 0.10
                risk_factors.append("Age > 65")
            if age > 80:
                risk_score += 0.15
                risk_factors.append("Age > 80")
        
        # Polypharmacy risk
        if len(medications) >= 5:
            risk_score += 0.10
            risk_factors.append("Polypharmacy (5+ medications)")
        
        # Cap at 1.0
        risk_score = min(risk_score, 1.0)
        
        # Determine risk level
        if risk_score >= 0.6:
            risk_level = "high"
        elif risk_score >= 0.3:
            risk_level = "moderate"
        else:
            risk_level = "low"
        
        return {
            "overall_score": round(risk_score, 2),
            "risk_level": risk_level,
            "readmission_30day": round(risk_score * 0.8, 2),
            "fall_risk": "high" if risk_score > 0.5 else "moderate" if risk_score > 0.25 else "low",
            "risk_factors": risk_factors,
        }
    
    def _calculate_patient_status(self, risk_scores: dict) -> dict:
        """Calculate patient status indicator (Green/Yellow/Red)."""
        risk_level = risk_scores.get("risk_level", "low")
        
        if risk_level == "high":
            return {
                "status": "RED",
                "label": "High Risk",
                "message": "Patient requires close monitoring",
                "factors": risk_scores.get("risk_factors", [])
            }
        elif risk_level == "moderate":
            return {
                "status": "YELLOW",
                "label": "Moderate Risk",
                "message": "Patient needs regular follow-up",
                "factors": risk_scores.get("risk_factors", [])
            }
        else:
            return {
                "status": "GREEN",
                "label": "Stable",
                "message": "Patient condition is stable",
                "factors": []
            }


async def create_postgres_pool(settings) -> Any:
    """
    Create an asyncpg connection pool.
    
    Args:
        settings: Settings object with postgres configuration
        
    Returns:
        asyncpg.Pool or None if connection fails
    """
    try:
        import asyncpg
        
        pool = await asyncpg.create_pool(
            host=settings.postgres.host,
            port=settings.postgres.port,
            user=settings.postgres.user,
            password=settings.postgres.password,
            database=settings.postgres.database,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        
        # Test connection
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        logger.info("PostgreSQL connection pool created", host=settings.postgres.host)
        return pool
        
    except ImportError:
        logger.warning("asyncpg not installed, PostgreSQL unavailable")
        return None
    except Exception as e:
        logger.warning("Failed to connect to PostgreSQL", error=str(e))
        return None
