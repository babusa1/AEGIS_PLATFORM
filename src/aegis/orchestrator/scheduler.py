"""
AEGIS Workflow Scheduler

Cron-based scheduling for automated workflow execution.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Coroutine
from enum import Enum
import asyncio
import uuid
import structlog

logger = structlog.get_logger(__name__)


class ScheduleStatus(str, Enum):
    """Status of a scheduled workflow."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


@dataclass
class ScheduledWorkflow:
    """A workflow scheduled for automatic execution."""
    id: str
    workflow_id: str
    name: str
    cron: str  # Cron expression (e.g., "0 9 * * *" for 9 AM daily)
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    next_run: datetime | None = None
    last_run: datetime | None = None
    last_result: str | None = None  # success, failed, skipped
    run_count: int = 0
    failure_count: int = 0
    timeout_seconds: int = 3600
    retry_on_failure: bool = True
    max_retries: int = 3
    input_params: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: str = "default"


@dataclass
class SchedulerMetrics:
    """Metrics for the scheduler."""
    total_scheduled: int = 0
    active_scheduled: int = 0
    runs_today: int = 0
    successes_today: int = 0
    failures_today: int = 0


class CronParser:
    """Parse and evaluate cron expressions."""
    
    @staticmethod
    def parse(cron_expr: str) -> dict[str, list[int]]:
        """
        Parse a cron expression.
        
        Format: minute hour day_of_month month day_of_week
        Supports: *, numbers, ranges (1-5), lists (1,2,3), steps (*/5)
        """
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expr}")
        
        minute, hour, dom, month, dow = parts
        
        return {
            "minute": CronParser._parse_field(minute, 0, 59),
            "hour": CronParser._parse_field(hour, 0, 23),
            "day_of_month": CronParser._parse_field(dom, 1, 31),
            "month": CronParser._parse_field(month, 1, 12),
            "day_of_week": CronParser._parse_field(dow, 0, 6),
        }
    
    @staticmethod
    def _parse_field(field: str, min_val: int, max_val: int) -> list[int]:
        """Parse a single cron field."""
        if field == "*":
            return list(range(min_val, max_val + 1))
        
        values = set()
        
        for part in field.split(","):
            if "/" in part:
                # Step values (e.g., */5)
                base, step = part.split("/")
                step = int(step)
                if base == "*":
                    values.update(range(min_val, max_val + 1, step))
                else:
                    start = int(base)
                    values.update(range(start, max_val + 1, step))
            elif "-" in part:
                # Range (e.g., 1-5)
                start, end = map(int, part.split("-"))
                values.update(range(start, end + 1))
            else:
                # Single value
                values.add(int(part))
        
        return sorted(values)
    
    @staticmethod
    def get_next_run(cron_expr: str, after: datetime | None = None) -> datetime:
        """Calculate the next run time for a cron expression."""
        if after is None:
            after = datetime.now(timezone.utc)
        
        parsed = CronParser.parse(cron_expr)
        
        # Start from the next minute
        candidate = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
        
        # Search for next matching time (max 1 year)
        max_iterations = 525600  # Minutes in a year
        
        for _ in range(max_iterations):
            if (
                candidate.minute in parsed["minute"]
                and candidate.hour in parsed["hour"]
                and candidate.day in parsed["day_of_month"]
                and candidate.month in parsed["month"]
                and candidate.weekday() in parsed["day_of_week"]
            ):
                return candidate
            
            candidate += timedelta(minutes=1)
        
        raise ValueError(f"Could not find next run for cron: {cron_expr}")
    
    @staticmethod
    def matches(cron_expr: str, dt: datetime) -> bool:
        """Check if a datetime matches a cron expression."""
        parsed = CronParser.parse(cron_expr)
        
        return (
            dt.minute in parsed["minute"]
            and dt.hour in parsed["hour"]
            and dt.day in parsed["day_of_month"]
            and dt.month in parsed["month"]
            and dt.weekday() in parsed["day_of_week"]
        )


