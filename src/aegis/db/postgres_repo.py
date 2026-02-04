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


class PostgresDenialsRepository:
    """
    Denials repository backed by PostgreSQL.
    
    Provides access to denial data for denial management and analytics.
    """
    
    def __init__(self, pool):
        self.pool = pool
    
    async def list_denials(
        self,
        tenant_id: str = "default",
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None
    ) -> tuple[list[dict], int]:
        """
        List denials with filtering options.
        
        Returns:
            Tuple of (denials list, total count)
        """
        async with self.pool.acquire() as conn:
            # Build WHERE clause
            conditions = ["d.tenant_id = $1"]
            params = [tenant_id]
            param_idx = 2
            
            if status:
                conditions.append(f"d.appeal_status = ${param_idx}")
                params.append(status)
                param_idx += 1
            
            if priority:
                conditions.append(f"d.priority = ${param_idx}")
                params.append(priority)
                param_idx += 1
            
            if category:
                conditions.append(f"d.denial_category = ${param_idx}")
                params.append(category)
                param_idx += 1
            
            where_clause = " AND ".join(conditions)
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM denials d WHERE {where_clause}"
            total = await conn.fetchval(count_query, *params)
            
            # Get denials with patient and claim info
            query = f"""
                SELECT 
                    d.id,
                    d.claim_id,
                    d.patient_id,
                    d.denial_code,
                    d.denial_category,
                    d.denial_reason,
                    d.denied_amount,
                    d.denial_date,
                    d.appeal_deadline,
                    d.appeal_status,
                    d.priority,
                    d.notes,
                    c.claim_number,
                    c.payer_name,
                    c.service_date,
                    p.given_name,
                    p.family_name,
                    p.mrn
                FROM denials d
                JOIN claims c ON d.claim_id = c.id
                JOIN patients p ON d.patient_id = p.id
                WHERE {where_clause}
                ORDER BY 
                    CASE d.priority 
                        WHEN 'critical' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'medium' THEN 3 
                        ELSE 4 
                    END,
                    d.appeal_deadline ASC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """
            params.extend([limit, offset])
            
            rows = await conn.fetch(query, *params)
            
            denials = []
            for row in rows:
                # Calculate days to deadline
                days_to_deadline = None
                if row["appeal_deadline"]:
                    from datetime import date as date_type
                    today = date_type.today()
                    delta = row["appeal_deadline"] - today
                    days_to_deadline = delta.days
                
                denials.append({
                    "id": row["id"],
                    "claim_id": row["claim_id"],
                    "claim_number": row["claim_number"],
                    "patient_id": row["patient_id"],
                    "patient_name": f"{row['given_name']} {row['family_name']}",
                    "mrn": row["mrn"],
                    "payer": row["payer_name"],
                    "denial_code": row["denial_code"],
                    "denial_category": row["denial_category"],
                    "denial_reason": row["denial_reason"],
                    "denied_amount": float(row["denied_amount"]),
                    "service_date": str(row["service_date"]) if row["service_date"] else None,
                    "denial_date": str(row["denial_date"]) if row["denial_date"] else None,
                    "appeal_deadline": str(row["appeal_deadline"]) if row["appeal_deadline"] else None,
                    "days_to_deadline": days_to_deadline,
                    "appeal_status": row["appeal_status"],
                    "priority": row["priority"],
                    "notes": row["notes"],
                })
            
            return denials, total
    
    async def get_denial(self, denial_id: str) -> dict | None:
        """Get a single denial by ID with full details."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    d.*,
                    c.claim_number, c.payer_name, c.service_date, c.billed_amount,
                    p.given_name, p.family_name, p.mrn, p.birth_date, p.gender
                FROM denials d
                JOIN claims c ON d.claim_id = c.id
                JOIN patients p ON d.patient_id = p.id
                WHERE d.id = $1
            """
            row = await conn.fetchrow(query, denial_id)
            
            if not row:
                return None
            
            return dict(row)
    
    async def get_denial_analytics(self, tenant_id: str = "default") -> dict:
        """Get denial analytics summary."""
        async with self.pool.acquire() as conn:
            # Total stats
            stats_query = """
                SELECT 
                    COUNT(*) as total_denials,
                    SUM(denied_amount) as total_denied_amount,
                    COUNT(*) FILTER (WHERE appeal_status = 'pending') as pending_count,
                    COUNT(*) FILTER (WHERE appeal_status = 'in_progress') as in_progress_count,
                    COUNT(*) FILTER (WHERE appeal_status = 'appealed') as appealed_count,
                    COUNT(*) FILTER (WHERE appeal_status = 'won') as won_count,
                    COUNT(*) FILTER (WHERE appeal_status = 'lost') as lost_count,
                    COUNT(*) FILTER (WHERE appeal_deadline < CURRENT_DATE + INTERVAL '7 days') as urgent_count
                FROM denials
                WHERE tenant_id = $1
            """
            stats = await conn.fetchrow(stats_query, tenant_id)
            
            # By category
            category_query = """
                SELECT 
                    denial_category,
                    COUNT(*) as count,
                    SUM(denied_amount) as amount
                FROM denials
                WHERE tenant_id = $1
                GROUP BY denial_category
                ORDER BY amount DESC
            """
            by_category = await conn.fetch(category_query, tenant_id)
            
            # By payer
            payer_query = """
                SELECT 
                    c.payer_name,
                    COUNT(*) as count,
                    SUM(d.denied_amount) as amount
                FROM denials d
                JOIN claims c ON d.claim_id = c.id
                WHERE d.tenant_id = $1
                GROUP BY c.payer_name
                ORDER BY amount DESC
            """
            by_payer = await conn.fetch(payer_query, tenant_id)
            
            # Calculate win rate
            total_resolved = (stats["won_count"] or 0) + (stats["lost_count"] or 0)
            win_rate = (stats["won_count"] or 0) / total_resolved if total_resolved > 0 else 0.68  # Default demo rate
            
            return {
                "total_denials": stats["total_denials"] or 0,
                "total_denied_amount": float(stats["total_denied_amount"] or 0),
                "pending_count": stats["pending_count"] or 0,
                "in_progress_count": stats["in_progress_count"] or 0,
                "appealed_count": stats["appealed_count"] or 0,
                "won_count": stats["won_count"] or 0,
                "lost_count": stats["lost_count"] or 0,
                "urgent_count": stats["urgent_count"] or 0,
                "win_rate": round(win_rate, 2),
                "by_category": [
                    {"category": r["denial_category"], "count": r["count"], "amount": float(r["amount"])}
                    for r in by_category
                ],
                "by_payer": [
                    {"payer": r["payer_name"], "count": r["count"], "amount": float(r["amount"])}
                    for r in by_payer
                ],
            }
    
    async def update_denial_status(self, denial_id: str, status: str, notes: str | None = None) -> bool:
        """Update denial appeal status."""
        async with self.pool.acquire() as conn:
            if notes:
                query = """
                    UPDATE denials SET appeal_status = $2, notes = $3 WHERE id = $1
                """
                await conn.execute(query, denial_id, status, notes)
            else:
                query = "UPDATE denials SET appeal_status = $2 WHERE id = $1"
                await conn.execute(query, denial_id, status)
            return True


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
