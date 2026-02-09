"""
Base Guideline Classes

Base classes for clinical guidelines with structured sections and citations.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class GuidelineType(str, Enum):
    """Types of clinical guidelines."""
    NCCN = "nccn"
    KDIGO = "kdigo"
    ACC_AHA = "acc_aha"
    ASCO = "asco"
    IDSA = "idsa"
    OTHER = "other"


class GuidelineSection:
    """A section within a clinical guideline."""
    
    def __init__(
        self,
        section_id: str,
        title: str,
        content: str,
        specialty: str,
        guideline_type: GuidelineType,
        version: str = "latest",
        publication_date: Optional[datetime] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        keywords: Optional[List[str]] = None,
    ):
        self.section_id = section_id
        self.title = title
        self.content = content
        self.specialty = specialty
        self.guideline_type = guideline_type
        self.version = version
        self.publication_date = publication_date or datetime.utcnow()
        self.citations = citations or []
        self.keywords = keywords or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "section_id": self.section_id,
            "title": self.title,
            "content": self.content,
            "specialty": self.specialty,
            "guideline_type": self.guideline_type.value,
            "version": self.version,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "citations": self.citations,
            "keywords": self.keywords,
        }


class BaseGuideline:
    """
    Base class for clinical guidelines.
    
    All guidelines inherit from this and provide:
    - Structured sections
    - Vectorized storage
    - Retrieval methods
    - Cross-check capabilities
    """
    
    def __init__(
        self,
        guideline_id: str,
        name: str,
        specialty: str,
        guideline_type: GuidelineType,
        version: str = "latest",
        publication_date: Optional[datetime] = None,
    ):
        self.guideline_id = guideline_id
        self.name = name
        self.specialty = specialty
        self.guideline_type = guideline_type
        self.version = version
        self.publication_date = publication_date or datetime.utcnow()
        self.sections: List[GuidelineSection] = []
    
    def add_section(self, section: GuidelineSection):
        """Add a section to the guideline."""
        self.sections.append(section)
    
    def get_section(self, section_id: str) -> Optional[GuidelineSection]:
        """Get a section by ID."""
        return next((s for s in self.sections if s.section_id == section_id), None)
    
    def search_sections(self, query: str) -> List[GuidelineSection]:
        """Search sections by query."""
        query_lower = query.lower()
        matching = []
        
        for section in self.sections:
            # Search in title and content
            if query_lower in section.title.lower() or query_lower in section.content.lower():
                matching.append(section)
            # Search in keywords
            elif any(query_lower in kw.lower() for kw in section.keywords):
                matching.append(section)
        
        return matching
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "guideline_id": self.guideline_id,
            "name": self.name,
            "specialty": self.specialty,
            "guideline_type": self.guideline_type.value,
            "version": self.version,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "sections": [s.to_dict() for s in self.sections],
        }
