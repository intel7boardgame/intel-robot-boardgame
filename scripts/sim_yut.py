"""윷놀이 한 판 시간 추정 (담당: 김관영 C2). 하드웨어 없이 규칙만으로 수천 판을 돌립니다.

    python scripts/sim_yut.py                      # 기본 가정으로 2000판
    python scripts/sim_yut.py --max-again 1        # 한 번 더 연속 1회 제한
    python scripts/sim_yut.py --robot-move 35      # 로봇 이동 시간 실측값 넣기
    python scripts/sim_yut.py --dump 1             # 한 판의 이벤트 목록과 템플릿 중계 출력

동작별 시간(초)은 추정값입니다. Day 2 점검에서 실측한 값으로 바꿔 다시 돌립니다.
"""
import argparse
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from game.yut_reference import YutBoard, choose_move, simulate  # noqa: E402
from llm.templates import template  # noqa: E402


def seconds(events, a) -> float:
    """이벤트 목록을 동작 시간으로 바꿉니다. 로봇이 잡으면 사람 말도 로봇이 치웁니다."""
    total, turns = 0.0, set()
    for e in events:
        robot = e.player == "robot"
        turns.add(e.turn)
        if e.kind == "throw":
            total += (a.robot_throw + a.refill if robot else a.human_throw) + a.read
            total += a.reroll * (a.robot_throw + a.refill + a.read if robot else a.human_throw + a.read)
        elif e.kind == "move":
            total += (a.robot_move if robot else a.human_choose + a.human_move) + a.verify
        elif e.kind == "capture":
            total += a.robot_move if robot else a.human_move  # 업힌 말도 한 번에 치움
    return total + len(turns) * a.narrate


def pct(values, q) -> float:
    return statistics.quantiles(values, n=100)[q - 1]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--games", type=int, default=2000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--flat-prob", type=float, default=0.5, help="윷가락 하나가 평평한 면으로 떨어질 확률")
    p.add_argument("--max-again", type=int, default=None, help="한 번 더 연속 최대 횟수")
    p.add_argument("--human", choices=["random", "smart"], default="random", help="사람 말 선택 방식")
    p.add_argument("--pieces", type=int, default=None, help="편마다 말 수 (기본: yut_board.json)")
    g = p.add_argument_group("동작 시간(초)")
    g.add_argument("--robot-throw", type=float, default=20, help="윷통 집기·뒤집기·HOME")
    g.add_argument("--refill", type=float, default=8, help="사람이 윷을 윷통에 다시 담기 (MVP)")
    g.add_argument("--human-throw", type=float, default=8)
    g.add_argument("--read", type=float, default=3, help="윷 인식 (다수결)")
    g.add_argument("--reroll", type=float, default=0.1, help="낙·인식 실패로 다시 던지는 비율")
    g.add_argument("--robot-move", type=float, default=25, help="말 집기·놓기·HOME")
    g.add_argument("--human-choose", type=float, default=5, help="화면에서 말 고르기")
    g.add_argument("--human-move", type=float, default=6)
    g.add_argument("--verify", type=float, default=2, help="HOME 자세에서 말 위치 확인")
    g.add_argument("--narrate", type=float, default=3, help="턴마다 LLM 중계 1회")
    p.add_argument("--dump", type=int, default=0, help="이벤트를 출력할 판 수")
    a = p.parse_args()

    board = YutBoard(ROOT / "config" / "yut_board.json")
    board.pieces = a.pieces or board.pieces
    rng = random.Random(a.seed)
    human = choose_move if a.human == "smart" else None

    minutes, turns, robot_moves, throws, captures, wins = [], [], [], [], [], 0
    for i in range(a.games):
        events = simulate(board, rng, a.flat_prob, human=human, max_again=a.max_again)
        if i < a.dump:
            for e in events:
                print(f"{e.turn:>3} {e.player:<5} {e.kind:<8} {e.detail}")
                if e.kind not in ("decision",):
                    print(f"{'':>20}→ {template(e)}")
            print()
        minutes.append(seconds(events, a) / 60)
        turns.append(events[-1].turn)
        robot_moves.append(sum(e.kind in ("move", "capture") and e.player == "robot" for e in events)
                           + sum(e.kind == "throw" and e.player == "robot" for e in events))
        throws.append(sum(e.kind == "throw" for e in events))
        captures.append(sum(e.kind == "capture" for e in events))
        wins += events[-1].player == "robot"

    print(f"{a.games}판 · 말 {board.pieces}개 · 윷가락 앞 확률 {a.flat_prob} · 한 번 더 제한 {a.max_again}"
          f" · 사람 {a.human}\n")
    print("| 항목 | 평균 | 중앙값 | 90% |")
    print("|---|---|---|---|")
    for name, v in (("한 판 시간(분)", minutes), ("턴 수", turns), ("던지기 횟수", throws),
                    ("로봇 동작 횟수(던지기+이동)", robot_moves), ("잡기 횟수", captures)):
        print(f"| {name} | {statistics.mean(v):.1f} | {statistics.median(v):.1f} | {pct(v, 90):.1f} |")
    over = sum(m > 20 for m in minutes) / a.games
    print(f"\n20분 초과 비율: {over:.0%} · 로봇 승률(사람 {a.human}): {wins / a.games:.0%}")


if __name__ == "__main__":
    main()
