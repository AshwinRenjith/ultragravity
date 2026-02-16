
import subprocess
import logging
from ultragravity.actions import Action, RiskLevel

class TerminalTool:
    def __init__(self, gateway=None):
        self.logger = logging.getLogger("TerminalTool")
        self.gateway = gateway

    def _execute_command(self, command: str) -> str:
        self.logger.info(f"Executing command: {command}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {e.stderr}")
            return f"Error: {e.stderr}"
        except Exception as e:
            self.logger.error(f"Execution error: {e}")
            return f"Error: {str(e)}"

    def execute(self, command: str) -> str:
        """Executes a shell command and returns the output."""
        if self.gateway is None:
            return self._execute_command(command)

        action = Action(
            tool_name="terminal",
            operation="shell_command",
            params={"command": command},
            risk_level=RiskLevel.R3,
            scope=["shell"],
            reversible=False,
            reason="Execute terminal command",
        )
        execution = self.gateway.execute(action, lambda: self._execute_command(command))
        if not execution.allowed:
            return f"Denied: {execution.error}"
        if not execution.executed:
            return f"Error: {execution.error}"
        return execution.result
