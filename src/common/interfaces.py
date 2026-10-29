"""모듈 간 약속. 바꿀 때는 팀 전원에게 먼저 알립니다 (docs/interfaces.md)."""
from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class DiceResult:
    value: Optional[int]  # 1~6, 확신이 없으면 None
    confidence: float


@dataclass
class Event:
    turn: int
    player: str  # "human" | "robot"
    kind: str  # "move" | "event" | "win" | "help"
    detail: dict = field(default_factory=dict)


@dataclass
class GameState:
    positions: dict  # {"human": 0, "robot": 0}
    current: str = "human"
    turn: int = 1
    winner: Optional[str] = None


class Vision(Protocol):
    def read_dice(self) -> DiceResult: ...
    def piece_at(self, cell: str) -> Optional[str]: ...


class Robot(Protocol):
    def home(self) -> None: ...
    def roll_dice(self) -> bool: ...
    def move(self, src: str, dst: str) -> bool: ...


class Narrator(Protocol):
    def narrate(self, event: Event) -> str: ...


class Store(Protocol):
    def save(self, event: Event) -> None: ...


class Screen(Protocol):
    def update(self, state: GameState, message: str = "") -> None: ...
    def ask_help(self, message: str) -> None: ...
