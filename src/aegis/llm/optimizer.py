"""
AEGIS LLM Cost Optimizer

Intelligent model selection and cost optimization.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class TaskComplexity(str, Enum):
    """Complexity levels for LLM tasks."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    EXPERT = "expert"


@dataclass
class ModelCost:
    """Cost information for a model."""
    model_id: str
    provider: str
    input_cost_per_1k: float
    output_cost_per_1k: float
    max_context: int
    complexity_rating: int = 5


@dataclass
class CostEstimate:
    """Estimated cost for a request."""
    model_id: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost: float


@dataclass
class UsageRecord:
    """Record of LLM usage."""
    id: str
    timestamp: datetime
    model_id: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost: float
    task_type: str | None = None
    tenant_id: str = "default"


@dataclass
class CostReport:
    """Cost report for a time period."""
    start_date: datetime
    end_date: datetime
    total_cost: float
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    by_model: dict[str, float] = field(default_factory=dict)
    by_provider: dict[str, float] = field(default_factory=dict)


MODEL_COSTS = {
    "gpt-4o": ModelCost("gpt-4o", "openai", 0.005, 0.015, 128000, 9),
    "gpt-4o-mini": ModelCost("gpt-4o-mini", "openai", 0.00015, 0.0006, 128000, 7),
    "claude-3-5-sonnet-20241022": ModelCost("claude-3-5-sonnet-20241022", "anthropic", 0.003, 0.015, 200000, 9),
    "claude-3-haiku-20240307": ModelCost("claude-3-haiku-20240307", "anthropic", 0.00025, 0.00125, 200000, 6),
    "gemini-1.5-pro": ModelCost("gemini-1.5-pro", "vertex_ai", 0.00125, 0.005, 1000000, 9),
    "gemini-1.5-flash": ModelCost("gemini-1.5-flash", "vertex_ai", 0.000075, 0.0003, 1000000, 7),
    "llama3": ModelCost("llama3", "ollama", 0.0, 0.0, 8000, 6),
}

COMPLEXITY_INDICATORS = {
    TaskComplexity.SIMPLE: ["extract", "format", "list", "convert"],
    TaskComplexity.MEDIUM: ["summarize", "explain", "describe", "compare"],
    TaskComplexity.COMPLEX: ["analyze", "reason", "evaluate", "diagnose"],
    TaskComplexity.EXPERT: ["clinical decision", "differential diagnosis", "treatment plan"],
}


class LLMOptimizer:
    """Optimizes LLM model selection and tracks costs."""
    
    def __init__(self, budget_limit_daily: float | None = None, prefer_local: bool = False):
        self.budget_limit_daily = budget_limit_daily
        self.prefer_local = prefer_local
        self._usage_records: list[UsageRecord] = []
        self._today_cost = 0.0
        self._today_date = datetime.now(timezone.utc).date()
    
    def analyze_complexity(self, prompt: str) -> TaskComplexity:
        """Analyze task complexity from prompt."""
        prompt_lower = prompt.lower()
        scores = {level: 0 for level in TaskComplexity}
        
        for level, indicators in COMPLEXITY_INDICATORS.items():
            for indicator in indicators:
                if indicator in prompt_lower:
                    scores[level] += 1
        
        word_count = len(prompt.split())
        if word_count > 500:
            scores[TaskComplexity.COMPLEX] += 2
        
        max_score = max(scores.values())
        if max_score == 0:
            return TaskComplexity.MEDIUM
        
        for level in [TaskComplexity.EXPERT, TaskComplexity.COMPLEX, TaskComplexity.MEDIUM, TaskComplexity.SIMPLE]:
            if scores[level] == max_score:
                return level
        return TaskComplexity.MEDIUM
    
    def select_model(
        self,
        complexity: TaskComplexity,
        max_budget: float | None = None,
        provider: str | None = None,
    ) -> str:
        """Select optimal model for a task."""
        min_rating = {
            TaskComplexity.SIMPLE: 3,
            TaskComplexity.MEDIUM: 5,
            TaskComplexity.COMPLEX: 7,
            TaskComplexity.EXPERT: 9,
        }[complexity]
        
        candidates = [(m, c) for m, c in MODEL_COSTS.items() if c.complexity_rating >= min_rating]
        
        if provider:
            candidates = [(m, c) for m, c in candidates if c.provider == provider]
        
        if self.prefer_local:
            local = [(m, c) for m, c in candidates if c.provider == "ollama"]
            if local:
                candidates = local
        
        if not candidates:
            return "gpt-4o-mini"
        
        candidates.sort(key=lambda x: x[1].input_cost_per_1k + x[1].output_cost_per_1k)
        return candidates[0][0]
    
    def estimate_cost(self, model_id: str, prompt: str, output_tokens: int = 500) -> CostEstimate:
        """Estimate request cost."""
        cost_info = MODEL_COSTS.get(model_id)
        if not cost_info:
            return CostEstimate(model_id, 0, 0, 0.0)
        
        input_tokens = len(prompt) // 4
        est_cost = (input_tokens / 1000) * cost_info.input_cost_per_1k + (output_tokens / 1000) * cost_info.output_cost_per_1k
        
        return CostEstimate(model_id, input_tokens, output_tokens, est_cost)
    
    def record_usage(self, model_id: str, input_tokens: int, output_tokens: int, task_type: str | None = None, tenant_id: str = "default") -> UsageRecord:
        """Record LLM usage."""
        import uuid
        cost_info = MODEL_COSTS.get(model_id)
        cost = 0.0
        if cost_info:
            cost = (input_tokens / 1000) * cost_info.input_cost_per_1k + (output_tokens / 1000) * cost_info.output_cost_per_1k
        
        record = UsageRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            model_id=model_id,
            provider=cost_info.provider if cost_info else "unknown",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            task_type=task_type,
            tenant_id=tenant_id,
        )
        self._usage_records.append(record)
        
        today = datetime.now(timezone.utc).date()
        if today != self._today_date:
            self._today_cost = 0.0
            self._today_date = today
        self._today_cost += cost
        
        return record
    
    def get_cost_report(self, start_date: datetime | None = None, end_date: datetime | None = None) -> CostReport:
        """Generate cost report."""
        end_date = end_date or datetime.now(timezone.utc)
        start_date = start_date or (end_date - timedelta(days=30))
        
        records = [r for r in self._usage_records if start_date <= r.timestamp <= end_date]
        
        by_model = {}
        by_provider = {}
        total_cost = 0.0
        total_input = 0
        total_output = 0
        
        for r in records:
            total_cost += r.cost
            total_input += r.input_tokens
            total_output += r.output_tokens
            by_model[r.model_id] = by_model.get(r.model_id, 0) + r.cost
            by_provider[r.provider] = by_provider.get(r.provider, 0) + r.cost
        
        return CostReport(start_date, end_date, total_cost, len(records), total_input, total_output, by_model, by_provider)
    
    def get_today_cost(self) -> float:
        """Get today's total cost."""
        return self._today_cost
    
    def is_within_budget(self, estimated_cost: float = 0.0) -> bool:
        """Check if request would stay within budget."""
        if not self.budget_limit_daily:
            return True
        return (self._today_cost + estimated_cost) <= self.budget_limit_daily


_optimizer: LLMOptimizer | None = None


def get_optimizer(budget_limit_daily: float | None = None) -> LLMOptimizer:
    """Get the global optimizer instance."""
    global _optimizer
    if _optimizer is None:
        _optimizer = LLMOptimizer(budget_limit_daily=budget_limit_daily)
    return _optimizer
