"""
Agent Tools

Tools available to AEGIS agents for interacting with the knowledge graph,
vector search, and performing calculations.
"""

from typing import Any
from datetime import datetime, timedelta
import json

import structlog

from aegis.graph.client import get_graph_client, GraphClient
from aegis.graph.queries import GraphQueries
from aegis.config import get_settings

logger = structlog.get_logger(__name__)


class AgentTools:
    """
    Collection of tools available to agents.
    
    Each tool is a callable that can be registered with an agent.
    Tools handle data retrieval, calculations, and external lookups.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._graph_client: GraphClient | None = None
        self._queries: GraphQueries | None = None
    
    async def _get_graph(self) -> tuple[GraphClient, GraphQueries]:
        """Get or create graph client and queries."""
        if self._graph_client is None:
            self._graph_client = await get_graph_client()
            self._queries = GraphQueries(self._graph_client)
        return self._graph_client, self._queries
    
    # =========================================================================
    # Patient Tools
    # =========================================================================
    
    async def get_patient(self, patient_id: str | None = None, mrn: str | None = None) -> dict:
        """
        Get patient information by ID or MRN.
        
        Args:
            patient_id: Patient vertex ID
            mrn: Medical Record Number
            
        Returns:
            Patient data dict or error
        """
        logger.info("Tool: get_patient", patient_id=patient_id, mrn=mrn)
        
        try:
            client, queries = await self._get_graph()
            
            if mrn:
                result = await queries.get_patient_by_mrn(mrn, self.tenant_id)
            elif patient_id:
                result = await client.execute(
                    "g.V(patient_id).hasLabel('Patient').valueMap(true)",
                    {"patient_id": patient_id}
                )
                result = result[0] if result else None
            else:
                return {"error": "Either patient_id or mrn must be provided"}
            
            if not result:
                return {"error": f"Patient not found"}
            
            return {"patient": result}
            
        except Exception as e:
            logger.error("get_patient failed", error=str(e))
            return {"error": str(e)}
    
    async def get_patient_360(self, patient_id: str) -> dict:
        """
        Get complete 360-degree patient view.
        
        Includes encounters, diagnoses, procedures, claims, medications.
        """
        logger.info("Tool: get_patient_360", patient_id=patient_id)
        
        try:
            client, queries = await self._get_graph()
            result = await queries.get_patient_360_view(patient_id)
            return result
            
        except Exception as e:
            logger.error("get_patient_360 failed", error=str(e))
            return {"error": str(e)}
    
    async def search_patients(
        self,
        name: str | None = None,
        diagnosis_code: str | None = None,
        payer_id: str | None = None,
        limit: int = 20,
    ) -> dict:
        """
        Search for patients by various criteria.
        """
        logger.info("Tool: search_patients", name=name, diagnosis_code=diagnosis_code)
        
        try:
            client, queries = await self._get_graph()
            
            # Build query based on criteria
            if name:
                query = """
                g.V().hasLabel('Patient')
                    .has('tenant_id', tenant_id)
                    .or(
                        has('given_name', containing(name)),
                        has('family_name', containing(name))
                    )
                    .limit(limit)
                    .valueMap(true)
                """
                result = await client.execute(query, {
                    "tenant_id": self.tenant_id,
                    "name": name,
                    "limit": limit,
                })
            elif diagnosis_code:
                result = await queries.get_patients_with_diagnosis(
                    diagnosis_code, self.tenant_id, limit
                )
            else:
                query = """
                g.V().hasLabel('Patient')
                    .has('tenant_id', tenant_id)
                    .limit(limit)
                    .valueMap(true)
                """
                result = await client.execute(query, {
                    "tenant_id": self.tenant_id,
                    "limit": limit,
                })
            
            return {"patients": result, "count": len(result)}
            
        except Exception as e:
            logger.error("search_patients failed", error=str(e))
            return {"error": str(e)}
    
    # =========================================================================
    # Encounter Tools
    # =========================================================================
    
    async def get_encounters(
        self,
        patient_id: str | None = None,
        status: str | None = None,
        days_back: int = 90,
        limit: int = 50,
    ) -> dict:
        """
        Get encounters for a patient or by status.
        """
        logger.info("Tool: get_encounters", patient_id=patient_id, status=status)
        
        try:
            client, queries = await self._get_graph()
            
            if patient_id:
                query = """
                g.V(patient_id).hasLabel('Patient')
                    .out('HAS_ENCOUNTER')
                    .order().by('admit_date', desc)
                    .limit(limit)
                    .valueMap(true)
                """
                result = await client.execute(query, {
                    "patient_id": patient_id,
                    "limit": limit,
                })
            else:
                cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
                query = """
                g.V().hasLabel('Encounter')
                    .has('tenant_id', tenant_id)
                    .has('admit_date', gte(cutoff_date))
                    .order().by('admit_date', desc)
                    .limit(limit)
                    .valueMap(true)
                """
                result = await client.execute(query, {
                    "tenant_id": self.tenant_id,
                    "cutoff_date": cutoff_date,
                    "limit": limit,
                })
            
            return {"encounters": result, "count": len(result)}
            
        except Exception as e:
            logger.error("get_encounters failed", error=str(e))
            return {"error": str(e)}
    
    # =========================================================================
    # Claims Tools
    # =========================================================================
    
    async def get_claim(self, claim_id: str) -> dict:
        """
        Get detailed claim information with context.
        """
        logger.info("Tool: get_claim", claim_id=claim_id)
        
        try:
            client, queries = await self._get_graph()
            result = await queries.get_claim_with_context(claim_id)
            return result
            
        except Exception as e:
            logger.error("get_claim failed", error=str(e))
            return {"error": str(e)}
    
    async def get_denied_claims(
        self,
        payer_id: str | None = None,
        min_amount: float | None = None,
        denial_category: str | None = None,
        limit: int = 50,
    ) -> dict:
        """
        Get denied claims for review.
        """
        logger.info("Tool: get_denied_claims", payer_id=payer_id, min_amount=min_amount)
        
        try:
            client, queries = await self._get_graph()
            
            result = await queries.get_denied_claims(
                tenant_id=self.tenant_id,
                payer_id=payer_id,
                min_amount=min_amount,
                limit=limit,
            )
            
            # Calculate total denied amount
            total_denied = sum(
                float(r.get("claim", {}).get("billed_amount", [0])[0] 
                      if isinstance(r.get("claim", {}).get("billed_amount"), list) 
                      else r.get("claim", {}).get("billed_amount", 0))
                for r in result
            )
            
            return {
                "denied_claims": result,
                "count": len(result),
                "total_denied_amount": total_denied,
            }
            
        except Exception as e:
            logger.error("get_denied_claims failed", error=str(e))
            return {"error": str(e)}
    
    async def get_claim_for_appeal(self, claim_id: str) -> dict:
        """
        Get all information needed to generate an appeal for a denied claim.
        
        Returns claim, denial, patient, encounter, diagnoses, procedures,
        and any relevant clinical notes.
        """
        logger.info("Tool: get_claim_for_appeal", claim_id=claim_id)
        
        try:
            client, queries = await self._get_graph()
            
            # Get claim with full context
            claim_data = await queries.get_claim_with_context(claim_id)
            
            if not claim_data or not claim_data.get("claim"):
                return {"error": f"Claim {claim_id} not found"}
            
            # Add denial details
            denial_query = """
            g.V(claim_id).hasLabel('Claim')
                .out('HAS_DENIAL')
                .valueMap(true)
            """
            denials = await client.execute(denial_query, {"claim_id": claim_id})
            
            # Get related prior authorizations
            auth_query = """
            g.V(claim_id).hasLabel('Claim')
                .in('BILLED_FOR')
                .out('REQUIRES_AUTH')
                .valueMap(true)
            """
            authorizations = await client.execute(auth_query, {"claim_id": claim_id})
            
            return {
                "claim": claim_data.get("claim"),
                "denials": denials,
                "patient": claim_data.get("patient"),
                "encounter": claim_data.get("encounter"),
                "diagnoses": claim_data.get("diagnoses", []),
                "procedures": claim_data.get("procedures", []),
                "authorizations": authorizations,
                "ready_for_appeal": len(denials) > 0,
            }
            
        except Exception as e:
            logger.error("get_claim_for_appeal failed", error=str(e))
            return {"error": str(e)}
    
    # =========================================================================
    # Analytics Tools
    # =========================================================================
    
    async def get_denial_analytics(
        self,
        days_back: int = 90,
        group_by: str = "category",  # category, payer, provider
    ) -> dict:
        """
        Get denial analytics summary.
        """
        logger.info("Tool: get_denial_analytics", days_back=days_back, group_by=group_by)
        
        try:
            client, queries = await self._get_graph()
            
            # Get denial summary
            result = await queries.get_denial_summary(self.tenant_id)
            
            # Calculate additional metrics
            total_denials = 0
            total_amount = 0.0
            by_category = {}
            
            if result:
                for category, data in result[0].items():
                    count = data.get("count", 0)
                    amount = data.get("total_amount", 0)
                    total_denials += count
                    total_amount += amount
                    by_category[category] = {
                        "count": count,
                        "amount": amount,
                        "avg_amount": amount / count if count > 0 else 0,
                    }
            
            return {
                "total_denials": total_denials,
                "total_denied_amount": total_amount,
                "by_category": by_category,
                "period_days": days_back,
            }
            
        except Exception as e:
            logger.error("get_denial_analytics failed", error=str(e))
            return {"error": str(e)}
    
    async def get_revenue_metrics(self, days_back: int = 30) -> dict:
        """
        Get revenue cycle metrics.
        """
        logger.info("Tool: get_revenue_metrics", days_back=days_back)
        
        try:
            client, _ = await self._get_graph()
            
            cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
            
            # Get claim totals
            query = """
            g.V().hasLabel('Claim')
                .has('tenant_id', tenant_id)
                .has('service_date_start', gte(cutoff_date))
                .group()
                    .by('status')
                    .by(
                        fold()
                            .project('count', 'total_billed', 'total_paid')
                            .by(count(local))
                            .by(unfold().values('billed_amount').sum())
                            .by(unfold().values('paid_amount').sum())
                    )
            """
            
            result = await client.execute(query, {
                "tenant_id": self.tenant_id,
                "cutoff_date": cutoff_date,
            })
            
            # Calculate metrics
            metrics = {
                "period_days": days_back,
                "total_claims": 0,
                "total_billed": 0.0,
                "total_paid": 0.0,
                "total_denied": 0.0,
                "clean_claim_rate": 0.0,
                "denial_rate": 0.0,
                "collection_rate": 0.0,
            }
            
            if result and result[0]:
                for status, data in result[0].items():
                    metrics["total_claims"] += data.get("count", 0)
                    metrics["total_billed"] += data.get("total_billed", 0)
                    metrics["total_paid"] += data.get("total_paid", 0)
                    
                    if status == "denied":
                        metrics["total_denied"] += data.get("total_billed", 0)
            
            # Calculate rates
            if metrics["total_claims"] > 0:
                denied_count = sum(
                    d.get("count", 0) for s, d in (result[0] if result else {}).items()
                    if s == "denied"
                )
                metrics["denial_rate"] = denied_count / metrics["total_claims"]
                metrics["clean_claim_rate"] = 1 - metrics["denial_rate"]
            
            if metrics["total_billed"] > 0:
                metrics["collection_rate"] = metrics["total_paid"] / metrics["total_billed"]
            
            return metrics
            
        except Exception as e:
            logger.error("get_revenue_metrics failed", error=str(e))
            return {"error": str(e)}
    
    # =========================================================================
    # Calculation Tools
    # =========================================================================
    
    def calculate_appeal_priority(
        self,
        denied_amount: float,
        days_to_deadline: int,
        historical_success_rate: float = 0.5,
    ) -> dict:
        """
        Calculate appeal priority score for a denial.
        
        Higher score = higher priority.
        """
        logger.info("Tool: calculate_appeal_priority", denied_amount=denied_amount)
        
        # Priority factors
        amount_score = min(denied_amount / 10000, 1.0) * 40  # Max 40 points
        urgency_score = max(0, (30 - days_to_deadline)) / 30 * 30  # Max 30 points
        success_score = historical_success_rate * 30  # Max 30 points
        
        total_score = amount_score + urgency_score + success_score
        
        priority = "low"
        if total_score >= 70:
            priority = "critical"
        elif total_score >= 50:
            priority = "high"
        elif total_score >= 30:
            priority = "medium"
        
        return {
            "priority_score": round(total_score, 1),
            "priority_level": priority,
            "factors": {
                "amount_score": round(amount_score, 1),
                "urgency_score": round(urgency_score, 1),
                "success_score": round(success_score, 1),
            },
            "recommendation": f"Priority: {priority.upper()}. "
                            f"{'Appeal immediately!' if priority == 'critical' else 'Schedule for review.'}"
        }
    
    def calculate_risk_score(
        self,
        age: int,
        diagnosis_codes: list[str],
        recent_admissions: int,
        chronic_conditions: int,
    ) -> dict:
        """
        Calculate patient risk scores.
        """
        logger.info("Tool: calculate_risk_score", age=age, admissions=recent_admissions)
        
        # Simplified risk calculation (real would use validated models)
        base_score = 0
        
        # Age factor
        if age >= 75:
            base_score += 30
        elif age >= 65:
            base_score += 20
        elif age >= 50:
            base_score += 10
        
        # Recent admissions (30-day readmission risk)
        if recent_admissions >= 3:
            base_score += 40
        elif recent_admissions >= 2:
            base_score += 25
        elif recent_admissions >= 1:
            base_score += 15
        
        # Chronic conditions
        base_score += min(chronic_conditions * 10, 30)
        
        # High-risk diagnoses (simplified)
        high_risk_prefixes = ["I50", "J44", "N18", "E11", "C"]  # Heart failure, COPD, CKD, Diabetes, Cancer
        for code in diagnosis_codes:
            for prefix in high_risk_prefixes:
                if code.startswith(prefix):
                    base_score += 10
                    break
        
        risk_score = min(base_score, 100) / 100
        
        risk_level = "low"
        if risk_score >= 0.7:
            risk_level = "high"
        elif risk_score >= 0.4:
            risk_level = "medium"
        
        return {
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "readmission_risk": round(risk_score * 0.8, 2),  # Simplified
            "interventions_recommended": risk_level in ["high", "medium"],
        }
    
    # =========================================================================
    # Tool Registry
    # =========================================================================
    
    def get_all_tools(self) -> dict[str, dict]:
        """
        Get all available tools with their descriptions.
        
        Returns dict of tool_name -> {function, description}
        """
        return {
            # Patient tools
            "get_patient": {
                "function": self.get_patient,
                "description": "Get patient information by ID or MRN",
            },
            "get_patient_360": {
                "function": self.get_patient_360,
                "description": "Get complete 360-degree patient view with all related data",
            },
            "search_patients": {
                "function": self.search_patients,
                "description": "Search for patients by name, diagnosis, or payer",
            },
            
            # Encounter tools
            "get_encounters": {
                "function": self.get_encounters,
                "description": "Get encounters for a patient or by status/date",
            },
            
            # Claims tools
            "get_claim": {
                "function": self.get_claim,
                "description": "Get detailed claim information with full context",
            },
            "get_denied_claims": {
                "function": self.get_denied_claims,
                "description": "Get list of denied claims for review",
            },
            "get_claim_for_appeal": {
                "function": self.get_claim_for_appeal,
                "description": "Get all information needed to appeal a denied claim",
            },
            
            # Analytics tools
            "get_denial_analytics": {
                "function": self.get_denial_analytics,
                "description": "Get denial analytics summary by category/payer",
            },
            "get_revenue_metrics": {
                "function": self.get_revenue_metrics,
                "description": "Get revenue cycle metrics",
            },
            
            # Calculation tools
            "calculate_appeal_priority": {
                "function": self.calculate_appeal_priority,
                "description": "Calculate priority score for appealing a denial",
            },
            "calculate_risk_score": {
                "function": self.calculate_risk_score,
                "description": "Calculate patient risk scores",
            },
        }
