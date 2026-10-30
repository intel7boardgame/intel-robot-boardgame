# 사전 준비 결과 (Day 1 전)

> 작성: 김관영 (C2) · 2026-10-30 · 집 PC(RTX 5060 Ti 8GB)에서 측정. 시연 PC(RTX 3050 6GB)에서 다시 확인해야 하는 값은 ⚠️로 표시했습니다.

## 1. 팀 공통: Python 버전은 3.12로 맞추기 (Day 1 결정 필요)

| 패키지 | 지원 Python | 근거 |
|---|---|---|
| LeRobot (A) | **3.12 이상** | 공식 설치 문서: "Python >=3.12, PyTorch >= 2.10" |
| geti-sdk (B, 쓸 경우) | 3.10 ~ 3.13 | PyPI 페이지 |
| openvino, opencv, ollama, pygame-ce, transitions | 3.14까지 설치 확인 | `pip install --dry-run -r requirements.txt` |

- 보고서 기술 스택의 **"Python 3.10"으로는 LeRobot을 설치할 수 없습니다.**
- 모든 패키지가 설치되는 버전은 **3.12**입니다. → 3.12.14로 통일하고 설치 스크립트를 만들었습니다 (`scripts/setup_env.ps1`, 규칙은 `docs/versions.md`). 집 PC에서 LeRobot·CUDA torch까지 설치해 확인했습니다.
- LeRobot 공식 문서는 conda(miniforge) 환경을 권장합니다 (`conda create -y -n lerobot python=3.12`, ffmpeg도 conda로 설치).

## 2. C2: 중계 모델 1차 비교

`python scripts/bench_llm.py --models exaone3.5:2.4b qwen2.5:3b exaone3.5:7.8b llama3.1:8b --runs 15` (윷놀이 한 턴 샘플 5종, 턴마다 LLM 1회)

| 모델 | VRAM(GB) | 평균 응답(초) | 최대(초) | LLM 문장 채택률 | 문장 품질 (눈으로 확인) |
|---|---|---|---|---|---|
| exaone3.5:2.4b | 1.9 | 0.29 | 0.39 | 87% | 빠르지만 없는 말을 덧붙임 ("곧 승리가 다가올 거예요") |
| qwen2.5:3b | 2.2 | 0.21 | 0.29 | 93% | 짧고 정확함. 한자 섞임은 코드로 걸러 냄 |
| exaone3.5:7.8b | 5.2 | 0.60 | 0.84 | 100% | 가장 자연스러움 |
| llama3.1:8b | 5.3 | 0.55 | 0.87 | 100% | 무난하지만 문장이 어색할 때가 있음 |

- 프롬프트에 예시 문장 2개를 넣고, 한 문장 50자 안팎으로 제한하고, 영어·한자·이모지와 잘린 문장을 거르게 했습니다. 이렇게 고치기 전에는 모든 모델이 내용을 지어내고 문장 중간에서 잘렸습니다.
- 채택률이 100%가 아니어도 게임은 멈추지 않습니다. 걸러진 응답은 템플릿 문장으로 대신합니다.
- ⚠️ **시연 PC 6GB에서는 7.8b·8b 모델(5.2GB)과 ACT 정책을 동시에 GPU에 올리기 어렵습니다.** `keep_alive="30m"` 때문에 모델이 VRAM을 계속 차지하기 때문입니다.
### 3050용 추가 후보 비교 (gemma4:e2b, gemma3:4b, qwen3.5:4b)

GPU 사용량은 `nvidia-smi`로 모델을 올리기 전후를 비교한 값입니다. `ollama ps`는 gemma4를 330MB로 잘못 표시합니다. 응답 시간은 첫 호출을 뺀 15회 평균입니다. 모델을 처음 올린 직후 첫 응답은 6~11초까지 걸릴 수 있으니, 게임 시작 전 warmup이 필요합니다.

| 모델 | GPU 사용량 | 평균 응답(초) | 문장 정확도 (눈으로 확인) |
|---|---|---|---|
| **gemma4:e2b** | 3.0GB | 0.23 | 가장 정확함. 윷→도 두 번 이동도 순서대로 설명함. 가끔 "유리한 위치를 선점" 같은 꾸밈말 |
| qwen2.5:3b | 2.2GB | 0.20 | 짧고 대체로 정확함. "업을!"처럼 문장이 덜 끝나기도 함 |
| gemma3:4b | 3.8GB | 0.34 | 대체로 정확함. "2마리가 업합니다"처럼 어색한 표현 |
| qwen3.5:4b | 3.8GB | 0.37 | 칸을 틀림 ("6번 칸"을 "4번 칸"으로, "뒷모"를 "모"로) |
| exaone3.5:2.4b | 1.9GB | 0.27 | 꾸밈말이 많음 ("압도적인 전략 발동!") |
| (참고) exaone3.5:7.8b | 5.0GB | 0.60 | 자연스럽지만 3050 6GB에는 빠듯함 |

