from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    def __init__(self, log_dir: str | Path = "logs/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _log_path(self) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        return self.log_dir / f"actions-{stamp}.jsonl"

    def write_event(self, event_type: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **payload,
        }
        with self._log_path().open("a", encoding="utf-8") as output:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
