from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from ultragravity.actions import RiskLevel


class StepType(str, Enum):
    START_BROWSER = "start_browser"
    NAVIGATE_URL = "navigate_url"
    EXECUTE_GOAL_LOOP = "execute_goal_loop"


@dataclass(frozen=True)
class StepRetryPolicy:
    max_attempts: int = 1
    backoff_seconds: float = 0.0
    fallback_step_id: str | None = None


@dataclass(frozen=True)
class PlanStep:
    id: str
    title: str
    step_type: StepType
    risk_level: RiskLevel
    checkpoint_required: bool
    params: dict[str, object] = field(default_factory=dict)
    retry_policy: StepRetryPolicy = field(default_factory=StepRetryPolicy)
    depends_on: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExecutionPlan:
    id: str
    goal: str
    mode: str
    created_at: str
    steps: list[PlanStep]


class Planner:
    def build_plan(
        self,
        instruction: str,
        mode: str,
        url: str | None,
        max_iterations: int,
        retry_attempts: int,
        retry_backoff_seconds: float,
    ) -> ExecutionPlan:
        plan_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        steps: list[PlanStep] = []

        if mode == "BROWSER":
            start_step = PlanStep(
                id="start_browser",
                title="Start browser context",
                step_type=StepType.START_BROWSER,
                risk_level=RiskLevel.R1,
                checkpoint_required=False,
                params={},
                retry_policy=StepRetryPolicy(max_attempts=max(1, retry_attempts), backoff_seconds=max(0.0, retry_backoff_seconds)),
            )
            steps.append(start_step)

            if url:
                steps.append(
                    PlanStep(
                        id="initial_navigation",
                        title="Navigate to initial URL",
                        step_type=StepType.NAVIGATE_URL,
                        risk_level=RiskLevel.R1,
                        checkpoint_required=False,
                        params={"url": url},
                        retry_policy=StepRetryPolicy(max_attempts=max(1, retry_attempts), backoff_seconds=max(0.0, retry_backoff_seconds)),
                        depends_on=[start_step.id],
                    )
                )

        loop_dependencies = [steps[-1].id] if steps else []
        steps.append(
            PlanStep(
                id="execute_goal_loop",
                title="Execute goal loop",
                step_type=StepType.EXECUTE_GOAL_LOOP,
                risk_level=RiskLevel.R2,
                checkpoint_required=True,
                params={
                    "instruction": instruction,
                    "max_iterations": max(1, max_iterations),
                },
                retry_policy=StepRetryPolicy(
                    max_attempts=max(1, retry_attempts),
                    backoff_seconds=max(0.0, retry_backoff_seconds),
                ),
                depends_on=loop_dependencies,
            )
        )

        return ExecutionPlan(
            id=plan_id,
            goal=instruction,
            mode=mode,
            created_at=created_at,
            steps=steps,
        )

    @staticmethod
    def render_plan(plan: ExecutionPlan) -> str:
        lines = [f"Execution Plan [{plan.id[:8]}]", f"Mode: {plan.mode}", f"Goal: {plan.goal}", "Steps:"]
        for index, step in enumerate(plan.steps, start=1):
            checkpoint = "checkpoint" if step.checkpoint_required else "no-checkpoint"
            lines.append(
                f"  {index}. {step.title} ({step.step_type}, risk={step.risk_level}, {checkpoint}, retries={step.retry_policy.max_attempts})"
            )
        return "\n".join(lines)
