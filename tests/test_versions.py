"""버전 기준 일관성 테스트 (작성: 김관영 C2). versions.json·requirements*.txt·*.lock·코드 기본값이 서로 맞는지 봅니다.

실패하면 docs/versions.md "버전 바꾸는 절차"를 빠뜨린 것입니다 (대개 scripts/lock_deps.ps1 미실행).
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

V = json.loads((ROOT / "versions.json").read_text(encoding="utf-8"))


def pins(path: Path) -> dict[str, str]:
    """'name==1.2.3 ; marker' 줄을 {이름: 버전}으로 (extras·marker 무시, 이름은 소문자·하이픈)."""
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?==([^\s;]+)", line.strip())
        if m:
            result[m.group(1).lower().replace("_", "-")] = m.group(2)
    return result


COMMON_TXT = pins(ROOT / "requirements.txt")
ROBOT_TXT = pins(ROOT / "requirements-robot.txt")
COMMON_LOCK = pins(ROOT / V["lock_files"]["common"])
ROBOT_LOCK = pins(ROOT / V["lock_files"]["robot"])


def test_python_is_312():
    assert V["python"]["version"].startswith("3.12.")


def test_requirements_pins_match_common_lock():
    for name, version in COMMON_TXT.items():
        assert COMMON_LOCK.get(name) == version, f"{name}: txt {version}, lock {COMMON_LOCK.get(name)} → lock_deps.ps1"


def test_robot_lock_has_same_common_versions():
    """공통 패키지는 로봇 환경에서도 같은 버전이어야 시연 PC와 개발 PC가 같게 동작."""
    for name, version in COMMON_LOCK.items():
        if name in ROBOT_LOCK:
            assert ROBOT_LOCK[name] == version, f"{name}: 공통 {version}, 로봇 {ROBOT_LOCK[name]}"


def test_lerobot_and_torch_match_versions_json():
    assert ROBOT_TXT["lerobot"] == V["lerobot"]["version"] == ROBOT_LOCK["lerobot"]
    cuda = "cu" + V["torch"]["cuda"].replace(".", "")
    for spec in V["torch"]["packages"]:
        name, version = spec.split("==")
        assert ROBOT_LOCK[name] == f"{version}+{cuda}", f"{name}: lock {ROBOT_LOCK[name]}"


def test_opencv_gui_matches_requirements():
    name, version = V["opencv_gui"].split("==")
    assert COMMON_TXT[name] == version
    assert ROBOT_LOCK.get("opencv-python-headless", version) == version  # headless와 GUI 빌드 버전이 같아야 함


def test_default_model_matches_code():
    from llm.narrator import DEFAULT_MODEL
    want = V["ollama"]["default_model"]
    assert want in V["ollama"]["models"] and not V["ollama"]["models"][want].get("optional")
    if "BOARDGAME_LLM" not in os.environ:
        assert DEFAULT_MODEL == want


def test_model_digests_look_valid():
    for name, info in V["ollama"]["models"].items():
        assert re.fullmatch(r"[0-9a-f]{64}", info["digest"]), name
