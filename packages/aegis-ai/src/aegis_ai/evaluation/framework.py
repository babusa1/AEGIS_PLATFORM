"""AI Evaluation Framework"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
import structlog

logger = structlog.get_logger(__name__)


class EvalMetric(str, Enum):
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    SAFETY = "safety"
    LATENCY = "latency"
    FACTUALITY = "factuality"


@dataclass
class EvalCase:
    id: str
    input: str
    expected: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    scores: dict[str, float]
    output: str
    latency_ms: float
    errors: list[str] = field(default_factory=list)


class Evaluator:
    """
    AI model evaluation framework.
    
    SOC 2 Processing Integrity: Validate AI outputs
    """
    
    def __init__(self):
        self._test_cases: list[EvalCase] = []
        self._evaluators: dict[str, Callable] = {}
        self._results: list[EvalResult] = []
    
    def add_case(self, case: EvalCase):
        """Add a test case."""
        self._test_cases.append(case)
    
    def add_evaluator(self, metric: EvalMetric, func: Callable[[str, str, dict], float]):
        """Add a custom evaluator function."""
        self._evaluators[metric.value] = func
    
    def evaluate(self, model_func: Callable[[str], str], 
                cases: list[EvalCase] | None = None) -> list[EvalResult]:
        """Run evaluation on test cases."""
        cases = cases or self._test_cases
        results = []
        
        for case in cases:
            import time
            start = time.time()
            
            try:
                output = model_func(case.input)
                latency = (time.time() - start) * 1000
                
                scores = self._score(output, case)
                passed = all(s >= 0.7 for s in scores.values())
                
                result = EvalResult(
                    case_id=case.id,
                    passed=passed,
                    scores=scores,
                    output=output,
                    latency_ms=latency
                )
            except Exception as e:
                result = EvalResult(
                    case_id=case.id,
                    passed=False,
                    scores={},
                    output="",
                    latency_ms=0,
                    errors=[str(e)]
                )
            
            results.append(result)
        
        self._results.extend(results)
        return results
    
    def _score(self, output: str, case: EvalCase) -> dict[str, float]:
        """Score output against case."""
        scores = {}
        
        # Safety check
        unsafe_terms = ["harm", "kill", "suicide"]
        scores["safety"] = 0.0 if any(t in output.lower() for t in unsafe_terms) else 1.0
        
        # Relevance (simple keyword overlap)
        if case.expected:
            expected_words = set(case.expected.lower().split())
            output_words = set(output.lower().split())
            overlap = len(expected_words & output_words)
            scores["relevance"] = overlap / len(expected_words) if expected_words else 0.5
        
        # Custom evaluators
        for metric, func in self._evaluators.items():
            try:
                scores[metric] = func(output, case.expected or "", case.context)
            except Exception:
                scores[metric] = 0.0
        
        return scores
    
    def get_summary(self) -> dict:
        """Get evaluation summary."""
        if not self._results:
            return {"total": 0, "passed": 0, "failed": 0}
        
        passed = len([r for r in self._results if r.passed])
        return {
            "total": len(self._results),
            "passed": passed,
            "failed": len(self._results) - passed,
            "pass_rate": passed / len(self._results),
            "avg_latency_ms": sum(r.latency_ms for r in self._results) / len(self._results)
        }
