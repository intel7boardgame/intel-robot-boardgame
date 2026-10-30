"""기록 질의 챗봇 (담당: 김관영, 확장). "오늘 로봇 승률은?" 같은 질문에 답합니다.

LLM이 SELECT 문 하나를 만들고(Text-to-SQL), 읽기 전용 연결로 실행한 뒤 결과를 문장으로 바꿉니다.
LLM이 없거나 SQL이 잘못되면 자주 묻는 질문(승률, 최근 경기)만 정해진 쿼리로 답합니다.
"""
import re
import sqlite3
from pathlib import Path

from db.store import SCHEMA
from llm.narrator import DEFAULT_MODEL, TIMEOUT, _make_client

SQL_PROMPT = (
    "아래 SQLite 스키마로 질문에 답하는 SELECT 문 하나만 써. 설명 없이 SQL만.\n"
    "player, winner 값은 'human'(사람) 또는 'robot'(로봇)이고, 날짜는 started_at(로컬 시각 문자열)이야. "
    "오늘은 date('now','localtime')로 비교해. 윷 결과는 turns.yut('도','개','걸','윷','모')이고, "
    "잡기는 events에서 kind='capture', 업기는 kind='stack'으로 세.\n{schema}\n질문: {question}"
)
ANSWER_PROMPT = (
    "질문: {question}\nSQL 결과: {rows}\n"
    "이 결과만 보고 한국어 한두 문장으로 답해. 숫자는 결과 그대로 써."
)
MAX_ROWS = 20


class StatsBot:
    def __init__(self, db_path: Path, model: str = DEFAULT_MODEL, client=None, use_llm: bool = True):
        self.db_path = Path(db_path)
        self.model = model
        self.client = client if client is not None else (_make_client(None, TIMEOUT * 2) if use_llm else None)

    def answer(self, question: str) -> str:
        if self.client is not None:
            try:
                sql = self._to_sql(question)
                rows = self.query(sql)
                return self._chat(ANSWER_PROMPT.format(question=question, rows=rows))
            except Exception:
                pass
        return self._fallback(question)

    def query(self, sql: str) -> list[tuple]:
        """SELECT 한 문장만, 읽기 전용으로 실행합니다."""
        sql = sql.strip().rstrip(";").strip()
        if not re.match(r"(?is)^(select|with)\b", sql) or ";" in sql:
            raise ValueError(f"SELECT 문만 실행합니다: {sql}")
        conn = sqlite3.connect(f"file:{self.db_path.as_posix()}?mode=ro", uri=True)
        try:
            return conn.execute(sql).fetchmany(MAX_ROWS)
        finally:
            conn.close()

    def _to_sql(self, question: str) -> str:
        text = self._chat(SQL_PROMPT.format(schema=SCHEMA, question=question))
        match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S)
        return match.group(1) if match else text

    def _chat(self, prompt: str) -> str:
        reply = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}],
                                 options={"temperature": 0})
        return reply["message"]["content"].strip()

    def _fallback(self, question: str) -> str:
        today = "오늘" in question
        day_sql = " AND date(started_at) = date('now', 'localtime')" if today else ""
        if "최근" in question or "지난" in question:
            rows = self.query("SELECT id, winner, total_turns FROM games WHERE winner IS NOT NULL"
                              " ORDER BY id DESC LIMIT 5")
            if not rows:
                return "아직 끝난 경기가 없어요."
            names = {"human": "사람", "robot": "로봇"}
            return "최근 경기: " + ", ".join(f"{i}번 {names.get(w, w)} 승({t}턴)" for i, w, t in rows)
        player = "human" if "사람" in question else "robot"
        who = "사람" if player == "human" else "로봇"
        when = "오늘 " if today else ""
        if "잡" in question:
            count = self.query("SELECT COUNT(*) FROM events e JOIN games g ON g.id = e.game_id"
                               " WHERE e.kind = 'capture' AND e.player = '" + player + "'"
                               + day_sql.replace("started_at", "g.started_at"))[0][0]
            return f"{when}{who}이 상대 말을 {count}번 잡았어요."
        games, wins = self.query(
            "SELECT COUNT(*), COALESCE(SUM(winner = '" + player + "'), 0) FROM games"
            " WHERE winner IS NOT NULL" + day_sql)[0]
        if not games:
            return f"{when}끝난 경기가 아직 없어요."
        return f"{when}{who}은 {games}판 중 {wins}판 이겨 승률 {wins / games:.0%}입니다."
