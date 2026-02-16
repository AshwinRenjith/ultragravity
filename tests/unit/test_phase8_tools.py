from ultragravity.gateway import ActionGateway
from ultragravity.policy import PolicyEngine, PolicyProfile
from ultragravity.permissions import PermissionBroker
from ultragravity.audit import AuditLogger
from ultragravity.tools import FileSystemAdapter, ToolOrchestrator, ToolRegistry


class DummyAdapter:
    name = "dummy"

    def capabilities(self):
        from ultragravity.actions import RiskLevel
        from ultragravity.tools import ToolCapability

        return {
            "echo": ToolCapability("echo", RiskLevel.R0, True, "Echo payload"),
        }

    def execute(self, operation, params):
        from ultragravity.tools import ToolExecutionResult

        if operation != "echo":
            return ToolExecutionResult(success=False, error="unsupported")
        return ToolExecutionResult(success=True, payload={"value": params.get("value")})


class MockSkill:
    def __init__(self, name="MockSkill"):
        self.name = name

    def execute(self, params):
        return {"status": "success", "message": f"ran {self.name}", "echo": params.get("instruction")}


def _permissive_orchestrator(tmp_path):
    gateway = ActionGateway(
        policy_engine=PolicyEngine(PolicyProfile.STRICT),
        permission_broker=PermissionBroker(input_func=lambda _: "1"),
        audit_logger=AuditLogger(log_dir=tmp_path / "audit"),
    )
    registry = ToolRegistry()
    return registry, ToolOrchestrator(registry, gateway)


def test_tool_registry_and_orchestrator_execute(tmp_path):
    registry, orchestrator = _permissive_orchestrator(tmp_path)
    registry.register(DummyAdapter())

    result = orchestrator.execute("dummy", "echo", {"value": "ok"}, scope=["unit"], reason="unit test")

    assert result.success is True
    assert result.payload["value"] == "ok"


def test_filesystem_adapter_sandbox_enforced(tmp_path):
    registry, orchestrator = _permissive_orchestrator(tmp_path)
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    registry.register(FileSystemAdapter(sandbox_root=str(sandbox)))

    write_ok = orchestrator.execute("filesystem", "write", {"path": "notes.txt", "content": "hello"}, scope=[str(sandbox)], reason="write inside")
    assert write_ok.success is True

    read_ok = orchestrator.execute("filesystem", "read", {"path": "notes.txt"}, scope=[str(sandbox)], reason="read inside")
    assert read_ok.success is True
    assert read_ok.payload["content"] == "hello"

    escape = orchestrator.execute("filesystem", "read", {"path": "../outside.txt"}, scope=[str(sandbox)], reason="escape attempt")
    assert escape.success is False
    assert "sandbox" in escape.error.lower()
