"""윷가락 학습 사진 촬영 (B 정성욱 Day 1~2용, 초안 작성: 김관영 C2). 카메라가 있는 PC에서 실행합니다.

    python scripts/capture_yut.py                    # 0번 카메라, data/yut_raw/에 저장
    python scripts/capture_yut.py --camera 1 --backend dshow --exposure -6 --focus 30

키: s=한 장 저장, b=1초 간격 10장 연속 저장(윷을 흔들어 다시 놓으며), q=종료.
시작할 때 자동 노출·자동 초점을 끄고, 카메라가 실제로 받아들인 값을 다시 읽어 출력합니다.
Windows 웹캠은 백엔드(msmf/dshow)에 따라 설정이 무시되기도 하니 출력값을 꼭 확인하세요.
"""
import argparse
import time
from datetime import datetime
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
BACKENDS = {"any": cv2.CAP_ANY, "msmf": cv2.CAP_MSMF, "dshow": cv2.CAP_DSHOW}


def open_camera(a) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(a.camera, BACKENDS[a.backend])
    if not cap.isOpened():
        raise SystemExit(f"카메라 {a.camera}번을 열 수 없습니다 (backend={a.backend})")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, a.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, a.height)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    if a.focus is not None:
        cap.set(cv2.CAP_PROP_FOCUS, a.focus)
    # 자동 노출 끄기 값은 백엔드마다 다릅니다 (DSHOW·V4L2는 0.25, MSMF는 0인 경우가 많음)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25 if a.backend == "dshow" else 0)
    if a.exposure is not None:
        cap.set(cv2.CAP_PROP_EXPOSURE, a.exposure)
    cap.set(cv2.CAP_PROP_AUTO_WB, 0)
    return cap


def report(cap: cv2.VideoCapture) -> None:
    """카메라가 실제로 적용한 값. 이 값을 docs와 slots.json 옆에 기록해 두면 시연 날 그대로 맞출 수 있습니다."""
    for name in ("FRAME_WIDTH", "FRAME_HEIGHT", "AUTOFOCUS", "FOCUS", "AUTO_EXPOSURE", "EXPOSURE", "AUTO_WB"):
        print(f"  {name:<14} {cap.get(getattr(cv2, 'CAP_PROP_' + name))}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--backend", choices=BACKENDS, default="msmf")
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--exposure", type=float, default=None, help="수동 노출값 (예: DSHOW -6)")
    p.add_argument("--focus", type=float, default=None, help="수동 초점값")
    p.add_argument("--out", type=Path, default=ROOT / "data" / "yut_raw")
    p.add_argument("--tag", default="", help="파일 이름에 붙일 조건 (예: lamp_on, tilted)")
    a = p.parse_args()

    a.out.mkdir(parents=True, exist_ok=True)
    cap = open_camera(a)
    print("카메라 설정 (실제 적용값):")
    report(cap)
    count, burst_left, next_shot = len(list(a.out.glob("*.jpg"))), 0, 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            print("프레임을 읽지 못했습니다")
            break
        view = frame.copy()
        cv2.putText(view, f"saved {count}  [s]save [b]burst10 [q]quit", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow("capture_yut", view)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("b"):
            burst_left, next_shot = 10, time.time()
        if key == ord("s") or (burst_left and time.time() >= next_shot):
            name = f"{datetime.now():%m%d_%H%M%S_%f}{'_' + a.tag if a.tag else ''}.jpg"
            cv2.imwrite(str(a.out / name), frame)
            count += 1
            if burst_left:
                burst_left -= 1
                next_shot = time.time() + 1.0
    cap.release()
    cv2.destroyAllWindows()
    print(f"총 {count}장: {a.out}")


if __name__ == "__main__":
    main()
