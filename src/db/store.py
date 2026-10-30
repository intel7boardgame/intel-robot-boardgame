"""대전 기록 (담당: 김관영).

SqliteStore를 만들 때 games에 새 판이 한 줄 생기고, save(event)마다
events(모든 이벤트 원본)와 turns(이동 결과)에 쌓입니다. win 이벤트가 오면 판을 마감합니다.
윷놀이(칸 이름 "cell_3", 윷 결과)와 주사위 게임(칸 번호, 주사위 눈)을 같은 표에 담습니다.
"""
import json
import sqlite3
from pathlib import Path

from common.interfaces import Event

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT DEFAULT (datetime('now', 'localtime')),
    ended_at TEXT,
    winner TEXT,              -- 'human' | 'robot', 끝나지 않은 판은 NULL
    total_turns INTEGER
);
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER REFERENCES games(id),
    turn INTEGER,
    player TEXT,
    piece INTEGER,            -- 움직인 말 번호 (윷놀이, 1부터)
    yut TEXT,                 -- '도' | '개' | '걸' | '윷' | '모' (윷놀이)
    dice INTEGER,             -- 이동 칸 수 (윷놀이: 도1~모5, 주사위 게임: 주사위 눈)
    from_pos TEXT,            -- 윷놀이: 'wait', 'cell_3', 'center' … / 주사위 게임: 칸 번호
    to_pos TEXT,              -- 윷놀이에서 완주는 'goal'
    stacked INTEGER,          -- 함께 움직인 말 수 (업힘이면 2)
    event_type TEXT,          -- 주사위 게임 이벤트 칸: 'forward' | 'back' | 'skip' | 'quiz' | NULL
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER REFERENCES games(id),
    turn INTEGER,
    player TEXT,
    kind TEXT,                -- 'throw' | 'move' | 'capture' | 'stack' | 'finish' | 'win' | 'help' | 'decision'
    detail TEXT,              -- JSON. 잡은 말 수는 kind='capture'의 json_extract(detail, '$.captured')
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
"""

TURN_KINDS = ("move", "win")
YUT_STEPS = {"도": 1, "개": 2, "걸": 3, "윷": 4, "모": 5}


class SqliteStore:
    def __init__(self, path: Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = Path(path)
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)
        self.game_id = self.conn.execute("INSERT INTO games DEFAULT VALUES").lastrowid
        self.conn.commit()

    def save(self, event: Event) -> None:
        d = event.detail
        self.conn.execute(
            "INSERT INTO events (game_id, turn, player, kind, detail) VALUES (?, ?, ?, ?, ?)",
            (self.game_id, event.turn, event.player, event.kind, json.dumps(d, ensure_ascii=False)),
        )
        if event.kind in TURN_KINDS and "to" in d:  # 윷놀이 win은 이동이 없음 (그 전 move에 기록됨)
            self.conn.execute(
                "INSERT INTO turns (game_id, turn, player, piece, yut, dice, from_pos, to_pos, stacked, event_type)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self.game_id, event.turn, event.player, d.get("piece"), d.get("yut"),
                 d.get("dice", YUT_STEPS.get(d.get("yut"))), d.get("from"), d.get("to"), d.get("stacked"),
                 (d.get("event") or {}).get("type")),
            )
        if event.kind == "win":
            self.conn.execute(
                "UPDATE games SET ended_at = datetime('now', 'localtime'), winner = ?, total_turns = ?"
                " WHERE id = ?",
                (event.player, event.turn, self.game_id),
            )
        self.conn.commit()

    # 기록 조회 (확장: 화면 결과 표시, 기록 질의 챗봇에서 사용)

    def win_rate(self, player: str = "robot", day: str | None = None) -> dict:
        """끝난 판 기준 승률. day='2026-11-03'처럼 주면 그날만 셉니다."""
        sql = "SELECT COUNT(*), SUM(winner = ?) FROM games WHERE winner IS NOT NULL"
        args: list = [player]
        if day:
            sql += " AND date(started_at) = ?"
            args.append(day)
        games, wins = self.conn.execute(sql, args).fetchone()
        wins = wins or 0
        return {"games": games, "wins": wins, "rate": wins / games if games else 0.0}

    def recent_games(self, limit: int = 5) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, started_at, winner, total_turns FROM games WHERE winner IS NOT NULL"
            " ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(zip(("id", "started_at", "winner", "total_turns"), r)) for r in rows]

    def close(self) -> None:
        self.conn.close()
