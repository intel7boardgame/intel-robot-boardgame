"""윷놀이 규칙 테스트 (작성: 김관영 C2). docs/rules.md "규칙 엔진 테스트 케이스" 1~14번과 같습니다.

지금은 참고 구현(game.yut_reference)으로 돌립니다. C1의 규칙 엔진이 나오면
import만 바꿔 같은 케이스로 검증합니다.
"""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from game.yut_reference import GOAL, WAIT, YutBoard, YutGame, choose_move, simulate  # noqa: E402

board = YutBoard(ROOT / "config" / "yut_board.json")
DO, GAE, GEOL, YUT, MO = 1, 2, 3, 4, 5


def game(robot=(WAIT, WAIT), human=(WAIT, WAIT)) -> YutGame:
    return YutGame(board, {"robot": list(robot), "human": list(human)})


class ScriptedRng(random.Random):
    """윷가락 앞 개수를 차례로 내놓는 가짜 난수 (앞=0.0, 뒤=0.99)."""

    def __init__(self, flats: list[int]):
        super().__init__(0)
        self.sticks = [0.0 if i < f else 0.99 for f in flats for i in range(4)]

    def random(self) -> float:
        return self.sticks.pop(0)


# rules.md 1~9: 이동 경로

def test_01_enter_from_wait():
    assert board.path(WAIT, DO) == ["cell_1"]


def test_02_stop_on_mo_takes_shortcut_next():
    assert board.path("cell_3", GAE)[-1] == "cell_5"
    assert board.path("cell_5", DO) == ["diag_r1"]


def test_03_mo_shortcut_to_center():
    assert board.path("cell_5", GEOL) == ["diag_r1", "diag_r2", "center"]


def test_04_pass_mo_stays_outside():
    assert board.path("cell_3", GEOL) == ["cell_4", "cell_5", "cell_6"]


def test_05_stop_in_room_goes_home_side():
    assert board.path("center", GAE) == ["diag_l3", "diag_l4"]


def test_06_pass_room_keeps_mo_shortcut():
    assert board.path("diag_r2", GEOL) == ["center", "diag_r3", "diag_r4"]


def test_07_pass_home_finishes():
    assert board.path("diag_l3", GEOL) == ["diag_l4", "cell_0", GOAL]


def test_08_stop_on_home_is_not_finish():
    assert board.path("cell_18", GAE) == ["cell_19", "cell_0"]


def test_09_from_home_any_result_finishes():
    assert board.path("cell_0", DO) == [GOAL]


# rules.md 10~14: 잡기·업기·한 번 더·승리

def test_10_capture_sends_home_and_throws_again():
    g = game(robot=("cell_2", WAIT), human=("cell_4", WAIT))
    r = g.move("robot", 0, GAE)
    assert r.captured == [0] and g.pieces["human"][0] == WAIT
    assert board.again_on_capture


def test_11_stack_moves_together():
    g = game(robot=("cell_2", "cell_4"))
    assert g.move("robot", 0, GAE).stacked == 2
    r = g.move("robot", 1, DO)
    assert r.moved == [0, 1] and g.pieces["robot"] == ["cell_5", "cell_5"]


def test_12_stacked_pieces_captured_together():
    g = game(robot=("cell_4", "cell_4"), human=("cell_2", WAIT))
    r = g.move("human", 0, GAE)
    assert r.captured == [0, 1] and g.pieces["robot"] == [WAIT, WAIT]


def test_13_yut_mo_do_collects_three_results():
    assert [board.throw(f).again for f in (4, 0, 1)] == [True, True, False]
    events = simulate(board, ScriptedRng([4, 0, 1] + [1] * 200), human=choose_move)
    throws = [e.detail["value"] for e in events if e.kind == "throw"][:3]
    moves = [e.detail["yut"] for e in events if e.kind == "move"][:3]
    assert throws == [4, 5, 1] and moves == ["윷", "모", "도"]


def test_14_stacked_pieces_finish_and_win():
    g = game(robot=("cell_19", "cell_19"), human=("cell_3", WAIT))
    r = g.move("robot", 0, GEOL)
    assert r.dst == GOAL and r.moved == [0, 1]
    assert g.winner() == "robot"


# 규칙서에 없는 경계 상황

def test_back_mo_shortcut_full():
    assert board.path("cell_10", MO) == ["diag_l1", "diag_l2", "center", "diag_l3", "diag_l4"]


def test_mo_shortcut_rejoins_outer_at_jjimo():
    assert board.path("diag_r4", GAE) == ["cell_15", "cell_16"]


def test_pass_back_mo_stays_outside():
    assert board.path("cell_8", GEOL) == ["cell_9", "cell_10", "cell_11"]


def test_overshoot_finishes():
    assert board.path("cell_19", MO) == ["cell_0", GOAL]


def test_waiting_pieces_do_not_stack():
    g = game()
    r = g.move("robot", 0, DO)
    assert r.moved == [0] and g.pieces["robot"] == ["cell_1", WAIT]
    assert g.options("robot") == [0, 1]


def test_no_capture_in_goal():
    g = game(robot=("cell_0", WAIT), human=(GOAL, WAIT))
    assert g.move("robot", 0, DO).captured == []


def test_distance():
    assert board.distance(WAIT) == 21  # 바깥길 20칸 + 참먹이 지나기
    assert board.distance("cell_5") == 12  # 모 지름길
    assert board.distance("center") == 4


def test_robot_strategy_priority():
    g = game(robot=("cell_1", "cell_2"), human=("cell_4", WAIT))
    assert choose_move(g, "robot", GAE) == (1, "capture")
    assert choose_move(g, "robot", DO) == (0, "stack")
    g = game(robot=("cell_1", "cell_6"))
    assert choose_move(g, "robot", DO) == (1, "advance")
    assert choose_move(game(), "robot", DO) == (0, "enter")


def test_random_games_always_finish():
    kinds = {"throw", "move", "capture", "stack", "finish", "win", "decision"}
    for seed in range(200):
        events = simulate(board, random.Random(seed))
        assert events[-1].kind == "win"
        assert {e.kind for e in events} <= kinds
