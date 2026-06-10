"""
================================================================================
⚠️  LEGACY CODE - DO NOT USE
================================================================================
This LLM module contains AI/LLM providers that are NO LONGER IN USE.
The OncoLife symptom checker is now 100% RULE-BASED (no AI).

These providers were used in an earlier prototype:
    - GPT4oProvider (OpenAI GPT-4o)
    - GroqProvider (Groq API)
    - CerebrasProvider (Cerebras API)

The current production system uses:
    symptom_checker/symptom_engine.py  (rule-based, deterministic)

This code is retained for future reference only.
DO NOT import or use these providers.

Last active: Pre-January 2026
================================================================================
"""

from .base import LLMProvider
from .groq import GroqProvider
from .cerebras import CerebrasProvider
from .gpt import GPT4oProvider
