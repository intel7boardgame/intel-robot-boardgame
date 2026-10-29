"""config/rules.json을 읽어 이동·이벤트·승리를 계산합니다."""
import json
from pathlib import Path


class Rules:
    def __init__(self, path: Path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.board_size: int = data["board_size"]
        self.events: dict = data.get("events", {})

    def advance(self, position: int, steps: int) -> int:
        return min(position + steps, self.board_size)

    def apply_event(self, position: int) -> tuple[int, dict]:
        """이벤트 칸이면 효과를 적용한 위치와 이벤트 내용을 돌려줍니다."""
        event = self.events.get(str(position))
        if not event:
            return position, {}
        if event["type"] == "forward":
            return self.advance(position, event["value"]), event
        if event["type"] == "back":
            return max(position - event["value"], 0), event
        return position, event  # skip, quiz 등은 오케스트레이터가 처리

    def is_win(self, position: int) -> bool:
        return position >= self.board_size

    @staticmethod
    def cell(position: int) -> str:
        return f"cell_{position}"