- **제안:** 기본 모델은 **gemma4:e2b**로 하고, 대안은 qwen2.5:3b(더 가벼움)입니다. 7.8b는 ACT를 쓰지 않을 때만 고려합니다.
- 모델은 환경 변수 `BOARDGAME_LLM`으로 바꿉니다. ⚠️ 시연 PC에서 `bench_llm.py`로 다시 재서 확정합니다. 이번 값은 5060 Ti 기준이라 3050에서는 응답이 약 2.5~3배 느릴 것으로 예상합니다.
- narrator는 `think=False`를 넘깁니다. qwen3 계열 같은 추론 모델의 생각 출력을 끄기 위한 것으로, 다른 모델에는 영향이 없습니다.

## 3. 한 판 시간 추정 (20분 목표 확인)

`python scripts/sim_yut.py --games 3000` (규칙 참고 구현으로 3000판 시뮬레이션, 로봇은 규칙서 MVP 전략, 사람은 무작위 선택)

동작 시간 가정: 로봇 던지기 20초 + 윷 다시 담기 8초, 로봇 말 이동 25초, 사람 던지기 8초, 사람 말 고르기 5초 + 옮기기 6초, 인식 3초, 확인 2초, 다시 던지기 10%, 중계 턴마다 3초.

| 조건 | 한 판 평균(분) | 90%(분) | 20분 초과 |
|---|---|---|---|
| 기본 (말 2개) | 19.5 | 27.6 | 46% |
| 한 번 더 연속 1회 제한 | 19.9 | 27.9 | 47% |
| 로봇이 느림 (이동 40초, 던지기 30초) | 25.3 | 35.8 | 70% |
| 로봇이 빠름 (이동 15초, 던지기 15초) | 16.0 | 22.5 | - |
| 말 1개 | 10.2 | 13.6 | - |

- 한 판에 평균 약 19턴, 던지기 25번, 로봇 동작 27번이 나옵니다. **시간을 정하는 건 로봇 동작 시간입니다.**
- **"한 번 더 연속 횟수 제한"은 시간을 줄이지 못합니다.** 한 턴에 가는 칸 수가 줄어 오히려 조금 늘어납니다. rules.md "정할 것"에서 제외를 제안합니다.
- 말 2개로 20분 안에 끝내려면 로봇 이동 한 번이 약 20초 이내여야 합니다. Day 2 점검에서 실측값을 넣어 다시 돌립니다 (`--robot-move 실측값 --robot-throw 실측값`).
- 로봇이 느리면 쓸 수 있는 대안:
  - 말 1개 (약 10분)
  - 시연용 "빠른 판": 처음부터 말 하나를 판 위 중간에 놓고 시작
- 로봇 승률은 사람이 무작위로 고르면 62%, 사람도 같은 전략을 쓰면 46%입니다.

## 4. C1 지원: 규칙 참고 구현과 테스트 (바로 사용 가능)

- `config/yut_board.json`: 29칸 그래프입니다. 바깥길, 모·뒷모 지름길, 방, 참먹이를 담았고, 윷 결과표와 칸 좌표 초안도 들어 있습니다.
- `src/game/yut_reference.py`: rules.md를 코드로 옮긴 참고 구현입니다. 이동, 지름길, 잡기, 업기, 완주, 한 번 더, 규칙서 MVP 말 선택 전략을 처리하고, interfaces.md 1절 형식으로 이벤트를 만듭니다. 오케스트레이터와는 아직 연결하지 않았습니다.
- `tests/test_yut_rules.py`: rules.md 테스트 케이스 1~14번과 경계 상황 8개를 담았습니다. 모두 통과합니다. C1 엔진이 나오면 import만 바꿔 같은 테스트로 검증할 수 있습니다.
- 말 위치는 칸 이름 하나로 충분합니다. 멈춘 칸이 다음 길을 정하기 때문입니다(`route_of`). 그래서 `GameState`에 "어느 길로 가는 중" 같은 상태를 따로 둘 필요가 없습니다.
- 이벤트 `move`의 `stacked`는 **함께 움직인 말 수**로 해석했습니다 (혼자면 1). Day 1 이벤트 형식 합의 때 확인이 필요합니다.

## 5. A 로봇: Day 1 오전 점검 순서 (LeRobot 공식 문서 SO-101 기준)

