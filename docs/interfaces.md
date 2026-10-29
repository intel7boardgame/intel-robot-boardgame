# 모듈 간 인터페이스

모듈끼리는 아래 함수만으로 주고받습니다. 칸은 `"cell_1"`처럼 **슬롯 이름**으로 부르며, 픽셀 좌표나 로봇 좌표는 각 모듈 안에서만 씁니다. 실제 정의는 `src/common/interfaces.py`, 가짜 구현은 `src/common/mock.py`에 있습니다.

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

## 순서 규칙

1. 로봇이 움직인 뒤에는 반드시 `home()`을 부른 다음 비전을 호출합니다 (팔이 화면을 가림).
2. `narrate()`는 로봇이 멈춰 있을 때만 호출합니다 (시연 PC 자원).
3. 인식·이동 실패는 최대 2회 재시도하고, 그래도 실패하면 `ui.ask_help()`로 사람에게 요청합니다.
