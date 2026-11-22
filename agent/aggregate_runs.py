"""Join several runs of the same configuration: mean and range of each metric.

    uv run python -m agent.aggregate_runs --brain thinking \\
        --group tasks_1024 reports/fix/repeticiones/fixrepeticiones_tasks_1024_a.json \\
                           reports/fix/repeticiones/fixrepeticiones_tasks_1024_b.json \\
        --group tasks_4096 reports/fix/repeticiones/fixrepeticiones_tasks_4096_a.json \\
        --markdown reports/fix/repeticiones/resumen.md

Between two runs of the same agent the success rate moves by a few tasks, so a difference of one
or two tasks between two configurations says nothing. A group is a name followed by the reports
of its runs; each metric is shown as the mean of the runs and, in brackets, the lowest and the
highest value. With three runs this is a range, not a confidence interval. Two groups differ
for real when their ranges do not overlap.

The last table says, for the core tasks, how many were right in every run, in some runs and in
none: the tasks that change from run to run are the noise, the ones that never pass are the
real failures.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.analyze_eval import analyse_brain


def _share(part: int, total: int) -> float | None:
    return part / total if total else None


# label, function of the metrics of analyse_brain, how to write the value
METRICS = [
    ("Éxito en las tareas principales", lambda m: _share(m["correct"], m["n_core"]), "pct"),
    ("Éxito fiel", lambda m: _share(m["faithful"], m["n_core"]), "pct"),
    ("Casos de borde acertados", lambda m: _share(m["edge_correct"], m["n_edge"]), "pct"),
    ("Llegan a final_answer", lambda m: _share(m["finished"], m["n_core"]), "pct"),
    ("Pasos sin llamada válida", lambda m: _share(m["invalid_steps"], m["n_steps"]), "pct"),
    ("Busca él mismo en la base de conocimiento",
     lambda m: _share(m["kb_used"], m["kb_needed"]), "pct"),
    ("Correcto y trazable", lambda m: _share(m["traceable"], m["n_traced"]), "pct"),
    ("Pasos medios", lambda m: m["mean_steps"], "num"),
    ("Tokens medios", lambda m: m["mean_tokens"], "int"),
    ("Latencia media por tarea (s)", lambda m: m["mean_latency"] if m["has_latency"] else None, "num"),
]


def _write(value: float, kind: str) -> str:
    if kind == "pct":
        return f"{100 * value:.0f} %"
    return f"{value:.0f}" if kind == "int" else f"{value:.1f}"


def summarise_values(values: list[float | None], kind: str) -> str:
    """'mean [lowest-highest]' of the runs that have a value, or 'sin dato'."""
    known = [v for v in values if v is not None]
    if not known:
        return "sin dato"
    mean = sum(known) / len(known)
    if len(known) == 1:
        return _write(mean, kind)
    return f"{_write(mean, kind)} [{_write(min(known), kind)}-{_write(max(known), kind)}]"


def load_runs(paths: list[str], brain: str) -> list[list[dict]]:
    """The rows of the brain in each report; a report without that brain is an error."""
    runs = []
    for path in paths:
        result = json.loads(Path(path).read_text(encoding="utf-8")).get(brain)
        if not result or "error" in result or not result.get("rows"):
            raise ValueError(f"{path}: no results for the brain {brain!r}")
        runs.append(result["rows"])
    return runs


def task_consistency(runs: list[list[dict]]) -> dict[str, int]:
    """How many core tasks were right in every run, in some runs and in none."""
    outcomes: dict[str, list[bool]] = {}
    for rows in runs:
        for row in rows:
            if row.get("core", True):
                outcomes.setdefault(row["id"], []).append(bool(row["correct"]))
    always = sum(all(v) for v in outcomes.values())
    never = sum(not any(v) for v in outcomes.values())
    return {"always": always, "sometimes": len(outcomes) - always - never, "never": never}


def aggregate(groups: dict[str, list[list[dict]]]) -> dict:
    """{group: {n_runs, metrics: {label: text}, consistency}} from the rows of each run."""
    summary = {}
    for name, runs in groups.items():
        analysed = [analyse_brain(rows) for rows in runs]
        summary[name] = {
            "n_runs": len(runs),
            "metrics": {
                label: summarise_values([fn(m) for m in analysed], kind)
                for label, fn, kind in METRICS
            },
            "consistency": task_consistency(runs),
        }
    return summary


def render(summary: dict, brain: str) -> str:
    names = list(summary)
    lines = [f"## Repeticiones del cerebro `{brain}`", ""]
    header = ["Métrica"] + [f"{n} ({summary[n]['n_runs']} ejecuciones)" for n in names]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for label, _, _ in METRICS:
        row = [label] + [summary[n]["metrics"][label] for n in names]
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "Cada celda es la media de las ejecuciones y, entre corchetes, el valor más bajo y el más alto.", ""]
    lines.append("| Tareas principales | " + " | ".join(names) + " |")
    lines.append("|" + "---|" * (len(names) + 1))
    for key, text in (("always", "Acertadas en todas las ejecuciones"),
                      ("sometimes", "Acertadas solo en algunas (ruido)"),
                      ("never", "Falladas en todas")):
        lines.append(f"| {text} | " + " | ".join(str(summary[n]["consistency"][key]) for n in names) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--brain", default="thinking")
    parser.add_argument(
        "--group", nargs="+", action="append", required=True, metavar=("NAME", "REPORT"),
        help="a name followed by the reports of the runs of that configuration",
    )
    parser.add_argument("--markdown", default=None, help="also write the tables to this file")
    args = parser.parse_args()

    groups = {}
    for name, *paths in args.group:
        if not paths:
            parser.error(f"group {name!r} has no reports")
        groups[name] = load_runs(paths, args.brain)
    text = render(aggregate(groups), args.brain)
    print(text)
    if args.markdown:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
