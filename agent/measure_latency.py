"""Measure how long each agent tool takes, to choose ``TOOL_TIMEOUT_S`` from data.

It calls ``registry.call`` directly, without the agent timeout, so slow calls are not cut.

    uv run python -m agent.measure_latency            # writes reports/agent_tool_latency.json

What it measures (seconds, wall clock, as the agent sees it):

* ``dose_calculator`` and ``convert_units``: local, many calls.
* ``search_medication_cima``: a real call to the CIMA API (network), several active ingredients.
* ``search_knowledge_base`` warm: the retriever is already built; one call per gold question.
* ``search_knowledge_base`` cold: the FIRST call of a fresh process, which builds the retriever
  (loads the embedding model and the saved dense index). Repeated in separate processes.
* ``search_knowledge_base`` cold, no saved index: the same, but the dense index has to be
  computed from the corpus (first deployment). Uses a temporary folder, the real index is
  not touched.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

GOLD = Path("rag/gold/gold.jsonl")
REPORT = Path("reports/agent_tool_latency.json")
INGREDIENTS = [
    "paracetamol",
    "ibuprofeno",
    "furosemida",
    "cefotaxima",
    "ceftriaxona",
    "amoxicilina",
    "omeprazol",
    "metformina",
    "atorvastatina",
    "heparina",
    "morfina",
    "ondansetron",
    "dexametasona",
    "enalapril",
    "diazepam",
    "salbutamol",
    "insulina",
    "zorbaxil",
]
N_COLD = 3


def timed(fn, *args, **kwargs) -> tuple[float, bool]:
    start = time.perf_counter()
    ok = fn(*args, **kwargs).ok
    return time.perf_counter() - start, ok


def summary(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "min": ordered[0],
        "median": statistics.median(ordered),
        "p95": ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))],
        "max": ordered[-1],
    }


def cold_child(fresh_index: bool) -> None:
    """Runs in its own process: time the first search_knowledge_base call, print the seconds."""
    from agent.react_agent import ReActAgent

    if fresh_index:
        import rag.generate

        rag.generate.INDEX_DIR = Path(tempfile.mkdtemp(prefix="latency_index_"))
    agent = ReActAgent.from_env()
    seconds, ok = timed(
        agent.registry.call, "search_knowledge_base", {"query": "cefotaxima", "top_k": 5}
    )
    print(json.dumps({"seconds": seconds, "ok": ok}))


def cold(fresh_index: bool, repeats: int) -> list[float]:
    values = []
    for _ in range(repeats):
        cmd = [sys.executable, "-m", "agent.measure_latency", "--cold-child"]
        out = (
            subprocess.run(
                cmd + (["--fresh-index"] if fresh_index else []),
                capture_output=True,
                text=True,
                check=True,
            )
            .stdout.strip()
            .splitlines()[-1]
        )
        result = json.loads(out)
        assert result["ok"], "the cold call failed"
        values.append(result["seconds"])
    return values


def main() -> None:
    from agent.react_agent import ReActAgent

    agent = ReActAgent.from_env()
    results: dict[str, dict] = {}

    for name, args in [
        ("dose_calculator", {"expression": "(12 * 7) / 3", "decimals": 2}),
        ("convert_units", {"value": 5, "from_unit": "mg", "to_unit": "mcg"}),
    ]:
        times = [timed(agent.registry.call, name, args)[0] for _ in range(200)]
        results[name] = summary(times)

    times = []
    for ingredient in INGREDIENTS:  # includes one that does not exist: it is a fast error path
        times.append(
            timed(agent.registry.call, "search_medication_cima", {"active_ingredient": ingredient})[
                0
            ]
        )
    results["search_medication_cima"] = summary(times)

    questions = [
        json.loads(line)["question"] for line in GOLD.read_text().splitlines() if line.strip()
    ]
    timed(
        agent.registry.call, "search_knowledge_base", {"query": questions[0], "top_k": 5}
    )  # build
    times = [
        timed(agent.registry.call, "search_knowledge_base", {"query": q, "top_k": 5})[0]
        for q in questions
    ]
    results["search_knowledge_base (warm)"] = summary(times)

    results["search_knowledge_base (cold)"] = summary(cold(False, N_COLD))
    results["search_knowledge_base (cold, no saved index)"] = summary(cold(True, 1))

    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"{'tool':48s} {'n':>4s} {'min':>8s} {'median':>8s} {'p95':>8s} {'max':>8s}")
    for name, s in results.items():
        stats = f"{s['min']:8.3f} {s['median']:8.3f} {s['p95']:8.3f} {s['max']:8.3f}"
        print(f"{name:48s} {s['n']:4d} {stats}")


if __name__ == "__main__":
    if "--cold-child" in sys.argv:
        cold_child("--fresh-index" in sys.argv)
    else:
        main()
