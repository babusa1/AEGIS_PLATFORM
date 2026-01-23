# ADR-005: LLM Provider Strategy

## Status
Accepted

## Context
AEGIS agents require LLM capabilities for reasoning, appeal generation, and insights. We need a strategy that balances performance, cost, compliance, and flexibility.

## Decision
**Multi-provider LLM Gateway with AWS Bedrock as primary**

### Provider Hierarchy

| Priority | Provider | Use Case | Why |
|----------|----------|----------|-----|
| Primary | AWS Bedrock (Claude) | Production | HIPAA-eligible, enterprise SLA |
| Secondary | Google Gemini | Large context | 1M token window for medical records |
| Fallback | OpenAI GPT-4 | Backup | Best general reasoning |
| Development | Ollama (local) | Dev/test | No API costs, offline capable |
| Demo | Mock | Demos | Predictable responses |

### LLM Gateway Architecture

```python
class LLMGateway:
    """Unified interface to multiple LLM providers."""
    
    providers: dict[str, LLMProvider]
    default_provider: str
    fallback_chain: list[str]
    
    async def generate(
        self,
        prompt: str,
        provider: str | None = None,
        model: str | None = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate with automatic fallback.
        
        If primary fails, tries fallback chain.
        """
        providers_to_try = [provider or self.default_provider] + self.fallback_chain
        
        for p in providers_to_try:
            try:
                return await self.providers[p].generate(prompt, model, **kwargs)
            except LLMProviderError:
                continue
        
        raise AllProvidersFailedError()
```

### Provider Abstraction

```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse: ...

class BedrockProvider(LLMProvider):
    """AWS Bedrock - Claude models."""
    default_model = "anthropic.claude-3-sonnet-20240229-v1:0"

class GeminiProvider(LLMProvider):
    """Google Gemini - Large context."""
    default_model = "gemini-1.5-pro"

class OpenAIProvider(LLMProvider):
    """OpenAI - GPT models."""
    default_model = "gpt-4o"

class OllamaProvider(LLMProvider):
    """Local Ollama - Development."""
    default_model = "llama3"
```

### HIPAA Compliance

- **Bedrock**: BAA available, data stays in AWS
- **Gemini**: Use only for non-PHI tasks or with BAA
- **OpenAI**: Enterprise agreement with BAA for healthcare
- **Ollama**: Local processing, no data leaves environment

### Cost Optimization

```python
class CostAwareRouter:
    """Route to cheapest provider that can handle the task."""
    
    def select_provider(self, task: AgentTask) -> str:
        if task.requires_large_context:
            return "gemini"  # 1M tokens
        elif task.is_simple_extraction:
            return "ollama"  # Free, local
        elif task.is_production:
            return "bedrock"  # HIPAA compliant
        else:
            return "openai"  # Best quality
```

## Consequences
- Single interface for all agent code
- Automatic failover improves reliability
- Cost optimization through smart routing
- HIPAA compliance maintained through provider selection
- Easy to add new providers (Anthropic direct, Cohere, etc.)

## References
- [AWS Bedrock](https://aws.amazon.com/bedrock/)
- [Google Gemini](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)
- [OpenAI API](https://platform.openai.com/docs/api-reference)
