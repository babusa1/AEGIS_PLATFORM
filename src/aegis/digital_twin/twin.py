"""Digital Twin MVP

Provides a minimal Digital Twin engine to simulate simple patient state
transitions for demo and testing purposes.
"""

from typing import Any, Dict
from datetime import datetime, timedelta


class DigitalTwin:
    """Simple patient twin simulator."""

    def __init__(self, patient_id: str):
        self.patient_id = patient_id
        self.state: Dict[str, Any] = {
            "id": patient_id,
            "vitals": {"hr": 80, "bp": "120/80"},
            "conditions": [],
            "last_updated": datetime.utcnow().isoformat(),
        }

    def step(self, minutes: int = 5) -> dict:
        """Advance the twin by given minutes and mutate state slightly."""
        # Simple deterministic state change for demo
        self.state["vitals"]["hr"] += 1
        self.state["last_updated"] = (datetime.utcnow() + timedelta(minutes=minutes)).isoformat()
        return self.state

    def snapshot(self) -> dict:
        """Return a snapshot of the current twin state."""
        return self.state
