"""
AEGIS RAG Evaluation Framework

Metrics for evaluating RAG pipeline quality:
- Retrieval metrics (precision, recall, MRR)
- Generation metrics (faithfulness, relevance)
- End-to-end evaluation
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RetrievalMetrics:
    """Metrics for retrieval quality."""
    precision_at_k: dict[int, float] = field(default_factory=dict)  # P@1, P@3, P@5, P@10
    recall_at_k: dict[int, float] = field(default_factory=dict)
    mrr: float = 0.0  # Mean Reciprocal Rank
    ndcg: float = 0.0  # Normalized Discounted Cumulative Gain
    hit_rate: float = 0.0


@dataclass
class GenerationMetrics:
    """Metrics for generation quality."""
    faithfulness: float = 0.0  # How well answer is supported by context
    relevance: float = 0.0  # How relevant answer is to question
    coherence: float = 0.0  # How well-structured the answer is
    completeness: float = 0.0  # How complete the answer is


@dataclass
class EvaluationResult:
    """Result of a RAG evaluation."""
    query: str
    retrieved_docs: list[str]
    generated_answer: str
    ground_truth: str | None = None
    retrieval_metrics: RetrievalMetrics | None = None
    generation_metrics: GenerationMetrics | None = None
    latency_ms: float = 0.0
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EvaluationDataset:
    """Dataset for RAG evaluation."""
    name: str
    queries: list[str]
    ground_truths: list[str]
    relevant_docs: list[list[str]]  # For each query, list of relevant doc IDs


@dataclass
class RAGASResult:
    """RAGAS-style evaluation result."""
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    overall_score: float


class RAGEvaluator:
    """
    Evaluates RAG pipeline quality.
    
    Features:
    - Retrieval quality metrics
    - Generation quality metrics
    - RAGAS-compatible evaluation
    - Custom evaluation datasets
    """
    
    def __init__(self, llm_judge=None):
        """
        Initialize evaluator.
        
        Args:
            llm_judge: Optional LLM for judging generation quality
        """
        self.llm_judge = llm_judge
        self._results: list[EvaluationResult] = []
    
    def evaluate_retrieval(
        self,
        retrieved_doc_ids: list[str],
        relevant_doc_ids: list[str],
        k_values: list[int] = [1, 3, 5, 10],
    ) -> RetrievalMetrics:
        """
        Evaluate retrieval quality.
        
        Args:
            retrieved_doc_ids: IDs of retrieved documents (ordered by relevance)
            relevant_doc_ids: IDs of actually relevant documents
            k_values: K values for P@K and R@K
        
        Returns:
            RetrievalMetrics
        """
        metrics = RetrievalMetrics()
        relevant_set = set(relevant_doc_ids)
        
        # Precision@K and Recall@K
        for k in k_values:
            top_k = retrieved_doc_ids[:k]
            relevant_in_k = len(set(top_k) & relevant_set)
            
            metrics.precision_at_k[k] = relevant_in_k / k if k > 0 else 0
            metrics.recall_at_k[k] = relevant_in_k / len(relevant_set) if relevant_set else 0
        
        # Mean Reciprocal Rank
        for i, doc_id in enumerate(retrieved_doc_ids):
            if doc_id in relevant_set:
                metrics.mrr = 1.0 / (i + 1)
                break
        
        # Hit Rate (any relevant doc in top-k)
        max_k = max(k_values)
        metrics.hit_rate = 1.0 if set(retrieved_doc_ids[:max_k]) & relevant_set else 0.0
        
        # NDCG
        dcg = 0.0
        idcg = 0.0
        for i, doc_id in enumerate(retrieved_doc_ids[:max_k]):
            rel = 1 if doc_id in relevant_set else 0
            dcg += rel / (i + 2)  # log2(i+2)
        
        for i in range(min(len(relevant_set), max_k)):
            idcg += 1 / (i + 2)
        
        metrics.ndcg = dcg / idcg if idcg > 0 else 0
        
        return metrics
    
    async def evaluate_generation(
        self,
        query: str,
        context: str,
        answer: str,
        ground_truth: str | None = None,
    ) -> GenerationMetrics:
        """
        Evaluate generation quality.
        
        Args:
            query: Original query
            context: Retrieved context
            answer: Generated answer
            ground_truth: Optional ground truth answer
        
        Returns:
            GenerationMetrics
        """
        metrics = GenerationMetrics()
        
        if self.llm_judge:
            # Use LLM as judge
            metrics = await self._llm_evaluate(query, context, answer, ground_truth)
        else:
            # Simple heuristic evaluation
            metrics = self._heuristic_evaluate(query, context, answer, ground_truth)
        
        return metrics
    
    def _heuristic_evaluate(
        self,
        query: str,
        context: str,
        answer: str,
        ground_truth: str | None,
    ) -> GenerationMetrics:
        """Simple heuristic-based evaluation."""
        metrics = GenerationMetrics()
        
        # Faithfulness: check if answer terms appear in context
        answer_words = set(answer.lower().split())
        context_words = set(context.lower().split())
        overlap = len(answer_words & context_words)
        metrics.faithfulness = min(1.0, overlap / len(answer_words)) if answer_words else 0
        
        # Relevance: check if query terms appear in answer
        query_words = set(query.lower().split())
        query_overlap = len(query_words & answer_words)
        metrics.relevance = min(1.0, query_overlap / len(query_words)) if query_words else 0
        
        # Coherence: based on length and structure
        sentences = answer.split(". ")
        metrics.coherence = min(1.0, 0.5 + len(sentences) * 0.1)
        
        # Completeness: compare with ground truth if available
        if ground_truth:
            gt_words = set(ground_truth.lower().split())
            gt_overlap = len(gt_words & answer_words)
            metrics.completeness = gt_overlap / len(gt_words) if gt_words else 0
        else:
            metrics.completeness = 0.5  # Default
        
        return metrics
    
    async def _llm_evaluate(
        self,
        query: str,
        context: str,
        answer: str,
        ground_truth: str | None,
    ) -> GenerationMetrics:
        """LLM-based evaluation."""
        # Use LLM judge for more accurate evaluation
        prompt = f"""Evaluate the following RAG response on a scale of 0-1 for each criterion:

