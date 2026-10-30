# AI 로봇 보드게임

사람과 AI 로봇이 실물 **윷놀이**로 대결하는 시스템입니다. 카메라가 윷 결과와 판을 읽고(비전), 로봇이 윷을 던지고 말을 옮기며(LeRobot), 로컬 LLM이 게임을 중계합니다(Ollama).

| 구분 | 게임 | 상태 |
|---|---|---|
| **본 계획** | 윷놀이 (편마다 말 2개, 잡기·업기) | 규칙서·인터페이스 제안 완료, 코드 전환 예정 |
| 차선책 | 돌 vs 인간 (정답 0·1·2 퀴즈, 로봇=돌, 3칸 먼저 승리) | Day 6 점검에서 윷놀이가 어려울 때만 전환. 현재 주사위 게임 골격을 활용 |

규칙은 [docs/rules.md](docs/rules.md), 윷놀이 인터페이스 제안은 [docs/interfaces.md](docs/interfaces.md)에 있습니다.

## 폴더 구조

```
intel-robot-boardgame/
├── config/            # 규칙·칸 좌표·로봇 자세 (코드 수정 없이 바꾸는 값)
│   ├── rules.json     # 게임 규칙 (현재 주사위 게임, 윷판 그래프로 전환 예정) (C1)
│   ├── quiz.json      # 퀴즈 문제 은행 (차선책 전환 시 0·1·2 형식으로 교체) (C2)
│   ├── slots.json     # 카메라 화면의 칸별 ROI 좌표 (29칸·대기 칸·트레이) (B)
│   └── poses.json     # 칸별 로봇 자세 (29칸·대기 칸·윷통)              (A)
├── src/
│   ├── main.py        # 실행 진입점 (--mock 으로 하드웨어 없이 실행)
│   ├── common/        # 모듈 간 약속: 데이터 형식, 인터페이스, mock     (C1)
│   ├── game/          # 오케스트레이터, 턴 상태 머신, 규칙, 실패 복구  (C1 김동현)
│   ├── vision/        # 카메라, 윷 결과 인식, 말 위치 인식             (B  정성욱)
│   ├── robot/         # 로봇 제어: home, throw_yut, move               (A  신이서)
│   ├── llm/           # Ollama 중계, 퀴즈, 기록 질의 챗봇               (C2 김관영)
│   ├── db/            # SQLite 대전 기록                                (C2 김관영)
│   └── ui/            # 게임 화면                                       (D  김민범)
├── scripts/           # 데이터 수집·학습 보조 스크립트
├── tests/             # 테스트
├── docs/              # 인터페이스 문서, 규칙서, 협업 규칙
├── data/              # 촬영 이미지·녹화 데이터 (git 제외)
└── models/            # 학습된 모델·체크포인트 (git 제외)
```

## 실행

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python src/main.py --mock       # 비전·로봇 없이 키보드로 한 판 진행 (현재는 주사위 게임)
python src/main.py              # 실제 카메라·로봇 연결
```

## 협업

브랜치·커밋 규칙은 [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md), 모듈 간 함수 약속은 [docs/interfaces.md](docs/interfaces.md)를 따릅니다.
