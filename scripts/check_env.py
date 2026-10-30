"""개발·시연 PC 환경 점검 (작성: 김관영 C2). 결과를 마크다운으로 출력하고 data/에 저장합니다.

    python scripts/check_env.py               # 기본 점검
    python scripts/check_env.py --cameras     # 카메라 0~4번을 잠깐 열어 해상도 확인 (카메라가 켜짐)
    python scripts/check_env.py --demo --robot  # 시연 PC: GPU·Ollama·모델·로봇 패키지까지 필수로 확인

버전 기준은 versions.json과 잠금 파일(requirements*.lock)입니다. 설치된 패키지를 lock과 하나하나 비교합니다.
빠진 패키지가 있어도 멈추지 않고 ❌로 표시합니다. 필수 항목이 하나라도 ❌면 종료 코드 1.
"""
import argparse
import importlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import urllib.request
from datetime import datetime
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V = json.loads((ROOT / "versions.json").read_text(encoding="utf-8"))
MODELS = {k: v for k, v in V["ollama"]["models"].items() if not v.get("optional")}  # 중계 기본·대안
PACKAGES = ["transitions", "numpy", "cv2", "openvino", "ollama", "pygame", "pytest"]
ROBOT_PACKAGES = ["torch", "lerobot", "serial"]
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

rows: list[tuple[str, str, str]] = []  # (항목, 결과, 상태)
failed = False
strict = False  # --demo: GPU·Ollama·모델을 필수로


def add(name: str, value: str, ok: bool | None = True, required: bool = True) -> None:
    """ok: True ✅, False ❌(필수면 실패), None ⚠️(확인 필요)."""
    global failed
    mark = "✅" if ok else ("⚠️" if ok is None or not required else "❌")
    failed |= ok is False and required
    rows.append((name, value, mark))


