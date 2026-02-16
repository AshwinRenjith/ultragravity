
import logging
import time
import json
import os
import re

from agent.vision import VisionAgent
from agent.browser import BrowserAgent
from agent.desktop import DesktopAgent
import agent.bridge_applescript as os_bridge
from skills import SearchSkill, NavigationSkill, ExtractionSkill
from skills.desktop_control import DesktopControlSkill
from skills.whatsapp import WhatsAppSkill
from termcolor import colored
from ultragravity.actions import Action, RiskLevel
from ultragravity.call_reduction import TTLCache, build_tool_cache_key
from ultragravity.gateway import ActionGateway
from ultragravity.policy import PolicyEngine, PolicyProfile
from ultragravity.config import AppRuntimeConfig
from ultragravity.executor import ExecutionState, PlanExecutor
from ultragravity.planner import Planner, PlanStep, StepType
from ultragravity.state_machine import SessionPhase, SessionStateMachine
from ultragravity.memory import MemoryManager, SQLiteMemoryRepository
from ultragravity.tools import (
    BrowserAdapter,
    DesktopAdapter,
    FileSystemAdapter,
    SkillAdapter,
    ToolOrchestrator,
    ToolRegistry,
)

class UltragravityAgent:
    def __init__(self, headless: bool = False, model_name: str = "gemini-1.5-flash", runtime_config: AppRuntimeConfig | None = None):
        self.logger = logging.getLogger("UltragravityAgent")
        self.vision = VisionAgent(model_name=model_name, runtime_config=runtime_config)
        self.runtime_config = runtime_config or self.vision.runtime_config

        self.memory_repo = SQLiteMemoryRepository(
            db_path=self.runtime_config.memory.sqlite_path,
            max_events=self.runtime_config.memory.max_events,
        )
        self.memory = MemoryManager(
            repository=self.memory_repo,
            retrieval_top_k=self.runtime_config.memory.retrieval_top_k,
        )

        preferred_policy_raw = (self.memory.get_preference("policy_profile", "strict") or "strict").lower().strip()
        try:
            preferred_policy = PolicyProfile(preferred_policy_raw)
        except Exception:
            preferred_policy = PolicyProfile.STRICT

        self.memory.set_preference("policy_profile", preferred_policy.value)
        self.memory.set_preference("interaction_style", self.memory.get_preference("interaction_style", "concise") or "concise")

        self.browser = BrowserAgent(headless=headless)
        self.desktop = DesktopAgent()
        self.gateway = ActionGateway(policy_engine=PolicyEngine(preferred_policy))
        os_bridge.set_action_gateway(self.gateway)

        self.tool_registry = ToolRegistry()
        self.tool_registry.register(BrowserAdapter(self.browser))
        self.tool_registry.register(DesktopAdapter(self.desktop))
        self.tool_registry.register(SkillAdapter(self.skills if hasattr(self, "skills") else []))
        self.tool_registry.register(FileSystemAdapter(sandbox_root=os.getcwd()))
        self.tool_orchestrator = ToolOrchestrator(self.tool_registry, self.gateway)
        self.tool_outcome_cache = TTLCache(
            ttl_seconds=self.runtime_config.call_reduction.tool_cache.ttl_seconds,
            max_entries=self.runtime_config.call_reduction.tool_cache.max_entries,
        )
        self.planner = Planner()
        self.plan_executor = PlanExecutor()
        self.session_state = SessionStateMachine()
        self.execution_state: ExecutionState | None = None
        self.history = []
        
        # Mode: "BROWSER" or "DESKTOP"
        self.mode = "BROWSER" 
        
        # Initialize Skills
        self.skills = [
            SearchSkill(self),
            NavigationSkill(self),
            ExtractionSkill(self),
            DesktopControlSkill(self),
            WhatsAppSkill(self),
        ]
        self.tool_registry.register(SkillAdapter(self.skills))

    def _risk_for_skill(self, skill_name: str) -> RiskLevel:
        if skill_name == "ExtractionSkill":
            return RiskLevel.R0
        if skill_name in {"SearchSkill", "NavigationSkill"}:
            return RiskLevel.R1
        if skill_name == "DesktopControlSkill":
            return RiskLevel.R2
        if skill_name == "WhatsAppSkill":
            return RiskLevel.R2
        return RiskLevel.R2

    def _build_skill_action(self, skill_name: str, instruction: str) -> Action:
        return Action(
            tool_name="skill",
            operation="execute_skill",
            params={"skill": skill_name, "instruction": instruction},
            risk_level=self._risk_for_skill(skill_name),
            scope=[self.mode.lower(), skill_name],
            reversible=False,
            reason=f"Fast-path skill execution for {skill_name}",
        )

    def _risk_for_plan_action(self, action_name: str) -> RiskLevel:
        if action_name in {"wait", "done"}:
            return RiskLevel.R0
        if action_name in {"click", "scroll"}:
            return RiskLevel.R2 if self.mode == "DESKTOP" else RiskLevel.R1
        if action_name == "type":
            return RiskLevel.R2
        return RiskLevel.R2

    def _build_plan_action(self, action_plan: dict, instruction: str) -> Action:
        action_name = action_plan.get("action", "unknown")
        page_url = ""
        if self.mode == "BROWSER" and self.browser.page:
            page_url = self.browser.page.url

        return Action(
            tool_name="vision_executor",
            operation=f"{self.mode.lower()}_{action_name}",
            params={
                "action": action_name,
                "target_element": action_plan.get("target_element", {}),
                "value": action_plan.get("value", ""),
            },
            risk_level=self._risk_for_plan_action(action_name),
            scope=[self.mode.lower(), page_url] if page_url else [self.mode.lower()],
            reversible=action_name in {"scroll", "wait"},
            reason=action_plan.get("reasoning") or f"Execute planned action for goal: {instruction}",
        )

    @staticmethod
    def _strip_memory_from_instruction(instruction: str) -> str:
        if "\n\nRelevant Memory:" not in instruction:
            return instruction.strip()
        return instruction.split("\n\nRelevant Memory:", 1)[0].strip()

    def _rewrite_runtime_instruction(self, instruction: str, current_url: str) -> str:
        clean_instruction = self._strip_memory_from_instruction(instruction)
        compact = " ".join(clean_instruction.split())

        if self.mode != "BROWSER":
            return compact

        search_hosts = ("google.com/search", "duckduckgo.com", "bing.com/search")
        if any(host in current_url for host in search_hosts):
            lowered = compact.lower()
            lowered = re.sub(r"\b(and|then)\s+(provide|give|return|summari[sz]e|write|format|include|list|show)\b.*$", "", lowered)
            lowered = re.sub(r"\b(with|including)\s+(source|sources|citation|citations|website|websites|links?)\b.*$", "", lowered)
            lowered = re.sub(r"^(search|find|look\s*up)\s+(for\s+)?", "", lowered)
            lowered = lowered.strip(" .,:;-")
            if lowered:
                return f"Search for {lowered}"

        return compact

    def _execute_wait_breaker(self, current_url: str) -> tuple[bool, str | None]:
        if self.mode != "BROWSER":
            return False, "Repeated wait actions without progress"

        fallback_plan = {
            "action": "scroll",
            "target_element": {"description": "results viewport", "coordinates": []},
            "value": "",
            "reasoning": "Wait-streak breaker: forcing viewport change",
        }
        execution_result = self.tool_orchestrator.execute(
            tool_name="browser",
            operation="execute_action",
            params={"action_plan": fallback_plan},
            scope=["browser", current_url] if current_url else ["browser"],
            reason="Break repeated wait loop by scrolling to trigger state change",
        )
        if execution_result.success:
            return True, None
        return False, execution_result.error or "Wait breaker action failed"

    def _execute_start_browser_step(self, step: PlanStep, state: ExecutionState) -> tuple[bool, dict[str, object], str]:
        result = self.tool_orchestrator.execute(
            tool_name="browser",
            operation="start",
            params={"headless": self.browser.headless},
            scope=["browser"],
            reason="Initialize browser automation context",
        )
        if not result.success:
            return False, {}, result.error or "Browser start failed"
        return True, {}, ""

    def _execute_navigate_step(self, step: PlanStep, state: ExecutionState) -> tuple[bool, dict[str, object], str]:
        url = str(step.params.get("url", ""))
        if not url:
            return False, {}, "No URL provided for navigation step"

        result = self.tool_orchestrator.execute(
            tool_name="browser",
            operation="navigate",
            params={"url": url},
            scope=[url],
            reason="Navigate to initial URL",
        )
        if not result.success:
            return False, {}, result.error or "Navigation failed"
        return True, {"current_url": url}, ""

    def _execute_goal_loop_step(self, step: PlanStep, state: ExecutionState) -> tuple[bool, dict[str, object], str]:
        instruction = str(step.params.get("instruction", ""))
        original_instruction = instruction
        max_iterations = int(step.params.get("max_iterations", 20))
        previous_url = str(state.recovery_context.get("current_url", ""))

        if not instruction:
            return False, {}, "Instruction is required for goal loop"

        consecutive_failures = 0
        wait_streak = 0

        for _ in range(max_iterations):
            current_url = ""
            if self.mode == "BROWSER" and self.browser.page:
                current_url = self.browser.page.url

            runtime_instruction = self._rewrite_runtime_instruction(instruction, current_url)

            for skill in self.skills:
                confidence = skill.can_handle(runtime_instruction)
                if confidence <= 0.8:
                    continue

                self.logger.info(f"Skill '{skill.name}' matched with confidence {confidence}")
                print(colored(f"⚡ Fast Path: Executing {skill.name}...", "cyan"))
                skill_action = self._build_skill_action(skill.name, instruction)

                skill_cache_key = build_tool_cache_key(
                    "skill",
                    skill.name,
                    {"instruction": runtime_instruction, "mode": self.mode},
                )

                if skill_action.risk_level == RiskLevel.R0 and self.runtime_config.call_reduction.enabled:
                    cached_skill_result = self.tool_outcome_cache.get(skill_cache_key)
                    if cached_skill_result is not None:
                        self.logger.info(f"Tool cache hit for {skill.name}")
                        result = cached_skill_result
                    else:
                        tool_result = self.tool_orchestrator.execute(
                            tool_name="skill",
                            operation="execute",
                            params={"skill": skill.name, "instruction": runtime_instruction},
                            scope=[self.mode.lower(), skill.name],
                            reason=f"Fast-path skill execution for {skill.name}",
                        )
                        if not tool_result.success:
                            return False, {"reason": tool_result.error or "Skill failed"}, "Skill failed"
                        result = tool_result.payload
                        if isinstance(result, dict) and result.get("status") == "success":
                            self.tool_outcome_cache.set(skill_cache_key, result)
                else:
                    tool_result = self.tool_orchestrator.execute(
                        tool_name="skill",
                        operation="execute",
                        params={"skill": skill.name, "instruction": runtime_instruction},
                        scope=[self.mode.lower(), skill.name],
                        reason=f"Fast-path skill execution for {skill.name}",
                    )
                    if not tool_result.success:
                        return False, {"reason": tool_result.error or "Skill failed"}, "Skill failed"
                    result = tool_result.payload

                if result["status"] == "success":
                    print(colored(f"✅ Skill Completed: {result.get('message', 'Done')}", "green"))

                    if "content" in result:
                        print(colored("📄 Content Extracted. Generating Summary...", "cyan"))
                        summary = self.vision.summarize_content(result["content"], instruction)
                        print(colored("\n" + "=" * 40, "green"))
                        print(colored("REPORT / SUMMARY", "green"))
                        print(colored("=" * 40 + "\n", "green"))
                        print(summary)
                        print(colored("\n" + "=" * 40, "green"))
                        print(colored("✅ Task Completed via Extraction!", "green"))
                        return True, {"completed_by": skill.name}, ""

                    if not runtime_instruction.lower().startswith("verify"):
                        instruction = "Verify the result matches the goal: " + runtime_instruction

                    break

                print(colored(f"⚠️ Skill Failed: {result.get('reason')}", "yellow"))

            print(colored(f"👀 Observing ({self.mode})...", "yellow"))
            current_url = ""
            if self.mode == "BROWSER" and self.browser.page:
                current_url = self.browser.page.url

            if self.mode == "BROWSER":
                screenshot_path = self.browser.get_screenshot()
            else:
                screenshot_path = self.desktop.get_screenshot()

            external_state_changed = current_url != previous_url if self.mode == "BROWSER" else False
            previous_url = current_url

            print(colored("🧠 Analyzing...", "magenta"))
            memory_hints = self.memory.retrieve_relevant_facts(
                query=runtime_instruction,
                top_k=self.runtime_config.memory.retrieval_top_k,
            )
            action_plan = self.vision.analyze_image(
                screenshot_path,
                runtime_instruction,
                mode=self.mode,
                current_url=current_url,
                external_state_changed=external_state_changed,
                memory_hints=memory_hints,
                wait_streak=wait_streak,
            )
            print(colored(f"💡 Plan: {json.dumps(action_plan, indent=2)}", "green"))

            if action_plan.get("action") == "done":
                print(colored("✅ Task Completed!", "green"))
                self.memory.remember(
                    kind="task_success",
                    content=f"Goal completed: {original_instruction}",
                    metadata={"mode": self.mode, "completion_source": "vision_done"},
                )
                return True, {"completed_by": "vision_done"}, ""

            if action_plan.get("action") == "fail":
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    return False, {"current_url": current_url}, "Vision failed to determine action repeatedly"
                time.sleep(1)
                continue

            if action_plan.get("action") == "wait":
                wait_streak += 1
                if wait_streak >= 3:
                    print(colored("🛠️ Wait-streak breaker activated (forcing scroll)", "cyan"))
                    breaker_success, breaker_error = self._execute_wait_breaker(current_url)
                    if not breaker_success:
                        consecutive_failures += 1
                        if consecutive_failures >= 3:
                            return False, {"current_url": current_url}, breaker_error or "Wait breaker failed repeatedly"
                    else:
                        consecutive_failures = 0
                    time.sleep(2)
                    continue
                print(colored("⏳ Waiting...", "blue"))
                time.sleep(2)
                continue

            wait_streak = 0

            plan_action = self._build_plan_action(action_plan, instruction)
            if self.mode == "BROWSER":
                execution_result = self.tool_orchestrator.execute(
                    tool_name="browser",
                    operation="execute_action",
                    params={"action_plan": action_plan},
                    scope=plan_action.scope,
                    reason=plan_action.reason,
                )
            else:
                execution_result = self.tool_orchestrator.execute(
                    tool_name="desktop",
                    operation="execute_action",
                    params={"action_plan": action_plan},
                    scope=plan_action.scope,
                    reason=plan_action.reason,
                )

            if not execution_result.success:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    return False, {"current_url": current_url}, execution_result.error or "Action execution failed repeatedly"
                continue

            consecutive_failures = 0
            time.sleep(5)

        return False, {"current_url": previous_url}, "Max iterations reached without completion"

    def start_session(self, url: str, instruction: str):
        print(colored("Starting Ultragravity Agent...", "cyan"))

        self.session_state.transition_to(SessionPhase.PLANNING)

        lower_instr = instruction.lower()
        if "open" in lower_instr or "app" in lower_instr or "note" in lower_instr or "write" in lower_instr:
             self.mode = "DESKTOP"
             print(colored("🖥️  Mode: DESKTOP", "blue"))
        else:
             self.mode = "BROWSER"
             print(colored("🌐 Mode: BROWSER", "blue"))

        try:
            augmented_instruction = self.memory.augment_goal_with_memory(
                instruction,
                top_k=self.runtime_config.memory.retrieval_top_k,
            )
            self.memory.remember(
                kind="task_start",
                content=f"Task started: {instruction}",
                metadata={"mode": self.mode, "url": url or ""},
            )

            plan = self.planner.build_plan(
                instruction=augmented_instruction,
                mode=self.mode,
                url=url,
                max_iterations=self.runtime_config.planner.max_iterations,
                retry_attempts=self.runtime_config.planner.retry_attempts,
                retry_backoff_seconds=self.runtime_config.planner.retry_backoff_seconds,
            )
            print(colored(self.planner.render_plan(plan), "cyan"))

            handlers = {
                StepType.START_BROWSER: self._execute_start_browser_step,
                StepType.NAVIGATE_URL: self._execute_navigate_step,
                StepType.EXECUTE_GOAL_LOOP: self._execute_goal_loop_step,
            }

            self.session_state.transition_to(SessionPhase.EXECUTING)
            self.execution_state = self.plan_executor.execute(plan=plan, handlers=handlers, state=self.execution_state)

            if self.execution_state is not None:
                serializable_state = {
                    "plan_id": self.execution_state.plan_id,
                    "current_step_index": self.execution_state.current_step_index,
                    "aborted": self.execution_state.aborted,
                    "completed": self.execution_state.completed,
                    "recovery_context": self.execution_state.recovery_context,
                    "records": {
                        key: {
                            "status": value.status,
                            "attempts": value.attempts,
                            "error": value.error,
                            "started_at": value.started_at,
                            "finished_at": value.finished_at,
                        }
                        for key, value in self.execution_state.records.items()
                    },
                }
                self.memory.save_execution_state(plan.id, serializable_state)

            if self.execution_state.completed:
                self.session_state.transition_to(SessionPhase.COMPLETED)
                self.memory.remember(
                    kind="task_success",
                    content=f"Plan completed successfully for goal: {instruction}",
                    metadata={"mode": self.mode, "plan_id": plan.id},
                )
                print(colored("✅ Plan completed successfully.", "green"))
                return

            self.session_state.transition_to(SessionPhase.RECOVERY)
            reason = str(self.execution_state.recovery_context.get("reason", "Unknown failure"))
            failed_step = str(self.execution_state.recovery_context.get("last_failed_step", "unknown"))
            self.memory.remember(
                kind="task_failure",
                content=f"Plan aborted for goal '{instruction}' at step '{failed_step}'",
                metadata={"mode": self.mode, "plan_id": plan.id, "reason": reason},
            )
            print(colored(f"❌ Plan aborted at step '{failed_step}': {reason}", "red"))
            self.session_state.transition_to(SessionPhase.ABORTED)
            return
                
        except KeyboardInterrupt:
            print("Stopping agent...")
        finally:
            self.browser.stop()

if __name__ == "__main__":
    # Test stub
    agent = UltragravityAgent(headless=False)
    # agents usually need a goal, we can pass it via CLI in main.py
