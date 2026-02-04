"""
Healthcare Terminology Services

Supports:
- ICD-10-CM/PCS lookup
- CPT/HCPCS lookup
- SNOMED CT lookup
- RxNorm lookup
- LOINC lookup
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio
import aiohttp

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Models
# =============================================================================

class CodeInfo(BaseModel):
    """Information about a medical code."""
    code: str
    system: str
    display: str
    description: Optional[str] = None
    category: Optional[str] = None
    is_valid: bool = True
    effective_date: Optional[str] = None
    
    # Hierarchy
    parent_codes: List[str] = Field(default_factory=list)
    child_codes: List[str] = Field(default_factory=list)
    
    # Related codes
    related: List[dict] = Field(default_factory=list)


class CodeSearchResult(BaseModel):
    """Search result for terminology lookup."""
    query: str
    system: str
    total: int = 0
    results: List[CodeInfo] = Field(default_factory=list)


# =============================================================================
# ICD-10 Lookup
# =============================================================================

class ICD10Lookup:
    """
    ICD-10-CM/PCS code lookup.
    
    Features:
    - Code validation
    - Description lookup
    - Category navigation
    - Code search
    """
    
    # Common ICD-10 codes for demo
    COMMON_CODES = {
        "E11.9": {"display": "Type 2 diabetes mellitus without complications", "category": "Diabetes"},
        "I10": {"display": "Essential (primary) hypertension", "category": "Cardiovascular"},
        "J06.9": {"display": "Acute upper respiratory infection, unspecified", "category": "Respiratory"},
        "M54.5": {"display": "Low back pain", "category": "Musculoskeletal"},
        "F32.9": {"display": "Major depressive disorder, single episode, unspecified", "category": "Mental Health"},
        "J18.9": {"display": "Pneumonia, unspecified organism", "category": "Respiratory"},
        "N39.0": {"display": "Urinary tract infection, site not specified", "category": "Genitourinary"},
        "K21.0": {"display": "Gastro-esophageal reflux disease with esophagitis", "category": "Digestive"},
        "G43.909": {"display": "Migraine, unspecified, not intractable", "category": "Nervous System"},
        "R05": {"display": "Cough", "category": "Symptoms"},
    }
    
    def __init__(self, api_url: str = None):
        self.api_url = api_url or "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3"
    
    def lookup(self, code: str) -> Optional[CodeInfo]:
        """Look up an ICD-10 code."""
        code = code.upper().strip()
        
        if code in self.COMMON_CODES:
            info = self.COMMON_CODES[code]
            return CodeInfo(
                code=code,
                system="http://hl7.org/fhir/sid/icd-10-cm",
                display=info["display"],
                category=info.get("category"),
            )
        
        return None
    
    async def search(self, query: str, max_results: int = 10) -> CodeSearchResult:
        """Search ICD-10 codes."""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "terms": query,
                    "maxList": max_results,
                }
                async with session.get(self.api_url + "/search", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        # Parse NLM API response format
                        if len(data) >= 4:
                            codes = data[1]
                            displays = data[3]
                            
                            for i, code in enumerate(codes):
                                display = displays[i][0] if i < len(displays) else ""
                                results.append(CodeInfo(
                                    code=code,
                                    system="http://hl7.org/fhir/sid/icd-10-cm",
                                    display=display,
                                ))
                        
                        return CodeSearchResult(
                            query=query,
                            system="ICD-10-CM",
                            total=len(results),
                            results=results,
                        )
        except Exception as e:
            logger.error(f"ICD-10 search error: {e}")
        
        return CodeSearchResult(query=query, system="ICD-10-CM")
    
    def validate(self, code: str) -> bool:
        """Validate an ICD-10 code format."""
        import re
        # ICD-10-CM pattern: Letter followed by 2 digits, optionally a period and more characters
        pattern = r'^[A-Z]\d{2}(\.\d{1,4})?$'
        return bool(re.match(pattern, code.upper()))


# =============================================================================
# CPT Lookup
# =============================================================================

class CPTLookup:
    """
    CPT/HCPCS code lookup.
    
    Note: CPT codes are copyrighted by AMA, so this uses
    limited demo data or requires proper licensing.
    """
    
    # Common CPT codes for demo
    COMMON_CODES = {
        "99213": {"display": "Office visit, established patient, low complexity", "category": "E&M"},
        "99214": {"display": "Office visit, established patient, moderate complexity", "category": "E&M"},
        "99215": {"display": "Office visit, established patient, high complexity", "category": "E&M"},
        "99203": {"display": "Office visit, new patient, low complexity", "category": "E&M"},
        "99204": {"display": "Office visit, new patient, moderate complexity", "category": "E&M"},
        "99385": {"display": "Initial preventive visit, 18-39 years", "category": "Preventive"},
        "99386": {"display": "Initial preventive visit, 40-64 years", "category": "Preventive"},
        "36415": {"display": "Collection of venous blood by venipuncture", "category": "Lab"},
        "80053": {"display": "Comprehensive metabolic panel", "category": "Lab"},
        "85025": {"display": "Complete blood count (CBC)", "category": "Lab"},
    }
    
    def lookup(self, code: str) -> Optional[CodeInfo]:
        """Look up a CPT code."""
        code = code.strip()
        
        if code in self.COMMON_CODES:
            info = self.COMMON_CODES[code]
            return CodeInfo(
                code=code,
                system="http://www.ama-assn.org/go/cpt",
                display=info["display"],
                category=info.get("category"),
            )
        
        return None
    
    def validate(self, code: str) -> bool:
        """Validate CPT code format."""
        # CPT codes are 5 digits
        return code.isdigit() and len(code) == 5


# =============================================================================
# SNOMED CT Lookup
# =============================================================================

class SNOMEDLookup:
    """
    SNOMED CT code lookup.
    
    Uses the NLM SNOMED CT Browser API.
    """
    
    COMMON_CODES = {
        "44054006": {"display": "Diabetes mellitus type 2", "category": "Clinical Finding"},
        "38341003": {"display": "Hypertensive disorder", "category": "Clinical Finding"},
        "195967001": {"display": "Asthma", "category": "Clinical Finding"},
        "13645005": {"display": "Chronic obstructive lung disease", "category": "Clinical Finding"},
        "22298006": {"display": "Myocardial infarction", "category": "Clinical Finding"},
    }
    
    def __init__(self, api_url: str = None):
        self.api_url = api_url or "https://browser.ihtsdotools.org/snowstorm/snomed-ct/browser/MAIN"
    
    def lookup(self, code: str) -> Optional[CodeInfo]:
        """Look up a SNOMED CT code."""
        if code in self.COMMON_CODES:
            info = self.COMMON_CODES[code]
            return CodeInfo(
                code=code,
                system="http://snomed.info/sct",
                display=info["display"],
                category=info.get("category"),
            )
        return None
    
    async def search(self, query: str, max_results: int = 10) -> CodeSearchResult:
        """Search SNOMED CT."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/concepts"
                params = {
                    "term": query,
                    "limit": max_results,
                    "activeFilter": "true",
                }
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        for item in data.get("items", []):
                            results.append(CodeInfo(
                                code=item.get("conceptId", ""),
                                system="http://snomed.info/sct",
                                display=item.get("fsn", {}).get("term", ""),
                            ))
                        
                        return CodeSearchResult(
                            query=query,
                            system="SNOMED-CT",
                            total=data.get("total", len(results)),
                            results=results,
                        )
        except Exception as e:
            logger.error(f"SNOMED search error: {e}")
        
        return CodeSearchResult(query=query, system="SNOMED-CT")


