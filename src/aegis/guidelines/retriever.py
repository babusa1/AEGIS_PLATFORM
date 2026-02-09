"""
Guideline Retriever

Retrieves relevant guideline sections using vector search.
"""

from typing import List, Dict, Any, Optional
import structlog

from aegis.guidelines.base import BaseGuideline, GuidelineSection, GuidelineType

logger = structlog.get_logger(__name__)


class GuidelineRetriever:
    """
    Retrieves relevant guideline sections for queries.
    
    Uses vector search to find guidelines matching clinical queries.
    """
    
    def __init__(self, vector_client=None, guideline_loader=None):
        """
        Initialize retriever.
        
        Args:
            vector_client: Vector database client
            guideline_loader: Guideline loader
        """
        self.vector_client = vector_client
        self.guideline_loader = guideline_loader
    
    async def retrieve_relevant_sections(
        self,
        query: str,
        specialty: Optional[str] = None,
        guideline_type: Optional[GuidelineType] = None,
        top_k: int = 5,
    ) -> List[GuidelineSection]:
        """
        Retrieve relevant guideline sections for a query.
        
        Args:
            query: Clinical query (e.g., "dose hold criteria for anemia")
            specialty: Optional specialty filter
            guideline_type: Optional guideline type filter
            top_k: Number of results
            
        Returns:
            List of relevant GuidelineSection objects
        """
        logger.info(
            "Retrieving guideline sections",
            query=query,
            specialty=specialty,
            guideline_type=guideline_type.value if guideline_type else None,
        )
        
        # In production, would use vector search
        # For now, use keyword matching
        
        relevant_sections = []
        
        # Search in loaded guidelines
        if self.guideline_loader:
            for guideline_id, guideline in self.guideline_loader.loaded_guidelines.items():
                # Apply filters
                if specialty and guideline.specialty != specialty:
                    continue
                if guideline_type and guideline.guideline_type != guideline_type:
                    continue
                
                # Search sections
                matching = guideline.search_sections(query)
                relevant_sections.extend(matching)
        
        # Sort by relevance (simplified - would use vector similarity)
        relevant_sections = relevant_sections[:top_k]
        
        return relevant_sections
    
    async def get_guideline_for_action(
        self,
        action: Dict[str, Any],
        specialty: str,
    ) -> Optional[GuidelineSection]:
        """
        Get relevant guideline section for a proposed action.
        
        Args:
            action: Proposed action (e.g., {"type": "medication", "name": "Lisinopril"})
            specialty: Specialty (e.g., "nephrology", "oncology")
            
        Returns:
            Relevant GuidelineSection or None
        """
        # Build query from action
        query_parts = []
        
        if action.get("type") == "medication":
            query_parts.append(f"{action.get('name')} guidelines")
        elif action.get("type") == "lab":
            query_parts.append(f"{action.get('test')} threshold")
        elif action.get("type") == "dose_modification"):
            query_parts.append("dose hold criteria")
        
        query = " ".join(query_parts)
        
        # Determine guideline type
        guideline_type = None
        if specialty == "oncology":
            guideline_type = GuidelineType.NCCN
        elif specialty == "nephrology":
            guideline_type = GuidelineType.KDIGO
        
        # Retrieve
        sections = await self.retrieve_relevant_sections(
            query=query,
            specialty=specialty,
            guideline_type=guideline_type,
            top_k=1,
        )
        
        return sections[0] if sections else None
