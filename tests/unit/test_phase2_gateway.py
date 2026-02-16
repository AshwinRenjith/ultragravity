from ultragravity.actions import Action, GatewayExecutionResult, RiskLevel
from ultragravity.audit import AuditLogger
from ultragravity.gateway import ActionGateway
from ultragravity.permissions import PermissionBroker
from ultragravity.policy import PolicyEngine, PolicyProfile
from tools.terminal import TerminalTool
import agent.bridge_applescript as bridge_applescript


class DenyGateway:
    def execute(self, action, executor):
        return GatewayExecutionResult(allowed=False, executed=False, error="denied")


def test_gateway_blocks_execution_when_user_denies(tmp_path):
    broker = PermissionBroker(input_func=lambda _: "3")
    gateway = ActionGateway(
        policy_engine=PolicyEngine(PolicyProfile.STRICT),
        permission_broker=broker,
        audit_logger=AuditLogger(log_dir=tmp_path / "audit"),
    )

    executed = {"value": False}

    action = Action(
        tool_name="terminal",
        operation="shell_command",
        params={"command": "echo blocked"},
        risk_level=RiskLevel.R3,
        scope=["shell"],
        reversible=False,
        reason="test",
    )

    result = gateway.execute(action, lambda: executed.update(value=True))
    assert result.allowed is False
    assert result.executed is False
    assert executed["value"] is False


def test_gateway_session_approval_reuses_cache(tmp_path):
    calls = {"count": 0}

    def fake_input(_):
        calls["count"] += 1
        return "2"

    broker = PermissionBroker(input_func=fake_input)
    gateway = ActionGateway(
        policy_engine=PolicyEngine(PolicyProfile.STRICT),
        permission_broker=broker,
        audit_logger=AuditLogger(log_dir=tmp_path / "audit"),
    )

    action = Action(
        tool_name="skill",
        operation="execute_skill",
        params={"skill": "NavigationSkill"},
        risk_level=RiskLevel.R1,
        scope=["browser", "NavigationSkill"],
        reversible=True,
        reason="test session grant",
    )

    first = gateway.execute(action, lambda: "first")
    second = gateway.execute(action, lambda: "second")

    assert first.allowed is True and first.executed is True
    assert second.allowed is True and second.executed is True
    assert calls["count"] == 1


def test_terminal_tool_denies_when_gateway_blocks():
    terminal_tool = TerminalTool(gateway=DenyGateway())
    output = terminal_tool.execute("echo should_not_run")
    assert output.startswith("Denied:")


def test_applescript_bridge_denied_by_gateway(monkeypatch):
    bridge_applescript.set_action_gateway(DenyGateway())
    output = bridge_applescript.open_app("Notes")
    assert output is None

    bridge_applescript.set_action_gateway(None)
