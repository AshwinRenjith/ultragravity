from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ultragravity.config import AppRuntimeConfig, load_runtime_config
from ultragravity.diagnostics import run_startup_diagnostics
from ultragravity.memory import MemoryManager, SQLiteMemoryRepository
from ultragravity.policy import PolicyProfile

DEFAULT_CONFIG_PATH = "ultragravity.config.yaml"
DEFAULT_SETUP_STATE_PATH = Path("data/setup_state.json")
DEFAULT_RUNTIME_STATUS_PATH = Path("logs/runtime/status.json")
DEFAULT_AUDIT_LOG_DIR = Path("logs/audit")
DEFAULT_TELEMETRY_LOG_DIR = Path("logs/telemetry")


def _is_quick_whatsapp_instruction(instruction: str) -> bool:
    lowered = (instruction or "").lower()
    return (
        "whatsapp" in lowered
        or ("send" in lowered and "to" in lowered)
        or ("message" in lowered and "to" in lowered)
        or ("text" in lowered and "to" in lowered)
    )


def _is_quick_note_instruction(instruction: str) -> bool:
    lowered = (instruction or "").lower()
    return "note" in lowered and any(token in lowered for token in ("write", "create", "add"))


def _extract_note_content(instruction: str) -> str:
    import re

    text = (instruction or "").strip()
    patterns = [
        r"(?:write|create|add)\s+(?:a\s+)?note\s+(?:about|on)\s+(.+)$",
        r"(?:write|create|add)\s+(?:a\s+)?note\s*[:\-]\s*(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().strip("\"'")
    return text


def _run_quick_note(instruction: str) -> int:
    from agent.bridge_applescript import create_note

    content = _extract_note_content(instruction)
    if not content:
        print("Quick note failed: no note content found in instruction.")
        return 1

    result = create_note(content)
    if result is None:
        print("Quick note failed: AppleScript bridge did not return success.")
        return 1

    print(f"Quick note complete: {content}")
    return 0


def _run_quick_whatsapp(instruction: str) -> int:
    from skills.whatsapp import WhatsAppSkill

    class _QuickAgent:
        def __init__(self) -> None:
            self.logger = logging.getLogger("QuickWhatsApp")
            self.desktop = None

    skill = WhatsAppSkill(_QuickAgent())
    if skill.can_handle(instruction) <= 0.5:
        return 2

    result = skill.execute({"instruction": instruction})
    if isinstance(result, dict) and result.get("status") == "success":
        recipient = result.get("contact") or result.get("phone") or "recipient"
        message = result.get("message") or ""
        print(f"Quick send complete: '{message}' -> {recipient}")
        return 0

    reason = "Unknown failure"
    if isinstance(result, dict):
        reason = str(result.get("reason", reason))
    print(f"Quick send failed: {reason}")
    return 1


