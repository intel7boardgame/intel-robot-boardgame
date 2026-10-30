"""윷놀이 참고 구현 (작성: 김관영 C2, 규칙서 검증·시뮬레이션용).

docs/rules.md를 그대로 코드로 옮겨 규칙 테스트(tests/test_yut_rules.py)와
가짜 윷놀이 이벤트·한 판 시간 추정(scripts/sim_yut.py)에 씁니다.
오케스트레이터는 아직 쓰지 않습니다. C1이 규칙 엔진을 만들 때 가져다 쓰거나 바꿔도 됩니다.

말 위치는 칸 이름 하나로 충분합니다. 멈춘 칸이 다음에 탈 길을 정하기 때문입니다
(config/yut_board.json의 route_of). 대기 칸은 "wait", 완주는 "goal"입니다.
"""
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from common.interfaces import Event

WAIT, GOAL = "wait", "goal"


def other(player: str) -> str:
    return "robot" if player == "human" else "human"


@dataclass
class Throw:
    name: str  # 도·개·걸·윷·모
    value: int  # 이동 칸 수
    again: bool  # 한 번 더


@dataclass
class MoveResult:
    src: str
    path: list[str]  # 지나간 칸, 마지막이 도착 칸 (완주면 "goal")
    moved: list[int]  # 함께 움직인 내 말 번호 (업힌 말 포함, 0부터)
    captured: list[int]  # 잡은 상대 말 번호
    stacked: int  # 이동 후 도착 칸에 있는 내 말 수 (2 이상이면 업힘)

    @property
    def dst(self) -> str:
        return self.path[-1]


