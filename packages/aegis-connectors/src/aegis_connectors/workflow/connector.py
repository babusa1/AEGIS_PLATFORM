"""Workflow/Task Connector"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult

logger = structlog.get_logger(__name__)

class TaskStatus(str, Enum):
    REQUESTED = "requested"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on-hold"

class TaskPriority(str, Enum):
    ROUTINE = "routine"
    URGENT = "urgent"
    ASAP = "asap"
    STAT = "stat"

class TaskCategory(str, Enum):
    CARE_GAP = "care-gap"
    FOLLOW_UP = "follow-up"
    REFERRAL = "referral"
    LAB_ORDER = "lab-order"
    MEDICATION = "medication"
    DOCUMENTATION = "documentation"
    ALERT = "alert"

@dataclass
class Task:
    task_id: str
    patient_id: str
    category: TaskCategory
    status: TaskStatus
    priority: TaskPriority
    description: str
    owner_id: str | None = None
    requester_id: str | None = None
    due_date: datetime | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str | None = None

class WorkflowConnector(BaseConnector):
    def __init__(self, tenant_id: str, source_system: str = "workflow"):
        super().__init__(tenant_id, source_system)
    
    @property
    def connector_type(self) -> str:
        return "workflow"
    
    async def parse(self, data: Any) -> ConnectorResult:
        if not isinstance(data, dict):
            return ConnectorResult(success=False, errors=["Data must be dict"])
        try:
            task = self._parse_task(data)
            if not task:
                return ConnectorResult(success=False, errors=["Failed to parse"])
            vertices, edges = self._transform(task)
            return ConnectorResult(success=True, vertices=vertices, edges=edges,
                metadata={"task_id": task.task_id, "status": task.status.value})
        except Exception as e:
            return ConnectorResult(success=False, errors=[str(e)])
    
    async def validate(self, data: Any) -> list[str]:
        errors = []
        if not isinstance(data, dict):
            errors.append("Data must be dict")
        elif not data.get("patient_id"):
            errors.append("Missing patient_id")
        return errors
    
    def _parse_task(self, data: dict) -> Task | None:
        try:
            status = TaskStatus(data.get("status", "requested"))
            priority = TaskPriority(data.get("priority", "routine"))
            category = TaskCategory(data.get("category", "follow-up"))
            due = data.get("due_date")
            if isinstance(due, str):
                due = datetime.fromisoformat(due.replace("Z", "+00:00"))
            created = data.get("created_at")
            if isinstance(created, str):
                created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            return Task(data.get("task_id", data.get("id", "")), data.get("patient_id", ""),
                category, status, priority, data.get("description", ""), data.get("owner_id"),
                data.get("requester_id"), due, created, None, data.get("notes"))
        except Exception as e:
            logger.error("Task parse failed", error=str(e))
            return None
    
    def _transform(self, task: Task):
        vertices, edges = [], []
        task_id = f"Task/{task.task_id}"
        vertices.append(self._create_vertex("Task", task_id, {
            "task_id": task.task_id, "category": task.category.value, "status": task.status.value,
            "priority": task.priority.value, "description": task.description,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "notes": task.notes}))
        edges.append(self._create_edge("HAS_TASK", "Patient", f"Patient/{task.patient_id}",
            "Task", task_id))
        if task.owner_id:
            edges.append(self._create_edge("ASSIGNED_TO", "Task", task_id,
                "Practitioner", f"Practitioner/{task.owner_id}"))
        return vertices, edges

SAMPLE_TASK = {"task_id": "TASK-001", "patient_id": "PAT12345", "category": "care-gap",
    "status": "requested", "priority": "urgent", "description": "Schedule HbA1c test - overdue",
    "owner_id": "NURSE-001", "due_date": "2024-01-25", "notes": "Last A1c was 8.5% in October"}
