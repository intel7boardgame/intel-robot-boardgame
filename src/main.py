"""실행 진입점: python src/main.py [--mock]"""
import argparse
from pathlib import Path

from common.mock import ConsoleScreen, MockNarrator, MockRobot, MockStore, MockVision
from game.orchestrator import Orchestrator
from game.rules import Rules

ROOT = Path(__file__).resolve().parent.parent


def build(mock: bool) -> Orchestrator:
    rules = Rules(ROOT / "config" / "rules.json")
    if mock:
        return Orchestrator(rules, MockVision(), MockRobot(), MockNarrator(), MockStore(),
                            ConsoleScreen(), verify_moves=False)

    from db.store import SqliteStore
    from llm.narrator import OllamaNarrator
    from robot.controller import RobotController
    from vision.detector import VisionDetector

    return Orchestrator(rules, VisionDetector(ROOT / "config" / "slots.json"),
                        RobotController(ROOT / "config" / "poses.json"), OllamaNarrator(),
                        SqliteStore(ROOT / "data" / "games.db"), ConsoleScreen())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="비전·로봇 없이 키보드로 진행")
    args = parser.parse_args()
    winner = build(args.mock).run()
    print(f"승자: {winner}")