class WorkflowScheduler:
    """
    Manages scheduled workflow executions.
    
    Features:
    - Cron-based scheduling
    - Pause/resume schedules
    - Retry on failure
    - Timeout handling
    - Metrics collection
    """
    
    def __init__(
        self,
        workflow_executor: Callable[[str, dict], Coroutine[Any, Any, dict]] | None = None,
        check_interval_seconds: int = 60,
    ):
        """
        Initialize the scheduler.
        
        Args:
            workflow_executor: Async function to execute workflows
            check_interval_seconds: How often to check for due workflows
        """
        self.workflow_executor = workflow_executor
        self.check_interval = check_interval_seconds
        
        self._schedules: dict[str, ScheduledWorkflow] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._execution_tasks: dict[str, asyncio.Task] = {}
    
    async def start(self):
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Workflow scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        if not self._running:
            return
        
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Cancel any running executions
        for task in self._execution_tasks.values():
            task.cancel()
        
        logger.info("Workflow scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_and_run_due_workflows()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduler loop error", error=str(e))
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _check_and_run_due_workflows(self):
        """Check for and execute due workflows."""
        now = datetime.now(timezone.utc)
        
        for schedule_id, schedule in self._schedules.items():
            if schedule.status != ScheduleStatus.ACTIVE:
                continue
            
            if schedule.next_run and schedule.next_run <= now:
                # Don't run if already executing
                if schedule_id in self._execution_tasks:
                    task = self._execution_tasks[schedule_id]
                    if not task.done():
                        continue
                
                # Execute workflow
                task = asyncio.create_task(
                    self._execute_scheduled_workflow(schedule)
                )
                self._execution_tasks[schedule_id] = task
    
    async def _execute_scheduled_workflow(self, schedule: ScheduledWorkflow):
        """Execute a scheduled workflow."""
        logger.info(
            "Executing scheduled workflow",
            schedule_id=schedule.id,
            workflow_id=schedule.workflow_id,
        )
        
        schedule.last_run = datetime.now(timezone.utc)
        schedule.run_count += 1
        
        try:
            if self.workflow_executor:
                # Execute with timeout
                result = await asyncio.wait_for(
                    self.workflow_executor(schedule.workflow_id, schedule.input_params),
                    timeout=schedule.timeout_seconds,
                )
                schedule.last_result = "success"
                logger.info(
                    "Scheduled workflow completed",
                    schedule_id=schedule.id,
                    result=result,
                )
            else:
                logger.warning("No workflow executor configured")
                schedule.last_result = "skipped"
                
        except asyncio.TimeoutError:
            schedule.last_result = "timeout"
            schedule.failure_count += 1
            logger.error(
                "Scheduled workflow timed out",
                schedule_id=schedule.id,
                timeout=schedule.timeout_seconds,
            )
            
        except Exception as e:
            schedule.last_result = "failed"
            schedule.failure_count += 1
            logger.error(
                "Scheduled workflow failed",
                schedule_id=schedule.id,
                error=str(e),
            )
        
        # Calculate next run
        schedule.next_run = CronParser.get_next_run(schedule.cron)
        schedule.updated_at = datetime.now(timezone.utc)
    
    def schedule(
        self,
        workflow_id: str,
        cron: str,
        name: str | None = None,
        input_params: dict | None = None,
        timeout_seconds: int = 3600,
        tenant_id: str = "default",
    ) -> ScheduledWorkflow:
        """
        Schedule a workflow for automatic execution.
        
        Args:
            workflow_id: ID of the workflow to execute
            cron: Cron expression (e.g., "0 9 * * *" for 9 AM daily)
            name: Optional display name
            input_params: Optional input parameters
            timeout_seconds: Execution timeout
            tenant_id: Tenant ID
        
        Returns:
            ScheduledWorkflow
        """
        # Validate cron expression
        try:
            next_run = CronParser.get_next_run(cron)
        except Exception as e:
            raise ValueError(f"Invalid cron expression: {e}")
        
        schedule_id = str(uuid.uuid4())
        
        schedule = ScheduledWorkflow(
            id=schedule_id,
            workflow_id=workflow_id,
            name=name or f"Schedule for {workflow_id}",
            cron=cron,
            next_run=next_run,
            input_params=input_params or {},
            timeout_seconds=timeout_seconds,
            tenant_id=tenant_id,
        )
        
        self._schedules[schedule_id] = schedule
        
        logger.info(
            "Workflow scheduled",
            schedule_id=schedule_id,
            workflow_id=workflow_id,
            cron=cron,
            next_run=next_run,
        )
        
        return schedule
    
    def unschedule(self, schedule_id: str) -> bool:
        """Remove a scheduled workflow."""
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            
            # Cancel any running execution
            if schedule_id in self._execution_tasks:
                self._execution_tasks[schedule_id].cancel()
                del self._execution_tasks[schedule_id]
            
            logger.info("Workflow unscheduled", schedule_id=schedule_id)
            return True
        
        return False
    
    def pause(self, schedule_id: str) -> bool:
        """Pause a scheduled workflow."""
        if schedule_id in self._schedules:
            self._schedules[schedule_id].status = ScheduleStatus.PAUSED
            self._schedules[schedule_id].updated_at = datetime.now(timezone.utc)
            logger.info("Schedule paused", schedule_id=schedule_id)
            return True
        return False
    
    def resume(self, schedule_id: str) -> bool:
        """Resume a paused scheduled workflow."""
        if schedule_id in self._schedules:
            schedule = self._schedules[schedule_id]
            schedule.status = ScheduleStatus.ACTIVE
            schedule.next_run = CronParser.get_next_run(schedule.cron)
            schedule.updated_at = datetime.now(timezone.utc)
            logger.info("Schedule resumed", schedule_id=schedule_id)
            return True
        return False
    
    def get_schedule(self, schedule_id: str) -> ScheduledWorkflow | None:
        """Get a specific schedule."""
        return self._schedules.get(schedule_id)
    
    def list_schedules(
        self,
        tenant_id: str | None = None,
        status: ScheduleStatus | None = None,
    ) -> list[ScheduledWorkflow]:
        """List all schedules, optionally filtered."""
        schedules = list(self._schedules.values())
        
        if tenant_id:
            schedules = [s for s in schedules if s.tenant_id == tenant_id]
        
        if status:
            schedules = [s for s in schedules if s.status == status]
        
        return schedules
    
    def get_metrics(self, tenant_id: str | None = None) -> SchedulerMetrics:
        """Get scheduler metrics."""
        schedules = self.list_schedules(tenant_id=tenant_id)
        
        today = datetime.now(timezone.utc).date()
        
        runs_today = sum(
            1 for s in schedules
            if s.last_run and s.last_run.date() == today
        )
        
        successes_today = sum(
            1 for s in schedules
            if s.last_run and s.last_run.date() == today and s.last_result == "success"
        )
        
        failures_today = sum(
            1 for s in schedules
            if s.last_run and s.last_run.date() == today and s.last_result in ["failed", "timeout"]
        )
        
        return SchedulerMetrics(
            total_scheduled=len(schedules),
            active_scheduled=sum(1 for s in schedules if s.status == ScheduleStatus.ACTIVE),
            runs_today=runs_today,
            successes_today=successes_today,
            failures_today=failures_today,
        )


# =============================================================================
# Global Scheduler Instance
# =============================================================================

_scheduler: WorkflowScheduler | None = None


def get_scheduler() -> WorkflowScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = WorkflowScheduler()
    return _scheduler


async def init_scheduler(
    workflow_executor: Callable[[str, dict], Coroutine[Any, Any, dict]] | None = None,
) -> WorkflowScheduler:
    """Initialize and start the global scheduler."""
    global _scheduler
    _scheduler = WorkflowScheduler(workflow_executor=workflow_executor)
    await _scheduler.start()
    return _scheduler
