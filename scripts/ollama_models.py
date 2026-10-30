"""Ollama 모델을 USB 등으로 옮깁니다 (작성: 김관영 C2). 시연장 인터넷이 느릴 때 씁니다.

    python scripts/ollama_models.py export E:\\ollama_usb gemma4:e2b qwen2.5:3b   # 이 PC → USB
    python scripts/ollama_models.py import E:\\ollama_usb                          # USB → 시연 PC
    python scripts/ollama_models.py export E:\\ollama_usb gemma4:e2b --dry-run     # 복사할 파일만 확인

모델 폴더는 OLLAMA_MODELS 환경 변수, 없으면 %USERPROFILE%\\.ollama\\models입니다.
가져온 뒤 `ollama list`에 안 보이면 트레이에서 Ollama를 껐다 켭니다.
"""
import argparse
import json
import os
import shutil
from pathlib import Path

REGISTRY = Path("manifests") / "registry.ollama.ai" / "library"


def models_dir() -> Path:
    return Path(os.environ.get("OLLAMA_MODELS") or Path.home() / ".ollama" / "models")


def manifest_path(root: Path, model: str) -> Path:
    name, _, tag = model.partition(":")
    return root / REGISTRY / name / (tag or "latest")


def files_of(root: Path, model: str) -> list[Path]:
    """모델 하나에 필요한 파일 (manifest + blob) 상대 경로."""
    m = manifest_path(root, model)
    if not m.exists():
        raise SystemExit(f"{model}: {m} 없음 (ollama list로 이름 확인)")
    data = json.loads(m.read_text(encoding="utf-8"))
    digests = [data["config"]["digest"]] + [layer["digest"] for layer in data["layers"]]
    return [m.relative_to(root)] + [Path("blobs") / d.replace(":", "-") for d in digests]


def copy(src_root: Path, dst_root: Path, rels: list[Path], dry_run: bool) -> None:
    total = 0
    for rel in rels:
        src, dst = src_root / rel, dst_root / rel
        size = src.stat().st_size
        same = dst.exists() and dst.stat().st_size == size
        total += 0 if same else size
        print(f"{'건너뜀' if same else '복사':<4} {size / 1e9:6.2f} GB  {rel}")
        if not (same or dry_run):
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    print(f"{'복사할' if dry_run else '복사한'} 용량: {total / 1e9:.2f} GB")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["export", "import"])
    p.add_argument("folder", type=Path, help="USB 쪽 폴더")
    p.add_argument("models", nargs="*", help="export할 모델 (예: gemma4:e2b)")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    local = models_dir()
    if a.action == "export":
        if not a.models:
            raise SystemExit("export할 모델 이름을 적어 주세요")
        rels = sorted({r for m in a.models for r in files_of(local, m)})
        copy(local, a.folder, rels, a.dry_run)
    else:
        rels = [f.relative_to(a.folder) for f in (a.folder / "manifests").rglob("*") if f.is_file()]
        rels += [f.relative_to(a.folder) for f in (a.folder / "blobs").glob("*") if f.is_file()]
        copy(a.folder, local, rels, a.dry_run)
        print("완료. `ollama list`로 확인하세요.")


if __name__ == "__main__":
    main()
