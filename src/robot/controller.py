"""로봇 모듈 (담당: 신이서). 슬롯 이름으로 받은 명령을 SO-101 동작으로 바꿉니다."""
import json
from pathlib import Path


class RobotController:
    def __init__(self, poses_path: Path):
        self.poses = json.loads(Path(poses_path).read_text(encoding="utf-8"))

    def home(self) -> None:
        """HOME 자세로 복귀. 비전 인식 전에 항상 호출됨."""
        raise NotImplementedError

    def roll_dice(self) -> bool:
        """트레이 모서리에서 주사위를 집어 투하 위치에서 떨어뜨림."""
        raise NotImplementedError

    def move(self, src: str, dst: str) -> bool:
        """src 칸 위로 이동 → 집기 → dst 칸 위로 이동 → 놓기."""
        raise NotImplementedError
