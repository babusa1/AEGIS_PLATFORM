"""Base Agent with DataService integration"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AgentContext:
    """Context passed to agents."""
    tenant_id: str
    user_id: str
    patient_id: str | None = None
    conversation_id: str | None = None
    metadata: dict | None = None


class BaseAgent(ABC):
    """
    Base class for all AEGIS agents.
    
    All agents use DataService for data access - never query DBs directly.
    """
    
    def __init__(self, data_service, llm_client=None):
        """
        Initialize agent with required services.
        
        Args:
            data_service: DataService instance for all data access
            llm_client: LLM client for AI capabilities
        """
        self.data = data_service
        self.llm = llm_client
    
    @abstractmethod
    async def run(self, context: AgentContext, input: str) -> str:
        """Execute the agent's main task."""
        pass
    
    async def get_patient_context(self, patient_id: str) -> str:
        """Get patient context for LLM prompts."""
        return await self.data.get_patient_summary(patient_id)
    
    async def log_action(self, context: AgentContext, action: str, details: dict | None = None):
        """Log agent action for audit."""
        logger.info("Agent action",
            agent=self.__class__.__name__,
            tenant=context.tenant_id,
            user=context.user_id,
            patient=context.patient_id,
            action=action,
            details=details)


class PatientSummaryAgent(BaseAgent):
    """Agent that generates patient summaries."""
    
    async def run(self, context: AgentContext, input: str) -> str:
        if not context.patient_id:
            return "No patient specified."
        
        # Get data through DataService
        patient_360 = await self.data.get_patient_360(context.patient_id)
        
        if not patient_360:
            return "Patient not found."
        
        # Generate summary
        summary = await self.data.get_patient_summary(context.patient_id)
        
        # Use LLM to enhance if available
        if self.llm:
            prompt = f"Based on this patient data, provide a clinical summary:\n\n{summary}"
            enhanced = await self.llm.generate(prompt)
            return enhanced
        
        return summary


class CareGapAgent(BaseAgent):
    """Agent that identifies care gaps."""
    
    async def run(self, context: AgentContext, input: str) -> str:
        if not context.patient_id:
            return "No patient specified."
        
        # Get care gaps through DataService
        gaps = await self.data.get_care_gaps(context.patient_id)
        
        if not gaps:
            return "No care gaps identified."
        
        lines = ["Care Gaps Identified:"]
        for gap in gaps:
            lines.append(f"- {gap['description']} ({gap['type']})")
        
        return "\n".join(lines)


class RiskAssessmentAgent(BaseAgent):
    """Agent that assesses patient risk."""
    
    async def run(self, context: AgentContext, input: str) -> str:
        if not context.patient_id:
            return "No patient specified."
        
        # Get risk factors through DataService
        risks = await self.data.get_patient_risk_factors(context.patient_id)
        
        lines = [f"Risk Score: {risks['risk_score']:.2f}"]
        
        if risks["chronic_conditions"]:
            lines.append("\nChronic Conditions:")
            for c in risks["chronic_conditions"]:
                lines.append(f"  - {c}")
        
        if risks["abnormal_vitals"]:
            lines.append("\nAbnormal Vitals:")
            for v in risks["abnormal_vitals"]:
                lines.append(f"  - {v}")
        
        return "\n".join(lines)
