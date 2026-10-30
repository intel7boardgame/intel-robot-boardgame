# 시연 PC 첫 점검 체크리스트

> 작성: 김관영 (C2). 시연 PC(RTX 3050 6GB)에서 처음 한 번 실행합니다. 스크립트 하나로 설치부터 측정까지 끝나고, 약 20~40분 걸립니다(대부분 다운로드 시간).

## 1. 가기 전에 준비 (개발 PC에서)

- [ ] **저장소 최신 상태 받기:** `git pull` (develop). 시연 PC에 git이 없으면 GitHub에서 ZIP으로 받아 USB에 담습니다.
- [ ] **(선택) 모델을 USB에 담기:** 시연장 인터넷이 느리거나 막혀 있을 때를 대비합니다. 두 모델 합계 6.5GB입니다.
  ```powershell
  .venv\Scripts\python scripts\ollama_models.py export E:\ollama gemma4:e2b qwen2.5:3b
  ```
- [ ] 로봇 점검까지 같이 할 경우: SO-101 리더·팔로워 USB 케이블 2개, 전원 어댑터

## 2. 시연 PC에서 실행

저장소 폴더에서 PowerShell을 열고 아래 중 하나를 실행합니다. 관리자 권한은 필요 없습니다.

```powershell
# 인터넷으로 모델 받기
powershell -ExecutionPolicy Bypass -File scripts\demo_pc_check.ps1

# USB에서 모델 복사 (E:\ollama에 export해 둔 경우)
powershell -ExecutionPolicy Bypass -File scripts\demo_pc_check.ps1 -ModelsFrom E:\ollama
```

| 옵션 | 쓸 때 |
|---|---|
| `-NoRobot` | LeRobot·CUDA torch(약 3GB) 설치를 건너뜀. LLM만 빨리 보고 싶을 때 |
| `-WithBig` | exaone3.5:7.8b(5GB)도 같이 비교. ACT를 쓰지 않기로 하면 품질 비교용 |
| `-Runs 20` | 모델마다 측정 횟수 (기본 10) |

스크립트가 하는 일:

1. **Ollama:** 없으면 winget으로 설치하고, 서버가 꺼져 있으면 켭니다.
2. **개발 환경:** `setup_env.ps1 -Robot`을 실행합니다.
   - uv 설치, Python 3.12 `.venv` 생성
   - requirements.txt 설치
   - CUDA torch 설치 → LeRobot 설치 → opencv 화면 출력 복구
   - 테스트와 mock 한 판 실행
3. **모델:** USB에서 복사하거나 `ollama pull`로 받습니다.
4. **환경 점검:** `check_env.py --demo --robot`
5. **중계 모델 비교:** `bench_llm.py`

## 3. 결과 확인 (통과 기준)

결과 파일 두 개가 `data\`에 생깁니다. 팀 채널에 붙이고, 확정된 값은 `docs/prep-notes.md`에 옮깁니다.

**`data\env_report_<PC이름>.md` (환경 점검)**

| 항목 | 통과 기준 | 안 될 때 |
|---|---|---|
| Python | 3.12.x | `setup_env.ps1 -Recreate` |
| NVIDIA GPU | RTX 3050 · VRAM 6GB로 표시 | 4GB면 노트북용. 7.8b는 쓰지 않음 |
| 드라이버 | 570 이상 | NVIDIA 홈페이지에서 최신 드라이버 설치 |
| torch CUDA | `12.8 · NVIDIA GeForce RTX 3050` | CPU 전용 torch가 깔린 것. `setup_env.ps1 -Robot` 다시 실행 |
| OpenCV 화면 출력 | 가능 | `setup_env.ps1 -Robot` 다시 실행 (headless가 덮어씀) |
| Ollama 서버·모델 | ✅ | 트레이에서 Ollama 실행 / `ollama pull gemma4:e2b` |
| COM 포트 | 로봇 USB를 꽂으면 COM 번호 2개 | 케이블·전원 확인. 번호를 README에 기록 (A) |

**`data\bench_<PC이름>.md` (중계 모델 비교)**

| 항목 | 통과 기준 | 판단 |
|---|---|---|
| GPU 비율 | 100% | 100% 미만이면 일부가 CPU에서 돎 → 더 작은 모델 사용 |
| 평균 응답 | 3초 이하 (예상 약 0.6~1초) | 넘으면 qwen2.5:3b로 |
| GPU 사용량 | gemma4:e2b 약 3GB | ACT까지 올릴 여유(약 2GB 이상)가 남는지 확인 |
| 문장 | 예시 5개를 눈으로 읽어 보기 | 사실이 틀린 문장이 많으면 모델 변경 |

**결정:** 통과하면 기본 모델 `gemma4:e2b`를 확정합니다. 바꿔야 하면 환경 변수 `BOARDGAME_LLM`을 설정하거나 `src/llm/narrator.py`의 `DEFAULT_MODEL`을 바꿉니다.

## 4. 이어서 할 것 (같은 날)

- [ ] **A 로봇 점검:** `docs/prep-notes.md` 5절 순서대로 진행합니다 (`lerobot-find-port` → `lerobot-calibrate` → `lerobot-teleoperate`). LeRobot은 위 스크립트로 이미 설치되어 있습니다.
- [ ] **B 카메라:** `python scripts\check_env.py --cameras`로 카메라 번호를 확인한 뒤 `python scripts\capture_yut.py --camera <번호>`를 실행합니다.
- [ ] **전원 설정:** 시연 중 화면이 꺼지거나 절전 모드로 들어가지 않게 설정합니다 (Windows 설정 → 전원).
- [ ] **Windows 업데이트:** 시연 날 자동 재시작하지 않게 업데이트를 일시 중지합니다.

## 문제 해결

| 증상 | 해결 |
|---|---|
| `스크립트를 실행할 수 없습니다` (실행 정책) | 위처럼 `powershell -ExecutionPolicy Bypass -File ...`로 실행 |
| uv를 설치했는데 못 찾음 | PowerShell 창을 새로 열고 다시 실행 |
| torch 다운로드가 너무 느림 | `-NoRobot`으로 먼저 LLM만 확인하고, 로봇 패키지는 나중에 `setup_env.ps1 -Robot` |
| `ollama list`에 USB로 복사한 모델이 없음 | 트레이에서 Ollama를 종료하고 다시 실행 |
| 한글이 깨져 보임 | 결과 파일(`data\*.md`)은 UTF-8이라 VS Code로 열면 정상 |
