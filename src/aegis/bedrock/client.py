"""
LLM Client

Unified interface for LLM providers (Bedrock, Ollama, Mock).
Supports switching between providers via configuration.
"""

import json
from abc import ABC, abstractmethod
from typing import Any

import structlog

from aegis.config import get_settings

logger = structlog.get_logger(__name__)


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Generate a structured response matching the schema."""
        pass


class MockLLMClient(BaseLLMClient):
    """
    Mock LLM client for local development and testing.
    
    Returns predictable responses without calling any external API.
    """
    
    def __init__(self):
        logger.info("Initialized Mock LLM client")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate a mock response."""
        logger.debug("Mock LLM generate", prompt_length=len(prompt))
        
        # Return contextual mock responses based on prompt content
        prompt_lower = prompt.lower()
        
        if "denial" in prompt_lower or "appeal" in prompt_lower:
            return self._mock_denial_response()
        elif "patient" in prompt_lower and "summary" in prompt_lower:
            return self._mock_patient_summary()
        elif "insight" in prompt_lower or "pattern" in prompt_lower:
            return self._mock_insight_response()
        else:
            return self._mock_generic_response()
    
    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Generate a mock structured response."""
        logger.debug("Mock LLM generate_structured", prompt_length=len(prompt))
        
        # Return a response matching the schema structure
        return self._generate_mock_from_schema(schema)
    
    def _mock_denial_response(self) -> str:
        return """Based on my analysis of the clinical documentation, I recommend the following appeal strategy:

**Key Clinical Evidence:**
1. Patient presented with elevated heart rate (115 bpm) indicating hemodynamic instability
2. History of COPD with previous hospitalizations suggests high-risk status
3. Failed outpatient management prior to admission (documented in progress notes)
4. Oxygen saturation below 92% on room air requiring supplemental O2

**Recommended Appeal Points:**
1. Cite InterQual criteria for inpatient admission with documented vital sign abnormalities
2. Reference the patient's comorbidity burden (CHF + COPD) per CMS guidelines
3. Include the failed home oxygen trial documentation
4. Attach the attending physician's attestation regarding severity

**Payer Policy Reference:**
Per UnitedHealthcare Medical Policy Section 4.2, patients with tachycardia >100 bpm combined with respiratory distress meet medical necessity criteria for inpatient observation.

**Confidence Score:** 0.85

This appeal has a high likelihood of success based on similar cases in the historical database."""
    
    def _mock_patient_summary(self) -> str:
        return """**Patient 360° Summary**

**Demographics:** John Smith, 68yo Male, MRN: 123456

**Active Conditions:**
- Congestive Heart Failure (I50.9) - Primary
- COPD with acute exacerbation (J44.1)
- Type 2 Diabetes Mellitus (E11.9)
- Essential Hypertension (I10)

**Current Encounter:**
- Admitted: 01/15/2026 via ED
- Status: Inpatient, Day 5
- Attending: Dr. Sarah Jones, Cardiology
- Location: ICU Room 302B

**Recent Labs (Critical):**
- BNP: 1,245 pg/mL (elevated)
- Troponin: 0.04 ng/mL (normal)
- Creatinine: 1.8 mg/dL (elevated)

**Risk Scores:**
- 30-day Readmission Risk: 78% (HIGH)
- Mortality Risk: 12% (MODERATE)
- Fall Risk: HIGH

**Financial Summary:**
- Total Billed: $287,450
- Pending Claims: 2 ($52,000)
- Denied: 1 claim ($35,000 - Medical Necessity)

**Recommended Actions:**
1. 🔴 Appeal denial CLM-2026-00456 (deadline: 02/15)
2. 🔴 Schedule cardiology follow-up within 7 days of discharge
3. 🟡 Pharmacy reconciliation needed
4. 🟡 Social work consult for home care coordination"""
    
    def _mock_insight_response(self) -> str:
        return """**Insight Discovery Analysis**

**Finding:** Cardiology denial rate increased 42% in Q4 2025

