"""
Semantic Normalization Engine (SNE)

LLM-enriched fuzzy matching for local lab codes to LOINC/SNOMED-CT.
Implements the "Medical Rosetta Stone" with expert-in-the-loop feedback.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CodeMapping:
    """A mapping from local code to standard terminology."""
    local_code: str
    local_description: str
    standard_code: str
    standard_system: str  # LOINC, SNOMED-CT, etc.
    standard_description: str
    confidence: float  # 0.0 to 1.0
    mapping_method: str  # "exact", "fuzzy", "llm", "expert_verified"
    verified_by: Optional[str] = None  # User ID who verified
    verified_at: Optional[datetime] = None
    source_system: Optional[str] = None


class LLMCodeMapper:
    """
    LLM-powered fuzzy matching for local codes to standard terminologies.
    
    Uses medical-BERT or small language model (SLM) ensemble to perform
    fuzzy matching on local lab codes (e.g., "HgbA1c-lab-01") and map them
    to global LOINC or SNOMED-CT codes.
    """
    
    def __init__(self, llm_client=None, terminology_service=None):
        """
        Initialize LLM code mapper.
        
        Args:
            llm_client: LLM client for semantic matching
            terminology_service: Terminology service for standard code lookup
        """
        self.llm_client = llm_client
        self.terminology_service = terminology_service
    
    async def map_local_code(
        self,
        local_code: str,
        local_description: str,
        target_system: str = "LOINC",
        source_system: str = None,
    ) -> Optional[CodeMapping]:
        """
        Map a local code to standard terminology using LLM.
        
        Args:
            local_code: Local lab code (e.g., "HgbA1c-lab-01")
            local_description: Description of the local code
            target_system: Target terminology system (LOINC, SNOMED-CT)
            source_system: Source system name
            
        Returns:
            CodeMapping if match found, None otherwise
        """
        if not self.llm_client:
            logger.warning("LLM client not available, using fallback matching")
            return self._fallback_match(local_code, local_description, target_system)
        
        try:
            # Build prompt for LLM semantic matching
            prompt = f"""You are a medical terminology expert. Map this local lab code to {target_system}.

Local Code: {local_code}
Local Description: {local_description}

Find the best matching {target_system} code. Consider:
1. Semantic similarity (meaning)
2. Common abbreviations (e.g., "HgbA1c" = "Hemoglobin A1c")
3. Component names and synonyms

Respond in JSON format:
{{
    "standard_code": "LOINC_CODE",
    "standard_description": "Full description",
    "confidence": 0.0-1.0,
    "reasoning": "Why this match"
}}
"""
            
            response = await self.llm_client.generate(prompt, max_tokens=200)
            
            # Parse LLM response
            import json
            try:
                # Extract JSON from response
                content = response.content if hasattr(response, 'content') else str(response)
                # Try to find JSON in response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    result = json.loads(content[json_start:json_end])
                    
                    # Verify code exists in terminology service
                    if self.terminology_service:
                        verified = await self.terminology_service.validate(
                            result.get("standard_code"),
                            target_system.lower()
                        )
                        if not verified:
                            logger.warning(f"LLM suggested invalid code: {result.get('standard_code')}")
                            return None
                    
                    return CodeMapping(
                        local_code=local_code,
                        local_description=local_description,
                        standard_code=result.get("standard_code", ""),
                        standard_system=target_system,
                        standard_description=result.get("standard_description", ""),
                        confidence=float(result.get("confidence", 0.5)),
                        mapping_method="llm",
                        source_system=source_system,
                    )
            except (json.JSONDecodeError, ValueError) as e:
                logger.error("Failed to parse LLM response", error=str(e))
                return None
                
        except Exception as e:
            logger.error("LLM mapping failed", error=str(e), local_code=local_code)
            return self._fallback_match(local_code, local_description, target_system)
    
    def _fallback_match(
        self,
        local_code: str,
        local_description: str,
        target_system: str,
    ) -> Optional[CodeMapping]:
        """Fallback matching using keyword search."""
        if not self.terminology_service:
            return None
        
        # Simple keyword matching
        keywords = local_description.lower().split()
        # Try to find matches in terminology service
        # This is a simplified version - in production would use proper search
        
        return None
    
    async def map_batch(
        self,
        local_codes: List[Tuple[str, str]],  # List of (code, description)
        target_system: str = "LOINC",
        source_system: str = None,
    ) -> List[CodeMapping]:
        """Map multiple local codes in batch."""
        mappings = []
        for local_code, local_description in local_codes:
            mapping = await self.map_local_code(
                local_code,
                local_description,
                target_system,
                source_system,
            )
            if mapping:
                mappings.append(mapping)
        return mappings


class SemanticNormalizationEngine:
    """
    Semantic Normalization Engine (SNE).
    
    Multi-stage pipeline for mapping local codes to standard terminologies:
    1. Exact match lookup
    2. Fuzzy matching (LLM-powered)
    3. Expert verification (if available)
    """
    
    def __init__(
        self,
        llm_client=None,
        terminology_service=None,
        knowledge_base=None,  # For storing verified mappings
    ):
        self.llm_mapper = LLMCodeMapper(llm_client, terminology_service)
        self.terminology_service = terminology_service
        self.knowledge_base = knowledge_base  # Will store verified mappings
    
    async def normalize(
        self,
        local_code: str,
        local_description: str,
        source_system: str,
        target_system: str = "LOINC",
    ) -> Optional[CodeMapping]:
        """
        Normalize a local code to standard terminology.
        
        Pipeline:
        1. Check knowledge base for existing verified mapping
        2. Try exact match lookup
        3. Use LLM fuzzy matching
        4. Return best match
        
        Args:
            local_code: Local code
            local_description: Description
            source_system: Source system name
            target_system: Target terminology system
            
        Returns:
            CodeMapping if found
        """
        # Step 1: Check knowledge base for verified mapping
        if self.knowledge_base:
            verified = await self.knowledge_base.get_verified_mapping(
                local_code,
                source_system,
            )
            if verified:
                logger.debug("Using verified mapping from knowledge base", local_code=local_code)
                return verified
        
        # Step 2: Try exact match (if terminology service supports it)
        if self.terminology_service:
            exact_match = await self.terminology_service.lookup(local_code)
            if exact_match:
                return CodeMapping(
                    local_code=local_code,
                    local_description=local_description,
                    standard_code=exact_match.code if hasattr(exact_match, 'code') else str(exact_match),
                    standard_system=target_system,
                    standard_description=exact_match.display if hasattr(exact_match, 'display') else "",
                    confidence=1.0,
                    mapping_method="exact",
                    source_system=source_system,
                )
        
        # Step 3: LLM fuzzy matching
        llm_mapping = await self.llm_mapper.map_local_code(
            local_code,
            local_description,
            target_system,
            source_system,
        )
        
        return llm_mapping
