"""게임 화면 (담당: 김민범). 완성 전까지는 common.mock.ConsoleScreen을 씁니다."""
from common.interfaces import GameState


class GameScreen:
    def update(self, state: GameState, message: str = "") -> None:
        """보드 상황, 현재 차례, 주사위 결과, 점수, 안내 문구 표시."""
        raise NotImplementedError

    def ask_help(self, message: str) -> None:
        """도움 요청 안내를 띄우고 사람이 확인 버튼을 누를 때까지 대기."""
        raise NotImplementedError
