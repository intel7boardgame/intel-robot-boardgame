import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from game.rules import Rules  # noqa: E402

rules = Rules(ROOT / "config" / "rules.json")


def test_advance_stops_at_goal():
    assert rules.advance(18, 6) == rules.board_size


def test_forward_event():
    assert rules.apply_event(5)[0] == 7


def test_back_event():
    assert rules.apply_event(9)[0] == 6


def test_win():
    assert rules.is_win(rules.board_size)
