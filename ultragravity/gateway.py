from __future__ import annotations

import traceback
from time import perf_counter
from typing import Callable, TypeVar

from .actions import Action, GatewayExecutionResult
from .audit import AuditLogger
from .permissions import PermissionBroker
from .policy import PolicyEngine

ExecutionType = TypeVar("ExecutionType")


class ActionGateway:
    def __init__(
        self,
        policy_engine: PolicyEngine | None = None,
        permission_broker: PermissionBroker | None = None,
        audit_logger: AuditLogger | None = None,
    ):
        self.policy_engine = policy_engine or PolicyEngine()
        self.permission_broker = permission_broker or PermissionBroker()
        self.audit_logger = audit_logger or AuditLogger()

    def execute(self, action: Action, executor: Callable[[], ExecutionType]) -> GatewayExecutionResult:
        policy_decision = self.policy_engine.evaluate(action)

        self.audit_logger.write_event(
            "policy_decision",
            {
                "action": action.model_dump(),
                "decision": policy_decision.model_dump(),
            },
        )

        if not policy_decision.allow:
            self.audit_logger.write_event(
                "action_blocked",
                {
                    "action": action.model_dump(),
                    "reason": policy_decision.reason,
                },
            )
            return GatewayExecutionResult(allowed=False, executed=False, error=policy_decision.reason)

        if policy_decision.require_prompt:
            permission = self.permission_broker.request_approval(action)
            self.audit_logger.write_event(
                "permission_outcome",
                {
                    "action": action.model_dump(),
                    "permission": permission.model_dump(),
                },
            )
            if not permission.approved:
                return GatewayExecutionResult(
                    allowed=False,
                    executed=False,
                    aborted=permission.abort_requested,
                    error=permission.reason,
                )

        started = perf_counter()
        try:
            result = executor()
            duration_ms = int((perf_counter() - started) * 1000)
            self.audit_logger.write_event(
                "action_executed",
                {
                    "action": action.model_dump(),
                    "duration_ms": duration_ms,
                    "success": True,
                },
            )
            return GatewayExecutionResult(allowed=True, executed=True, result=result)
        except Exception as exc:  # pragma: no cover - explicit auditing branch
            duration_ms = int((perf_counter() - started) * 1000)
            self.audit_logger.write_event(
                "action_executed",
                {
                    "action": action.model_dump(),
                    "duration_ms": duration_ms,
                    "success": False,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
            return GatewayExecutionResult(allowed=True, executed=False, error=str(exc))
