from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import AppRuntimeConfig

_PLACEHOLDER_PREFIXES = {
    "your_",
    "replace_",
    "example_",
}


def _is_placeholder_secret(value: str | None) -> bool:
    if not value:
        return False

    normalized = value.strip().lower()
    return any(normalized.startswith(prefix) for prefix in _PLACEHOLDER_PREFIXES)


def run_startup_diagnostics(config: AppRuntimeConfig, env_path: str | Path = ".env") -> dict[str, Any]:
    warnings: list[str] = []
    checks: dict[str, bool] = {}

    env_file = Path(env_path)
    checks["env_file_present"] = env_file.exists()

    gemini_key = os.getenv("GEMINI_API_KEY")
    mistral_key = os.getenv("MISTRAL_API_KEY")

    has_provider_key = bool(gemini_key or mistral_key)
    checks["provider_key_present"] = has_provider_key

    if config.security.require_env_file and not env_file.exists():
        warnings.append(".env file not found. Create it from .env.example before running production workflows.")

    if config.security.fail_if_no_provider_key and not has_provider_key:
        warnings.append("No provider API key found. Set GEMINI_API_KEY or MISTRAL_API_KEY in your environment.")

    if config.diagnostics.warn_on_default_secrets:
        if _is_placeholder_secret(gemini_key):
            warnings.append("GEMINI_API_KEY appears to be a placeholder value.")
        if _is_placeholder_secret(mistral_key):
            warnings.append("MISTRAL_API_KEY appears to be a placeholder value.")

    return {
        "checks": checks,
        "warnings": warnings,
        "ok": len(warnings) == 0,
    }
