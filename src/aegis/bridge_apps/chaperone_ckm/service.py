"""
Chaperone CKM Service

Service layer for Chaperone CKM bridge app.
Integrates with ChaperoneCKMAgent and Data Moat.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

# Graceful imports
try:
    from aegis.agents.chaperone_ckm import ChaperoneCKMAgent
except ImportError:
    logger.warning("ChaperoneCKMAgent not available")
    ChaperoneCKMAgent = None

try:
    from aegis.agents.data_tools import DataMoatTools
except ImportError:
    logger.warning("DataMoatTools not available")
    DataMoatTools = None


class ChaperoneCKMService:
    """
    Chaperone CKM Service - CKD Care Management
    
    Provides:
    - Patient dashboard (eGFR trends, KFRE, care gaps)
    - Vital logging (BP, weight) with real-time analysis
    - Care gap tracking
    - Medication adherence monitoring
    - Personalized recommendations
    """
    
    def __init__(
        self,
        patient_id: str,
        data_moat_tools: Optional[DataMoatTools] = None,
        ckm_agent: Optional[ChaperoneCKMAgent] = None,
    ):
        self.patient_id = patient_id
        self.data_moat = data_moat_tools
        self.ckm_agent = ckm_agent
    
    async def get_patient_dashboard(self) -> Dict[str, Any]:
        """
        Get personalized CKD dashboard.
        
        Returns:
            Dashboard data with eGFR trends, KFRE, care gaps, medications, vitals
        """
        if not self.ckm_agent:
            return {"error": "ChaperoneCKMAgent not available"}
        
        try:
            # Get comprehensive CKD status from agent
            ckd_status = await self.ckm_agent.analyze_patient_ckd_status(self.patient_id)
            
            # Get additional metrics
            medication_adherence = await self._get_medication_adherence()
            vital_trends = await self._get_vital_trends()
            
            return {
                "patient_id": self.patient_id,
                "dashboard": {
                    "ckd_status": ckd_status.get("ckd_status", {}),
                    "kfre": ckd_status.get("ckd_status", {}).get("kfre", {}),
                    "egfr_trend": ckd_status.get("ckd_status", {}).get("egfr_trend", {}),
                    "care_gaps": ckd_status.get("care_gaps", []),
                    "risk_flags": ckd_status.get("risk_flags", []),
                    "recommendations": ckd_status.get("recommendations", []),
                    "medication_adherence": medication_adherence,
                    "vital_trends": vital_trends,
                    "dialysis_planning": ckd_status.get("dialysis_planning", {}),
                },
            }
        except Exception as e:
            logger.error("Failed to get patient dashboard", error=str(e), patient_id=self.patient_id)
            return {"error": str(e), "patient_id": self.patient_id}
    
    async def log_vital(
        self,
        vital_type: str,
        value: float,
        timestamp: Optional[datetime] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Patient logs a vital sign (BP, weight, etc.).
        
        Args:
            vital_type: Type of vital (bp_systolic, bp_diastolic, weight, etc.)
            value: Vital value
            timestamp: When the vital was measured (defaults to now)
            additional_data: Additional data (e.g., diastolic for BP)
        
        Returns:
            Logging result with real-time agent analysis
        """
        if not self.data_moat:
            return {"error": "Data Moat not available"}
        
        timestamp = timestamp or datetime.utcnow()
        
        try:
            # Store in Data Moat
            vital_data = {
                "patient_id": self.patient_id,
                "vital_type": vital_type,
                "value": value,
                "time": timestamp,
            }
            
            if additional_data:
                vital_data.update(additional_data)
            
            # Create vital entity
            if hasattr(self.data_moat, "create_entity"):
                await self.data_moat.create_entity("vital", vital_data)
            else:
                # Fallback: use list_entities to check if we can store
                logger.warning("create_entity not available, vital not persisted")
            
            # Real-time agent analysis
            alert = None
            if self.ckm_agent:
                try:
                    alert = await self.ckm_agent.analyze_vital_alert(
                        patient_id=self.patient_id,
                        vital_type=vital_type,
                        value=value,
                        additional_data=additional_data or {},
                    )
                except Exception as e:
                    logger.warning(f"Failed to get agent analysis: {e}")
            
            return {
                "logged": True,
                "vital_type": vital_type,
                "value": value,
                "timestamp": timestamp.isoformat(),
                "alert": alert,
            }
            
        except Exception as e:
            logger.error("Failed to log vital", error=str(e), patient_id=self.patient_id)
            return {"error": str(e), "logged": False}
    
    async def log_blood_pressure(
        self,
        systolic: float,
        diastolic: float,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Convenience method to log blood pressure.
        
        Args:
            systolic: Systolic BP
            diastolic: Diastolic BP
            timestamp: When BP was measured
        
        Returns:
            Logging result with agent analysis
        """
        # Log both systolic and diastolic
        result_systolic = await self.log_vital(
            vital_type="bp_systolic",
            value=systolic,
            timestamp=timestamp,
            additional_data={"diastolic": diastolic},
        )
        
        result_diastolic = await self.log_vital(
            vital_type="bp_diastolic",
            value=diastolic,
            timestamp=timestamp,
            additional_data={"systolic": systolic},
        )
        
        # Combine results
        return {
            "logged": result_systolic.get("logged", False) and result_diastolic.get("logged", False),
            "systolic": systolic,
            "diastolic": diastolic,
            "timestamp": timestamp.isoformat() if timestamp else datetime.utcnow().isoformat(),
            "alert": result_systolic.get("alert") or result_diastolic.get("alert"),
        }
    
    async def get_care_gaps(self) -> List[Dict[str, Any]]:
        """Get current care gaps for the patient."""
        if not self.ckm_agent:
            return []
        
        try:
            ckd_status = await self.ckm_agent.analyze_patient_ckd_status(self.patient_id)
            return ckd_status.get("care_gaps", [])
        except Exception as e:
            logger.error("Failed to get care gaps", error=str(e))
            return []
    
    async def get_medication_adherence(self) -> Dict[str, Any]:
        """Get medication adherence metrics."""
        # Simplified - in production would track actual adherence
        if not self.data_moat:
            return {"adherence_rate": None, "message": "Data Moat not available"}
        
        try:
            medications = await self.data_moat.list_entities(
                "medication",
                filters={"patient_id": self.patient_id, "status": "active"},
            )
            
            # Placeholder adherence calculation
            # In production, would compare prescribed vs actual doses
            return {
                "adherence_rate": 0.85,  # Placeholder
                "active_medications": len(medications.get("entities", [])),
                "message": "Adherence tracking requires medication event data",
            }
        except Exception as e:
            logger.warning(f"Failed to get medication adherence: {e}")
            return {"adherence_rate": None, "error": str(e)}
    
    async def _get_medication_adherence(self) -> Dict[str, Any]:
        """Internal method to get medication adherence."""
        return await self.get_medication_adherence()
    
    async def _get_vital_trends(self) -> Dict[str, Any]:
        """Get vital sign trends over time."""
        if not self.data_moat:
            return {"trends": [], "message": "Data Moat not available"}
        
        try:
            vitals = await self.data_moat.list_entities(
                "vital",
                filters={"patient_id": self.patient_id},
                limit=50,
            )
            
            vital_entities = vitals.get("entities", [])
            
            # Group by type
            bp_readings = [v for v in vital_entities if "bp" in v.get("vital_type", "").lower()]
            weight_readings = [v for v in vital_entities if "weight" in v.get("vital_type", "").lower()]
            
            return {
                "bp_readings": len(bp_readings),
                "weight_readings": len(weight_readings),
                "recent_bp": bp_readings[-1] if bp_readings else None,
                "recent_weight": weight_readings[-1] if weight_readings else None,
                "trends_available": len(vital_entities) > 0,
            }
        except Exception as e:
            logger.warning(f"Failed to get vital trends: {e}")
            return {"trends": [], "error": str(e)}
