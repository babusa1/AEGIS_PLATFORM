"""
AEGIS LLM Benchmarking

Healthcare-specific benchmarks for evaluating LLM performance:
- Clinical reasoning
- Medical coding
- Clinical summarization
- Medication safety
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine
from enum import Enum
import asyncio
import json
import time
import structlog

logger = structlog.get_logger(__name__)


class BenchmarkCategory(str, Enum):
    """Categories of healthcare benchmarks."""
    CLINICAL_REASONING = "clinical_reasoning"
    MEDICAL_CODING = "medical_coding"
    SUMMARIZATION = "summarization"
    MEDICATION_SAFETY = "medication_safety"
    PATIENT_COMMUNICATION = "patient_communication"
    GENERAL_QA = "general_qa"


@dataclass
class BenchmarkTask:
    """A single benchmark task."""
    id: str
    category: BenchmarkCategory
    prompt: str
    expected_output: str | None = None
    evaluation_criteria: list[str] = field(default_factory=list)
    difficulty: int = 5  # 1-10
    timeout_seconds: int = 60


@dataclass
class BenchmarkResult:
    """Result of running a benchmark task."""
    task_id: str
    model_id: str
    response: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    score: float | None = None  # 0-1
    evaluation_notes: str = ""
    error: str | None = None


@dataclass
class ModelBenchmarkSummary:
    """Summary of benchmark results for a model."""
    model_id: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    average_score: float
    average_latency_ms: float
    total_tokens: int
    by_category: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class BenchmarkComparison:
    """Comparison of multiple models on benchmarks."""
    benchmark_name: str
    run_at: datetime
    models: list[str]
    results: dict[str, ModelBenchmarkSummary]
    winner: str | None = None
    notes: str = ""


# Healthcare benchmark tasks
HEALTHCARE_BENCHMARKS: list[BenchmarkTask] = [
    # Clinical Reasoning
    BenchmarkTask(
        id="cr-001",
        category=BenchmarkCategory.CLINICAL_REASONING,
        prompt="""A 65-year-old male presents with sudden onset chest pain, shortness of breath, 
        and diaphoresis. His ECG shows ST elevation in leads II, III, and aVF. 
        What is the most likely diagnosis and what are the immediate management steps?""",
        expected_output="Inferior STEMI",
        evaluation_criteria=[
            "Correctly identifies inferior STEMI",
            "Mentions immediate aspirin",
            "Discusses antiplatelet therapy",
            "Mentions urgent cardiac catheterization or thrombolytics",
            "Addresses oxygen and pain management",
        ],
        difficulty=7,
    ),
    BenchmarkTask(
        id="cr-002",
        category=BenchmarkCategory.CLINICAL_REASONING,
        prompt="""A 45-year-old diabetic woman presents with fever, flank pain, and dysuria for 3 days. 
        Labs show WBC 18,000, creatinine 1.8 (baseline 0.9). Urinalysis shows pyuria and bacteriuria.
        What is the diagnosis and treatment plan?""",
        expected_output="Pyelonephritis with AKI",
        evaluation_criteria=[
            "Diagnoses pyelonephritis",
            "Recognizes acute kidney injury",
            "Recommends IV antibiotics",
            "Considers urine/blood cultures",
            "Addresses fluid management",
        ],
        difficulty=6,
    ),
    
    # Medical Coding
    BenchmarkTask(
        id="mc-001",
        category=BenchmarkCategory.MEDICAL_CODING,
        prompt="""Assign the appropriate ICD-10-CM code for: 
        Type 2 diabetes mellitus with diabetic chronic kidney disease, stage 3""",
        expected_output="E11.65, N18.3",
        evaluation_criteria=[
            "Includes E11.65 for diabetes with CKD",
            "Includes N18.3 for CKD stage 3",
            "Codes are in correct order",
        ],
        difficulty=5,
    ),
    BenchmarkTask(
        id="mc-002",
        category=BenchmarkCategory.MEDICAL_CODING,
        prompt="""Assign CPT codes for: Office visit for established patient, moderate complexity (30 minutes), 
        with EKG interpretation""",
        expected_output="99214, 93010",
        evaluation_criteria=[
            "Includes 99214 for E/M",
            "Includes 93010 or 93000 for EKG",
        ],
        difficulty=4,
    ),
    
    # Summarization
    BenchmarkTask(
        id="sum-001",
        category=BenchmarkCategory.SUMMARIZATION,
        prompt="""Summarize this clinical note in 2-3 sentences:
        
        Chief Complaint: Chest pain x 2 days
        HPI: 58 yo M with HTN, DM2, hyperlipidemia presents with substernal chest pain started 2 days ago.
        Pain is pressure-like, 6/10, radiates to left arm, worse with exertion, relieved with rest.
        No associated SOB, diaphoresis, or nausea. Denies recent illness. Takes metformin, lisinopril, atorvastatin.
        PE: BP 142/88, HR 82, SpO2 98%. Heart RRR, no murmurs. Lungs clear. No leg edema.
        EKG: Normal sinus rhythm, no ST changes.
        Plan: Troponins, stress test, continue current meds, lifestyle counseling.""",
        expected_output=None,
        evaluation_criteria=[
            "Captures chief complaint",
            "Mentions key risk factors",
            "Summarizes workup plan",
            "Is concise (2-3 sentences)",
        ],
        difficulty=4,
    ),
    
    # Medication Safety
    BenchmarkTask(
        id="med-001",
        category=BenchmarkCategory.MEDICATION_SAFETY,
        prompt="""Identify any drug interactions or safety concerns:
        Patient medications: warfarin 5mg daily, aspirin 81mg daily, ibuprofen 400mg TID, 
        lisinopril 10mg daily, metformin 500mg BID
        New prescription: fluconazole 200mg daily for 7 days""",
        expected_output="warfarin-fluconazole interaction, aspirin-ibuprofen-warfarin bleeding risk",
        evaluation_criteria=[
            "Identifies warfarin-fluconazole interaction",
            "Warns about increased INR/bleeding risk",
            "Notes aspirin + ibuprofen + warfarin bleeding risk",
            "Recommends INR monitoring",
        ],
        difficulty=6,
    ),
    BenchmarkTask(
        id="med-002",
        category=BenchmarkCategory.MEDICATION_SAFETY,
        prompt="""Check this prescription for errors:
        Patient: 8-year-old, 25 kg
        Prescription: Amoxicillin 500mg TID for otitis media""",
        expected_output="Dose may be appropriate, verify indication",
        evaluation_criteria=[
            "Calculates appropriate pediatric dose",
            "Considers weight-based dosing (25-50mg/kg/day)",
            "Notes that 500mg TID = 60mg/kg/day is at upper range",
            "Considers severity/indication",
        ],
        difficulty=5,
    ),
    
    # Patient Communication
    BenchmarkTask(
        id="pc-001",
        category=BenchmarkCategory.PATIENT_COMMUNICATION,
        prompt="""Write a patient-friendly explanation of:
        You have been diagnosed with atrial fibrillation. We are starting you on 
        apixaban to prevent blood clots and metoprolol to control your heart rate.""",
        expected_output=None,
        evaluation_criteria=[
            "Uses plain language",
            "Explains what afib is",
            "Explains why each medication is needed",
            "Mentions key safety points",
            "Is reassuring but informative",
        ],
        difficulty=4,
    ),
    
    # General QA
    BenchmarkTask(
        id="qa-001",
        category=BenchmarkCategory.GENERAL_QA,
        prompt="What are the ABCDE criteria for melanoma assessment?",
        expected_output="Asymmetry, Border, Color, Diameter, Evolution",
        evaluation_criteria=[
            "Lists all 5 criteria",
            "Defines each criterion correctly",
        ],
        difficulty=2,
    ),
]


class LLMBenchmark:
    """
    Runs healthcare benchmarks on LLM models.
    
    Features:
    - Standard healthcare benchmark suite
    - Custom benchmark tasks
    - Multi-model comparison
    - Detailed scoring and analysis
    """
    
    def __init__(
        self,
        model_executor: Callable[[str, str], Coroutine[Any, Any, dict]] | None = None,
    ):
        """
        Initialize the benchmark runner.
        
        Args:
            model_executor: Async function(model_id, prompt) -> {"response": str, "usage": dict}
        """
        self.model_executor = model_executor
        self._results: list[BenchmarkResult] = []
    
    async def run_benchmark(
        self,
        model_id: str,
        tasks: list[BenchmarkTask] | None = None,
        categories: list[BenchmarkCategory] | None = None,
    ) -> ModelBenchmarkSummary:
        """
        Run benchmarks on a model.
        
        Args:
            model_id: Model to benchmark
            tasks: Specific tasks (default: healthcare suite)
            categories: Filter to specific categories
        
        Returns:
            ModelBenchmarkSummary
        """
        tasks = tasks or HEALTHCARE_BENCHMARKS
        
        if categories:
            tasks = [t for t in tasks if t.category in categories]
        
        logger.info(
            "Starting benchmark",
            model=model_id,
            tasks=len(tasks),
        )
        
        results = []
        
        for task in tasks:
            try:
                result = await self._run_task(model_id, task)
                results.append(result)
                self._results.append(result)
            except Exception as e:
                logger.error(
                    "Benchmark task failed",
                    task_id=task.id,
                    error=str(e),
                )
                results.append(BenchmarkResult(
                    task_id=task.id,
                    model_id=model_id,
                    response="",
                    latency_ms=0,
                    input_tokens=0,
                    output_tokens=0,
                    error=str(e),
                ))
        
        # Calculate summary
        completed = [r for r in results if r.error is None]
        failed = [r for r in results if r.error is not None]
        
        avg_score = (
            sum(r.score or 0 for r in completed) / len(completed)
            if completed else 0
        )
        avg_latency = (
            sum(r.latency_ms for r in completed) / len(completed)
            if completed else 0
        )
        total_tokens = sum(r.input_tokens + r.output_tokens for r in results)
        
        # By category
        by_category = {}
        for cat in BenchmarkCategory:
            cat_results = [r for r in completed if self._get_task(r.task_id).category == cat]
            if cat_results:
                by_category[cat.value] = {
                    "count": len(cat_results),
                    "avg_score": sum(r.score or 0 for r in cat_results) / len(cat_results),
                    "avg_latency_ms": sum(r.latency_ms for r in cat_results) / len(cat_results),
                }
        
        summary = ModelBenchmarkSummary(
            model_id=model_id,
            total_tasks=len(tasks),
            completed_tasks=len(completed),
            failed_tasks=len(failed),
            average_score=avg_score,
            average_latency_ms=avg_latency,
            total_tokens=total_tokens,
            by_category=by_category,
        )
        
        logger.info(
            "Benchmark completed",
            model=model_id,
            avg_score=avg_score,
            avg_latency_ms=avg_latency,
        )
        
        return summary
    
    def _get_task(self, task_id: str) -> BenchmarkTask:
        """Get task by ID."""
        for task in HEALTHCARE_BENCHMARKS:
            if task.id == task_id:
                return task
        raise ValueError(f"Task not found: {task_id}")
    
    async def _run_task(
        self,
        model_id: str,
        task: BenchmarkTask,
    ) -> BenchmarkResult:
        """Run a single benchmark task."""
        start_time = time.time()
        
        # Execute model
        if self.model_executor:
            response_data = await asyncio.wait_for(
                self.model_executor(model_id, task.prompt),
                timeout=task.timeout_seconds,
            )
            response = response_data.get("response", "")
            usage = response_data.get("usage", {})
        else:
            # Mock execution
            response = f"[Mock response for {task.id}]"
            usage = {"input_tokens": 100, "output_tokens": 50}
        
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        # Score the response
        score, notes = self._score_response(task, response)
        
        return BenchmarkResult(
            task_id=task.id,
            model_id=model_id,
            response=response,
            latency_ms=latency_ms,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            score=score,
            evaluation_notes=notes,
        )
    
    def _score_response(
        self,
        task: BenchmarkTask,
        response: str,
    ) -> tuple[float, str]:
        """
        Score a response against criteria.
        
        Returns:
            Tuple of (score 0-1, evaluation notes)
        """
        if not task.evaluation_criteria:
            return 0.5, "No criteria defined"
        
        response_lower = response.lower()
        criteria_met = 0
        notes = []
        
        for criterion in task.evaluation_criteria:
            # Simple keyword matching (in production, use LLM-as-judge)
            criterion_lower = criterion.lower()
            key_terms = criterion_lower.split()[:3]  # First few words as key terms
            
            matches = sum(1 for term in key_terms if term in response_lower)
            if matches >= len(key_terms) // 2 + 1:
                criteria_met += 1
                notes.append(f"✓ {criterion}")
            else:
                notes.append(f"✗ {criterion}")
        
        score = criteria_met / len(task.evaluation_criteria)
        
        # Check expected output if provided
        if task.expected_output:
            expected_lower = task.expected_output.lower()
            if expected_lower in response_lower:
                score = min(1.0, score + 0.2)
                notes.append(f"✓ Contains expected: {task.expected_output}")
            else:
                notes.append(f"? Expected not found: {task.expected_output}")
        
        return score, "\n".join(notes)
    
    async def compare_models(
        self,
        models: list[str],
        tasks: list[BenchmarkTask] | None = None,
        categories: list[BenchmarkCategory] | None = None,
    ) -> BenchmarkComparison:
        """
        Compare multiple models on benchmarks.
        
        Args:
            models: List of model IDs to compare
            tasks: Specific tasks (default: healthcare suite)
            categories: Filter to specific categories
        
        Returns:
            BenchmarkComparison
        """
        results = {}
        
        for model_id in models:
            summary = await self.run_benchmark(model_id, tasks, categories)
            results[model_id] = summary
        
        # Determine winner
        winner = None
        best_score = 0
        for model_id, summary in results.items():
            if summary.average_score > best_score:
                best_score = summary.average_score
                winner = model_id
        
        return BenchmarkComparison(
            benchmark_name="Healthcare LLM Benchmark",
            run_at=datetime.now(timezone.utc),
            models=models,
            results=results,
            winner=winner,
            notes=f"Winner: {winner} with score {best_score:.2%}",
        )
    
    def get_healthcare_benchmark_suite(self) -> list[BenchmarkTask]:
        """Get the standard healthcare benchmark suite."""
        return HEALTHCARE_BENCHMARKS.copy()
    
    def add_custom_task(self, task: BenchmarkTask):
        """Add a custom benchmark task."""
        HEALTHCARE_BENCHMARKS.append(task)
    
    def get_results(
        self,
        model_id: str | None = None,
        category: BenchmarkCategory | None = None,
    ) -> list[BenchmarkResult]:
        """Get benchmark results, optionally filtered."""
        results = self._results
        
        if model_id:
            results = [r for r in results if r.model_id == model_id]
        
        if category:
            task_ids = {t.id for t in HEALTHCARE_BENCHMARKS if t.category == category}
            results = [r for r in results if r.task_id in task_ids]
        
        return results


# =============================================================================
# Global Instance
# =============================================================================

_benchmark: LLMBenchmark | None = None


def get_benchmark() -> LLMBenchmark:
    """Get the global benchmark instance."""
    global _benchmark
    if _benchmark is None:
        _benchmark = LLMBenchmark()
    return _benchmark
