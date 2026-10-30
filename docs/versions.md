# 버전 관리

> 관리: 김관영 (C2). 팀원 5명의 개발 PC와 시연 PC가 **같은 버전**으로 돌게 하는 규칙입니다. "내 PC에서는 되는데"를 막는 것이 목적입니다.

## 버전이 적힌 곳

| 파일 | 내용 | 직접 고치나 |
|---|---|---|
| `versions.json` | **전체 기준.** Python, uv, NVIDIA 드라이버, CUDA torch, LeRobot, Ollama 앱, LLM 모델(digest 포함), OpenVINO, Geti, 로봇 캘리브레이션 id | ✅ |
| `requirements.txt` | 공통으로 직접 쓰는 패키지 (버전 고정) | ✅ |
| `requirements-robot.txt` | 로봇·ACT용 패키지 (lerobot) | ✅ |
| `requirements.lock` | 공통 패키지 + 하위 의존성 전부 (모든 OS) | ❌ `lock_deps.ps1`이 만듦 |
| `requirements-robot.lock` | 공통 + CUDA torch + lerobot + 하위 의존성 전부 (Windows) | ❌ `lock_deps.ps1`이 만듦 |
| `src/llm/narrator.py` `DEFAULT_MODEL` | 중계 기본 모델 | `versions.json`과 같게 |

- **설치는 항상 lock 파일로 합니다** (`scripts/setup_env.ps1`). `uv pip sync`를 써서 lock에 없는 패키지는 지우기 때문에, 모든 PC가 똑같아집니다.
- `requirements.txt`만으로 설치하면 하위 패키지(pydantic, httpx 등)가 설치한 날에 따라 달라질 수 있습니다.

## 지금 기준 (2026-10-30)

| 구분 | 버전 | 이유 |
|---|---|---|
| Python | 3.12.14 | LeRobot ≥3.12, geti-sdk ≤3.13 |
| numpy | 2.2.6 | LeRobot 0.6.1 조건 `numpy<2.3` |
| opencv-python | 4.13.0.92 | LeRobot이 까는 headless와 같은 버전 (`<4.14`) |
| torch / torchvision | 2.11.0+cu128 / 0.26.0+cu128 | PyPI의 Windows torch는 CPU 전용 → PyTorch 저장소의 CUDA 12.8 빌드 |
| NVIDIA 드라이버 | 570 이상 | CUDA 12.8 빌드 조건 |
| LeRobot | 0.6.1 | |
| OpenVINO | 2026.4.1 | |
| Ollama 앱 | 0.40.13 | |
| 중계 모델 | gemma4:e2b (대안 qwen2.5:3b) | 3050 6GB 기준 (docs/prep-notes.md 2절) |
| Geti 서버·SDK | 미정 | B가 Day 1에 확인해 채움 |
| 로봇 캘리브레이션 id | 미정 | A가 Day 1에 정해 채움 |

## 확인하는 방법

```powershell
python scripts\check_env.py                 # 개발 PC
python scripts\check_env.py --demo --robot  # 시연 PC (GPU·Ollama·모델·로봇 패키지까지 필수)
```

- 설치된 **모든 패키지**를 lock과 하나씩 비교합니다.
- Python 버전, 드라이버, Ollama 앱 버전, 모델 digest도 `versions.json`과 비교합니다.
- 결과는 `data/env_report_<PC이름>.md`에 저장됩니다.
- `python -m pytest tests`의 `test_versions.py`가 파일끼리 어긋나지 않았는지 검사합니다. 예: requirements.txt만 고치고 lock을 안 만든 경우, 코드 기본 모델과 `versions.json`이 다른 경우.

## 버전 바꾸는 절차

패키지를 추가하거나 올릴 때는 **혼자 바꾸지 말고 팀에 먼저 알립니다.** 다른 사람 환경이 바뀌기 때문입니다.

1. `develop`에서 브랜치를 땁니다: `chore/KAN-xx-deps-<내용>`
2. 바꿉니다.
   - 패키지: `requirements.txt` 또는 `requirements-robot.txt`에 `이름==버전`으로 추가·수정
   - torch, Python, Ollama, 모델: `versions.json` 수정 (모델은 `ollama list`의 digest도 바꿈)
3. lock을 다시 만듭니다: `powershell -ExecutionPolicy Bypass -File scripts\lock_deps.ps1`
4. 새 환경에서 확인합니다: `setup_env.ps1 -Recreate -Robot` → 테스트와 `check_env.py` 통과
5. PR 제목을 `chore(deps): KAN-xx …`로 하고, 본문에 **무엇을 왜 바꿨는지**와 `git diff *.lock`의 주요 변화를 적습니다.
6. 병합되면 팀 채널에 알립니다. 팀원은 `git pull` 후 `setup_env.ps1`을 다시 실행합니다.

**주의할 조합**
- numpy·opencv는 LeRobot 조건(`numpy<2.3`, `opencv<4.14`) 안에서만 올립니다. 벗어나면 lock 단계에서 실패합니다.
- 공통 lock은 로봇 lock을 제약으로 걸어서 만듭니다. 그래서 개발 PC와 시연 PC에서 겹치는 패키지 버전이 같습니다.
- `opencv-python`과 `opencv-python-headless`는 같은 버전이어야 합니다. 로봇 환경에서는 설치 후 GUI 빌드를 다시 깔아 `imshow`를 살립니다(`setup_env.ps1`이 처리).

## LLM 모델 버전

- Ollama 태그(`gemma4:e2b`)는 같은 이름이어도 나중에 내용이 바뀔 수 있습니다. 그래서 `versions.json`에 digest를 적고, `check_env.py`가 비교합니다.
- digest가 다르면 기준 PC에서 USB로 복사해 맞춥니다.
  ```powershell
  python scripts\ollama_models.py export E:\ollama gemma4:e2b qwen2.5:3b   # 기준 PC
  python scripts\ollama_models.py import E:\ollama                          # 맞출 PC
  ```

## 버전 관리 대상이 아닌 것 (각 담당이 따로 관리)

| 대상 | 관리 방법 | 담당 |
|---|---|---|
| Geti 학습 모델 (OpenVINO IR) | `models/`에 두고 Hugging Face Hub에 버전별로 올림. 파일 이름에 날짜와 정확도 표시 | B |
| ACT 체크포인트 | Hugging Face Hub (LeRobot 기본 방식) | A |
| 로봇 캘리브레이션 파일 | LeRobot 캐시 폴더. id는 `versions.json`의 `robot`에 기록 | A |
| 카메라 설정값 | `capture_yut.py` 출력값을 `config/slots.json` 옆에 기록 | B |

## 저장소 위치 주의

`F:\` 같은 **FAT32 USB 드라이브**에 저장소를 두면 문제가 생깁니다.
- git이 "dubious ownership" 오류를 냅니다.
- 하드링크를 지원하지 않아 `.venv` 설치(특히 torch 약 6GB)가 매우 느려집니다.

가능하면 내장 SSD(예: `C:\dev\intel-robot-boardgame`)에 clone해서 쓰는 것을 권장합니다.
