"""LLM 중계 (담당: 김관영). 로봇이 멈춰 있을 때만 호출됩니다.

Ollama가 없거나, 느리거나, 숫자를 바꿔 말하면 templates.template() 문장으로 대신합니다.
모델은 환경 변수 BOARDGAME_LLM으로 바꿀 수 있습니다 (scripts/bench_llm.py로 비교).
"""
import os
import re
import time

from common.interfaces import Event
from llm.templates import facts, headline, template

DEFAULT_MODEL = os.environ.get("BOARDGAME_LLM", "gemma4:e2b")  # 3050 6GB 기준 (docs/prep-notes.md 2절)
TIMEOUT = 8.0  # 초. 넘으면 템플릿 문장 사용
MAX_CHARS = 120  # 화면 한두 줄

SYSTEM = (
    "너는 사람과 로봇이 대결하는 윷놀이의 신나는 한국어 중계자야. "
    "주어진 턴 결과에서 가장 중요한 장면(승리 > 잡기 > 완주 > 업기 > 이동) 하나를 골라 "
    "50자 안팎의 한 문장으로 중계해. 도·개·걸·윷·모, 잡기, 업기, 한 번 더, 참먹이, 지름길 같은 윷놀이 말을 써. "
    "숫자와 칸 이름은 주어진 것만 그대로 쓰고, 주어지지 않은 사실이나 전략 해설을 지어내지 마. "
    "이모지, 영어, 따옴표, 머리말 없이 문장만 써.\n"
    "예) 입력: 3턴 사람 차례. 윷을 던져 '개'(2칸)이 나옴. 사람의 1번 말이 '개'로 2번 칸에서 4번 칸으로 이동. "
    "사람이 4번 칸에서 상대 말 1개를 잡아 대기 칸으로 돌려보냄. 잡았으니 한 번 더 던짐.\n"
    "출력: 개! 사람이 4번 칸에서 로봇 말을 잡고 한 번 더 던집니다!\n"
    "예) 입력: 6턴 로봇 차례. 윷을 던져 '도'(1칸)이 나옴. 로봇의 2번 말이 '도'로 4번 칸에서 모 자리로 이동.\n"
    "출력: 로봇, 도로 모 자리에 섰습니다. 다음엔 지름길이 열려요!"
)


class OllamaNarrator:
    def __init__(self, model: str = DEFAULT_MODEL, host: str | None = None,
                 timeout: float = TIMEOUT, client=None, warmup: bool = True):
        self.model = model
        self.client = client if client is not None else _make_client(host, timeout)
        self.last_latency: float | None = None  # 마지막 LLM 응답 시간(초), 측정용
        self.last_source = ""  # "llm" | "template"
        if warmup:
            self.warmup()

    def warmup(self) -> bool:
        """게임 시작 전에 모델을 GPU에 올려 첫 중계가 늦지 않게 합니다."""
        if self.client is None:
            return False
        try:
            self.client.generate(model=self.model, prompt="", keep_alive="30m")
            return True
        except Exception:
            return False

    def narrate(self, event: Event) -> str:
        return self.narrate_turn([event])

    def narrate_turn(self, events: list[Event]) -> str:
        """한 턴의 이벤트(던지기·이동·잡기 …)를 LLM 한 번으로 중계합니다. 실패하면 핵심 이벤트 하나를 템플릿으로."""
        reply = self._ask_llm(" ".join(facts(e) for e in events))
        if reply and _numbers_ok(reply, events) and not re.search("[A-Za-z一-鿿]", reply):  # 영어·한자
            self.last_source = "llm"
            return reply
        self.last_source = "template"
        return template(headline(events))

    def _ask_llm(self, prompt: str) -> str:
        if self.client is None:
            return ""
        start = time.perf_counter()
        try:
            reply = self.client.chat(
                model=self.model,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": prompt}],
                options={"temperature": 0.7, "num_predict": 70},
                think=False,  # qwen3 계열 등 추론 모델의 생각 출력을 꺼서 응답을 빠르게 함
                keep_alive="30m",
            )
        except Exception:
            return ""
        finally:
            self.last_latency = time.perf_counter() - start
        return _clean(reply["message"]["content"])


def _make_client(host: str | None, timeout: float):
    try:
        import ollama
    except ImportError:
        return None
    return ollama.Client(host=host, timeout=timeout)


def _clean(text: str) -> str:
    """따옴표·이모지를 지우고, 너무 길면 MAX_CHARS 안의 마지막 문장 끝에서 자릅니다."""
    text = re.sub("[\U00010000-\U0010FFFF☀-➿️]", "", text)
    text = re.sub(r"^(출력|중계)\s*:\s*", "", text.strip()).strip('"\'“”‘’ ').replace("\n", " ")
    if len(text) <= MAX_CHARS:
        return text
    cut = text[:MAX_CHARS]
    end = max(cut.rfind(c) for c in ".!?")
    return cut[:end + 1] if end > 0 else ""  # 문장 끝이 없으면 템플릿으로


def _numbers_ok(text: str, events: Event | list[Event]) -> bool:
    """중계 문장에 이벤트에 없는 숫자가 나오면 거짓 (LLM이 숫자를 지어내는 것 방지)."""
    allowed: set[str] = set()
    for event in events if isinstance(events, list) else [events]:
        allowed |= {str(event.turn)} | {str(n) for n in _ints(event.detail)}
        d = event.detail
        if isinstance(d.get("from"), int) and isinstance(d.get("dice"), int):
            allowed.add(str(d["from"] + d["dice"]))  # 이벤트 칸 도착 위치
    return all(n in allowed for n in re.findall(r"\d+", text))


def _ints(value) -> list[int]:
    if isinstance(value, bool):
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        return [int(n) for n in re.findall(r"\d+", value)]  # "cell_6" → 6번 칸
    if isinstance(value, dict):
        return [n for v in value.values() for n in _ints(v)]
    if isinstance(value, (list, tuple)):
        return [n for v in value for n in _ints(v)]
    return []