class YutBoard:
    def __init__(self, path: Path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.pieces: int = data["pieces_per_side"]
        self.again_on_capture: bool = data["again_on_capture"]
        self.yut = {int(k): Throw(*v) for k, v in data["yut"].items() if k.isdigit()}
        self.routes = {k: v for k, v in data["routes"].items() if not k.startswith("_")}
        self.route_of = {k: v for k, v in data["route_of"].items() if not k.startswith("_")}
        self.layout = {k: v for k, v in data["layout"].items() if not k.startswith("_")}

    def throw(self, flats: int) -> Throw:
        """평평한 면이 위로 온 윷가락 수(0~4)를 결과로 바꿉니다."""
        return self.yut[flats]

    def path(self, pos: str, steps: int) -> list[str]:
        """pos에서 steps칸 갈 때 밟는 칸들. 참먹이를 지나면 마지막이 "goal"."""
        if pos == GOAL:
            raise ValueError("완주한 말은 움직일 수 없습니다")
        route = self.routes[self.route_of.get(pos, "outer")]
        i = route.index(pos)
        path = route[i + 1:i + 1 + steps]
        if len(path) < steps:
            path.append(GOAL)
        return path

    def distance(self, pos: str) -> int:
        """완주까지 남은 칸 수 (참먹이를 지나는 한 칸 포함)."""
        if pos == GOAL:
            return 0
        route = self.routes[self.route_of.get(pos, "outer")]
        return len(route) - route.index(pos)


@dataclass
class YutGame:
    board: YutBoard
    pieces: dict = field(default_factory=dict)  # {"human": ["wait", "cell_3"], "robot": [...]}

    def __post_init__(self):
        for player in ("human", "robot"):
            self.pieces.setdefault(player, [WAIT] * self.board.pieces)

    def options(self, player: str) -> list[int]:
        """고를 수 있는 말 번호. 같은 칸(업힘, 대기)의 말은 하나만 보여 줍니다."""
        seen, result = set(), []
        for i, pos in enumerate(self.pieces[player]):
            if pos != GOAL and pos not in seen:
                seen.add(pos)
                result.append(i)
        return result

    def move(self, player: str, piece: int, steps: int) -> MoveResult:
        mine = self.pieces[player]
        src = mine[piece]
        group = [piece] if src == WAIT else [i for i, p in enumerate(mine) if p == src]
        path = self.board.path(src, steps)
        dst = path[-1]
        for i in group:
            mine[i] = dst
        captured: list[int] = []
        if dst != GOAL:
            theirs = self.pieces[other(player)]
            captured = [i for i, p in enumerate(theirs) if p == dst]
            for i in captured:
                theirs[i] = WAIT
        stacked = sum(p == dst for p in mine) if dst != GOAL else 0
        return MoveResult(src, path, group, captured, stacked)

    def preview(self, player: str, piece: int, steps: int) -> MoveResult:
        """상태를 바꾸지 않고 이동 결과만 봅니다."""
        trial = YutGame(self.board, {p: list(v) for p, v in self.pieces.items()})
        return trial.move(player, piece, steps)

    def winner(self) -> Optional[str]:
        for player, pos in self.pieces.items():
            if all(p == GOAL for p in pos):
                return player
        return None


def choose_move(game: YutGame, player: str, steps: int) -> tuple[int, str]:
    """규칙서 MVP 우선순위: 잡기 → 업기 → 완주에 가까운 말 전진 → 새 말 올리기."""
    options = game.options(player)
    previews = {i: game.preview(player, i, steps) for i in options}
    for reason, ok in (("capture", lambda r: r.captured), ("stack", lambda r: r.stacked > len(r.moved))):
        hits = [i for i in options if ok(previews[i])]
        if hits:
            return hits[0], reason
    on_board = [i for i in options if game.pieces[player][i] != WAIT]
    if on_board:
        return min(on_board, key=lambda i: game.board.distance(game.pieces[player][i])), "advance"
    return options[0], "enter"


def choose_random(rng: random.Random) -> Callable[[YutGame, str, int], tuple[int, str]]:
    return lambda game, player, steps: (rng.choice(game.options(player)), "random")


def simulate(board: YutBoard, rng: random.Random, flat_prob: float = 0.5,
             human: Optional[Callable] = None, robot: Callable = choose_move,
             max_again: Optional[int] = None, max_turns: int = 500) -> list[Event]:
    """한 판을 끝까지 돌려 interfaces.md 1절 형식의 이벤트 목록을 돌려줍니다.

    flat_prob: 윷가락 하나가 평평한 면으로 떨어질 확률. max_again: 한 번 더 연속 최대 횟수(None이면 무제한).
    """
    game = YutGame(board)
    choosers = {"human": human or choose_random(rng), "robot": robot}
    events: list[Event] = []
    player, turn = "human", 1

    def throw_until_stop(pending: list[Throw]) -> None:
        again = 0
        while True:
            t = board.throw(sum(rng.random() < flat_prob for _ in range(4)))
            more = t.again and (max_again is None or again < max_again)
            events.append(Event(turn, player, "throw", {"yut": t.name, "value": t.value, "again": more}))
            pending.append(t)
            if not more:
                return
            again += 1

    while turn <= max_turns:
        pending: list[Throw] = []
        throw_until_stop(pending)
        while pending:
            t = pending.pop(0)
            piece, reason = choosers[player](game, player, t.value)
            if player == "robot":
                events.append(Event(turn, player, "decision", {"piece": piece + 1, "reason": reason}))
            r = game.move(player, piece, t.value)
            events.append(Event(turn, player, "move", {"piece": piece + 1, "yut": t.name, "from": r.src,
                                                        "to": r.dst, "stacked": len(r.moved)}))
            if r.captured:
                events.append(Event(turn, player, "capture", {"cell": r.dst, "captured": len(r.captured),
                                                              "again": board.again_on_capture}))
            if r.stacked > len(r.moved):
                events.append(Event(turn, player, "stack", {"cell": r.dst, "stacked": r.stacked}))
            if r.dst == GOAL:
                left = sum(p != GOAL for p in game.pieces[player])
                events.append(Event(turn, player, "finish", {"pieces": len(r.moved), "left": left}))
            if game.winner():
                events.append(Event(turn, player, "win", {"turns": turn}))
                return events
            if r.captured and board.again_on_capture:
                throw_until_stop(pending)
        player = other(player)
        turn += 1
    raise RuntimeError(f"{max_turns}턴 안에 끝나지 않았습니다")
