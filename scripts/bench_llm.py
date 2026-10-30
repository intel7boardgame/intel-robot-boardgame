"""중계 모델 비교 (담당: 김관영). 시연 PC에서 실행해 응답 시간과 숫자 정확도를 잽니다.

    ollama pull gemma4:e2b       # 비교할 모델을 먼저 받아 둡니다
    python scripts/bench_llm.py --models gemma4:e2b qwen2.5:3b --runs 10 --out data/bench.md

결과는 마크다운 표로 출력됩니다. docs/prep-notes.md나 Jira에 붙여 넣으세요.
"""
import argparse
import json
import shutil
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from common.interfaces import Event  # noqa: E402
from llm.narrator import OllamaNarrator, _make_client  # noqa: E402

SAMPLES = [  # 윷놀이 한 턴씩 (docs/interfaces.md 1절 이벤트)
    [Event(1, "human", "throw", {"yut": "걸", "value": 3, "again": False}),
     Event(1, "human", "move", {"piece": 1, "yut": "걸", "from": "wait", "to": "cell_3", "stacked": 1})],
    [Event(2, "robot", "throw", {"yut": "윷", "value": 4, "again": True}),
     Event(2, "robot", "throw", {"yut": "도", "value": 1, "again": False}),
     Event(2, "robot", "decision", {"piece": 1, "reason": "enter"}),
     Event(2, "robot", "move", {"piece": 1, "yut": "윷", "from": "wait", "to": "cell_4", "stacked": 1}),
     Event(2, "robot", "move", {"piece": 1, "yut": "도", "from": "cell_4", "to": "cell_5", "stacked": 1})],
    [Event(7, "human", "throw", {"yut": "개", "value": 2, "again": False}),
     Event(7, "human", "move", {"piece": 2, "yut": "개", "from": "cell_4", "to": "cell_6", "stacked": 1}),
     Event(7, "human", "capture", {"cell": "cell_6", "captured": 2, "again": True})],
    [Event(10, "robot", "throw", {"yut": "도", "value": 1, "again": False}),
     Event(10, "robot", "decision", {"piece": 2, "reason": "stack"}),
     Event(10, "robot", "move", {"piece": 2, "yut": "도", "from": "cell_9", "to": "cell_10", "stacked": 1}),
     Event(10, "robot", "stack", {"cell": "cell_10", "stacked": 2})],
    [Event(18, "robot", "throw", {"yut": "모", "value": 5, "again": True}),
     Event(18, "robot", "move", {"piece": 1, "yut": "모", "from": "cell_19", "to": "goal", "stacked": 2}),
     Event(18, "robot", "finish", {"pieces": 2, "left": 0}),
     Event(18, "robot", "win", {"turns": 18})],
]


def bench(model: str, runs: int) -> dict:
    client = _make_client(None, 30.0)
    if client is not None:
        try:
            client.generate(model=model, prompt="", keep_alive=0)  # 이미 올라가 있으면 내려야 사용량을 잴 수 있음
            time.sleep(2)
        except Exception:
            pass
    before = _gpu_used()
    load_start = time.perf_counter()
    n = OllamaNarrator(model=model, timeout=30.0)
    load = time.perf_counter() - load_start
    n.narrate_turn(SAMPLES[-1])  # 첫 응답은 느려서(최대 10초) 평균에서 뺌. 게임도 시작 전에 한 번 부르면 됨
    first = n.last_latency or 0.0
    times, llm_ok, examples = [], 0, []
    for i in range(runs):
        text = n.narrate_turn(SAMPLES[i % len(SAMPLES)])
        if n.last_latency is not None:
            times.append(n.last_latency)
        llm_ok += n.last_source == "llm"
        if i < len(SAMPLES):
            examples.append(f"[{n.last_source}] {text}")
    after = _gpu_used()
    gpu = _gpu_ratio(n.client, model)
    if n.client is not None:
        n.client.generate(model=model, prompt="", keep_alive=0)  # 다음 모델 측정과 겹치지 않게 내림
        time.sleep(2)
    return {"model": model, "load": load, "first": first, "avg": statistics.mean(times) if times else 0,
            "max": max(times, default=0), "ok": llm_ok / runs, "gpu": gpu, "examples": examples,
            "vram": after - before if after is not None and before is not None else 0.0, "used": after}


def _gpu_used() -> float | None:
    """nvidia-smi 기준 GPU 전체 사용량(GB). ollama ps는 gemma4 같은 모델에서 VRAM을 작게 잘못 보여 줌."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.split()[0]) / 1024
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


def _gpu_total() -> float | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.split()[0]) / 1024
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


def _gpu_ratio(client, model: str) -> float:
    """ollama ps 기준 GPU에 올라간 비율. 100%보다 낮으면 일부가 CPU에서 돌아 느려짐."""
    try:
        for m in client.ps().models:
            if m.model == model:
                return m.size_vram / m.size if m.size else 0.0
    except Exception:
        pass
    return 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    versions = json.loads((Path(__file__).resolve().parent.parent / "versions.json").read_text(encoding="utf-8"))
    default = [m for m, v in versions["ollama"]["models"].items() if not v.get("optional")]
    parser.add_argument("--models", nargs="+", default=default, help="기본: versions.json의 중계 모델")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--out", type=Path, help="결과 마크다운을 이 파일에도 저장")
    args = parser.parse_args()

    results = [bench(m, args.runs) for m in args.models]
    gpu_name = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                              capture_output=True, text=True).stdout.strip() if shutil.which("nvidia-smi") else "?"
    lines = [f"## 중계 모델 비교 · {socket.gethostname()} · {gpu_name} (총 {_gpu_total() or 0:.1f}GB)", "",
             "| 모델 | GPU 사용량(GB) | GPU 비율 | 로딩(초) | 첫 응답(초) | 평균 응답(초) | 최대 응답(초)"
             " | LLM 문장 채택률 | 측정 중 GPU 전체 사용(GB) |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['model']} | {r['vram']:.1f} | {r['gpu']:.0%} | {r['load']:.1f} | {r['first']:.2f}"
                     f" | {r['avg']:.2f} | {r['max']:.2f} | {r['ok']:.0%} | {r['used'] or 0:.1f} |")
    for r in results:
        lines += ["", f"### {r['model']}"] + [f"- {e}" for e in r["examples"]]
    lines += ["", "- GPU 사용량은 nvidia-smi로 모델을 올리기 전후를 비교한 값입니다. GPU 비율이 100%보다 낮으면 일부가 CPU에서 돕니다.",
              "- 채택률이 낮으면 숫자를 지어내 템플릿으로 대체된 것입니다. 평균 응답 3초 이하를 권장합니다."]
    text = "\n".join(lines)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"\n저장: {args.out}")


if __name__ == "__main__":
    main()
