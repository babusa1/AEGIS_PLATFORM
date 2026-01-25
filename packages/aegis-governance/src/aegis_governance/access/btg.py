"""Break-the-Glass Emergency Access"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import structlog

logger = structlog.get_logger(__name__)


class BTGReason(str, Enum):
    EMERGENCY = "emergency"
    PATIENT_CARE = "patient_care"
    LIFE_THREATENING = "life_threatening"


class BTGStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVIEWED = "reviewed"


@dataclass
class BTGRequest:
    user_id: str
    patient_id: str
    reason: BTGReason
    justification: str


@dataclass
class BTGSession:
    id: str
    request: BTGRequest
    status: BTGStatus
    granted_at: datetime
    expires_at: datetime
    accessed: list[str] = field(default_factory=list)


class BreakTheGlass:
    def __init__(self):
        self._sessions: dict[str, BTGSession] = {}
        self._pending: list[str] = []
    
    def request_access(self, req: BTGRequest) -> BTGSession:
        sid = f"BTG-{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()
        s = BTGSession(sid, req, BTGStatus.ACTIVE, now, now + timedelta(hours=4))
        self._sessions[sid] = s
        self._pending.append(sid)
        logger.warning("BTG granted", session=sid, user=req.user_id)
        return s
    
    def check_access(self, sid: str) -> bool:
        s = self._sessions.get(sid)
        if not s or s.status != BTGStatus.ACTIVE:
            return False
        if datetime.utcnow() > s.expires_at:
            s.status = BTGStatus.EXPIRED
            return False
        return True
    
    def review(self, sid: str, reviewer: str):
        s = self._sessions.get(sid)
        if s:
            s.status = BTGStatus.REVIEWED
            if sid in self._pending:
                self._pending.remove(sid)
