"""
Conversation session management — SQLite backed.
One session per browser visit; tracks skill, answers, and chat history.
"""

import json
import os
import sqlite3
import time
import uuid
from typing import Any, Optional

DB_PATH = os.getenv("ASSESS_DB_PATH", os.path.join(
    os.path.dirname(__file__), "..", "leads.db"))

_DDL = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id           TEXT PRIMARY KEY,
    created_at   INTEGER NOT NULL,
    updated_at   INTEGER NOT NULL,
    skill_id     TEXT,
    phase        TEXT NOT NULL DEFAULT 'welcome',
    state        TEXT NOT NULL DEFAULT '{}'
);
"""


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_sessions_db() -> None:
    with _conn() as c:
        c.executescript(_DDL)


def create_session() -> str:
    init_sessions_db()
    sid = str(uuid.uuid4())
    now = int(time.time())
    with _conn() as c:
        c.execute(
            "INSERT INTO chat_sessions (id, created_at, updated_at, phase, state) VALUES (?,?,?,'welcome','{}')",
            (sid, now, now),
        )
    return sid


def get_session(sid: str) -> Optional[dict]:
    init_sessions_db()
    with _conn() as c:
        row = c.execute("SELECT * FROM chat_sessions WHERE id=?", (sid,)).fetchone()
    if not row:
        return None
    return {
        "id":         row["id"],
        "skill_id":   row["skill_id"],
        "phase":      row["phase"],
        "state":      json.loads(row["state"]),
        "created_at": row["created_at"],
    }


def save_session(sid: str, skill_id: Optional[str], phase: str, state: dict) -> None:
    init_sessions_db()
    with _conn() as c:
        c.execute(
            "UPDATE chat_sessions SET skill_id=?, phase=?, state=?, updated_at=? WHERE id=?",
            (skill_id, phase, json.dumps(state), int(time.time()), sid),
        )


def update_state(sid: str, updates: dict) -> dict:
    """Merge updates into the session state dict and persist."""
    sess = get_session(sid)
    if not sess:
        raise KeyError(f"Session {sid} not found")
    new_state = {**sess["state"], **updates}
    save_session(sid, sess["skill_id"], sess["phase"], new_state)
    return new_state
