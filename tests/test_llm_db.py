"""C2(llm·db) 테스트. Ollama 없이 가짜 클라이언트와 가짜 이벤트로 확인합니다."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import random  # noqa: E402

from common.interfaces import Event  # noqa: E402
from db.store import SqliteStore  # noqa: E402
from game.yut_reference import YutBoard, simulate  # noqa: E402
from llm.narrator import OllamaNarrator, _numbers_ok  # noqa: E402
from llm.quiz import QuizMaster  # noqa: E402
from llm.stats_bot import StatsBot  # noqa: E402
from llm.templates import cell_name, facts, josa, template  # noqa: E402

BOARD = YutBoard(ROOT / "config" / "yut_board.json")

MOVE = Event(3, "robot", "move", {"dice": 4, "from": 1, "to": 7, "event": {"type": "forward", "value": 2}})
WIN = Event(12, "human", "win", {"dice": 6, "from": 16, "to": 20, "event": {}})


class FakeClient:
    def __init__(self, reply: str = "", fail: bool = False):
        self.reply, self.fail = reply, fail

    def generate(self, **kwargs):
        return {}

    def chat(self, **kwargs):
        if self.fail:
            raise ConnectionError("ollama 꺼짐")
        return {"message": {"content": self.reply}}


def narrator(reply: str = "", fail: bool = False) -> OllamaNarrator:
    return OllamaNarrator(client=FakeClient(reply, fail), warmup=False)


def test_narrate_uses_llm_reply():
    n = narrator("로봇이 주사위 4로 5번 칸을 밟고 7번 칸까지 날아갑니다!")
    assert n.narrate(MOVE).startswith("로봇이")
    assert n.last_source == "llm"


def test_narrate_falls_back_when_ollama_down():
    n = narrator(fail=True)
    text = n.narrate(MOVE)
    assert n.last_source == "template" and "7" in text


def test_narrate_rejects_made_up_numbers():
    n = narrator("로봇이 주사위 3으로 9번 칸에 갑니다!")
    n.narrate(MOVE)
    assert n.last_source == "template"


def test_facts_mention_event_and_win():
    assert "2칸 앞으로" in facts(MOVE)
    assert "승리" in facts(WIN)


def test_store_records_game(tmp_path):
    store = SqliteStore(tmp_path / "games.db")
    store.save(MOVE)
    store.save(Event(4, "human", "help", {"message": "주사위 인식 실패"}))
    store.save(WIN)
    c = store.conn
    assert c.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 3
    assert c.execute("SELECT COUNT(*) FROM turns").fetchone()[0] == 2
    assert c.execute("SELECT event_type FROM turns WHERE turn = 3").fetchone()[0] == "forward"
    assert c.execute("SELECT winner, total_turns FROM games").fetchone() == ("human", 12)
    assert store.win_rate("human") == {"games": 1, "wins": 1, "rate": 1.0}
    store.close()


def test_store_separates_games(tmp_path):
    for winner in ("robot", "robot", "human"):
        store = SqliteStore(tmp_path / "games.db")
        store.save(Event(9, winner, "win", {"dice": 6, "from": 14, "to": 20}))
        store.close()
    SqliteStore(tmp_path / "games.db").close()  # 끝나지 않은 판은 승률에서 빠짐
    store = SqliteStore(tmp_path / "games.db")
    assert store.win_rate("robot")["games"] == 3
    assert round(store.win_rate("robot")["rate"], 2) == 0.67
    assert [g["winner"] for g in store.recent_games()] == ["human", "robot", "robot"]


def test_quiz_grade_and_no_repeat():
    qm = QuizMaster(ROOT / "config" / "quiz.json", seed=1)
    seen = [qm.ask().question for _ in range(len(qm.bank))]
    assert len(set(seen)) == len(qm.bank)
    quiz = qm.bank[1]  # 모방학습 문제
    assert qm.grade(quiz, "2") and qm.grade(quiz, "2번") and qm.grade(quiz, "모방학습")
    assert not qm.grade(quiz, "1")


def test_stats_bot_fallback_and_readonly(tmp_path):
    store = SqliteStore(tmp_path / "games.db")
    store.save(Event(9, "robot", "win", {"dice": 6, "from": 14, "to": 20}))
    store.close()
    bot = StatsBot(tmp_path / "games.db", use_llm=False)
    assert "100%" in bot.answer("오늘 로봇 승률은?")
    assert "로봇 승" in bot.answer("최근 경기 알려줘")
    try:
        bot.query("DELETE FROM games")
        assert False, "SELECT가 아닌 SQL이 실행됨"
    except ValueError:
        pass


def test_stats_bot_with_llm_sql(tmp_path):
    store = SqliteStore(tmp_path / "games.db")
    store.save(WIN)
    store.close()

    class SqlClient(FakeClient):
        def chat(self, messages, **kwargs):
            if "SQL 결과" in messages[0]["content"]:
                return {"message": {"content": "사람이 1번 이겼어요."}}
            return {"message": {"content": "```sql\nSELECT COUNT(*) FROM games WHERE winner='human'\n```"}}

    assert StatsBot(tmp_path / "games.db", client=SqlClient()).answer("사람 몇 번 이겼어?") == "사람이 1번 이겼어요."


# 윷놀이 이벤트 (docs/interfaces.md 1절)

YUT_TURN = [
    Event(5, "robot", "throw", {"yut": "윷", "value": 4, "again": True}),
    Event(5, "robot", "throw", {"yut": "개", "value": 2, "again": False}),
    Event(5, "robot", "decision", {"piece": 1, "reason": "capture"}),
    Event(5, "robot", "move", {"piece": 1, "yut": "윷", "from": "cell_2", "to": "cell_6", "stacked": 1}),
    Event(5, "robot", "capture", {"cell": "cell_6", "captured": 1, "again": True}),
]


def test_josa_and_cell_names():
    assert josa("걸", "이가") == "걸이" and josa("도", "이가") == "도가"
    assert josa("방", "으로") == "방으로" and josa("참먹이", "으로") == "참먹이로"
    assert josa("지름길", "으로") == "지름길로"  # ㄹ 받침
    assert cell_name("cell_7") == "7번 칸" and cell_name("diag_l2") == "지름길" and cell_name(3) == "3번 칸"


def test_yut_templates_never_break_number_check():
    """시뮬레이션 300판의 모든 이벤트: 템플릿 문장이 깨지지 않고, 숫자 검사도 통과해야 대체 문장으로 쓸 수 있음."""
    for seed in range(300):
        for e in simulate(BOARD, random.Random(seed)):
            for text in (template(e), facts(e)):
                assert "None" not in text and "{" not in text, (e, text)
                assert _numbers_ok(text, e), (e, text)


def test_narrate_turn_one_llm_call():
    calls = []

    class CountingClient(FakeClient):
        def chat(self, **kwargs):
            calls.append(kwargs["messages"][1]["content"])
            return {"message": {"content": "로봇, 윷에 개까지! 6번 칸에서 사람 말을 잡고 한 번 더 던집니다!"}}

    n = OllamaNarrator(client=CountingClient(), warmup=False)
    assert "잡고" in n.narrate_turn(YUT_TURN) and n.last_source == "llm"
    assert len(calls) == 1 and "잡아" in calls[0] and "6번 칸" in calls[0]


def test_narrate_turn_fallback_picks_capture():
    n = narrator(fail=True)
    assert "잡았" in n.narrate_turn(YUT_TURN) and n.last_source == "template"


def test_store_and_stats_with_yut_game(tmp_path):
    events = simulate(BOARD, random.Random(7))
    store = SqliteStore(tmp_path / "games.db")
    for e in events:
        store.save(e)
    c = store.conn
    moves = sum(e.kind == "move" for e in events)
    assert c.execute("SELECT COUNT(*) FROM turns").fetchone()[0] == moves
    assert c.execute("SELECT COUNT(*) FROM turns WHERE yut IS NULL OR dice IS NULL").fetchone()[0] == 0
    assert c.execute("SELECT winner, total_turns FROM games").fetchone() == (events[-1].player, events[-1].turn)
    store.close()
    caps = sum(e.kind == "capture" and e.player == "robot" for e in events)
    assert f"{caps}번 잡았" in StatsBot(tmp_path / "games.db", use_llm=False).answer("로봇이 몇 번 잡았어?")


def test_clean_strips_emoji_and_cuts_at_sentence_end():
    from llm.narrator import MAX_CHARS, _clean
    assert _clean("출력: \"로봇 승리! 🎉\"") == "로봇 승리!"
    long = "로봇이 잡았습니다! " + "가" * MAX_CHARS
    assert _clean(long) == "로봇이 잡았습니다!"
    assert _clean("가" * (MAX_CHARS + 5)) == ""


def test_rejects_english_or_hanzi_reply():
    for reply in ("사람이 boldly 6번 칸으로!", "사람이 6번 칸으로 移动!"):
        n = narrator(reply)
        n.narrate_turn(YUT_TURN)
        assert n.last_source == "template"
