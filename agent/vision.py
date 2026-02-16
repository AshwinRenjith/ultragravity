import base64
import json
import os
import time
import warnings
from typing import Any

import PIL
import google.generativeai as genai
from dotenv import load_dotenv

from ultragravity.budget import BudgetManager, ProviderBudgetLimits
from ultragravity.call_reduction import (
    DeterministicRouter,
    StateChangeDetector,
    TTLCache,
    build_summary_cache_key,
    build_vision_cache_key,
)
from ultragravity.config import AppRuntimeConfig, load_runtime_config
from ultragravity.context_shaper import ContextShaper
from ultragravity.prompt_library import PromptLibrary
from ultragravity.scheduler import ProviderCallRequest, ProviderScheduler
from ultragravity.telemetry import ProviderTelemetry

# Mistral imports
try:
    from mistralai import Mistral
except ImportError:
    Mistral = None

# Suppress the FutureWarning from google.generativeai
warnings.filterwarnings("ignore", category=FutureWarning)

load_dotenv()

class VisionAgent:
    def __init__(self, model_name: str = "gemini-2.5-flash", runtime_config: AppRuntimeConfig | None = None):
        self.gemini_available = False
        self.mistral_available = False
        self.model_name = model_name

        config_path = os.getenv("ULTRAGRAVITY_CONFIG_PATH", "ultragravity.config.yaml")
        self.runtime_config = runtime_config or load_runtime_config(config_path)

        self.telemetry = ProviderTelemetry()
        self.budget_manager = BudgetManager(
            limits_by_provider={
                "gemini": ProviderBudgetLimits(
                    rpm_limit=self.runtime_config.provider.gemini.rpm_limit,
                    tpm_limit=self.runtime_config.provider.gemini.tpm_limit,
                    daily_request_limit=self.runtime_config.provider.gemini.daily_request_limit,
                    soft_cap_ratio=self.runtime_config.provider.gemini.soft_cap_ratio,
                ),
                "mistral": ProviderBudgetLimits(
                    rpm_limit=self.runtime_config.provider.mistral.rpm_limit,
                    tpm_limit=self.runtime_config.provider.mistral.tpm_limit,
                    daily_request_limit=self.runtime_config.provider.mistral.daily_request_limit,
                    soft_cap_ratio=self.runtime_config.provider.mistral.soft_cap_ratio,
                ),
            },
            clock=time.time,
        )
        self.scheduler = ProviderScheduler(
            budget_manager=self.budget_manager,
            telemetry=self.telemetry,
            sleep_fn=time.sleep,
        )
        self.scheduler_config = self.runtime_config.provider.scheduler
        self.call_reduction_config = self.runtime_config.call_reduction
        self.prompt_config = self.runtime_config.prompt_optimization

        self.state_detector = StateChangeDetector(
            image_distance_threshold=self.call_reduction_config.state_change_threshold,
        )
        self.router = DeterministicRouter()
        self.context_shaper = ContextShaper()
        self.prompts = PromptLibrary(debug_reasoning=self.prompt_config.debug_reasoning)
        self.vision_cache = TTLCache(
            ttl_seconds=self.call_reduction_config.vision_cache.ttl_seconds,
            max_entries=self.call_reduction_config.vision_cache.max_entries,
        )
        self.summary_cache = TTLCache(
            ttl_seconds=self.call_reduction_config.summary_cache.ttl_seconds,
            max_entries=self.call_reduction_config.summary_cache.max_entries,
        )
        self.last_action: str | None = None
        self.call_reduction_stats = {
            "vision_cache_hits": 0,
            "summary_cache_hits": 0,
            "deterministic_shortcuts": 0,
            "state_unchanged_shortcuts": 0,
            "hierarchical_summary_chunks": 0,
        }
        
        # Initialize Gemini
        if "GEMINI_API_KEY" in os.environ:
            genai.configure(api_key=os.environ["GEMINI_API_KEY"])
            self.model = genai.GenerativeModel(model_name)
            self.gemini_available = True
        
        # Initialize Mistral
        if "MISTRAL_API_KEY" in os.environ and Mistral:
            self.mistral_client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
            self.mistral_available = True
            self.pixtral_model = "pixtral-12b-2409"
            self.mistral_text_model = "mistral-large-latest"
        elif "MISTRAL_API_KEY" in os.environ and not Mistral:
            print("⚠️ MISTRAL_API_KEY found but 'mistralai' package not installed.")

        if not self.gemini_available and not self.mistral_available:
             raise ValueError("Neither GEMINI_API_KEY nor MISTRAL_API_KEY found.")

    def _provider_enabled(self, provider: str) -> bool:
        if provider == "gemini":
            return self.gemini_available
        if provider == "mistral":
            return self.mistral_available
        return False

    @staticmethod
    def _estimate_tokens(prompt: str, image_path: str | None = None) -> int:
        prompt_tokens = max(50, len(prompt) // 4)
        image_tokens = 0
        if image_path and os.path.exists(image_path):
            image_bytes = os.path.getsize(image_path)
            image_tokens = max(200, int(image_bytes / 350))
        return prompt_tokens + image_tokens

    @staticmethod
    def _extract_gemini_tokens(response) -> int | None:
        usage = getattr(response, "usage_metadata", None)
        if not usage:
            return None

        total = getattr(usage, "total_token_count", None)
        if total:
            return int(total)

        prompt = getattr(usage, "prompt_token_count", 0) or 0
        candidates = getattr(usage, "candidates_token_count", 0) or 0
        combined = int(prompt) + int(candidates)
        return combined if combined > 0 else None

    @staticmethod
    def _extract_mistral_tokens(response) -> int | None:
        usage = getattr(response, "usage", None)
        if not usage:
            return None
        total = getattr(usage, "total_tokens", None)
        return int(total) if total else None

    def _schedule_call(
        self,
        provider: str,
        model: str,
        operation: str,
        estimated_tokens: int,
        call,
        token_extractor,
    ):
        request = ProviderCallRequest(
            provider=provider,
            model=model,
            operation=operation,
            estimated_tokens=estimated_tokens,
            call=call,
            extract_actual_tokens=token_extractor,
            max_retries=self.scheduler_config.max_retries,
            base_backoff_seconds=self.scheduler_config.base_backoff_seconds,
            max_backoff_seconds=self.scheduler_config.max_backoff_seconds,
            jitter_seconds=self.scheduler_config.jitter_seconds,
        )
        return self.scheduler.execute(request)

    def _generate_text_with_fallback(
        self,
        operation: str,
        prompt: str,
        max_output_tokens: int,
    ) -> tuple[str | None, list[str]]:
        estimated_tokens = self._estimate_tokens(prompt)
        errors: list[str] = []

        if self._provider_enabled("gemini"):
            gemini_result = self._schedule_call(
                provider="gemini",
                model=self.model_name,
                operation=operation,
                estimated_tokens=estimated_tokens,
                call=lambda: self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": max_output_tokens,
                    },
                ),
                token_extractor=self._extract_gemini_tokens,
            )
            if gemini_result.success and gemini_result.result is not None:
                return str(gemini_result.result.text), errors
            errors.append(f"Gemini: {gemini_result.error}")

        if self._provider_enabled("mistral"):
            mistral_result = self._schedule_call(
                provider="mistral",
                model=self.mistral_text_model,
                operation=operation,
                estimated_tokens=estimated_tokens,
                call=lambda: self.mistral_client.chat.complete(
                    model=self.mistral_text_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_output_tokens,
                    temperature=0.1,
                ),
                token_extractor=self._extract_mistral_tokens,
            )
            if mistral_result.success and mistral_result.result is not None and mistral_result.result.choices:
                return str(mistral_result.result.choices[0].message.content), errors
            errors.append(f"Mistral: {mistral_result.error}")

        return None, errors

    def _normalize_action_plan(self, candidate: dict[str, Any]) -> dict[str, Any]:
        allowed_actions = {"click", "type", "scroll", "wait", "done", "fail"}
        action = str(candidate.get("action", "wait")).lower()
        if action not in allowed_actions:
            action = "wait"

        target = candidate.get("target_element") if isinstance(candidate.get("target_element"), dict) else {}
        description = str(target.get("description", ""))[:180]

        raw_coords = target.get("coordinates") if isinstance(target, dict) else None
        coords: list[int] = []
        if isinstance(raw_coords, list) and len(raw_coords) >= 2:
            try:
                coords = [int(raw_coords[0]), int(raw_coords[1])]
            except Exception:
                coords = []

        if action in {"wait", "done", "fail", "scroll"}:
            coords = []

        value = candidate.get("value", "")
        value_text = str(value)[:500]
        reasoning = str(candidate.get("reasoning", ""))[:240]
        if not self.prompt_config.debug_reasoning:
            reasoning = ""

        return {
            "action": action,
            "target_element": {
                "description": description,
                "coordinates": coords,
            },
            "value": value_text,
            "reasoning": reasoning,
        }

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def analyze_image(
        self,
        image_path: str,
        instruction: str,
        mode: str = "BROWSER",
        current_url: str = "",
        external_state_changed: bool = False,
        memory_hints: list[str] | None = None,
        wait_streak: int = 0,
    ) -> dict[str, Any]:
        """Analyze screenshot and return a strict action plan."""
        if not os.path.exists(image_path):
            return {"action": "fail", "reasoning": f"Screenshot not found at {image_path}"}

        snapshot = self.state_detector.inspect(
            image_path=image_path,
            mode=mode,
            url=current_url,
            external_signal_changed=external_state_changed,
        )

        delta_context = self.context_shaper.build_delta_context(
            state_changed=snapshot.changed,
            changed_by_url=snapshot.changed_by_url,
            changed_by_image=snapshot.changed_by_image,
            last_action=self.last_action,
            current_url=current_url,
            memory_hints=memory_hints,
        )

        prompt_text = self.prompts.build_action_prompt(
            goal=instruction,
            mode=mode,
            delta_context=delta_context,
        )

        allow_wait_shortcuts = wait_streak < 2

        if self.call_reduction_config.enabled and self.call_reduction_config.enable_deterministic_router and allow_wait_shortcuts:
            deterministic_plan = self.router.route(
                instruction=instruction,
                mode=mode,
                state_changed=snapshot.changed,
                last_action=self.last_action,
                current_url=current_url,
            )
            if deterministic_plan:
                self.call_reduction_stats["deterministic_shortcuts"] += 1
                if not snapshot.changed:
                    self.call_reduction_stats["state_unchanged_shortcuts"] += 1
                normalized = self._normalize_action_plan(deterministic_plan)
                self.last_action = normalized.get("action")
                return normalized

        cache_key = build_vision_cache_key(instruction, snapshot)
        if self.call_reduction_config.enabled:
            cached_action_plan = self.vision_cache.get(cache_key)
            if cached_action_plan is not None:
                cached_action = str(cached_action_plan.get("action", "")).lower()
                if not (wait_streak >= 2 and cached_action == "wait"):
                    self.call_reduction_stats["vision_cache_hits"] += 1
                    self.last_action = cached_action_plan.get("action")
                    return cached_action_plan

        estimated_tokens = self._estimate_tokens(prompt_text, image_path)
        errors: list[str] = []

        if self._provider_enabled("gemini"):
            img = PIL.Image.open(image_path)
            gemini_result = self._schedule_call(
                provider="gemini",
                model=self.model_name,
                operation="analyze_image",
                estimated_tokens=estimated_tokens,
                call=lambda: self.model.generate_content(
                    [prompt_text, img],
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": self.prompt_config.max_output_tokens_action,
                    },
                ),
                token_extractor=self._extract_gemini_tokens,
            )
            if gemini_result.success and gemini_result.result is not None:
                parsed = self._normalize_action_plan(self._parse_json(gemini_result.result.text))
                self.last_action = parsed.get("action")
                if self.call_reduction_config.enabled:
                    self.vision_cache.set(cache_key, parsed)
                return parsed
            errors.append(f"Gemini: {gemini_result.error}")

        if self._provider_enabled("mistral"):
            base64_img = self._encode_image(image_path)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_img}"}
                    ]
                }
            ]
            mistral_result = self._schedule_call(
                provider="mistral",
                model=self.pixtral_model,
                operation="analyze_image",
                estimated_tokens=estimated_tokens,
                call=lambda: self.mistral_client.chat.complete(
                    model=self.pixtral_model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=self.prompt_config.max_output_tokens_action,
                    temperature=0.1,
                ),
                token_extractor=self._extract_mistral_tokens,
            )
            if mistral_result.success and mistral_result.result is not None and mistral_result.result.choices:
                parsed = self._normalize_action_plan(self._parse_json(mistral_result.result.choices[0].message.content))
                self.last_action = parsed.get("action")
                if self.call_reduction_config.enabled:
                    self.vision_cache.set(cache_key, parsed)
                return parsed
            errors.append(f"Mistral: {mistral_result.error}")

        failed_response = {"action": "fail", "reasoning": "All vision providers exhausted", "errors": errors}
        self.last_action = "fail"
        return failed_response

    def summarize_content(self, content: str, instruction: str) -> str:
        """Hierarchical summarization with chunk ranking and compact prompts."""

        cache_key = build_summary_cache_key(content, instruction)
        if self.call_reduction_config.enabled:
            cached_summary = self.summary_cache.get(cache_key)
            if cached_summary is not None:
                self.call_reduction_stats["summary_cache_hits"] += 1
                return cached_summary

        chunks = self.context_shaper.chunk_text(
            content,
            chunk_chars=self.prompt_config.summary_chunk_chars,
            overlap_chars=self.prompt_config.summary_overlap_chars,
        )

        if not chunks:
            return "No content available to summarize."

        ranked = self.context_shaper.rank_chunks(
            chunks,
            query=instruction,
            top_k=self.prompt_config.summary_top_k_chunks,
        )
        self.call_reduction_stats["hierarchical_summary_chunks"] = len(ranked)

        chunk_summaries: list[str] = []
        total_chunks = len(chunks)

        for ranked_chunk in ranked:
            map_prompt = self.prompts.build_chunk_summary_prompt(
                goal=instruction,
                chunk=ranked_chunk.text,
                chunk_index=ranked_chunk.index,
                total_chunks=total_chunks,
            )
            map_summary, map_errors = self._generate_text_with_fallback(
                operation="summarize_chunk",
                prompt=map_prompt,
                max_output_tokens=self.prompt_config.max_output_tokens_summary_chunk,
            )
            if map_summary:
                chunk_summaries.append(map_summary)
            elif map_errors:
                chunk_summaries.append(f"[chunk-{ranked_chunk.index+1} unavailable: {map_errors}]")

        if not chunk_summaries:
            return "Failed to summarize chunks from all providers."

        merge_prompt = self.prompts.build_merge_summary_prompt(
            goal=instruction,
            chunk_summaries=chunk_summaries,
        )
        merged_summary, merge_errors = self._generate_text_with_fallback(
            operation="summarize_merge",
            prompt=merge_prompt,
            max_output_tokens=self.prompt_config.max_output_tokens_summary_merge,
        )

        if merged_summary is None:
            return f"Failed to merge summary from all providers. Errors: {merge_errors}"

        if self.call_reduction_config.enabled:
            self.summary_cache.set(cache_key, merged_summary)
        return merged_summary

    def _parse_json(self, text: str) -> dict[str, Any]:
        try:
            text = text.strip()
            # Cleanup code blocks
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])
            return json.loads(text)
        except Exception:
            # Simple retry/repair or fail
            return {"action": "wait", "reasoning": "Invalid JSON response"}
