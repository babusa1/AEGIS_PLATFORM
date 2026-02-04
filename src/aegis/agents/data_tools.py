"""
Data Moat Tools

Tools that leverage the AEGIS Data Moat - unified access to:
- PostgreSQL (relational clinical data)
- TimescaleDB (time-series vitals/labs)
- Graph Database (relationships)
- Vector Search (semantic similarity)

These tools demonstrate how agents can orchestrate across all data sources.
"""

from typing import Any
from datetime import datetime, timedelta, date
import structlog

logger = structlog.get_logger(__name__)


class DataMoatTools:
    """
    Tools for accessing the AEGIS Data Moat.
    
    The Data Moat is the unified healthcare data layer consisting of:
    1. PostgreSQL - Patient demographics, conditions, medications, claims, denials
    2. TimescaleDB - High-frequency vitals, lab results, wearable data
    3. Graph DB - Clinical relationships, care pathways
    4. Vector DB - Semantic search, similar patients
    
    These tools provide agents with comprehensive data access.
    """
    
    def __init__(self, pool, tenant_id: str = "default"):
        """
        Initialize with database connection pool.
        
        Args:
            pool: asyncpg connection pool
            tenant_id: Tenant context for multi-tenancy
        """
        self.pool = pool
        self.tenant_id = tenant_id
    
    # =========================================================================
    # Patient Tools - Comprehensive patient data access
    # =========================================================================
    
    async def get_patient_summary(self, patient_id: str) -> dict:
        """
        Get comprehensive patient summary from the Data Moat.
        
        Aggregates data from multiple sources:
        - Demographics (PostgreSQL)
        - Active conditions (PostgreSQL)
        - Current medications (PostgreSQL)
        - Recent vitals (TimescaleDB)
        - Recent encounters (PostgreSQL)
        
        Returns:
            Complete patient summary for agent reasoning
        """
        logger.info("DataMoat: get_patient_summary", patient_id=patient_id)
        
        if not self.pool:
            return {"error": "Database not available", "patient_id": patient_id}
        
        try:
            async with self.pool.acquire() as conn:
                # Get patient demographics
                patient = await conn.fetchrow("""
                    SELECT id, mrn, given_name, family_name, birth_date, gender,
                           phone, email, address_city, address_state, status
                    FROM patients WHERE id = $1 AND tenant_id = $2
                """, patient_id, self.tenant_id)
                
                if not patient:
                    return {"error": f"Patient {patient_id} not found"}
                
                # Calculate age
                age = None
                if patient["birth_date"]:
                    today = date.today()
                    age = today.year - patient["birth_date"].year
                
                # Get active conditions
                conditions = await conn.fetch("""
                    SELECT code, display, status, onset_date, severity
                    FROM conditions 
                    WHERE patient_id = $1 AND tenant_id = $2 AND status = 'active'
                    ORDER BY onset_date DESC
                """, patient_id, self.tenant_id)
                
                # Get current medications
                medications = await conn.fetch("""
                    SELECT code, display, dosage, frequency, status
                    FROM medications 
                    WHERE patient_id = $1 AND tenant_id = $2 AND status = 'active'
                    ORDER BY start_date DESC
                """, patient_id, self.tenant_id)
                
                # Get recent vitals (last 30 days)
                vitals = await conn.fetch("""
                    SELECT vital_type, value, unit, time
                    FROM vitals 
                    WHERE patient_id = $1 AND tenant_id = $2 
                      AND time > NOW() - INTERVAL '30 days'
                    ORDER BY time DESC
                    LIMIT 20
                """, patient_id, self.tenant_id)
                
                # Get recent labs (last 90 days)
                labs = await conn.fetch("""
                    SELECT test_code, test_name, value, unit, interpretation, abnormal, time
                    FROM lab_results 
                    WHERE patient_id = $1 AND tenant_id = $2 
                      AND time > NOW() - INTERVAL '90 days'
                    ORDER BY time DESC
                    LIMIT 20
                """, patient_id, self.tenant_id)
                
                # Get recent encounters
                encounters = await conn.fetch("""
                    SELECT id, encounter_type, status, admit_date, discharge_date, reason
                    FROM encounters 
                    WHERE patient_id = $1 AND tenant_id = $2
                    ORDER BY admit_date DESC
                    LIMIT 5
                """, patient_id, self.tenant_id)
                
                return {
                    "patient": {
                        "id": patient["id"],
                        "mrn": patient["mrn"],
                        "name": f"{patient['given_name']} {patient['family_name']}",
                        "age": age,
                        "gender": patient["gender"],
                        "location": f"{patient['address_city']}, {patient['address_state']}",
                        "status": patient["status"],
                    },
                    "conditions": [dict(c) for c in conditions],
                    "medications": [dict(m) for m in medications],
                    "recent_vitals": [dict(v) for v in vitals],
                    "recent_labs": [dict(l) for l in labs],
                    "recent_encounters": [dict(e) for e in encounters],
                    "condition_count": len(conditions),
                    "medication_count": len(medications),
                    "data_sources": ["postgresql", "timescaledb"],
                }
                
        except Exception as e:
            logger.error("get_patient_summary failed", error=str(e))
            return {"error": str(e), "patient_id": patient_id}
    
    async def get_high_risk_patients(self, limit: int = 10) -> dict:
        """
        Identify high-risk patients using Data Moat intelligence.
        
        Risk factors analyzed:
        - Multiple chronic conditions
        - Recent hospitalizations
        - Abnormal lab values
        - Polypharmacy (5+ medications)
        - Age > 65
        
        Returns:
            List of high-risk patients with risk factors
        """
        logger.info("DataMoat: get_high_risk_patients", limit=limit)
        
        if not self.pool:
            return {"error": "Database not available"}
        
        try:
            async with self.pool.acquire() as conn:
                # Complex query joining multiple data sources
                query = """
                    WITH patient_risk AS (
                        SELECT 
                            p.id,
                            p.mrn,
                            p.given_name || ' ' || p.family_name as name,
                            DATE_PART('year', AGE(p.birth_date)) as age,
                            (SELECT COUNT(*) FROM conditions c 
                             WHERE c.patient_id = p.id AND c.status = 'active') as condition_count,
                            (SELECT COUNT(*) FROM medications m 
                             WHERE m.patient_id = p.id AND m.status = 'active') as medication_count,
                            (SELECT COUNT(*) FROM encounters e 
                             WHERE e.patient_id = p.id 
                               AND e.encounter_type = 'inpatient'
                               AND e.admit_date > NOW() - INTERVAL '90 days') as recent_admissions,
                            (SELECT COUNT(*) FROM lab_results l 
                             WHERE l.patient_id = p.id 
                               AND l.abnormal = true
                               AND l.time > NOW() - INTERVAL '30 days') as abnormal_labs
                        FROM patients p
                        WHERE p.tenant_id = $1
                    )
                    SELECT *,
                        (CASE WHEN age > 65 THEN 2 ELSE 0 END +
                         CASE WHEN condition_count >= 3 THEN 3 ELSE condition_count END +
                         CASE WHEN medication_count >= 5 THEN 2 ELSE 0 END +
                         recent_admissions * 3 +
                         abnormal_labs) as risk_score
                    FROM patient_risk
                    ORDER BY risk_score DESC
                    LIMIT $2
                """
                
                rows = await conn.fetch(query, self.tenant_id, limit)
                
                patients = []
                for row in rows:
                    risk_factors = []
                    if row["age"] and row["age"] > 65:
                        risk_factors.append(f"Age {int(row['age'])}")
                    if row["condition_count"] >= 3:
                        risk_factors.append(f"{row['condition_count']} chronic conditions")
                    if row["medication_count"] >= 5:
                        risk_factors.append(f"Polypharmacy ({row['medication_count']} meds)")
                    if row["recent_admissions"] > 0:
                        risk_factors.append(f"{row['recent_admissions']} recent admissions")
                    if row["abnormal_labs"] > 0:
                        risk_factors.append(f"{row['abnormal_labs']} abnormal labs")
                    
                    patients.append({
                        "id": row["id"],
                        "mrn": row["mrn"],
                        "name": row["name"],
                        "age": int(row["age"]) if row["age"] else None,
                        "risk_score": row["risk_score"],
                        "risk_factors": risk_factors,
                    })
                
                return {
                    "high_risk_patients": patients,
                    "total_found": len(patients),
                    "analysis_date": datetime.utcnow().isoformat(),
                    "data_sources": ["postgresql", "timescaledb"],
                }
                
        except Exception as e:
            logger.error("get_high_risk_patients failed", error=str(e))
            return {"error": str(e)}
    
    # =========================================================================
    # Denial Tools - Financial data access
    # =========================================================================
    
    async def get_denial_intelligence(self, days_back: int = 90) -> dict:
        """
        Get denial intelligence from the Data Moat.
        
        Analyzes:
        - Denial patterns by category
        - Denial trends over time
        - High-value denials requiring immediate attention
        - Payer-specific denial rates
        
        Returns:
            Actionable denial intelligence for agents
        """
        logger.info("DataMoat: get_denial_intelligence", days_back=days_back)
        
        if not self.pool:
            return {"error": "Database not available"}
        
        try:
            async with self.pool.acquire() as conn:
                # Get denial summary
                summary = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_denials,
                        SUM(denied_amount) as total_denied,
                        COUNT(*) FILTER (WHERE appeal_status = 'pending') as pending_appeals,
                        COUNT(*) FILTER (WHERE appeal_deadline < CURRENT_DATE + INTERVAL '7 days') as urgent_deadlines,
                        AVG(denied_amount) as avg_denial_amount
                    FROM denials
                    WHERE tenant_id = $1 
                      AND denial_date > CURRENT_DATE - $2 * INTERVAL '1 day'
                """, self.tenant_id, days_back)
                
                # Get top denial reasons
                by_category = await conn.fetch("""
                    SELECT 
                        denial_category,
                        COUNT(*) as count,
                        SUM(denied_amount) as total_amount,
                        AVG(denied_amount) as avg_amount
                    FROM denials
                    WHERE tenant_id = $1
                    GROUP BY denial_category
                    ORDER BY total_amount DESC
                """, self.tenant_id)
                
                # Get high-value pending denials
                urgent = await conn.fetch("""
                    SELECT 
                        d.id, d.denial_code, d.denial_reason, d.denied_amount,
                        d.appeal_deadline, d.priority,
                        c.claim_number, p.given_name || ' ' || p.family_name as patient_name
                    FROM denials d
                    JOIN claims c ON d.claim_id = c.id
                    JOIN patients p ON d.patient_id = p.id
                    WHERE d.tenant_id = $1 
                      AND d.appeal_status = 'pending'
                    ORDER BY d.denied_amount DESC
                    LIMIT 5
                """, self.tenant_id)
                
                return {
                    "summary": {
                        "total_denials": summary["total_denials"],
                        "total_denied_amount": float(summary["total_denied"] or 0),
                        "pending_appeals": summary["pending_appeals"],
                        "urgent_deadlines": summary["urgent_deadlines"],
                        "avg_denial_amount": float(summary["avg_denial_amount"] or 0),
                    },
                    "by_category": [
                        {
                            "category": r["denial_category"],
                            "count": r["count"],
                            "total_amount": float(r["total_amount"]),
                        }
                        for r in by_category
                    ],
                    "urgent_denials": [
                        {
                            "id": r["id"],
                            "claim_number": r["claim_number"],
                            "patient_name": r["patient_name"],
                            "denial_reason": r["denial_reason"],
                            "amount": float(r["denied_amount"]),
                            "deadline": str(r["appeal_deadline"]) if r["appeal_deadline"] else None,
                            "priority": r["priority"],
                        }
                        for r in urgent
                    ],
                    "analysis_period_days": days_back,
                    "data_sources": ["postgresql"],
                }
                
        except Exception as e:
            logger.error("get_denial_intelligence failed", error=str(e))
            return {"error": str(e)}
    
    async def get_claim_for_appeal(self, claim_id: str) -> dict:
        """
        Get all data needed for appeal generation.
        
        Aggregates from Data Moat:
        - Claim details
        - Denial information
        - Patient clinical data
        - Encounter details
        - Supporting documentation
        
        Returns:
            Complete appeal context for agent
        """
        logger.info("DataMoat: get_claim_for_appeal", claim_id=claim_id)
        
        if not self.pool:
            return {"error": "Database not available", "claim_id": claim_id}
        
        try:
            async with self.pool.acquire() as conn:
                # Get claim and denial
                claim = await conn.fetchrow("""
                    SELECT c.*, 
                           p.given_name, p.family_name, p.mrn, p.birth_date, p.gender,
                           d.denial_code, d.denial_category, d.denial_reason, 
                           d.denied_amount, d.appeal_deadline
                    FROM claims c
                    JOIN patients p ON c.patient_id = p.id
                    LEFT JOIN denials d ON d.claim_id = c.id
                    WHERE c.id = $1 AND c.tenant_id = $2
                """, claim_id, self.tenant_id)
                
                if not claim:
                    return {"error": f"Claim {claim_id} not found"}
                
                # Get patient conditions at time of service
                conditions = await conn.fetch("""
                    SELECT code, display, status
                    FROM conditions
                    WHERE patient_id = $1 AND tenant_id = $2 AND status = 'active'
                """, claim["patient_id"], self.tenant_id)
                
                # Get encounter if linked
                encounter = None
                if claim["encounter_id"]:
                    encounter = await conn.fetchrow("""
                        SELECT * FROM encounters WHERE id = $1
                    """, claim["encounter_id"])
                
                return {
                    "claim": {
                        "id": claim["id"],
                        "claim_number": claim["claim_number"],
                        "type": claim["claim_type"],
                        "status": claim["status"],
                        "billed_amount": float(claim["billed_amount"] or 0),
                        "payer": claim["payer_name"],
                        "service_date": str(claim["service_date"]) if claim["service_date"] else None,
                    },
                    "denial": {
                        "code": claim["denial_code"],
                        "category": claim["denial_category"],
                        "reason": claim["denial_reason"],
                        "amount": float(claim["denied_amount"] or 0),
                        "appeal_deadline": str(claim["appeal_deadline"]) if claim["appeal_deadline"] else None,
                    } if claim["denial_code"] else None,
                    "patient": {
                        "id": claim["patient_id"],
                        "name": f"{claim['given_name']} {claim['family_name']}",
                        "mrn": claim["mrn"],
                        "birth_date": str(claim["birth_date"]) if claim["birth_date"] else None,
                        "gender": claim["gender"],
                    },
                    "conditions": [dict(c) for c in conditions],
                    "encounter": dict(encounter) if encounter else None,
                    "ready_for_appeal": claim["denial_code"] is not None,
                    "data_sources": ["postgresql"],
                }
                
        except Exception as e:
            logger.error("get_claim_for_appeal failed", error=str(e))
            return {"error": str(e), "claim_id": claim_id}
    
    # =========================================================================
    # Clinical Monitoring Tools
    # =========================================================================
    
    async def get_patients_needing_attention(self) -> dict:
        """
        Identify patients needing clinical attention.
        
        Monitors:
        - Abnormal vital signs
        - Critical lab values
        - Overdue follow-ups
        - Medication adherence issues
        
        Returns:
            Prioritized list of patients for triage
        """
        logger.info("DataMoat: get_patients_needing_attention")
        
        if not self.pool:
            return {"error": "Database not available"}
        
        try:
            async with self.pool.acquire() as conn:
                # Get patients with critical/abnormal labs
                abnormal_labs = await conn.fetch("""
                    SELECT DISTINCT ON (l.patient_id)
                        l.patient_id,
                        p.given_name || ' ' || p.family_name as name,
                        p.mrn,
                        l.test_name,
                        l.value,
                        l.unit,
                        l.interpretation,
                        l.critical,
                        l.time
                    FROM lab_results l
                    JOIN patients p ON l.patient_id = p.id
                    WHERE l.tenant_id = $1 
                      AND (l.abnormal = true OR l.critical = true)
                      AND l.time > NOW() - INTERVAL '7 days'
                    ORDER BY l.patient_id, l.critical DESC, l.time DESC
                """, self.tenant_id)
                
                # Get patients with high BP or concerning vitals
                concerning_vitals = await conn.fetch("""
                    SELECT DISTINCT ON (v.patient_id)
                        v.patient_id,
                        p.given_name || ' ' || p.family_name as name,
                        p.mrn,
                        v.vital_type,
                        v.value,
                        v.unit,
                        v.time
                    FROM vitals v
                    JOIN patients p ON v.patient_id = p.id
                    WHERE v.tenant_id = $1 
                      AND v.time > NOW() - INTERVAL '7 days'
                      AND (
                          (v.vital_type = 'bp_systolic' AND v.value > 160) OR
                          (v.vital_type = 'bp_diastolic' AND v.value > 100) OR
                          (v.vital_type = 'heart_rate' AND (v.value > 120 OR v.value < 50)) OR
                          (v.vital_type = 'spo2' AND v.value < 92)
                      )
                    ORDER BY v.patient_id, v.time DESC
                """, self.tenant_id)
                
                return {
                    "patients_with_abnormal_labs": [
                        {
                            "patient_id": r["patient_id"],
                            "name": r["name"],
                            "mrn": r["mrn"],
                            "alert_type": "critical_lab" if r["critical"] else "abnormal_lab",
                            "test": r["test_name"],
                            "value": f"{r['value']} {r['unit']}",
                            "interpretation": r["interpretation"],
                            "time": r["time"].isoformat() if r["time"] else None,
                            "priority": "critical" if r["critical"] else "high",
                        }
                        for r in abnormal_labs
                    ],
                    "patients_with_concerning_vitals": [
                        {
                            "patient_id": r["patient_id"],
                            "name": r["name"],
                            "mrn": r["mrn"],
                            "alert_type": "concerning_vital",
                            "vital": r["vital_type"],
                            "value": f"{r['value']} {r['unit']}",
                            "time": r["time"].isoformat() if r["time"] else None,
                            "priority": "high",
                        }
                        for r in concerning_vitals
                    ],
                    "total_alerts": len(abnormal_labs) + len(concerning_vitals),
                    "analysis_time": datetime.utcnow().isoformat(),
                    "data_sources": ["timescaledb", "postgresql"],
                }
                
        except Exception as e:
            logger.error("get_patients_needing_attention failed", error=str(e))
            return {"error": str(e)}
    
    # =========================================================================
    # Tool Registry
    # =========================================================================
    
    def get_all_tools(self) -> dict:
        """
        Get all available Data Moat tools.
        
        Returns:
            Dictionary of tool name -> {function, description}
        """
        return {
            "get_patient_summary": {
                "function": self.get_patient_summary,
                "description": "Get comprehensive patient summary from the Data Moat (demographics, conditions, medications, vitals, labs, encounters)",
                "parameters": {"patient_id": "string"},
            },
            "get_high_risk_patients": {
                "function": self.get_high_risk_patients,
                "description": "Identify high-risk patients based on multiple factors (conditions, medications, age, recent admissions, abnormal labs)",
                "parameters": {"limit": "integer (default: 10)"},
            },
            "get_denial_intelligence": {
                "function": self.get_denial_intelligence,
                "description": "Get denial analytics and intelligence for revenue cycle management",
                "parameters": {"days_back": "integer (default: 90)"},
            },
            "get_claim_for_appeal": {
                "function": self.get_claim_for_appeal,
                "description": "Get all data needed to generate a denial appeal",
                "parameters": {"claim_id": "string"},
            },
            "get_patients_needing_attention": {
                "function": self.get_patients_needing_attention,
                "description": "Identify patients with abnormal labs or concerning vitals requiring clinical attention",
                "parameters": {},
            },
        }
