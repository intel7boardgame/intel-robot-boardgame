# AGENTS.md

AI 코딩 에이전트(Claude Code, Codex, Cursor 등)가 이 저장소에서 작업할 때 따르는 안내입니다.

## 프로젝트

사람과 AI 로봇(SO-101)이 실물 **윷놀이**로 대결하는 시스템입니다. 카메라가 윷 결과와 판을 읽고(Intel Geti + OpenVINO), 로봇이 윷을 던지고 말을 옮기며(LeRobot), 로컬 LLM이 게임을 중계합니다(Ollama). 기간은 10일이고 시연이 목표이므로, 확장 기능보다 **한 판이 끝까지 안정적으로 도는 것**이 우선입니다.

- **본 계획: 윷놀이** (편마다 말 2개, 잡기·업기 포함). 1주차(Day 1~5)는 윷놀이만 만듭니다. 규칙은 `docs/rules.md`, 인터페이스 제안은 `docs/interfaces.md` 1절.
- **차선책: 돌 vs 인간** (정답이 0·1·2인 퀴즈, 로봇이 돌 편으로 주사위를 굴려 답함, 맞히면 1칸 전진, 3칸 먼저 승리. 「돌 vs 인간」 규칙 참고, 원작 문제는 쓰지 않음). 2주차 첫날(Day 6) 점검에서 윷놀이 완성이 어렵다고 판단될 때만 전환합니다.
- 지금 코드는 처음 만든 **주사위 게임 골격**입니다. 윷놀이 인터페이스가 Day 1에 확정되면 C1이 전환하며, 주사위 골격은 차선책 전환에 대비해 남겨 둡니다.

## 명령

```bash
pip install -r requirements.txt
python src/main.py --mock        # 비전·로봇 없이 키보드로 한 판 진행 (하드웨어 없이 확인할 때)
python src/main.py               # 실제 카메라·로봇 연결
python -m pytest tests           # 테스트
```

코드를 고친 뒤에는 최소한 `python src/main.py --mock`으로 한 판이 끝까지 도는지, `pytest`가 통과하는지 확인합니다.

## 구조

| 경로 | 역할 | 담당 |
|---|---|---|
| `src/main.py` | 진입점. `--mock`이면 `common/mock.py` 구현을 끼움 | 김동현 |
| `src/common/interfaces.py` | 모듈 간 약속 (데이터 형식, Protocol) | 김동현 |
| `src/common/mock.py` | 하드웨어 없는 가짜 구현 | 김동현 |
| `src/game/` | 오케스트레이터, 턴 상태 머신(transitions), 규칙, 실패 복구 | 김동현 |
| `src/vision/` | `read_yut()`(윷놀이), `read_dice()`(돌 vs 인간), `piece_at(cell)` | 정성욱 |
| `src/robot/` | `home()`, `throw_yut()`(윷놀이), `roll_dice()`(돌 vs 인간), `move(src, dst)` | 신이서 |
| `src/llm/` | `narrate(event)` (Ollama), 퀴즈(`quiz.py`), 기록 질의(`stats_bot.py`) | 김관영 |
| `src/db/` | `save(event)` (SQLite) | 김관영 |
| `src/ui/` | `update(state, message)`, `ask_help(message)` | 김민범 |
| `config/` | `rules.json` 규칙, `quiz.json` 퀴즈 문제, `slots.json` 칸 ROI, `poses.json` 로봇 자세 | 각 담당 |
| `docs/` | `interfaces.md`, `CONTRIBUTING.md`, `rules.md` | - |

## 반드시 지킬 설계 규칙

1. **모듈끼리는 `common/interfaces.py`의 함수로만 주고받습니다.** 칸은 `"cell_3"` 같은 슬롯 이름으로 부르고, 픽셀 좌표나 관절 값은 해당 모듈 밖으로 내보내지 않습니다.
2. **비전과 로봇은 서로를 import하지 않습니다.** 둘을 잇는 것은 `game/orchestrator.py`뿐입니다.
3. **로봇이 움직인 뒤에는 `home()`을 부르고 나서 비전을 호출합니다.** 팔이 카메라를 가립니다.
4. **로봇이 움직이는 동안에는 LLM을 호출하지 않습니다.** 시연 PC가 RTX 3050 6GB라 자원이 부족합니다.
5. **실패해도 게임이 멈추면 안 됩니다.** 인식·이동 실패는 최대 2회 재시도(`game/recovery.py`)하고, 그래도 안 되면 `ask_help()`로 사람에게 넘깁니다.
6. **규칙 값은 코드에 쓰지 않고 `config/`에 둡니다.** 윷판 연결(29칸·지름길), 말 수, 한 번 더 조건, 돌 vs 인간 칸 수를 바꿀 때 코드를 고치지 않아도 되게 합니다.
7. **새 하드웨어 기능을 만들면 `common/mock.py`에 가짜 구현도 함께 둡니다.** `--mock` 실행이 깨지면 안 됩니다.

## 인터페이스를 바꿀 때

`common/interfaces.py`의 함수 이름, 인자, 반환 형식을 바꾸면 다른 팀원의 코드가 깨집니다. 바꿔야 한다면 같은 작업 안에서 `docs/interfaces.md`, `common/mock.py`, 그 함수를 부르는 모든 곳을 함께 고치고, 변경 내용을 PR 설명에 적습니다.

## 코드 스타일

- Python 3.10 이상, 타입 힌트 사용, 데이터는 `dataclass`.
- 모듈·클래스 docstring과 주석은 한국어로 짧게. 주변 코드와 같은 밀도로 씁니다.
- 파일 경로는 `pathlib.Path`, 설정 파일은 `encoding="utf-8"`로 읽습니다.
- 새 의존성은 `requirements.txt`에 추가합니다. 무거운 패키지(lerobot, mediapipe 등)는 필요할 때만 주석을 풉니다.

## git

- 브랜치: `develop`에서 `feature/KAN-<번호>-<모듈>-<설명>`으로 따고 `develop`으로 PR. `main`에 직접 push하지 않습니다.
- 커밋: `<유형>(<모듈>): KAN-<번호> <한 줄 설명>` (유형: feat, fix, refactor, docs, test, chore).
- 커밋·push·PR은 사람이 요청할 때만 합니다.
- `data/`, `models/`, `.env`, 학습 체크포인트, 촬영 이미지는 커밋하지 않습니다. 모델은 Hugging Face Hub로 공유합니다.

자세한 규칙은 `docs/CONTRIBUTING.md`를 따릅니다.

## 하지 말 것

- 다른 담당자의 폴더를 크게 바꾸는 작업은 먼저 사람에게 확인합니다.
- `config/slots.json`, `config/poses.json`의 측정값을 임의의 숫자로 채우지 않습니다. 실제 카메라·로봇에서 측정한 값만 넣습니다.
- 로봇을 실제로 움직이는 코드를 사람 확인 없이 실행하지 않습니다.
