"""G1: Consent Enforcement Engine - HITRUST 09.a, SOC 2 Privacy"""
from aegis_governance.consent.engine import ConsentEngine
from aegis_governance.consent.models import Consent, ConsentScope, ConsentDecision

__all__ = ["ConsentEngine", "Consent", "ConsentScope", "ConsentDecision"]
