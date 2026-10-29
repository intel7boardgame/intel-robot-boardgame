"""게임 진행 지휘자. 비전·로봇·LLM·DB·화면을 순서대로 부릅니다."""
from common.interfaces import Event, GameState, Narrator, Robot, Screen, Store, Vision
from game.recovery import MAX_RETRY, with_retry
from game.rules import Rules
from game.state_machine import TurnMachine


class Orchestrator:
    def __init__(self, rules: Rules, vision: Vision, robot: Robot, narrator: Narrator,
                 store: Store, screen: Screen, verify_moves: bool = True):
        self.rules, self.vision, self.robot = rules, vision, robot
        self.narrator, self.store, self.screen = narrator, store, screen
        self.verify_moves = verify_moves
        self.state = GameState(positions={"human": 0, "robot": 0})
        self.sm = TurnMachine()

    def run(self) -> str:
        self.robot.home()
        self.screen.update(self.state, "게임 시작")
        while self.state.winner is None:
            self.play_turn()
        return self.state.winner

    def play_turn(self) -> None:
        player = self.state.current
        value = self._roll_and_read(player)

        src = self.state.positions[player]
        dst = self.rules.advance(src, value)
        self.sm.move()
        self._move_piece(player, src, dst)
        self.sm.check()
        if self.verify_moves and not self._verify(player, src, dst):
            self.screen.ask_help(f"{player} 말을 {Rules.cell(dst)}로 옮겨 주세요")

        self.sm.do_event()
        final, event_info = self.rules.apply_event(dst)
        if final != dst:
            self._move_piece(player, dst, final)
        self.state.positions[player] = final

        won = self.rules.is_win(final)
        event = Event(self.state.turn, player, "win" if won else "move",
                      {"dice": value, "from": src, "to": final, "event": event_info})
        self.store.save(event)
        self.screen.update(self.state, self.narrator.narrate(event))

        if won:
            self.sm.finish()
            self.state.winner = player
        else:
            self.sm.next_turn()
            self.state.current = "robot" if player == "human" else "human"
            self.state.turn += 1

    def _roll_and_read(self, player: str) -> int:
        self.sm.roll()
        for attempt in range(MAX_RETRY + 1):
            if attempt:
                self.sm.reroll()
            if player == "robot":
                self.robot.roll_dice()
                self.robot.home()  # 팔이 화면을 가리지 않게 복귀 후 인식
            else:
                self.screen.update(self.state, "주사위를 굴려 주세요")
            self.sm.read()
            result = self.vision.read_dice()
            if result.value is not None:
                return result.value
        self.screen.ask_help("주사위 인식 실패: 화면에서 눈을 입력해 주세요")
        return int(input("주사위 눈: "))

    def _move_piece(self, player: str, src: int, dst: int) -> None:
        if player == "robot":
            self.robot.move(Rules.cell(src), Rules.cell(dst))
            self.robot.home()
        else:
            self.screen.update(self.state, f"말을 {Rules.cell(dst)}로 옮겨 주세요")

    def _verify(self, player: str, src: int, dst: int) -> bool:
        def ok() -> bool:
            return self.vision.piece_at(Rules.cell(dst)) == player

        if ok():
            return True
        if player != "robot":
            return False

        def retry_move() -> None:
            self.sm.retry()
            self._move_piece(player, src, dst)
            self.sm.check()

        return with_retry(retry_move, ok, tries=MAX_RETRY)
