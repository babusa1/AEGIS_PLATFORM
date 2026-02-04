"""
Patient Symptoms Tracking Module

Track patient-reported symptoms:
- Symptom entry and history
- Severity tracking
- Pattern detection
- Alert generation for concerning symptoms
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Symptom Definitions
# =============================================================================

class SymptomSeverity(str, Enum):
    """Symptom severity levels."""
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class SymptomCategory(str, Enum):
    """Symptom categories."""
    RESPIRATORY = "respiratory"
    CARDIOVASCULAR = "cardiovascular"
    GASTROINTESTINAL = "gastrointestinal"
    NEUROLOGICAL = "neurological"
    MUSCULOSKELETAL = "musculoskeletal"
    PAIN = "pain"
    GENERAL = "general"
    MENTAL_HEALTH = "mental_health"
    SKIN = "skin"


# Common symptoms catalog
SYMPTOM_CATALOG = {
    # Respiratory
    "cough": {"category": SymptomCategory.RESPIRATORY, "snomed": "49727002", "display": "Cough"},
    "shortness_of_breath": {"category": SymptomCategory.RESPIRATORY, "snomed": "267036007", "display": "Shortness of breath"},
    "wheezing": {"category": SymptomCategory.RESPIRATORY, "snomed": "56018004", "display": "Wheezing"},
    "chest_congestion": {"category": SymptomCategory.RESPIRATORY, "snomed": "23924001", "display": "Chest congestion"},
    
    # Cardiovascular
    "chest_pain": {"category": SymptomCategory.CARDIOVASCULAR, "snomed": "29857009", "display": "Chest pain", "alert_threshold": SymptomSeverity.MODERATE},
    "palpitations": {"category": SymptomCategory.CARDIOVASCULAR, "snomed": "80313002", "display": "Palpitations"},
    "swelling_legs": {"category": SymptomCategory.CARDIOVASCULAR, "snomed": "102572006", "display": "Leg swelling"},
    
    # Gastrointestinal
    "nausea": {"category": SymptomCategory.GASTROINTESTINAL, "snomed": "422587007", "display": "Nausea"},
    "vomiting": {"category": SymptomCategory.GASTROINTESTINAL, "snomed": "422400008", "display": "Vomiting"},
    "abdominal_pain": {"category": SymptomCategory.GASTROINTESTINAL, "snomed": "21522001", "display": "Abdominal pain"},
    "diarrhea": {"category": SymptomCategory.GASTROINTESTINAL, "snomed": "62315008", "display": "Diarrhea"},
    "constipation": {"category": SymptomCategory.GASTROINTESTINAL, "snomed": "14760008", "display": "Constipation"},
    
    # Neurological
    "headache": {"category": SymptomCategory.NEUROLOGICAL, "snomed": "25064002", "display": "Headache"},
    "dizziness": {"category": SymptomCategory.NEUROLOGICAL, "snomed": "404640003", "display": "Dizziness"},
    "confusion": {"category": SymptomCategory.NEUROLOGICAL, "snomed": "40917007", "display": "Confusion", "alert_threshold": SymptomSeverity.MODERATE},
    "weakness": {"category": SymptomCategory.NEUROLOGICAL, "snomed": "13791008", "display": "Weakness"},
    "numbness": {"category": SymptomCategory.NEUROLOGICAL, "snomed": "44077006", "display": "Numbness"},
    
    # Pain
    "back_pain": {"category": SymptomCategory.PAIN, "snomed": "161891005", "display": "Back pain"},
    "joint_pain": {"category": SymptomCategory.PAIN, "snomed": "57676002", "display": "Joint pain"},
    "muscle_pain": {"category": SymptomCategory.PAIN, "snomed": "68962001", "display": "Muscle pain"},
    
    # General
    "fatigue": {"category": SymptomCategory.GENERAL, "snomed": "84229001", "display": "Fatigue"},
    "fever": {"category": SymptomCategory.GENERAL, "snomed": "386661006", "display": "Fever"},
    "chills": {"category": SymptomCategory.GENERAL, "snomed": "43724002", "display": "Chills"},
    "weight_loss": {"category": SymptomCategory.GENERAL, "snomed": "89362005", "display": "Weight loss"},
    "loss_of_appetite": {"category": SymptomCategory.GENERAL, "snomed": "79890006", "display": "Loss of appetite"},
    
    # Mental Health
    "anxiety": {"category": SymptomCategory.MENTAL_HEALTH, "snomed": "48694002", "display": "Anxiety"},
    "depression": {"category": SymptomCategory.MENTAL_HEALTH, "snomed": "35489007", "display": "Depression"},
    "insomnia": {"category": SymptomCategory.MENTAL_HEALTH, "snomed": "193462001", "display": "Insomnia"},
    
    # Skin
    "rash": {"category": SymptomCategory.SKIN, "snomed": "271807003", "display": "Rash"},
    "itching": {"category": SymptomCategory.SKIN, "snomed": "418290006", "display": "Itching"},
}


# =============================================================================
# Symptom Models
# =============================================================================

class Symptom(BaseModel):
    """Symptom definition."""
    code: str
    display: str
    category: SymptomCategory
    snomed_code: Optional[str] = None
    alert_threshold: SymptomSeverity = SymptomSeverity.SEVERE


class SymptomEntry(BaseModel):
    """Patient symptom entry."""
    id: str
    patient_id: str
    tenant_id: str = "default"
    
    # Symptom
    symptom_code: str
    symptom_display: str
    category: SymptomCategory
    
    # Severity
    severity: SymptomSeverity
    severity_score: int = Field(ge=0, le=10, description="0-10 severity score")
    
    # Details
    onset_date: Optional[datetime] = None
    duration_hours: Optional[int] = None
    frequency: Optional[str] = None  # constant, intermittent, occasional
    
    # Context
    location: Optional[str] = None
    triggers: List[str] = Field(default_factory=list)
    relieving_factors: List[str] = Field(default_factory=list)
    associated_symptoms: List[str] = Field(default_factory=list)
    
    # Notes
    notes: Optional[str] = None
    
    # Timing
    reported_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Alert
    alert_generated: bool = False


class SymptomHistory(BaseModel):
    """Patient symptom history."""
    patient_id: str
    entries: List[SymptomEntry] = Field(default_factory=list)
    
    # Summary
    active_symptoms: int = 0
    severe_symptoms: int = 0
    symptom_trend: str = "stable"  # improving, stable, worsening
    
    # Last reported
    last_report_date: Optional[datetime] = None


class SymptomTrend(BaseModel):
    """Symptom trend analysis."""
    symptom_code: str
    symptom_display: str
    
    # History
    entries: List[dict] = Field(default_factory=list)
    
    # Trend
    trend: str  # improving, stable, worsening
    severity_change: float
    
    # Statistics
    average_severity: float
    max_severity: int
    frequency_per_week: float


# =============================================================================
# Symptom Tracker Service
# =============================================================================

class SymptomTracker:
    """
    Service for tracking patient-reported symptoms.
    
    Features:
    - Symptom entry
    - History tracking
    - Trend analysis
    - Alert generation
    """
    
    def __init__(self, pool=None):
        self.pool = pool
        self._symptom_store: Dict[str, List[SymptomEntry]] = {}  # In-memory for demo
    
    async def record_symptom(
        self,
        patient_id: str,
        symptom_code: str,
        severity_score: int,
        tenant_id: str = "default",
        notes: str = None,
        onset_date: datetime = None,
        triggers: List[str] = None,
    ) -> SymptomEntry:
        """
        Record a patient symptom.
        
        Args:
            patient_id: Patient identifier
            symptom_code: Symptom code from catalog
            severity_score: 0-10 severity score
            tenant_id: Tenant identifier
            notes: Additional notes
            onset_date: When symptom started
            triggers: What triggers the symptom
            
        Returns:
            Created symptom entry
        """
        import uuid
        
        # Get symptom info
        symptom_info = SYMPTOM_CATALOG.get(symptom_code)
        if not symptom_info:
            raise ValueError(f"Unknown symptom code: {symptom_code}")
        
        # Map score to severity
        severity = self._score_to_severity(severity_score)
        
        entry = SymptomEntry(
            id=str(uuid.uuid4()),
            patient_id=patient_id,
            tenant_id=tenant_id,
            symptom_code=symptom_code,
            symptom_display=symptom_info["display"],
            category=symptom_info["category"],
            severity=severity,
            severity_score=severity_score,
            onset_date=onset_date,
            notes=notes,
            triggers=triggers or [],
        )
        
        # Check if alert needed
        alert_threshold = symptom_info.get("alert_threshold", SymptomSeverity.SEVERE)
        if self._severity_exceeds(severity, alert_threshold):
            entry.alert_generated = True
            await self._generate_alert(entry)
        
        # Store
        await self._store_entry(entry)
        
        logger.info(
            "Symptom recorded",
            patient_id=patient_id,
            symptom=symptom_code,
            severity=severity.value,
            alert=entry.alert_generated,
        )
        
        return entry
    
    async def get_patient_symptoms(
        self,
        patient_id: str,
        tenant_id: str = "default",
        days: int = 30,
    ) -> SymptomHistory:
        """
        Get patient symptom history.
        
        Args:
            patient_id: Patient identifier
            tenant_id: Tenant identifier
            days: Number of days to include
            
        Returns:
            Symptom history
        """
        entries = await self._get_entries(patient_id, tenant_id, days)
        
        active = [e for e in entries if e.reported_at > datetime.utcnow() - timedelta(days=7)]
        severe = [e for e in entries if e.severity in [SymptomSeverity.SEVERE, SymptomSeverity.CRITICAL]]
        
        # Determine trend
        trend = self._calculate_trend(entries)
        
        return SymptomHistory(
            patient_id=patient_id,
            entries=entries,
            active_symptoms=len(set(e.symptom_code for e in active)),
            severe_symptoms=len(severe),
            symptom_trend=trend,
            last_report_date=entries[0].reported_at if entries else None,
        )
    
    async def get_symptom_trend(
        self,
        patient_id: str,
        symptom_code: str,
        days: int = 30,
    ) -> SymptomTrend:
        """
        Get trend for a specific symptom.
        
        Args:
            patient_id: Patient identifier
            symptom_code: Symptom to analyze
            days: Days to analyze
            
        Returns:
            Symptom trend analysis
        """
        entries = await self._get_entries(patient_id, symptom_code=symptom_code, days=days)
        
        if not entries:
            symptom_info = SYMPTOM_CATALOG.get(symptom_code, {})
            return SymptomTrend(
                symptom_code=symptom_code,
                symptom_display=symptom_info.get("display", symptom_code),
                trend="no_data",
                severity_change=0,
                average_severity=0,
                max_severity=0,
                frequency_per_week=0,
            )
        
        # Calculate statistics
        scores = [e.severity_score for e in entries]
        avg_severity = sum(scores) / len(scores)
        max_severity = max(scores)
        
        # Calculate frequency
        time_span = (datetime.utcnow() - entries[-1].reported_at).days or 1
        frequency = len(entries) / (time_span / 7) if time_span >= 7 else len(entries)
        
        # Calculate trend
        if len(entries) >= 2:
            recent = entries[:len(entries)//2]
            older = entries[len(entries)//2:]
            recent_avg = sum(e.severity_score for e in recent) / len(recent)
            older_avg = sum(e.severity_score for e in older) / len(older)
            
            if recent_avg > older_avg + 1:
                trend = "worsening"
            elif recent_avg < older_avg - 1:
                trend = "improving"
            else:
                trend = "stable"
            
            severity_change = recent_avg - older_avg
        else:
            trend = "insufficient_data"
            severity_change = 0
        
        return SymptomTrend(
            symptom_code=symptom_code,
            symptom_display=entries[0].symptom_display,
            entries=[
                {"date": e.reported_at.isoformat(), "severity": e.severity_score}
                for e in entries
            ],
            trend=trend,
            severity_change=round(severity_change, 2),
            average_severity=round(avg_severity, 2),
            max_severity=max_severity,
            frequency_per_week=round(frequency, 2),
        )
    
    async def get_symptom_catalog(
        self,
        category: SymptomCategory = None,
    ) -> List[Symptom]:
        """Get available symptoms."""
        symptoms = []
        
        for code, info in SYMPTOM_CATALOG.items():
            if category and info["category"] != category:
                continue
            
            symptoms.append(Symptom(
                code=code,
                display=info["display"],
                category=info["category"],
                snomed_code=info.get("snomed"),
                alert_threshold=info.get("alert_threshold", SymptomSeverity.SEVERE),
            ))
        
        return symptoms
    
    def _score_to_severity(self, score: int) -> SymptomSeverity:
        """Convert 0-10 score to severity level."""
        if score == 0:
            return SymptomSeverity.NONE
        elif score <= 3:
            return SymptomSeverity.MILD
        elif score <= 6:
            return SymptomSeverity.MODERATE
        elif score <= 8:
            return SymptomSeverity.SEVERE
        else:
            return SymptomSeverity.CRITICAL
    
    def _severity_exceeds(
        self,
        current: SymptomSeverity,
        threshold: SymptomSeverity,
    ) -> bool:
        """Check if current severity exceeds threshold."""
        order = [
            SymptomSeverity.NONE,
            SymptomSeverity.MILD,
            SymptomSeverity.MODERATE,
            SymptomSeverity.SEVERE,
            SymptomSeverity.CRITICAL,
        ]
        return order.index(current) >= order.index(threshold)
    
    async def _generate_alert(self, entry: SymptomEntry):
        """Generate alert for severe symptom."""
        logger.warning(
            "SYMPTOM ALERT",
            patient_id=entry.patient_id,
            symptom=entry.symptom_display,
            severity=entry.severity.value,
            score=entry.severity_score,
        )
        # Would integrate with notification service
    
    async def _store_entry(self, entry: SymptomEntry):
        """Store symptom entry."""
        if self.pool:
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO symptoms 
                        (id, patient_id, tenant_id, symptom_code, symptom_display,
                         category, severity, severity_score, notes, reported_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                        entry.id, entry.patient_id, entry.tenant_id,
                        entry.symptom_code, entry.symptom_display,
                        entry.category.value, entry.severity.value,
                        entry.severity_score, entry.notes, entry.reported_at,
                    )
            except Exception as e:
                logger.error(f"Failed to store symptom: {e}")
        
        # In-memory storage
        key = f"{entry.tenant_id}:{entry.patient_id}"
        if key not in self._symptom_store:
            self._symptom_store[key] = []
        self._symptom_store[key].insert(0, entry)
    
    async def _get_entries(
        self,
        patient_id: str,
        tenant_id: str = "default",
        symptom_code: str = None,
        days: int = 30,
    ) -> List[SymptomEntry]:
        """Get symptom entries."""
        key = f"{tenant_id}:{patient_id}"
        entries = self._symptom_store.get(key, [])
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        filtered = [e for e in entries if e.reported_at > cutoff]
        
        if symptom_code:
            filtered = [e for e in filtered if e.symptom_code == symptom_code]
        
        return filtered
    
    def _calculate_trend(self, entries: List[SymptomEntry]) -> str:
        """Calculate overall symptom trend."""
        if len(entries) < 3:
            return "insufficient_data"
        
        recent = entries[:len(entries)//2]
        older = entries[len(entries)//2:]
        
        recent_avg = sum(e.severity_score for e in recent) / len(recent)
        older_avg = sum(e.severity_score for e in older) / len(older)
        
        if recent_avg > older_avg + 1:
            return "worsening"
        elif recent_avg < older_avg - 1:
            return "improving"
        else:
            return "stable"


# =============================================================================
# API Router
# =============================================================================

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel as PydanticBaseModel

router = APIRouter(prefix="/symptoms", tags=["Symptoms Tracking"])


class RecordSymptomRequest(PydanticBaseModel):
    """Request to record a symptom."""
    patient_id: str
    symptom_code: str
    severity_score: int = Field(ge=0, le=10)
    tenant_id: str = "default"
    notes: Optional[str] = None
    onset_date: Optional[datetime] = None
    triggers: Optional[List[str]] = None


@router.get("/catalog")
async def get_symptom_catalog(
    category: str = Query(default=None, description="Filter by category"),
):
    """Get available symptom codes."""
    tracker = SymptomTracker()
    
    cat = SymptomCategory(category) if category else None
    symptoms = await tracker.get_symptom_catalog(cat)
    
    return {
        "symptoms": [s.model_dump() for s in symptoms],
        "categories": [c.value for c in SymptomCategory],
    }


@router.post("/record")
async def record_symptom(request: RecordSymptomRequest):
    """
    Record a patient symptom.
    
    Generates alerts for severe symptoms.
    """
    tracker = SymptomTracker()
    
    try:
        entry = await tracker.record_symptom(
            patient_id=request.patient_id,
            symptom_code=request.symptom_code,
            severity_score=request.severity_score,
            tenant_id=request.tenant_id,
            notes=request.notes,
            onset_date=request.onset_date,
            triggers=request.triggers,
        )
        
        return {
            "id": entry.id,
            "symptom": entry.symptom_display,
            "severity": entry.severity.value,
            "severity_score": entry.severity_score,
            "alert_generated": entry.alert_generated,
            "reported_at": entry.reported_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/patient/{patient_id}")
async def get_patient_symptoms(
    patient_id: str,
    tenant_id: str = Query(default="default"),
    days: int = Query(default=30, ge=1, le=365),
):
    """Get patient symptom history."""
    tracker = SymptomTracker()
    
    history = await tracker.get_patient_symptoms(patient_id, tenant_id, days)
    
    return {
        "patient_id": history.patient_id,
        "active_symptoms": history.active_symptoms,
        "severe_symptoms": history.severe_symptoms,
        "trend": history.symptom_trend,
        "last_report": history.last_report_date.isoformat() if history.last_report_date else None,
        "entries": [
            {
                "id": e.id,
                "symptom": e.symptom_display,
                "category": e.category.value,
                "severity": e.severity.value,
                "severity_score": e.severity_score,
                "reported_at": e.reported_at.isoformat(),
                "alert": e.alert_generated,
            }
            for e in history.entries
        ],
    }


@router.get("/patient/{patient_id}/trend/{symptom_code}")
async def get_symptom_trend(
    patient_id: str,
    symptom_code: str,
    days: int = Query(default=30, ge=7, le=365),
):
    """Get trend for a specific symptom."""
    tracker = SymptomTracker()
    
    trend = await tracker.get_symptom_trend(patient_id, symptom_code, days)
    
    return {
        "symptom": trend.symptom_display,
        "trend": trend.trend,
        "severity_change": trend.severity_change,
        "average_severity": trend.average_severity,
        "max_severity": trend.max_severity,
        "frequency_per_week": trend.frequency_per_week,
        "history": trend.entries,
    }
