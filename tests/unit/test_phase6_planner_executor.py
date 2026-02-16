from ultragravity.actions import RiskLevel
from ultragravity.executor import CheckpointBroker, ExecutionState, PlanExecutor, StepStatus
from ultragravity.planner import Planner, PlanStep, StepRetryPolicy, StepType


def test_planner_builds_expected_browser_steps():
    planner = Planner()
    plan = planner.build_plan(
        instruction="Search for latest AI news",
        mode="BROWSER",
        url="https://example.com",
        max_iterations=8,
        retry_attempts=2,
        retry_backoff_seconds=0.1,
    )

    assert len(plan.steps) == 3
    assert plan.steps[0].step_type == StepType.START_BROWSER
    assert plan.steps[1].step_type == StepType.NAVIGATE_URL
    assert plan.steps[2].step_type == StepType.EXECUTE_GOAL_LOOP
    assert plan.steps[2].checkpoint_required is True


def test_executor_blocks_on_checkpoint_denial():
    planner = Planner()
    plan = planner.build_plan(
        instruction="Do sensitive action",
        mode="DESKTOP",
        url=None,
        max_iterations=3,
        retry_attempts=1,
        retry_backoff_seconds=0.0,
    )

    broker = CheckpointBroker(input_func=lambda _: "n")
    executor = PlanExecutor(checkpoint_broker=broker, sleep_fn=lambda _: None)

    handlers = {
        StepType.EXECUTE_GOAL_LOOP: lambda step, state: (True, {}, ""),
    }

    state = executor.execute(plan, handlers)
    record = state.records["execute_goal_loop"]

    assert state.aborted is True
    assert state.completed is False
    assert record.status == StepStatus.BLOCKED


def test_executor_retries_then_succeeds():
    step = PlanStep(
        id="retry_step",
        title="Retryable",
        step_type=StepType.EXECUTE_GOAL_LOOP,
        risk_level=RiskLevel.R2,
        checkpoint_required=False,
        retry_policy=StepRetryPolicy(max_attempts=2, backoff_seconds=0.0),
    )

    from ultragravity.planner import ExecutionPlan

    plan = ExecutionPlan(
        id="plan-retry",
        goal="retry-goal",
        mode="DESKTOP",
        created_at="now",
        steps=[step],
    )

    attempts = {"count": 0}

    def flaky_handler(step, state):
        attempts["count"] += 1
        if attempts["count"] == 1:
            return False, {}, "temporary failure"
        return True, {"done": True}, ""

    executor = PlanExecutor(checkpoint_broker=CheckpointBroker(input_func=lambda _: "y"), sleep_fn=lambda _: None)
    state = executor.execute(plan, {StepType.EXECUTE_GOAL_LOOP: flaky_handler})

    assert state.completed is True
    assert state.aborted is False
    assert state.records["retry_step"].attempts == 2
    assert state.records["retry_step"].status == StepStatus.SUCCEEDED


def test_executor_stops_when_dependency_not_satisfied():
    step1 = PlanStep(
        id="step1",
        title="Step 1",
        step_type=StepType.START_BROWSER,
        risk_level=RiskLevel.R1,
        checkpoint_required=False,
        retry_policy=StepRetryPolicy(max_attempts=1),
    )
    step2 = PlanStep(
        id="step2",
        title="Step 2",
        step_type=StepType.NAVIGATE_URL,
        risk_level=RiskLevel.R1,
        checkpoint_required=False,
        depends_on=["step1"],
        retry_policy=StepRetryPolicy(max_attempts=1),
    )

    from ultragravity.planner import ExecutionPlan

    plan = ExecutionPlan(
        id="dep-plan",
        goal="dep-goal",
        mode="BROWSER",
        created_at="now",
        steps=[step1, step2],
    )

    def fail_first(step, state):
        return False, {}, "failed start"

    executor = PlanExecutor(checkpoint_broker=CheckpointBroker(input_func=lambda _: "y"), sleep_fn=lambda _: None)
    state = executor.execute(plan, {StepType.START_BROWSER: fail_first, StepType.NAVIGATE_URL: lambda s, st: (True, {}, "")})

    assert state.aborted is True
    assert state.completed is False
    assert state.records["step1"].status == StepStatus.FAILED
