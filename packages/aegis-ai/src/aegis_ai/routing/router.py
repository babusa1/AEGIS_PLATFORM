"""Model Router - Route to appropriate AI model"""
from dataclasses import dataclass
from enum import Enum
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class TaskType(str, Enum):
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    REASONING = "reasoning"
    CONVERSATION = "conversation"
    CODE = "code"


class ModelTier(str, Enum):
    FAST = "fast"  # Small, fast models
    BALANCED = "balanced"  # Medium models
    POWERFUL = "powerful"  # Large, capable models


@dataclass
class ModelConfig:
    name: str
    tier: ModelTier
    tasks: list[TaskType]
    max_tokens: int
    cost_per_1k: float


class ModelRouter:
    """
    Route requests to appropriate AI model.
    
    Optimizes for cost, latency, and capability.
    """
    
    MODELS = {
        "claude-3-haiku": ModelConfig("claude-3-haiku", ModelTier.FAST, 
            [TaskType.CLASSIFICATION, TaskType.EXTRACTION], 4096, 0.25),
        "claude-3-sonnet": ModelConfig("claude-3-sonnet", ModelTier.BALANCED,
            [TaskType.SUMMARIZATION, TaskType.CONVERSATION, TaskType.EXTRACTION], 8192, 3.0),
        "claude-3-opus": ModelConfig("claude-3-opus", ModelTier.POWERFUL,
            [TaskType.REASONING, TaskType.CODE, TaskType.CONVERSATION], 8192, 15.0),
    }
    
    TASK_PREFERENCES = {
        TaskType.CLASSIFICATION: ["claude-3-haiku", "claude-3-sonnet"],
        TaskType.EXTRACTION: ["claude-3-haiku", "claude-3-sonnet"],
        TaskType.SUMMARIZATION: ["claude-3-sonnet", "claude-3-opus"],
        TaskType.REASONING: ["claude-3-opus", "claude-3-sonnet"],
        TaskType.CONVERSATION: ["claude-3-sonnet", "claude-3-opus"],
        TaskType.CODE: ["claude-3-opus"],
    }
    
    def __init__(self, default_model: str = "claude-3-sonnet"):
        self.default_model = default_model
    
    def route(self, task_type: TaskType, input_length: int = 0,
             require_tier: ModelTier | None = None) -> str:
        """Route to appropriate model for task."""
        # Get preferred models for task
        candidates = self.TASK_PREFERENCES.get(task_type, [self.default_model])
        
        # Filter by tier if required
        if require_tier:
            candidates = [c for c in candidates 
                         if self.MODELS[c].tier == require_tier]
        
        if not candidates:
            return self.default_model
        
        # For long inputs, prefer models with higher token limits
        if input_length > 4000:
            candidates = [c for c in candidates 
                         if self.MODELS[c].max_tokens >= input_length]
        
        # Return first (preferred) candidate
        model = candidates[0] if candidates else self.default_model
        
        logger.debug("Model routed", task=task_type.value, model=model)
        return model
    
    def get_model_config(self, model_name: str) -> ModelConfig | None:
        return self.MODELS.get(model_name)
    
    def estimate_cost(self, model_name: str, tokens: int) -> float:
        config = self.MODELS.get(model_name)
        if config:
            return (tokens / 1000) * config.cost_per_1k
        return 0.0
