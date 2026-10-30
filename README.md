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

## 개발 환경

**Python 3.12로 통일합니다.** LeRobot은 3.12 이상이 필요하고, geti-sdk는 3.13까지만 지원합니다. 모든 버전 기준은 `versions.json`과 잠금 파일(`requirements*.lock`)에 있고, 규칙은 [docs/versions.md](docs/versions.md)에 있습니다.

Windows에서는 설치 스크립트 하나로 끝납니다. uv 설치, `.venv`(3.12) 생성, 패키지 설치, 테스트, 환경 점검까지 합니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1          # 공통 (C1·C2·B·D)
powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1 -Robot   # + LeRobot·CUDA torch (A, 시연 PC)
.venv\Scripts\activate
```

<details>
<summary>스크립트 없이 직접 설치 (macOS/Linux 포함)</summary>

```bash
uv venv --python 3.12.14 .venv         # uv가 없으면: python3.12 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
uv pip sync requirements.lock          # 또는 pip install -r requirements.lock

# 로봇(A)·시연 PC만 (Windows): lock에 CUDA torch까지 들어 있음 → opencv 화면 출력 복구
uv pip sync requirements-robot.lock --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match
uv pip install --reinstall --no-deps opencv-python==4.13.0.92
winget install --id BtbN.FFmpeg.GPL.Shared.7.1   # torchcodec(LeRobot 영상)용 FFmpeg 4~8 shared. 설치 후 새 터미널
```
</details>

- 환경 확인: `python scripts/check_env.py` (결과는 `data/env_report_<PC이름>.md`에 저장)
- **시연 PC 첫 점검**은 [docs/demo-pc-checklist.md](docs/demo-pc-checklist.md)를 따릅니다 (`scripts\demo_pc_check.ps1`).
- 새 패키지를 넣거나 버전을 올릴 때는 [docs/versions.md](docs/versions.md) "버전 바꾸는 절차"를 따릅니다. 요약하면 `requirements.txt` 수정 → `scripts\lock_deps.ps1` → 테스트 → PR 순서입니다.

## 실행

```bash
python src/main.py --mock       # 비전·로봇 없이 키보드로 한 판 진행 (현재는 주사위 게임)
python src/main.py              # 실제 카메라·로봇 연결
python -m pytest tests          # 테스트
```

중계 모델은 Ollama `gemma4:e2b`가 기본입니다 (`ollama pull gemma4:e2b`). 바꾸려면 환경 변수 `BOARDGAME_LLM`을 설정합니다.

## 협업

브랜치·커밋 규칙은 [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md), 모듈 간 함수 약속은 [docs/interfaces.md](docs/interfaces.md)를 따릅니다.