# =============================================================================
# RxNorm Lookup
# =============================================================================

class RxNormLookup:
    """
    RxNorm medication code lookup.
    
    Uses the NLM RxNorm API.
    """
    
    COMMON_CODES = {
        "197361": {"display": "Metformin 500 MG Oral Tablet", "category": "Diabetes"},
        "310798": {"display": "Lisinopril 10 MG Oral Tablet", "category": "Cardiovascular"},
        "197380": {"display": "Atorvastatin 20 MG Oral Tablet", "category": "Cardiovascular"},
        "312961": {"display": "Omeprazole 20 MG Delayed Release Oral Capsule", "category": "GI"},
        "197517": {"display": "Amlodipine 5 MG Oral Tablet", "category": "Cardiovascular"},
    }
    
    def __init__(self):
        self.api_url = "https://rxnav.nlm.nih.gov/REST"
    
    def lookup(self, code: str) -> Optional[CodeInfo]:
        """Look up an RxNorm code."""
        if code in self.COMMON_CODES:
            info = self.COMMON_CODES[code]
            return CodeInfo(
                code=code,
                system="http://www.nlm.nih.gov/research/umls/rxnorm",
                display=info["display"],
                category=info.get("category"),
            )
        return None
    
    async def search(self, query: str, max_results: int = 10) -> CodeSearchResult:
        """Search RxNorm medications."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/drugs.json"
                params = {"name": query}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        drug_group = data.get("drugGroup", {})
                        concept_group = drug_group.get("conceptGroup", [])
                        
                        for group in concept_group:
                            for props in group.get("conceptProperties", [])[:max_results]:
                                results.append(CodeInfo(
                                    code=props.get("rxcui", ""),
                                    system="http://www.nlm.nih.gov/research/umls/rxnorm",
                                    display=props.get("name", ""),
                                ))
                        
                        return CodeSearchResult(
                            query=query,
                            system="RxNorm",
                            total=len(results),
                            results=results[:max_results],
                        )
        except Exception as e:
            logger.error(f"RxNorm search error: {e}")
        
        return CodeSearchResult(query=query, system="RxNorm")


# =============================================================================
# Unified Terminology Service
# =============================================================================

class TerminologyService:
    """
    Unified terminology service.
    
    Provides single interface to all terminology systems.
    """
    
    def __init__(self):
        self.icd10 = ICD10Lookup()
        self.cpt = CPTLookup()
        self.snomed = SNOMEDLookup()
        self.rxnorm = RxNormLookup()
    
    def lookup(self, code: str, system: str = None) -> Optional[CodeInfo]:
        """Look up a code, auto-detecting system if not specified."""
        # Auto-detect system based on code format
        if system is None:
            if code[0].isalpha() and len(code) >= 3:
                system = "icd10"
            elif code.isdigit() and len(code) == 5:
                system = "cpt"
            elif code.isdigit() and len(code) > 5:
                system = "snomed"
        
        system = system.lower() if system else ""
        
        if system in ["icd10", "icd-10", "icd10cm"]:
            return self.icd10.lookup(code)
        elif system in ["cpt", "hcpcs"]:
            return self.cpt.lookup(code)
        elif system in ["snomed", "snomedct"]:
            return self.snomed.lookup(code)
        elif system in ["rxnorm", "ndc"]:
            return self.rxnorm.lookup(code)
        
        # Try all systems
        for lookup in [self.icd10, self.cpt, self.snomed, self.rxnorm]:
            result = lookup.lookup(code)
            if result:
                return result
        
        return None
    
    async def search(
        self,
        query: str,
        systems: List[str] = None,
        max_results: int = 10,
    ) -> Dict[str, CodeSearchResult]:
        """Search across terminology systems."""
        systems = systems or ["icd10", "snomed", "rxnorm"]
        results = {}
        
        tasks = []
        if "icd10" in systems:
            tasks.append(("icd10", self.icd10.search(query, max_results)))
        if "snomed" in systems:
            tasks.append(("snomed", self.snomed.search(query, max_results)))
        if "rxnorm" in systems:
            tasks.append(("rxnorm", self.rxnorm.search(query, max_results)))
        
        for system, task in tasks:
            try:
                results[system] = await task
            except Exception as e:
                logger.error(f"Search error for {system}: {e}")
                results[system] = CodeSearchResult(query=query, system=system)
        
        return results
    
    def validate(self, code: str, system: str) -> bool:
        """Validate a code format."""
        system = system.lower()
        
        if system in ["icd10", "icd-10"]:
            return self.icd10.validate(code)
        elif system in ["cpt"]:
            return self.cpt.validate(code)
        
        return True  # Default to valid for unknown systems
