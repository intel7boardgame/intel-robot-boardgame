# 모듈 간 인터페이스

모듈끼리는 아래 함수만으로 주고받습니다. 칸은 `"cell_1"`처럼 **슬롯 이름**으로 부르며, 픽셀 좌표나 로봇 좌표는 각 모듈 안에서만 씁니다. 실제 정의는 `src/common/interfaces.py`, 가짜 구현은 `src/common/mock.py`에 있습니다.

> **10/30 회의 결정:** 게임이 **윷놀이**로 바뀌었습니다 (차선책: 돌 vs 인간, Day 6 판단). 아래 1절은 Day 1에 확정할 **윷놀이 인터페이스(제안)**이고, 2절은 지금 코드에 들어 있는 **주사위 게임 인터페이스**입니다. 주사위 게임 골격은 차선책(돌 vs 인간)으로 전환할 때 씁니다.
> 확정되면 김동현(C1)이 `interfaces.py`, `mock.py`, 호출하는 곳을 함께 고칩니다 (AGENTS.md "인터페이스를 바꿀 때").

## 1. 윷놀이 인터페이스 (제안, Day 1 확정)

| 모듈 | 함수 | 반환 | 담당 | 바뀐 점 |
|---|---|---|---|---|
| vision | `read_yut()` | `YutResult(flats, value, confidence)` · 4개가 안 보이거나 애매하면 `value=None` | 정성욱 | `read_dice()` 대신 |
| vision | `piece_at(cell)` | 그 칸에 있는 말의 편 `"robot"` / `"human"` / `None` | 정성욱 | 칸 이름이 29칸 + 대기 칸으로 늘어남 |
| robot | `home()` | 없음 · HOME 자세로 복귀 | 신이서 | 같음 |
| robot | `throw_yut()` | `bool` 성공 여부 · 윷통을 집어 트레이 위에서 뒤집기 | 신이서 | `roll_dice()` 대신 |
| robot | `move(src, dst)` | `bool` 성공 여부 · 업힌 말도 같은 함수로 옮김 | 신이서 | 같음 |
| game | `choose_move(state, results)` | `Move(piece, result)` · 로봇이 움직일 말과 적용할 결과 | 김동현 | 새로 추가 (전략) |
| llm | `narrate(event)` | 중계 문장 `str` | 김관영 | 이벤트 종류가 늘어남 |
| db | `save(event)` | 없음 | 김관영 | 같음 |
| ui | `update(state, message)` / `ask_help(msg)` | 없음 | 김민범 | 윷판·모아 둔 결과 표시 |
| ui | `ask_choice(options)` | 고른 번호 `int` · 사람이 움직일 말 선택 | 김민범 | 새로 추가 |

### 데이터 형식 (제안)

```python
@dataclass
class YutResult:
    flats: Optional[int]   # 평평한 면이 위인 윷가락 수 0~4, 인식 실패면 None
    value: Optional[int]   # 이동 칸 수: 도1 개2 걸3 윷4 모5
    confidence: float

@dataclass
class GameState:
    pieces: dict           # {"robot": ["wait_robot", "cell_7"], "human": ["cell_4", "cell_4"]}  업힘 = 같은 칸
    current: str = "human"
    turn: int = 1
    pending: list = field(default_factory=list)  # 모아 둔 결과, 예: [4, 5, 1]
    winner: Optional[str] = None
```

슬롯 이름: `cell_0`~`cell_19`, `diag_r1`~`diag_r4`, `diag_l1`~`diag_l4`, `center`, `wait_human`, `wait_robot`, `goal_human`, `goal_robot`, `yut_tray`, `yut_cup`. 연결 관계는 `docs/rules.md` 윷판 그림을 따릅니다.

### 이벤트 형식 (제안, C1·C2 Day 1 합의)

`Event(turn, player, kind, detail)`은 그대로 두고 `kind`와 `detail`만 늘립니다.

| kind | 언제 | detail 예 |
|---|---|---|
| `throw` | 윷 결과가 확정될 때 | `{"yut": "윷", "value": 4, "again": true}` |
| `move` | 말 하나(또는 업힌 말)를 옮길 때 | `{"piece": 1, "yut": "걸", "from": "cell_3", "to": "cell_6", "stacked": 1}` |
| `capture` | 상대 말을 잡았을 때 | `{"cell": "cell_4", "captured": 2, "again": true}` |
| `stack` | 내 말을 업었을 때 | `{"cell": "cell_4", "stacked": 2}` |
| `finish` | 말이 완주했을 때 | `{"pieces": 2, "left": 0}` |
| `win` | 승리 | `{"turns": 18}` |
| `help` | 사람 도움 요청 | `{"message": "윷 인식 실패"}` |
| `decision` | (확장) 로봇이 말을 고른 이유 | `{"piece": 2, "reason": "capture"}` |

## 2. 주사위 게임 인터페이스 (현재 코드, 차선책 전환 시 사용)

| 모듈 | 함수 | 반환 | 담당 |
|---|---|---|---|
| vision | `read_dice()` | `DiceResult(value, confidence)` · 애매하면 `value=None` | 정성욱 |
| vision | `piece_at(cell)` | 그 칸에 있는 말 `"robot"` / `"human"` / `None` | 정성욱 |
| robot | `home()` | 없음 · HOME 자세로 복귀 | 신이서 |
| robot | `roll_dice()` | `bool` 성공 여부 | 신이서 |
| robot | `move(src, dst)` | `bool` 성공 여부 | 신이서 |
| llm | `narrate(event)` | 중계 문장 `str` | 김관영 |
| db | `save(event)` | 없음 | 김관영 |
| ui | `update(state)` / `ask_help(msg)` | 없음 | 김민범 |

돌 vs 인간에서는 `read_dice()` 결과를 돌의 답(0·1·2)으로 바꿔 쓰고, 문제 출제·채점은 `llm/quiz.py`(`QuizMaster.ask()`, `grade()`)를 씁니다. 문제 은행 형식은 `{"question", "answer": 0|1|2, "explain"}`로 바꿀 예정입니다 (현재는 보기형).

## 순서 규칙 (두 게임 공통)

1. 로봇이 움직인 뒤에는 반드시 `home()`을 부른 다음 비전을 호출합니다 (팔이 화면을 가림).
2. `narrate()`는 로봇이 멈춰 있을 때만 호출합니다 (시연 PC 자원).
3. 인식·이동 실패는 최대 2회 재시도하고, 그래도 실패하면 `ui.ask_help()`로 사람에게 요청합니다.