```bash
conda create -y -n lerobot python=3.12 && conda activate lerobot
conda install ffmpeg -c conda-forge
pip install "lerobot[core_scripts,feetech]"         # 학습까지 하면 core_scripts,training,feetech

lerobot-find-port                                   # 팔마다 실행, Windows는 COM3 같은 이름이 나옴
lerobot-calibrate --robot.type=so101_follower --robot.port=COM3 --robot.id=follower
lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM4 --teleop.id=leader
lerobot-teleoperate --robot.type=so101_follower --robot.port=COM3 --robot.id=follower \
    --teleop.type=so101_leader --teleop.port=COM4 --teleop.id=leader
```

- 조립 완료품이면 `lerobot-setup-motors`(모터 ID 설정)는 보통 필요 없습니다. 모터를 바꿨을 때만 씁니다.
- 캘리브레이션 `id`는 이후 모든 명령에서 똑같이 써야 합니다. 이름이 바뀌면 다른 캘리브레이션 파일을 읽습니다. 정한 이름을 README에 적어 둡니다 (A 불참 대비).
- `config/poses.json`은 아직 주사위 게임 키(`tray`, `drop`)만 있습니다. 윷놀이 슬롯 이름으로 등록해야 합니다: `home`, `cell_0`~`cell_19`, `diag_*`, `center`, `wait_*`, `goal_*`, `yut_cup`, `yut_tray`.
- 칸 위치 초안은 `config/yut_board.json`의 `layout`(정규화 좌표)에 있습니다. 윷판 실측 크기를 곱하면 ikpy 계산의 목표 위치로 쓸 수 있습니다.

## 6. B 비전: 확인한 것

- **촬영 스크립트:** `scripts/capture_yut.py`. s는 한 장, b는 1초 간격 10장을 저장하고, `--tag`로 조건을 파일 이름에 붙입니다. 시작할 때 자동 노출·초점을 끄고, **카메라가 실제로 적용한 값을 다시 읽어 출력**합니다. 아직 실제 카메라로는 실행해 보지 않았습니다.
- **Windows 웹캠 설정:** 자동 초점·노출 끄기는 웹캠과 백엔드(MSMF/DSHOW)에 따라 무시되는 경우가 많습니다 (OpenCV 포럼 사례). 두 백엔드를 모두 시험하고 출력값으로 확인합니다. 안 되면 제조사 프로그램(예: Logitech G HUB)으로 고정합니다.
- **Geti → 추론:** Geti 화면에서 "Code Deployment"로 받으면 geti-sdk 기반 예제가 함께 옵니다 (`deployment.load_inference_models(device="CPU")`). geti-sdk는 Python 3.13까지 지원하므로 3.12 환경이면 문제없습니다. SDK 2.6 미만은 Geti 서버 버전과 맞춰야 합니다.
- **`read_yut()` 다수결:** 프레임마다 "앞 개수"를 구하되 윷가락이 4개 다 안 잡힌 프레임은 버리고, 가장 많이 나온 값의 비율이 `MIN_AGREE`(0.75) 이상이면 채택합니다. 결과 → (도·개·걸·윷·모) 변환은 `config/yut_board.json`의 `yut` 표를 함께 쓰면 규칙 엔진과 어긋나지 않습니다.
- **ROI:** 윷판 네 모서리(`cell_10`, `cell_5`, `cell_15`, `cell_0`)의 픽셀 좌표 4개만 찍으면, `layout` 정규화 좌표에 원근 변환(`cv2.getPerspectiveTransform`)을 적용해 29칸 ROI 중심을 한 번에 구할 수 있습니다. ArUco 자동 보정(확장)도 같은 방식입니다.

## 7. D 제작·화면

- 화면에 윷판을 그릴 때 `config/yut_board.json`의 `layout`을 쓰면 규칙 엔진·ROI와 칸 이름이 같아집니다 (정사각형, 모서리 사이 4칸, 대각선 2칸 + 방).
- 중계 문장은 `MAX_CHARS`(120자) 이내 한 문장입니다. 화면 안내 영역은 두 줄 정도면 충분합니다.

## 출처

- LeRobot 설치: https://huggingface.co/docs/lerobot/installation
- LeRobot SO-101: https://huggingface.co/docs/lerobot/so101
- geti-sdk: https://pypi.org/project/geti-sdk
- Geti 배포: https://docs.geti.intel.com/docs/user-guide/geti-fundamentals/deployments/
- OpenCV Windows 자동 초점: https://answers.opencv.org/question/211355/how-to-disable-autofocus-of-a-webcam-on-windows-10