Query: {query}

Context: {context[:1000]}...

Answer: {answer}

{f"Ground Truth: {ground_truth}" if ground_truth else ""}

Rate each criterion (0-1):
1. Faithfulness: Is the answer supported by the context?
2. Relevance: Does the answer address the query?
3. Coherence: Is the answer well-structured?
4. Completeness: Is the answer complete?

Return JSON: {{"faithfulness": X, "relevance": X, "coherence": X, "completeness": X}}"""

        try:
            response = await self.llm_judge(prompt)
            import json
            scores = json.loads(response)
            return GenerationMetrics(
                faithfulness=scores.get("faithfulness", 0),
                relevance=scores.get("relevance", 0),
                coherence=scores.get("coherence", 0),
                completeness=scores.get("completeness", 0),
            )
        except Exception:
            return self._heuristic_evaluate(query, context, answer, ground_truth)
    
    async def run_ragas(
        self,
        queries: list[str],
        contexts: list[list[str]],
        answers: list[str],
        ground_truths: list[str] | None = None,
    ) -> RAGASResult:
        """
        Run RAGAS-style evaluation.
        
        Args:
            queries: List of queries
            contexts: List of context lists for each query
            answers: List of generated answers
            ground_truths: Optional list of ground truth answers
        
        Returns:
            RAGASResult
        """
        faithfulness_scores = []
        relevancy_scores = []
        precision_scores = []
        recall_scores = []
        
        for i, (query, context_list, answer) in enumerate(zip(queries, contexts, answers)):
            context = "\n".join(context_list)
            gt = ground_truths[i] if ground_truths else None
            
            metrics = await self.evaluate_generation(query, context, answer, gt)
            faithfulness_scores.append(metrics.faithfulness)
            relevancy_scores.append(metrics.relevance)
            
            # Context precision/recall based on ground truth overlap
            if gt:
                gt_words = set(gt.lower().split())
                context_words = set(context.lower().split())
                overlap = len(gt_words & context_words)
                precision_scores.append(overlap / len(context_words) if context_words else 0)
                recall_scores.append(overlap / len(gt_words) if gt_words else 0)
        
        result = RAGASResult(
            faithfulness=sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else 0,
            answer_relevancy=sum(relevancy_scores) / len(relevancy_scores) if relevancy_scores else 0,
            context_precision=sum(precision_scores) / len(precision_scores) if precision_scores else 0,
            context_recall=sum(recall_scores) / len(recall_scores) if recall_scores else 0,
            overall_score=0,
        )
        
        result.overall_score = (
            result.faithfulness + result.answer_relevancy +
            result.context_precision + result.context_recall
        ) / 4
        
        return result
    
    def create_evaluation_dataset(
        self,
        name: str,
        qa_pairs: list[dict[str, Any]],
    ) -> EvaluationDataset:
        """
        Create an evaluation dataset.
        
        Args:
            name: Dataset name
            qa_pairs: List of {"query": str, "answer": str, "relevant_docs": [str]}
        
        Returns:
            EvaluationDataset
        """
        return EvaluationDataset(
            name=name,
            queries=[p["query"] for p in qa_pairs],
            ground_truths=[p["answer"] for p in qa_pairs],
            relevant_docs=[p.get("relevant_docs", []) for p in qa_pairs],
        )
    
    def get_aggregate_metrics(self) -> dict[str, float]:
        """Get aggregate metrics from all evaluations."""
        if not self._results:
            return {}
        
        avg_retrieval = {
            "precision_at_1": 0, "precision_at_5": 0,
            "recall_at_5": 0, "mrr": 0, "hit_rate": 0,
        }
        avg_generation = {
            "faithfulness": 0, "relevance": 0, "coherence": 0, "completeness": 0,
        }
        
        for result in self._results:
            if result.retrieval_metrics:
                avg_retrieval["precision_at_1"] += result.retrieval_metrics.precision_at_k.get(1, 0)
                avg_retrieval["precision_at_5"] += result.retrieval_metrics.precision_at_k.get(5, 0)
                avg_retrieval["recall_at_5"] += result.retrieval_metrics.recall_at_k.get(5, 0)
                avg_retrieval["mrr"] += result.retrieval_metrics.mrr
                avg_retrieval["hit_rate"] += result.retrieval_metrics.hit_rate
            
            if result.generation_metrics:
                avg_generation["faithfulness"] += result.generation_metrics.faithfulness
                avg_generation["relevance"] += result.generation_metrics.relevance
                avg_generation["coherence"] += result.generation_metrics.coherence
                avg_generation["completeness"] += result.generation_metrics.completeness
        
        n = len(self._results)
        return {
            **{k: v / n for k, v in avg_retrieval.items()},
            **{k: v / n for k, v in avg_generation.items()},
            "total_evaluations": n,
        }


def get_evaluator(llm_judge=None) -> RAGEvaluator:
    """Get a RAG evaluator instance."""
    return RAGEvaluator(llm_judge=llm_judge)
