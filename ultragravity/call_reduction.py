from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

from PIL import Image


class TTLCache:
    def __init__(self, ttl_seconds: int, max_entries: int):
        self.ttl_seconds = max(1, ttl_seconds)
        self.max_entries = max(1, max_entries)
        self._store: dict[str, tuple[float, Any]] = {}

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [key for key, (expires_at, _) in self._store.items() if expires_at <= now]
        for key in expired:
            del self._store[key]

    def get(self, key: str) -> Any | None:
        self._purge_expired()
        item = self._store.get(key)
        if not item:
            return None
        _, value = item
        return value

    def set(self, key: str, value: Any) -> None:
        self._purge_expired()
        if key in self._store:
            del self._store[key]
        elif len(self._store) >= self.max_entries:
            oldest_key = min(self._store, key=lambda k: self._store[k][0])
            del self._store[oldest_key]

        self._store[key] = (time.time() + self.ttl_seconds, value)

    def stats(self) -> dict[str, int]:
        self._purge_expired()
        return {"entries": len(self._store), "max_entries": self.max_entries}


@dataclass(frozen=True)
class StateSnapshot:
    image_hash: str
    mode: str
    url: str
    changed: bool
    changed_by_url: bool
    changed_by_image: bool
    changed_by_signal: bool


class StateChangeDetector:
    def __init__(self, image_distance_threshold: int = 5):
        self.image_distance_threshold = max(0, image_distance_threshold)
        self._last_by_mode: dict[str, tuple[int, str]] = {}

    @staticmethod
    def _dhash(image_path: str) -> int:
        image = Image.open(image_path).convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        pixels = list(image.getdata())
        bits = []
        for row in range(8):
            row_start = row * 9
            for col in range(8):
                left = pixels[row_start + col]
                right = pixels[row_start + col + 1]
                bits.append(1 if left > right else 0)

        value = 0
        for bit in bits:
            value = (value << 1) | bit
        return value

    @staticmethod
    def _hamming_distance(a: int, b: int) -> int:
        return (a ^ b).bit_count()

    @staticmethod
    def _hash_string(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    def inspect(self, image_path: str, mode: str, url: str = "", external_signal_changed: bool = False) -> StateSnapshot:
        current_hash_int = self._dhash(image_path)
        last = self._last_by_mode.get(mode)

        changed_by_image = True
        changed_by_url = True
        if last:
            last_hash_int, last_url = last
            image_distance = self._hamming_distance(last_hash_int, current_hash_int)
            changed_by_image = image_distance > self.image_distance_threshold
            changed_by_url = url != last_url

        changed = changed_by_image or changed_by_url or external_signal_changed or last is None

        self._last_by_mode[mode] = (current_hash_int, url)

        cacheable_hash = self._hash_string(f"{mode}:{url}:{current_hash_int}")
        return StateSnapshot(
            image_hash=cacheable_hash,
            mode=mode,
            url=url,
            changed=changed,
            changed_by_url=changed_by_url if last else True,
            changed_by_image=changed_by_image if last else True,
            changed_by_signal=external_signal_changed,
        )


class DeterministicRouter:
    def route(
        self,
        instruction: str,
        mode: str,
        state_changed: bool,
        last_action: str | None,
        current_url: str = "",
    ) -> dict[str, Any] | None:
        lowered = instruction.lower()

        if "wait" in lowered and "do not" not in lowered:
            return {
                "action": "wait",
                "reasoning": "Instruction explicitly requests waiting.",
                "source": "deterministic_router",
            }

        if not state_changed and last_action in {"click", "type", "scroll"}:
            return {
                "action": "wait",
                "reasoning": "State unchanged after recent interactive action. Waiting to avoid redundant multimodal call.",
                "source": "deterministic_router",
            }

        return None


def normalize_instruction(instruction: str) -> str:
    return " ".join(instruction.lower().strip().split())


def build_vision_cache_key(instruction: str, snapshot: StateSnapshot) -> str:
    payload = {
        "instruction": normalize_instruction(instruction),
        "mode": snapshot.mode,
        "url": snapshot.url,
        "image_hash": snapshot.image_hash,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def build_summary_cache_key(content: str, instruction: str) -> str:
    payload = {
        "instruction": normalize_instruction(instruction),
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def build_tool_cache_key(tool_name: str, operation: str, payload: dict[str, Any]) -> str:
    normalized_payload = json.dumps(payload, sort_keys=True, default=str)
    base = f"{tool_name}:{operation}:{normalized_payload}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
