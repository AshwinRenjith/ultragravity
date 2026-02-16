from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    log_level: str = "INFO"
    model_name: str = "gemini-2.5-flash"
    headless: bool = False


class SecurityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    require_env_file: bool = True
    fail_if_no_provider_key: bool = True


class DiagnosticsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    warn_on_default_secrets: bool = True


class ProviderLimitsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rpm_limit: int = 10
    tpm_limit: int = 12000
    daily_request_limit: int = 500
    soft_cap_ratio: float = 0.6


class SchedulerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_retries: int = 3
    base_backoff_seconds: float = 2.0
    max_backoff_seconds: float = 20.0
    jitter_seconds: float = 0.4


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: str = "free_tier_ultra_safe"
    gemini: ProviderLimitsConfig = Field(default_factory=ProviderLimitsConfig)
    mistral: ProviderLimitsConfig = Field(default_factory=ProviderLimitsConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)


class CacheConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ttl_seconds: int = 300
    max_entries: int = 1000


class CallReductionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    state_change_threshold: int = 5
    enable_deterministic_router: bool = True
    vision_cache: CacheConfig = Field(default_factory=lambda: CacheConfig(ttl_seconds=300, max_entries=1000))
    summary_cache: CacheConfig = Field(default_factory=lambda: CacheConfig(ttl_seconds=3600, max_entries=300))
    tool_cache: CacheConfig = Field(default_factory=lambda: CacheConfig(ttl_seconds=300, max_entries=500))


class PromptOptimizationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    debug_reasoning: bool = False
    max_output_tokens_action: int = 220
    max_output_tokens_summary_chunk: int = 220
    max_output_tokens_summary_merge: int = 420
    summary_chunk_chars: int = 3500
    summary_overlap_chars: int = 250
    summary_top_k_chunks: int = 6


class PlannerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    max_iterations: int = 20
    retry_attempts: int = 2
    retry_backoff_seconds: float = 1.0


class MemoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    backend: str = "sqlite"
    sqlite_path: str = "data/ultragravity_memory.db"
    max_events: int = 5000
    retrieval_top_k: int = 5


class AppRuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app: AppConfig = Field(default_factory=AppConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    diagnostics: DiagnosticsConfig = Field(default_factory=DiagnosticsConfig)
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    call_reduction: CallReductionConfig = Field(default_factory=CallReductionConfig)
    prompt_optimization: PromptOptimizationConfig = Field(default_factory=PromptOptimizationConfig)
    planner: PlannerConfig = Field(default_factory=PlannerConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)


def _load_yaml_dict(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a top-level mapping: {config_path}")

    return data


def load_runtime_config(config_path: str | Path = "ultragravity.config.yaml") -> AppRuntimeConfig:
    path = Path(config_path)
    raw = _load_yaml_dict(path)
    try:
        return AppRuntimeConfig.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid config at {path}: {exc}") from exc
