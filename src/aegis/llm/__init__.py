"""
VeritOS LLM Module

Multi-provider LLM support:
- AWS Bedrock (Claude, Llama, Titan)
- OpenAI (GPT-4, GPT-3.5)
- Azure OpenAI
- Anthropic (Claude direct)
- Ollama (local models)
- Google Vertex AI (Gemini)

Plus:
- Cost optimization and model selection
- Benchmarking for healthcare tasks
"""

from aegis.llm.providers import (
    LLMProvider,
    LLMConfig,
    LLMResponse,
    Message,
    Role,
)
from aegis.llm.registry import LLMRegistry, get_llm_registry
from aegis.llm.bedrock import BedrockProvider
from aegis.llm.openai import OpenAIProvider
from aegis.llm.anthropic import AnthropicProvider
from aegis.llm.ollama import OllamaProvider
from aegis.llm.vertex import (
    VertexAIProvider,
    VertexAIConfig,
    VertexAIResponse,
    MockVertexAIProvider,
    get_vertex_provider,
)
from aegis.llm.optimizer import (
    LLMOptimizer,
    TaskComplexity,
    ModelCost,
    CostEstimate,
    UsageRecord,
    CostReport,
    get_optimizer,
)
from aegis.llm.benchmark import (
    LLMBenchmark,
    BenchmarkTask,
    BenchmarkResult,
    BenchmarkCategory,
    ModelBenchmarkSummary,
    BenchmarkComparison,
    get_benchmark,
    HEALTHCARE_BENCHMARKS,
)

__all__ = [
    # Core providers
    "LLMProvider",
    "LLMConfig",
    "LLMResponse",
    "Message",
    "Role",
    "LLMRegistry",
    "get_llm_registry",
    "BedrockProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    # Vertex AI
    "VertexAIProvider",
    "VertexAIConfig",
    "VertexAIResponse",
    "MockVertexAIProvider",
    "get_vertex_provider",
    # Optimizer
    "LLMOptimizer",
    "TaskComplexity",
    "ModelCost",
    "CostEstimate",
    "UsageRecord",
    "CostReport",
    "get_optimizer",
    # Benchmark
    "LLMBenchmark",
    "BenchmarkTask",
    "BenchmarkResult",
    "BenchmarkCategory",
    "ModelBenchmarkSummary",
    "BenchmarkComparison",
    "get_benchmark",
    "HEALTHCARE_BENCHMARKS",
]
