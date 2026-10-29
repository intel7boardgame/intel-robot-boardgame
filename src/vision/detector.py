"""비전 모듈 (담당: 정성욱). 위 카메라 화면에서 주사위 눈과 말 위치를 읽습니다."""
import json
from pathlib import Path
from typing import Optional

from common.interfaces import DiceResult

FRAMES = 8  # 다수결에 쓸 프레임 수
MIN_AGREE = 0.75  # 이 비율 이상 일치해야 결과로 인정


class VisionDetector:
    def __init__(self, slots_path: Path, camera_index: int = 0):
        self.slots = json.loads(Path(slots_path).read_text(encoding="utf-8"))
        self.camera_index = camera_index

    def read_dice(self) -> DiceResult:
        """트레이 ROI를 FRAMES장 인식해 다수결로 판정. 일치율이 낮으면 value=None."""
        raise NotImplementedError

    def piece_at(self, cell: str) -> Optional[str]:
        """칸 ROI의 색으로 'robot' / 'human' / None 판별."""
        raise NotImplementedError
