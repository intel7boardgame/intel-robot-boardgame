"""대전 기록 (담당: 김관영)."""
import json
import sqlite3
from pathlib import Path

from common.interfaces import Event

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    turn INTEGER, player TEXT, kind TEXT, detail TEXT
)
"""


class SqliteStore:
    def __init__(self, path: Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute(SCHEMA)

    def save(self, event: Event) -> None:
        self.conn.execute(
            "INSERT INTO events (turn, player, kind, detail) VALUES (?, ?, ?, ?)",
            (event.turn, event.player, event.kind, json.dumps(event.detail, ensure_ascii=False)),
        )
        self.conn.commit()
