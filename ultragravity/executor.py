from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

from .planner import ExecutionPlan, PlanStep, StepType


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class StepExecutionRecord:
    step_id: str
    status: StepStatus = StepStatus.PENDING
    attempts: int = 0
    error: str = ""
    started_at: str = ""
    finished_at: str = ""


@dataclass
class ExecutionState:
    plan_id: str
    current_step_index: int = 0
    records: dict[str, StepExecutionRecord] = field(default_factory=dict)
    aborted: bool = False
    completed: bool = False
    recovery_context: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckpointDecision:
    approved: bool
    reason: str = ""


class CheckpointBroker:
    def __init__(self, input_func: Callable[[str], str] = input):
        self.input_func = input_func

    def confirm(self, step: PlanStep, plan: ExecutionPlan) -> CheckpointDecision:
        print("\n=== Plan Checkpoint Confirmation ===")
        print(f"Plan ID   : {plan.id}")
        print(f"Step      : {step.title}")
        print(f"Risk      : {step.risk_level}")
        print(f"Params    : {step.params}")
        choice = self.input_func("Approve this checkpoint? [y/N]: ").strip().lower()
        if choice in {"y", "yes"}:
            return CheckpointDecision(approved=True, reason="Approved by user")
        return CheckpointDecision(approved=False, reason="User denied checkpoint")


StepHandler = Callable[[PlanStep, ExecutionState], tuple[bool, dict[str, object], str]]


class PlanExecutor:
    def __init__(self, checkpoint_broker: CheckpointBroker | None = None, sleep_fn: Callable[[float], None] = time.sleep):
        self.checkpoint_broker = checkpoint_broker or CheckpointBroker()
        self.sleep_fn = sleep_fn

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def execute(
        self,
        plan: ExecutionPlan,
        handlers: dict[StepType, StepHandler],
        state: ExecutionState | None = None,
    ) -> ExecutionState:
        execution_state = state or ExecutionState(plan_id=plan.id)

        if execution_state.records == {}:
            execution_state.records = {
                step.id: StepExecutionRecord(step_id=step.id)
                for step in plan.steps
            }

        while execution_state.current_step_index < len(plan.steps):
            step = plan.steps[execution_state.current_step_index]
            record = execution_state.records[step.id]

            for dependency in step.depends_on:
                dependency_record = execution_state.records.get(dependency)
                if dependency_record and dependency_record.status != StepStatus.SUCCEEDED:
                    record.status = StepStatus.BLOCKED
                    record.error = f"Dependency not satisfied: {dependency}"
                    execution_state.aborted = True
                    execution_state.recovery_context.update(
                        {
                            "last_failed_step": step.id,
                            "reason": record.error,
                        }
                    )
                    return execution_state

            if step.checkpoint_required:
                decision = self.checkpoint_broker.confirm(step, plan)
                if not decision.approved:
                    record.status = StepStatus.BLOCKED
                    record.error = decision.reason
                    record.finished_at = self._timestamp()
                    execution_state.aborted = True
                    execution_state.recovery_context.update(
                        {
                            "last_failed_step": step.id,
                            "reason": decision.reason,
                        }
                    )
                    return execution_state

            handler = handlers.get(step.step_type)
            if handler is None:
                record.status = StepStatus.FAILED
                record.error = f"No handler registered for step type: {step.step_type}"
                record.finished_at = self._timestamp()
                execution_state.aborted = True
                execution_state.recovery_context.update(
                    {
                        "last_failed_step": step.id,
                        "reason": record.error,
                    }
                )
                return execution_state

            max_attempts = max(1, step.retry_policy.max_attempts)
            for attempt in range(1, max_attempts + 1):
                record.status = StepStatus.RUNNING
                record.attempts = attempt
                if not record.started_at:
                    record.started_at = self._timestamp()

                succeeded, payload, error = handler(step, execution_state)
                if payload:
                    execution_state.recovery_context.update(payload)

                if succeeded:
                    record.status = StepStatus.SUCCEEDED
                    record.error = ""
                    record.finished_at = self._timestamp()
                    execution_state.current_step_index += 1
                    break

                record.status = StepStatus.FAILED
                record.error = error
                record.finished_at = self._timestamp()

                if attempt < max_attempts:
                    backoff = step.retry_policy.backoff_seconds * attempt
                    if backoff > 0:
                        self.sleep_fn(backoff)
                else:
                    fallback_id = step.retry_policy.fallback_step_id
                    if fallback_id:
                        fallback_index = next((i for i, candidate in enumerate(plan.steps) if candidate.id == fallback_id), None)
                        if fallback_index is not None:
                            execution_state.current_step_index = fallback_index
                            execution_state.recovery_context.update(
                                {
                                    "fallback_triggered_from": step.id,
                                    "fallback_target": fallback_id,
                                    "failure_reason": error,
                                }
                            )
                            break

                    execution_state.aborted = True
                    execution_state.recovery_context.update(
                        {
                            "last_failed_step": step.id,
                            "reason": error,
                        }
                    )
                    return execution_state

        execution_state.completed = True
        execution_state.aborted = False
        return execution_state
