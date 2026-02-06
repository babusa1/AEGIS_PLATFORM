"""
Kill Switch (Guardian Override)

Allows administrators to pause specific agent types during downtime or emergencies.
Implements the "Constrained Autonomy" model for trusted AI.
"""

from typing import Dict, List, Optional, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import structlog

logger = structlog.get_logger(__name__)


class AgentStatus(str, Enum):
    """Status of an agent type."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


@dataclass
class AgentControl:
    """Control state for an agent type."""
    agent_type: str  # e.g., "oncolife", "chaperone_ckm", "triage", "action"
    status: AgentStatus = AgentStatus.ACTIVE
    paused_by: Optional[str] = None  # User ID who paused
    paused_at: Optional[datetime] = None
    pause_reason: Optional[str] = None
    resume_after: Optional[datetime] = None  # Auto-resume after this time


class KillSwitchManager:
    """
    Kill Switch Manager for agent control.
    
    Features:
    - Pause/resume specific agent types
    - Scheduled pause/resume
    - Emergency pause all agents
    - Audit trail of all pause/resume actions
    """
    
    def __init__(self):
        """Initialize kill switch manager."""
        self._agent_controls: Dict[str, AgentControl] = {}
        self._audit_log: List[Dict[str, Any]] = []
    
    def pause_agent(
        self,
        agent_type: str,
        paused_by: str,
        reason: Optional[str] = None,
        resume_after: Optional[datetime] = None,
    ) -> AgentControl:
        """
        Pause a specific agent type.
        
        Args:
            agent_type: Agent type to pause (e.g., "oncolife", "triage", "all")
            paused_by: User ID who initiated pause
            reason: Reason for pausing
            resume_after: Optional auto-resume time
            
        Returns:
            AgentControl updated
        """
        if agent_type == "all":
            # Pause all agents
            for existing_type in self._agent_controls.keys():
                self._pause_single_agent(existing_type, paused_by, reason, resume_after)
            # Also pause any new agents
            self._pause_all_new = True
            logger.warning("ALL AGENTS PAUSED", paused_by=paused_by, reason=reason)
            return AgentControl(agent_type="all", status=AgentStatus.PAUSED)
        
        return self._pause_single_agent(agent_type, paused_by, reason, resume_after)
    
    def _pause_single_agent(
        self,
        agent_type: str,
        paused_by: str,
        reason: Optional[str],
        resume_after: Optional[datetime],
    ) -> AgentControl:
        """Pause a single agent type."""
        control = self._agent_controls.get(agent_type, AgentControl(agent_type=agent_type))
        control.status = AgentStatus.PAUSED
        control.paused_by = paused_by
        control.paused_at = datetime.utcnow()
        control.pause_reason = reason
        control.resume_after = resume_after
        
        self._agent_controls[agent_type] = control
        
        # Audit log
        self._audit_log.append({
            "action": "pause",
            "agent_type": agent_type,
            "paused_by": paused_by,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        logger.info("Agent paused", agent_type=agent_type, paused_by=paused_by, reason=reason)
        return control
    
    def resume_agent(
        self,
        agent_type: str,
        resumed_by: str,
    ) -> AgentControl:
        """
        Resume a paused agent type.
        
        Args:
            agent_type: Agent type to resume (e.g., "oncolife", "all")
            resumed_by: User ID who initiated resume
            
        Returns:
            AgentControl updated
        """
        if agent_type == "all":
            # Resume all agents
            for existing_type in list(self._agent_controls.keys()):
                self._resume_single_agent(existing_type, resumed_by)
            self._pause_all_new = False
            logger.info("ALL AGENTS RESUMED", resumed_by=resumed_by)
            return AgentControl(agent_type="all", status=AgentStatus.ACTIVE)
        
        return self._resume_single_agent(agent_type, resumed_by)
    
    def _resume_single_agent(
        self,
        agent_type: str,
        resumed_by: str,
    ) -> AgentControl:
        """Resume a single agent type."""
        control = self._agent_controls.get(agent_type, AgentControl(agent_type=agent_type))
        control.status = AgentStatus.ACTIVE
        control.paused_by = None
        control.paused_at = None
        control.pause_reason = None
        control.resume_after = None
        
        self._agent_controls[agent_type] = control
        
        # Audit log
        self._audit_log.append({
            "action": "resume",
            "agent_type": agent_type,
            "resumed_by": resumed_by,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        logger.info("Agent resumed", agent_type=agent_type, resumed_by=resumed_by)
        return control
    
    def is_agent_active(self, agent_type: str) -> bool:
        """
        Check if an agent type is currently active.
        
        Args:
            agent_type: Agent type to check
            
        Returns:
            True if agent is active, False if paused
        """
        # Check if all agents are paused
        if hasattr(self, '_pause_all_new') and self._pause_all_new:
            return False
        
        control = self._agent_controls.get(agent_type)
        if not control:
            return True  # Default to active if not explicitly paused
        
        # Check if auto-resume time has passed
        if control.resume_after and datetime.utcnow() >= control.resume_after:
            control.status = AgentStatus.ACTIVE
            control.resume_after = None
            logger.info("Agent auto-resumed", agent_type=agent_type)
        
        return control.status == AgentStatus.ACTIVE
    
    def get_agent_status(self, agent_type: str) -> AgentStatus:
        """Get current status of an agent type."""
        if hasattr(self, '_pause_all_new') and self._pause_all_new:
            return AgentStatus.PAUSED
        
        control = self._agent_controls.get(agent_type)
        if not control:
            return AgentStatus.ACTIVE
        
        # Check auto-resume
        if control.resume_after and datetime.utcnow() >= control.resume_after:
            control.status = AgentStatus.ACTIVE
        
        return control.status
    
    def list_paused_agents(self) -> List[str]:
        """List all currently paused agent types."""
        paused = []
        for agent_type, control in self._agent_controls.items():
            if control.status == AgentStatus.PAUSED:
                paused.append(agent_type)
        return paused
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit log of pause/resume actions."""
        return self._audit_log[-limit:]


# Global kill switch instance
_kill_switch_manager: Optional[KillSwitchManager] = None


def get_kill_switch() -> KillSwitchManager:
    """Get global kill switch manager instance."""
    global _kill_switch_manager
    if _kill_switch_manager is None:
        _kill_switch_manager = KillSwitchManager()
    return _kill_switch_manager