def run(cmd: list[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        return (out.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def check_python() -> None:
    v = sys.version_info
    have, want = f"{v.major}.{v.minor}.{v.micro}", V["python"]["version"]
    same_minor = have.rsplit(".", 1)[0] == want.rsplit(".", 1)[0]
    add("Python", f"{have} (기준 {want}) · {sys.executable}", True if have == want else (None if same_minor else False))
    add("venv 사용", "예" if sys.prefix != sys.base_prefix else "아니오 (.venv를 켜고 실행하세요)",
        sys.prefix != sys.base_prefix)


def check_lock(robot: bool) -> None:
    """설치된 패키지 버전을 lock 파일과 하나하나 비교합니다 (다른 OS용 줄은 건너뜀)."""
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name

    lock = V["lock_files"]["robot" if robot else "common"]
    wrong, total = [], 0
    for line in (ROOT / lock).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        req = Requirement(line)
        if req.marker and not req.marker.evaluate():
            continue
        total += 1
        want = str(req.specifier).lstrip("=")
        try:
            have = metadata.version(canonicalize_name(req.name))
        except metadata.PackageNotFoundError:
            have = "없음"
        if have != want:
            wrong.append(f"{req.name} {have}≠{want}")
    detail = f"{total}개 중 {total - len(wrong)}개 일치"
    if wrong:
        detail += " · 다름: " + ", ".join(wrong[:8]) + (" …" if len(wrong) > 8 else "")
        detail += f" → setup_env.ps1{' -Robot' if robot else ''} 다시 실행"
    add(f"패키지 버전 ({lock})", detail, not wrong)


def check_packages(robot: bool) -> None:
    for name in PACKAGES + (ROBOT_PACKAGES if robot else []):
        try:
            mod = importlib.import_module(name)
            add(f"패키지 {name}", getattr(mod, "__version__", "설치됨"))
        except Exception as e:  # noqa: BLE001 - 어떤 import 오류든 표에 남김
            add(f"패키지 {name}", f"없음 ({type(e).__name__})", False)
    try:
        import cv2
        gui = "Win32 UI" in cv2.getBuildInformation() or "GTK" in cv2.getBuildInformation()
        add("OpenCV 화면 출력(imshow)", "가능" if gui else "불가 (headless 빌드가 덮어씀 → setup_env.ps1 다시 실행)", gui)
    except Exception:
        pass
    try:
        import openvino as ov
        add("OpenVINO 장치", ", ".join(ov.Core().available_devices))
    except Exception:
        pass


def check_gpu() -> None:
    out = run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used", "--format=csv,noheader"])
    if not out:
        add("NVIDIA GPU", "nvidia-smi 없음 (드라이버 확인)", False, required=strict)
        return
    for line in out.splitlines():
        name, driver, total, used = [s.strip() for s in line.split(",")]
        add("NVIDIA GPU", f"{name} · VRAM {total} (사용 중 {used})")
        need = int(V["nvidia_driver"]["min"])
        add("드라이버", f"{driver} (CUDA {V['torch']['cuda']} 빌드는 {need} 이상 필요)",
            int(driver.split(".")[0]) >= need, required=strict)
    try:
        import torch
        cuda = torch.cuda.is_available()
        add("torch CUDA", f"{torch.version.cuda} · {torch.cuda.get_device_name(0)}" if cuda
            else "사용 불가 (CPU 전용 torch일 수 있음)", cuda, required=strict)
    except Exception:
        pass


def check_ollama() -> None:
    exe = shutil.which("ollama")
    version = run(["ollama", "--version"]).split()[-1:] or [""]
    want = V["ollama"]["app"]
    add("Ollama", f"{version[0] or '없음'} (기준 {want})", (True if version[0] == want else None) if exe else False,
        required=strict)
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as r:
            have = {m["name"]: m["digest"] for m in json.load(r)["models"]}
        add("Ollama 서버", "켜져 있음")
    except Exception:
        add("Ollama 서버", "응답 없음 (트레이에서 Ollama 실행)", False, required=strict)
        return
    for m, info in MODELS.items():
        if m not in have:
            add(f"모델 {m}", f"없음 → ollama pull {m}", False, required=strict)
        elif have[m] != info["digest"]:
            add(f"모델 {m}", f"digest 다름 ({have[m][:12]}, 기준 {info['digest'][:12]}) → 기준 PC에서 "
                f"scripts/ollama_models.py로 복사", False, required=strict)
        else:
            add(f"모델 {m}", f"있음 · {info['role']} · digest 일치 ({info['digest'][:12]})")
    others = sorted(set(have) - set(MODELS))
    if others:
        add("기타 모델", ", ".join(others), None)


def check_ports() -> None:
    try:
        from serial.tools import list_ports
        ports = [f"{p.device} ({p.description})" for p in list_ports.comports()]
    except ImportError:
        out = run(["powershell", "-NoProfile", "-Command",
                   "[Console]::OutputEncoding = [Text.Encoding]::UTF8; Get-CimInstance Win32_PnPEntity | Where-Object Name -match '\\(COM\\d+\\)' | "
                   "Select-Object -ExpandProperty Name"])
        ports = [p for p in out.splitlines() if p]
    add("COM 포트 (로봇 팔)", ", ".join(ports) if ports else "없음 (로봇 USB 연결 전이면 정상)", None if not ports else True,
        required=False)


def check_cameras() -> None:
    try:
        import cv2
    except ImportError:
        return
    for i in range(5):
        cap = cv2.VideoCapture(i, cv2.CAP_MSMF)
        if cap.isOpened():
            ok, frame = cap.read()
            add(f"카메라 {i}", f"{frame.shape[1]}x{frame.shape[0]}" if ok else "열림, 프레임 없음", ok, required=False)
        cap.release()


def check_project() -> None:
    for rel in ("config/yut_board.json", "config/rules.json", "data"):
        add(f"저장소 {rel}", "있음" if (ROOT / rel).exists() else "없음", (ROOT / rel).exists())


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cameras", action="store_true", help="카메라 0~4번을 잠깐 열어 확인")
    p.add_argument("--robot", action="store_true", help="torch·lerobot·pyserial도 필수로 확인")
    p.add_argument("--demo", action="store_true", help="시연 PC: GPU·Ollama·모델도 필수로 확인")
    a = p.parse_args()
    global strict
    strict = a.demo

    check_python()
    check_lock(a.robot)
    check_packages(a.robot)
    check_gpu()
    check_ollama()
    check_ports()
    if a.cameras:
        check_cameras()
    check_project()

    host = socket.gethostname()
    lines = [f"# 환경 점검: {host}", "",
             f"{datetime.now():%Y-%m-%d %H:%M} · {platform.platform()} · {platform.processor()}"
             f" · 기준 versions.json ({V['updated']})", "",
             "| 항목 | 결과 | 상태 |", "|---|---|---|"]
    lines += [f"| {n} | {v} | {m} |" for n, v, m in rows]
    lines += ["", "결과: " + ("❌ 필수 항목 실패, 위 표에서 ❌를 확인하세요" if failed else "✅ 필수 항목 통과")]
    text = "\n".join(lines)
    print(text)
    out = ROOT / "data" / f"env_report_{host}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(f"\n저장: {out}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
