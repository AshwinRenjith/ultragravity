from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from .migrations import MIGRATIONS
from .models import MemoryEvent


class SQLiteMemoryRepository:
    def __init__(self, db_path: str = "data/ultragravity_memory.db", max_events: int = 5000):
        self.db_path = Path(db_path)
        self.max_events = max(100, max_events)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row

    def initialize(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            for version, sql in MIGRATIONS:
                already = self._connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = ?",
                    (version,),
                ).fetchone()
                if already:
                    continue
                self._connection.executescript(sql)
                self._connection.execute(
                    "INSERT INTO schema_migrations(version) VALUES (?)",
                    (version,),
                )

    def _row_to_event(self, row: sqlite3.Row) -> MemoryEvent:
        metadata_json = row["metadata_json"]
        try:
            metadata = json.loads(metadata_json) if metadata_json else {}
        except Exception:
            metadata = {}
        return MemoryEvent(
            id=int(row["id"]),
            session_id=str(row["session_id"]),
            kind=str(row["kind"]),
            content=str(row["content"]),
            metadata=metadata,
            created_at=str(row["created_at"]),
        )

    def _trim_events_if_needed(self) -> None:
        row = self._connection.execute("SELECT COUNT(1) as count FROM memory_events").fetchone()
        if not row:
            return
        total = int(row["count"])
        if total <= self.max_events:
            return

        to_delete = total - self.max_events
        with self._connection:
            self._connection.execute(
                """
                DELETE FROM memory_events
                WHERE id IN (
                    SELECT id FROM memory_events
                    ORDER BY created_at ASC, id ASC
                    LIMIT ?
                )
                """,
                (to_delete,),
            )

    def add_event(self, session_id: str, kind: str, content: str, metadata: dict[str, object]) -> int:
        with self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO memory_events(session_id, kind, content, metadata_json)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, kind, content, json.dumps(metadata, ensure_ascii=False)),
            )
            event_id = int(cursor.lastrowid)
        self._trim_events_if_needed()
        return event_id

    def list_recent_events(self, limit: int) -> list[MemoryEvent]:
        rows = self._connection.execute(
            """
            SELECT id, session_id, kind, content, metadata_json, created_at
            FROM memory_events
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (max(1, limit),),
        ).fetchall()
        return [self._row_to_event(row) for row in rows]

    @staticmethod
    def _keywords(text: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z0-9]{3,}", text.lower()))

    def search_relevant_events(self, query: str, top_k: int, candidate_limit: int = 200) -> list[MemoryEvent]:
        rows = self._connection.execute(
            """
            SELECT id, session_id, kind, content, metadata_json, created_at
            FROM memory_events
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (max(1, candidate_limit),),
        ).fetchall()

        query_keywords = self._keywords(query)
        if not query_keywords:
            query_keywords = {"task"}

        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            content = str(row["content"]).lower()
            hits = sum(1 for key in query_keywords if key in content)
            if hits == 0:
                continue

            kind = str(row["kind"]).lower()
            kind_boost = 0.2 if kind in {"preference", "summary"} else 0.0
            score = float(hits) + kind_boost
            scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [self._row_to_event(row) for _, row in scored[: max(1, top_k)]]

    def set_preference(self, key: str, value: str) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO preferences(key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key)
                DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )

    def get_preference(self, key: str) -> str | None:
        row = self._connection.execute(
            "SELECT value FROM preferences WHERE key = ?",
            (key,),
        ).fetchone()
        if not row:
            return None
        return str(row["value"])

    def save_execution_snapshot(self, plan_id: str, payload_json: str) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO execution_snapshots(plan_id, payload_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(plan_id)
                DO UPDATE SET payload_json = excluded.payload_json, updated_at = CURRENT_TIMESTAMP
                """,
                (plan_id, payload_json),
            )

    def load_execution_snapshot(self, plan_id: str) -> str | None:
        row = self._connection.execute(
            "SELECT payload_json FROM execution_snapshots WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()
        if not row:
            return None
        return str(row["payload_json"])
