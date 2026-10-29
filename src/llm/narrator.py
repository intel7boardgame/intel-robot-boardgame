"""LLM 중계 (담당: 김관영). 로봇이 멈춰 있을 때만 호출됩니다."""
import ollama

from common.interfaces import Event

PROMPT = (
    "너는 보드게임 중계자야. 아래 턴 결과를 한국어 한두 문장으로 재미있게 중계해. "
    "숫자는 바꾸지 마.\n{event}"
)


class OllamaNarrator:
    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model

    def narrate(self, event: Event) -> str:
        reply = ollama.chat(model=self.model,
                            messages=[{"role": "user", "content": PROMPT.format(event=event)}])
        return reply["message"]["content"].strip()
