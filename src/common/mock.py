"""하드웨어 없이 개발·테스트할 때 쓰는 가짜 구현."""
import random
from typing import Optional

from common.interfaces import DiceResult, Event, GameState


class MockVision:
    def __init__(self, ask_human: bool = True):
        self.ask_human = ask_human

    def read_dice(self) -> DiceResult:
        if self.ask_human:
            raw = input("주사위 눈 입력 (1~6, 엔터=랜덤): ").strip()
            if raw.isdigit() and 1 <= int(raw) <= 6:
                return DiceResult(int(raw), 1.0)
        return DiceResult(random.randint(1, 6), 1.0)

    def piece_at(self, cell: str) -> Optional[str]:
        return None  # mock에서는 이동 확인을 항상 통과시킴


class MockRobot:
    def home(self) -> None:
        print("[robot] HOME")

    def roll_dice(self) -> bool:
        print("[robot] 주사위 굴리기")
        return True

    def move(self, src: str, dst: str) -> bool:
        print(f"[robot] {src} → {dst}")
        return True


class MockNarrator:
    def narrate(self, event: Event) -> str:
        return f"{event.turn}턴 {event.player}: {event.detail}"


class MockStore:
    def save(self, event: Event) -> None:
        pass


class ConsoleScreen:
    def update(self, state: GameState, message: str = "") -> None:
        print(f"[screen] 사람 {state.positions['human']}칸 · 로봇 {state.positions['robot']}칸 {message}")

    def ask_help(self, message: str) -> None:
        input(f"[도움 요청] {message} (처리 후 엔터) ")
