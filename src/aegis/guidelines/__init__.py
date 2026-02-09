"""
Clinical Guidelines

Specialty-specific guideline databases:
- NCCN (National Comprehensive Cancer Network) - Oncology
- KDIGO (Kidney Disease Improving Global Outcomes) - Nephrology
- ACC/AHA (American College of Cardiology/American Heart Association) - Cardiology

Guidelines are vectorized for RAG retrieval and cross-checked against agent outputs.
"""

from aegis.guidelines.base import BaseGuideline, GuidelineSection
from aegis.guidelines.nccn import NCCNGuideline
from aegis.guidelines.kdigo import KDIGOGuideline
from aegis.guidelines.loader import GuidelineLoader
from aegis.guidelines.vectorizer import GuidelineVectorizer
from aegis.guidelines.retriever import GuidelineRetriever
from aegis.guidelines.cross_check import GuidelineCrossChecker

__all__ = [
    "BaseGuideline",
    "GuidelineSection",
    "NCCNGuideline",
    "KDIGOGuideline",
    "GuidelineLoader",
    "GuidelineVectorizer",
    "GuidelineRetriever",
    "GuidelineCrossChecker",
]
