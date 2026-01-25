"""Consent Enforcement Engine - Real-time consent checking"""
from datetime import datetime
from typing import Any
import structlog

from aegis_governance.consent.models import (
    Consent, ConsentStatus, ConsentScope, ConsentAction,
    ConsentDecision, ConsentProvision, DataCategory
)

logger = structlog.get_logger(__name__)


class ConsentEngine:
    """
    Real-time consent enforcement engine.
    
    SOC 2 Privacy: Ensures data access aligns with consent
    HITRUST 09.a: Privacy notice and consent
    """
    
    def __init__(self):
        self._consents: dict[str, list[Consent]] = {}  # patient_id -> consents
        self._default_policy = "deny"  # deny by default
    
    def register_consent(self, consent: Consent) -> str:
        """Register a new consent record."""
        if consent.patient_id not in self._consents:
            self._consents[consent.patient_id] = []
        
        # Check for existing consent with same scope
        existing = [c for c in self._consents[consent.patient_id] 
                   if c.scope == consent.scope and c.status == ConsentStatus.ACTIVE]
        
        # Deactivate old consents
        for old in existing:
            old.status = ConsentStatus.INACTIVE
            old.updated_at = datetime.utcnow()
        
        self._consents[consent.patient_id].append(consent)
        
        logger.info("Consent registered",
            consent_id=consent.id,
            patient_id=consent.patient_id,
            scope=consent.scope.value)
        
        return consent.id
    
    def check_consent(
        self,
        patient_id: str,
        action: ConsentAction,
        purpose: ConsentScope,
        actor: str,
        data_categories: list[DataCategory] | None = None
    ) -> ConsentDecision:
        """
        Check if an action is permitted by patient consent.
        
        Returns ConsentDecision with allowed=True/False and reason.
        """
        data_categories = data_categories or [DataCategory.GENERAL]
        
        # Get active consents for patient
        consents = self._consents.get(patient_id, [])
        active_consents = [c for c in consents 
                         if c.status == ConsentStatus.ACTIVE
                         and (c.expires_at is None or c.expires_at > datetime.utcnow())]
        
        if not active_consents:
            return ConsentDecision(
                allowed=self._default_policy == "permit",
                consent_id=None,
                reason="No active consent found for patient"
            )
        
        # Find matching consent for purpose
        matching = [c for c in active_consents if c.scope == purpose]
        
        if not matching:
            # Check for general treatment consent as fallback
            matching = [c for c in active_consents if c.scope == ConsentScope.TREATMENT]
        
        if not matching:
            return ConsentDecision(
                allowed=False,
                consent_id=None,
                reason=f"No consent found for purpose: {purpose.value}"
            )
        
        # Evaluate provisions
        consent = matching[0]
        decision = self._evaluate_provisions(
            consent, action, purpose, actor, data_categories
        )
        
        logger.info("Consent checked",
            patient_id=patient_id,
            action=action.value,
            purpose=purpose.value,
            allowed=decision.allowed)
        
        return decision
    
    def _evaluate_provisions(
        self,
        consent: Consent,
        action: ConsentAction,
        purpose: ConsentScope,
        actor: str,
        data_categories: list[DataCategory]
    ) -> ConsentDecision:
        """Evaluate consent provisions against requested action."""
        
        if not consent.provisions:
            # No specific provisions = general permit
            return ConsentDecision(
                allowed=True,
                consent_id=consent.id,
                reason="Consent granted (no specific restrictions)"
            )
        
        applied_provisions = []
        restrictions = {}
        
        # Check each provision
        for provision in consent.provisions:
            # Check if provision applies to this action
            if action not in provision.action:
                continue
            
            # Check if provision applies to requested data categories
            category_match = any(
                cat in provision.data_categories for cat in data_categories
            ) or DataCategory.GENERAL in provision.data_categories
            
            if not category_match:
                continue
            
            # Check actor restriction
            if provision.actors and actor not in provision.actors:
                continue
            
            # Check time period
            now = datetime.utcnow()
            if provision.period_start and now < provision.period_start:
                continue
            if provision.period_end and now > provision.period_end:
                continue
            
            # Provision applies
            applied_provisions.append(provision.type)
            
            if provision.type == "deny":
                # Explicit deny for sensitive categories
                denied_cats = [c.value for c in data_categories 
                              if c in provision.data_categories]
                return ConsentDecision(
                    allowed=False,
                    consent_id=consent.id,
                    reason=f"Consent denies access to: {denied_cats}",
                    provisions_applied=applied_provisions
                )
            
            # Track any restrictions
            if provision.data_categories:
                restrictions["allowed_categories"] = [
                    c.value for c in provision.data_categories
                ]
        
        # Default to permit if no deny provisions matched
        return ConsentDecision(
            allowed=True,
            consent_id=consent.id,
            reason="Consent permits action",
            provisions_applied=applied_provisions,
            restrictions=restrictions
        )
    
    def revoke_consent(self, consent_id: str, reason: str = "") -> bool:
        """Revoke a specific consent."""
        for patient_consents in self._consents.values():
            for consent in patient_consents:
                if consent.id == consent_id:
                    consent.status = ConsentStatus.INACTIVE
                    consent.updated_at = datetime.utcnow()
                    logger.info("Consent revoked",
                        consent_id=consent_id,
                        reason=reason)
                    return True
        return False
    
    def get_patient_consents(self, patient_id: str) -> list[Consent]:
        """Get all consents for a patient."""
        return self._consents.get(patient_id, [])
    
    def get_active_consents(self, patient_id: str) -> list[Consent]:
        """Get only active consents for a patient."""
        consents = self._consents.get(patient_id, [])
        now = datetime.utcnow()
        return [c for c in consents 
                if c.status == ConsentStatus.ACTIVE
                and (c.expires_at is None or c.expires_at > now)]
