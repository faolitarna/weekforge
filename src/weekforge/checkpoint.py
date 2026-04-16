import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel


@dataclass
class CheckpointRecord:
    thread_id: str
    workflow: str
    step: str
    state_json: str
    updated_at: str


class CheckpointStore:
    def __init__(self, db_path: str = ".weekforge/checkpoints.sqlite") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id  TEXT PRIMARY KEY,
                workflow   TEXT NOT NULL,
                step       TEXT NOT NULL,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def save(self, thread_id: str, workflow: str, step: str, state: BaseModel) -> None:
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO checkpoints (thread_id, workflow, step, state_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(thread_id) DO UPDATE SET
                workflow=excluded.workflow,
                step=excluded.step,
                state_json=excluded.state_json,
                updated_at=excluded.updated_at
            """,
            (thread_id, workflow, step, state.model_dump_json(), now),
        )
        self._conn.commit()

    def load(self, thread_id: str) -> CheckpointRecord | None:
        row = self._conn.execute(
            "SELECT thread_id, workflow, step, state_json, updated_at FROM checkpoints WHERE thread_id = ?",
            (thread_id,),
        ).fetchone()
        if row is None:
            return None
        return CheckpointRecord(*row)

    def list_active(self) -> list[CheckpointRecord]:
        rows = self._conn.execute(
            "SELECT thread_id, workflow, step, state_json, updated_at FROM checkpoints ORDER BY updated_at DESC"
        ).fetchall()
        return [CheckpointRecord(*row) for row in rows]

    def delete(self, thread_id: str) -> None:
        self._conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        self._conn.commit()
