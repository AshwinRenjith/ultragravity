from __future__ import annotations

from typing import Callable

from .actions import Action, PermissionOutcome, action_signature


class PermissionBroker:
    def __init__(self, input_func: Callable[[str], str] = input):
        self.input_func = input_func
        self.session_approvals: set[str] = set()

    def has_session_approval(self, action: Action) -> bool:
        return action_signature(action) in self.session_approvals

    def request_approval(self, action: Action) -> PermissionOutcome:
        if self.has_session_approval(action):
            return PermissionOutcome(approved=True, grant_scope="session", reason="Session approval cache hit")

        print("\n=== Ultragravity Safety Approval Required ===")
        print(f"Action ID : {action.action_id}")
        print(f"Tool      : {action.tool_name}")
        print(f"Operation : {action.operation}")
        print(f"Risk      : {action.risk_level}")
        print(f"Scope     : {', '.join(action.scope) if action.scope else '(none)'}")
        print(f"Reason    : {action.reason or '(not provided)'}")
        print(f"Params    : {action.params}")
        print("Choices   : [1] approve once, [2] approve for session, [3] deny, [4] abort")

        raw_choice = self.input_func("Enter choice (1/2/3/4): ").strip().lower()
        choice_map = {
            "1": "approve_once",
            "2": "approve_session",
            "3": "deny",
            "4": "abort",
            "approve once": "approve_once",
            "approve session": "approve_session",
            "deny": "deny",
            "abort": "abort",
        }

        selected = choice_map.get(raw_choice, "deny")

        if selected == "approve_session":
            self.session_approvals.add(action_signature(action))
            return PermissionOutcome(approved=True, grant_scope="session", reason="User approved for session")

        if selected == "approve_once":
            return PermissionOutcome(approved=True, grant_scope="once", reason="User approved once")

        if selected == "abort":
            return PermissionOutcome(approved=False, abort_requested=True, grant_scope="once", reason="User aborted")

        return PermissionOutcome(approved=False, abort_requested=False, grant_scope="once", reason="User denied")