def configure_logging(log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _detect_mode(instruction: str) -> str:
    lowered = instruction.lower()
    if (
        "open" in lowered
        or "app" in lowered
        or "note" in lowered
        or "write" in lowered
        or "whatsapp" in lowered
        or ("send" in lowered and "to" in lowered)
        or ("message" in lowered and "to" in lowered)
        or ("text" in lowered and "to" in lowered)
    ):
        return "DESKTOP"
    return "BROWSER"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_or_replace_env_var(env_path: Path, key: str, value: str) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        env_path.write_text("", encoding="utf-8")

    lines = env_path.read_text(encoding="utf-8").splitlines()
    prefix = f"{key}="
    replaced = False
    updated: list[str] = []

    for line in lines:
        if line.strip().startswith(prefix):
            updated.append(f"{key}={value}")
            replaced = True
        else:
            updated.append(line)

    if not replaced:
        updated.append(f"{key}={value}")

    env_path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")


def _choose_policy(prompt_input: callable) -> PolicyProfile:
    print("Select default policy profile:")
    print("  1) strict (recommended)")
    print("  2) balanced")
    print("  3) developer")
    selection = (prompt_input("Choose [1-3] (default 1): ") or "1").strip()
    if selection == "2":
        return PolicyProfile.BALANCED
    if selection == "3":
        return PolicyProfile.DEVELOPER
    return PolicyProfile.STRICT


def _run_first_run_wizard(config: AppRuntimeConfig, force: bool = False) -> None:
    from dotenv import load_dotenv

    state = _load_json(DEFAULT_SETUP_STATE_PATH)
    if state.get("completed") and not force:
        return

    print("\nUltragravity first-run setup wizard")
    print("-" * 36)

    env_path = Path(".env")
    if not env_path.exists() and Path(".env.example").exists():
        shutil.copyfile(".env.example", ".env")
        print("Created .env from .env.example")

    gemini_value = (input("Gemini API key (leave blank to keep current): ") or "").strip()
    if gemini_value:
        _append_or_replace_env_var(env_path, "GEMINI_API_KEY", gemini_value)

    mistral_value = (input("Mistral API key (leave blank to keep current): ") or "").strip()
    if mistral_value:
        _append_or_replace_env_var(env_path, "MISTRAL_API_KEY", mistral_value)

    if gemini_value or mistral_value:
        load_dotenv(override=True)

    print("\nmacOS permissions checklist:")
    print("- Accessibility permission for terminal/IDE")
    print("- Screen Recording permission for screenshots")
    print("- Automation permission (when prompted)")
    _ = input("Press Enter after you have reviewed/granted permissions...")

    selected_profile = _choose_policy(input)

    memory_repo = SQLiteMemoryRepository(
        db_path=config.memory.sqlite_path,
        max_events=config.memory.max_events,
    )
    memory = MemoryManager(repository=memory_repo, retrieval_top_k=config.memory.retrieval_top_k)
    memory.set_preference("policy_profile", selected_profile.value)
    memory.set_preference("interaction_style", memory.get_preference("interaction_style", "concise") or "concise")

    _write_json(
        DEFAULT_SETUP_STATE_PATH,
        {
            "completed": True,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "policy_profile": selected_profile.value,
            "memory_backend": config.memory.backend,
        },
    )

    print(f"Setup complete. Default policy set to '{selected_profile.value}'.\n")


def _collect_approval_stats(audit_dir: Path) -> dict[str, int]:
    stats = {
        "prompted": 0,
        "approved": 0,
        "denied": 0,
    }
    if not audit_dir.exists():
        return stats

    for path in sorted(audit_dir.glob("actions-*.jsonl")):
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(raw_line)
            except Exception:
                continue

            if record.get("event_type") != "permission_outcome":
                continue

            stats["prompted"] += 1
            approved = bool(((record.get("permission") or {}).get("approved")))
            if approved:
                stats["approved"] += 1
            else:
                stats["denied"] += 1

    return stats


def _collect_telemetry_stats(telemetry_dir: Path) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    if not telemetry_dir.exists():
        return stats

    for path in sorted(telemetry_dir.glob("provider-*.jsonl")):
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(raw_line)
            except Exception:
                continue

            provider = str(record.get("provider") or "unknown")
            provider_stats = stats.setdefault(
                provider,
                {
                    "requests": 0,
                    "successes": 0,
                    "failures": 0,
                    "estimated_tokens": 0,
                    "actual_tokens": 0,
                },
            )
            provider_stats["requests"] += 1
            provider_stats["estimated_tokens"] += max(0, int(record.get("estimated_tokens") or 0))
            provider_stats["actual_tokens"] += max(0, int(record.get("actual_tokens") or 0))
            if bool(record.get("success")):
                provider_stats["successes"] += 1
            else:
                provider_stats["failures"] += 1

    return stats


def _print_status(config: AppRuntimeConfig) -> int:
    runtime = _load_json(DEFAULT_RUNTIME_STATUS_PATH)
    telemetry = _collect_telemetry_stats(DEFAULT_TELEMETRY_LOG_DIR)
    approvals = _collect_approval_stats(DEFAULT_AUDIT_LOG_DIR)

    mode = runtime.get("mode", "IDLE")
    queue_depth = int(runtime.get("queue_depth", 0))
    running = bool(runtime.get("running", False))

    print("Ultragravity Status")
    print("=" * 22)
    print(f"Runtime: {'RUNNING' if running else 'IDLE'}")
    print(f"Mode: {mode}")
    print(f"Queue depth: {queue_depth}")
    print(f"Policy profile: {runtime.get('policy_profile', 'strict')}")

    print("\nBudget & provider usage:")
    provider_configs = {
        "gemini": config.provider.gemini,
        "mistral": config.provider.mistral,
    }
    for provider_name, provider_cfg in provider_configs.items():
        usage = telemetry.get(provider_name, {})
        requests = int(usage.get("requests", 0))
        actual_tokens = int(usage.get("actual_tokens", 0))
        print(
            f"- {provider_name}: requests={requests}, actual_tokens={actual_tokens}, "
            f"soft_rpm={int(provider_cfg.rpm_limit * provider_cfg.soft_cap_ratio)}, "
            f"soft_tpm={int(provider_cfg.tpm_limit * provider_cfg.soft_cap_ratio)}"
        )

    print("\nApprovals:")
    print(
        f"- prompted={approvals['prompted']} approved={approvals['approved']} denied={approvals['denied']}"
    )
    return 0


def _print_logs(kind: str, lines: int) -> int:
    selected_paths: list[Path] = []

    if kind in {"audit", "all"}:
        selected_paths.extend(sorted(DEFAULT_AUDIT_LOG_DIR.glob("actions-*.jsonl")))
    if kind in {"telemetry", "all"}:
        selected_paths.extend(sorted(DEFAULT_TELEMETRY_LOG_DIR.glob("provider-*.jsonl")))

    if not selected_paths:
        print("No log files found.")
        return 0

    selected_paths = sorted(selected_paths, key=lambda p: p.stat().st_mtime)
    tail_lines: list[str] = []
    for path in selected_paths:
        file_lines = path.read_text(encoding="utf-8").splitlines()
        for line in file_lines:
            tail_lines.append(f"[{path.name}] {line}")

    for line in tail_lines[-max(1, lines):]:
        print(line)

    return 0


def _update_runtime_status(mode: str, running: bool, policy_profile: str) -> None:
    payload = _load_json(DEFAULT_RUNTIME_STATUS_PATH)
    payload.update(
        {
            "running": running,
            "mode": mode,
            "queue_depth": 0,
            "policy_profile": policy_profile,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if running:
        payload["started_at"] = payload.get("started_at") or datetime.now(timezone.utc).isoformat()
    else:
        payload["last_finished_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(DEFAULT_RUNTIME_STATUS_PATH, payload)


def _resolve_memory(config: AppRuntimeConfig) -> MemoryManager:
    repo = SQLiteMemoryRepository(
        db_path=config.memory.sqlite_path,
        max_events=config.memory.max_events,
    )
    return MemoryManager(repository=repo, retrieval_top_k=config.memory.retrieval_top_k)


def _run_agent(instruction: str, url: str | None, headless: bool, model: str | None, config_path: str, wizard: bool) -> int:
    # Load .env early so API keys are available for quick paths
    try:
        from dotenv import load_dotenv as _load
        _load()
    except ImportError:
        # dotenv not installed — parse .env manually
        import pathlib
        env_file = pathlib.Path(__file__).resolve().parent.parent / ".env"
        if env_file.is_file():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

    # Quick path for simple WhatsApp instructions:
    # avoids full browser/runtime startup and interactive checkpoints.
    if _is_quick_whatsapp_instruction(instruction):
        quick_result = _run_quick_whatsapp(instruction)
        if quick_result in {0, 1}:
            return quick_result

    # Quick path for simple Notes instructions.
    if _is_quick_note_instruction(instruction):
        quick_note_result = _run_quick_note(instruction)
        if quick_note_result in {0, 1}:
            return quick_note_result

    from agent.core import UltragravityAgent
    from dotenv import load_dotenv

    load_dotenv()
    config = load_runtime_config(config_path)
    configure_logging(config.app.log_level)

    if wizard:
        _run_first_run_wizard(config, force=True)
    else:
        _run_first_run_wizard(config, force=False)

    diagnostics = run_startup_diagnostics(config)
    if config.diagnostics.enabled and diagnostics["warnings"]:
        print("\nStartup diagnostics warnings:")
        for warning in diagnostics["warnings"]:
            print(f"  - {warning}")
        print("")

    memory = _resolve_memory(config)
    profile = (memory.get_preference("policy_profile", "strict") or "strict").strip().lower()

    effective_model = model or config.app.model_name
    effective_headless = bool(headless or config.app.headless)
    mode = _detect_mode(instruction)

    _update_runtime_status(mode=mode, running=True, policy_profile=profile)

    print("Starting Ultragravity with:")
    print(f"  URL: {url}")
    print(f"  Goal: {instruction}")
    print(f"  Headless: {effective_headless}")
    print(f"  Model: {effective_model}")
    print(f"  Config: {config_path}")

    try:
        agent = UltragravityAgent(headless=effective_headless, model_name=effective_model, runtime_config=config)
        agent.start_session(url, instruction)
    except Exception as exc:
        logging.critical(f"Fatal error: {exc}", exc_info=True)
        _update_runtime_status(mode=mode, running=False, policy_profile=profile)
        return 1

    _update_runtime_status(mode=mode, running=False, policy_profile=profile)
    return 0


def _handle_policy_command(set_profile: str | None, config_path: str) -> int:
    config = load_runtime_config(config_path)
    memory = _resolve_memory(config)

    if set_profile is None:
        current = memory.get_preference("policy_profile", "strict") or "strict"
        print(f"Current policy profile: {current}")
        print("Available profiles: strict, balanced, developer")
        return 0

    normalized = set_profile.strip().lower()
    try:
        profile = PolicyProfile(normalized)
    except Exception:
        print(f"Invalid policy profile: {set_profile}")
        print("Valid profiles: strict, balanced, developer")
        return 2

    memory.set_preference("policy_profile", profile.value)
    print(f"Policy profile updated to: {profile.value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ultragravity CLI")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to runtime config file")

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a full Ultragravity task")
    run_parser.add_argument("instruction", type=str, help="Instruction for the agent")
    run_parser.add_argument("--url", type=str, default=None, help="Starting URL")
    run_parser.add_argument("--headless", action="store_true", help="Run browser headless")
    run_parser.add_argument("--model", type=str, default=None, help="Override model name")
    run_parser.add_argument("--wizard", action="store_true", help="Force first-run setup wizard")

    ask_parser = subparsers.add_parser("ask", help="Run a task without providing a starting URL")
    ask_parser.add_argument("instruction", type=str, help="Instruction for the agent")
    ask_parser.add_argument("--headless", action="store_true", help="Run browser headless")
    ask_parser.add_argument("--model", type=str, default=None, help="Override model name")
    ask_parser.add_argument("--wizard", action="store_true", help="Force first-run setup wizard")

    policy_parser = subparsers.add_parser("policy", help="Show or update policy profile")
    policy_parser.add_argument("--set", dest="set_profile", type=str, default=None, help="Set profile: strict|balanced|developer")

    logs_parser = subparsers.add_parser("logs", help="Show recent audit/telemetry logs")
    logs_parser.add_argument("--kind", choices=["audit", "telemetry", "all"], default="all")
    logs_parser.add_argument("--lines", type=int, default=40)

    subparsers.add_parser("status", help="Show runtime status, budget usage, and approvals")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return _run_agent(
            instruction=args.instruction,
            url=args.url,
            headless=args.headless,
            model=args.model,
            config_path=args.config,
            wizard=args.wizard,
        )

    if args.command == "ask":
        return _run_agent(
            instruction=args.instruction,
            url=None,
            headless=args.headless,
            model=args.model,
            config_path=args.config,
            wizard=args.wizard,
        )

    if args.command == "policy":
        return _handle_policy_command(args.set_profile, args.config)

    if args.command == "logs":
        return _print_logs(args.kind, args.lines)

    if args.command == "status":
        config = load_runtime_config(args.config)
        return _print_status(config)

    parser.print_help()
    return 2


def legacy_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ultragravity legacy entrypoint")
    parser.add_argument("instruction", type=str, help="Instruction for the agent")
    parser.add_argument("--url", type=str, default=None, help="The URL to start browsing (optional)")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--model", type=str, default=None, help="Model override")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_PATH, help="Path to runtime config file")
    args = parser.parse_args(argv)

    return _run_agent(
        instruction=args.instruction,
        url=args.url,
        headless=args.headless,
        model=args.model,
        config_path=args.config,
        wizard=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