**Root Cause Analysis:**
1. **Primary Driver (72% of increase):** New UnitedHealthcare LCD policy (L35018) effective 01/01/2026 changed medical necessity criteria for cardiac catheterization
2. **Secondary Driver (18%):** Documentation gaps - cardiologists not consistently documenting ejection fraction in admission notes
3. **Tertiary Driver (10%):** Increased volume from new referral patterns

**Pattern Details:**
- Denial Code: PR-204 (Not Medically Necessary)
- Affected Procedures: 93458, 93459 (Cardiac cath)
- Average Denial Amount: $8,500
- Total Q4 Impact: $1.2M in denied revenue

**Recommended Actions:**
1. Alert cardiology department to include EF% in all admission documentation
2. Update charge capture template to prompt for LCD criteria
3. Schedule payer meeting with UHC to clarify new policy interpretation
4. Create real-time documentation alert for missing EF values

**Projected Recovery:** $850K (if actions implemented within 30 days)"""
    
    def _mock_generic_response(self) -> str:
        return """I've analyzed the request and here is my response:

Based on the healthcare data context provided, I can offer the following insights:

1. The data shows patterns consistent with typical healthcare operational workflows
2. There are opportunities for optimization in the current process
3. I recommend reviewing the detailed metrics for actionable next steps

Please let me know if you need more specific analysis on any particular aspect."""
    
    def _generate_mock_from_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate mock data matching a JSON schema."""
        result = {}
        properties = schema.get("properties", {})
        
        for key, prop in properties.items():
            prop_type = prop.get("type", "string")
            if prop_type == "string":
                result[key] = f"mock_{key}_value"
            elif prop_type == "number" or prop_type == "integer":
                result[key] = 42
            elif prop_type == "boolean":
                result[key] = True
            elif prop_type == "array":
                result[key] = []
            elif prop_type == "object":
                result[key] = {}
        
        return result


class BedrockLLMClient(BaseLLMClient):
    """
    AWS Bedrock LLM client.
    
    Supports Claude and other models available on Bedrock.
    """
    
    def __init__(self):
        import boto3
        
        settings = get_settings().llm
        
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key.get_secret_value() 
                if settings.aws_secret_access_key else None,
        )
        self.model_id = settings.bedrock_model_id
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
        
        logger.info(
            "Initialized Bedrock LLM client",
            model_id=self.model_id,
            region=settings.aws_region,
        )
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate a response using Bedrock."""
        messages = [{"role": "user", "content": prompt}]
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature or self.temperature,
            "messages": messages,
        }
        
        if system_prompt:
            body["system"] = system_prompt
        
        logger.debug("Bedrock generate", model=self.model_id, prompt_length=len(prompt))
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
        )
        
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]
    
    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Generate a structured response using Bedrock."""
        # Add schema instructions to prompt
        structured_prompt = f"""{prompt}

Please respond with valid JSON matching this schema:
{json.dumps(schema, indent=2)}

Respond ONLY with the JSON, no other text."""
        
        system = system_prompt or "You are a helpful healthcare AI assistant. Always respond with valid JSON."
        
        response_text = await self.generate(
            structured_prompt,
            system_prompt=system,
        )
        
        # Parse JSON response
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Could not parse JSON from response: {response_text[:200]}")


class LLMClient:
    """
    Unified LLM client that delegates to the configured provider.
    
    Usage:
        client = LLMClient()
        response = await client.generate("What is the patient's status?")
    """
    
    def __init__(self):
        settings = get_settings().llm
        provider = settings.llm_provider
        
        if provider == "mock":
            self._client = MockLLMClient()
        elif provider == "bedrock":
            self._client = BedrockLLMClient()
        elif provider == "ollama":
            # TODO: Implement Ollama client
            raise NotImplementedError("Ollama client not yet implemented")
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
        
        self.provider = provider
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate a response from the configured LLM."""
        return await self._client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    
    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Generate a structured response from the configured LLM."""
        return await self._client.generate_structured(
            prompt=prompt,
            schema=schema,
            system_prompt=system_prompt,
        )


# Singleton instance
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get the singleton LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
