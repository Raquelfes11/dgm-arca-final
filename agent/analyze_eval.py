"""Read reports/phase4_eval.json and explain why each brain fails, not only how often.

    uv run python -m agent.analyze_eval
    uv run python -m agent.analyze_eval --report reports/phase4_eval.json \\
        --markdown reports/phase4_analysis.md

The success rate of agent/evaluate.py is one number per brain. When it is low it does not
say whether the model reasons badly, never calls a tool, writes calls the parser cannot read,
or stops with an empty answer. This script adds, per brain:

* the success rate on the core tasks, and the faithful success rate (correct and all the
  required_tools used: a right answer written from memory does not count);
* how many steps had no valid tool call, how many runs ended with an empty answer and how
  often the knowledge base was used on the tasks that need it;
* every failed core task in exactly one class (FAILURE_CLASSES), first match wins;
* a task by brain grid, so single tasks can be compared.

Brains that were skipped (their entry has an error) are listed and left out of the tables.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Order matters: a failed run gets the first class that applies.
FAILURE_CLASSES = {
    "no_termina": "No llega a dar una respuesta (se agotan los pasos o no hay llamada válida)",
    "respuesta_vacia": "Llama a final_answer pero sin respuesta",
    "sin_herramientas": "Responde sin usar las herramientas necesarias",
    "resultado_incorrecto": "Usa las herramientas necesarias pero el resultado es incorrecto",
}


def classify_failure(row: dict) -> str | None:
    """Class of a failed run (see FAILURE_CLASSES), or None if the run was correct."""
    if row["correct"]:
        return None
    if not row["succeeded"]:
        return "no_termina"
    if not str(row.get("final_answer", "")).strip():
        return "respuesta_vacia"
    if not row.get("required_tools_used", False):
        return "sin_herramientas"
    return "resultado_incorrecto"


def _rate(part: int, total: int) -> float:
    return part / total if total else 0.0


def analyse_brain(rows: list[dict]) -> dict:
    """Metrics of one brain from its result rows (core and edge tasks together)."""
    core = [r for r in rows if r.get("core", True)]
    edge = [r for r in rows if not r.get("core", True)]
    steps = [s for r in core for s in r["steps"]]
    needs_kb = [r for r in core if "search_knowledge_base" in r.get("required_tools", [])]
    failures = {name: 0 for name in FAILURE_CLASSES}
    for row in core:
        kind = classify_failure(row)
        if kind:
            failures[kind] += 1
    return {
        "n_core": len(core),
        "n_edge": len(edge),
        "correct": sum(r["correct"] for r in core),
        "faithful": sum(r["correct"] and r.get("required_tools_used", False) for r in core),
        "finished": sum(r["succeeded"] for r in core),
        "edge_correct": sum(r["correct"] for r in edge),
        "invalid_steps": sum(1 for s in steps if s.get("action") is None),
        "n_steps": len(steps),
        "empty_answers": sum(
            1 for r in core if r["succeeded"] and not str(r.get("final_answer", "")).strip()
        ),
        "kb_used": sum("search_knowledge_base" in r.get("tools_used", []) for r in needs_kb),
        "kb_needed": len(needs_kb),
        "mean_steps": sum(r["n_steps"] for r in core) / len(core) if core else 0.0,
        "mean_tokens": sum(r["tokens_used"] for r in core) / len(core) if core else 0.0,
        "failures": failures,
    }


def analyse(results: dict) -> dict:
    """{brain: metrics} for every brain that ran, plus the names of those that did not."""
    done = {b: r for b, r in results.items() if "error" not in r and r.get("rows")}
    return {
        "brains": {brain: analyse_brain(r["rows"]) for brain, r in done.items()},
        "skipped": {b: r["error"] for b, r in results.items() if "error" in r},
        "grid": _grid(done),
    }


def _grid(results: dict) -> dict[str, dict[str, str]]:
    """{task id: {brain: "OK" | "fallo"}}."""
    grid: dict[str, dict[str, str]] = {}
    for brain, result in results.items():
        for row in result["rows"]:
            grid.setdefault(row["id"], {})[brain] = "OK" if row["correct"] else "fallo"
    return dict(sorted(grid.items()))


def _pct(part: int, total: int) -> str:
    return f"{part}/{total} ({100 * _rate(part, total):.0f} %)"


def render(analysis: dict, grid: bool = True) -> str:
    """The analysis as Markdown tables, ready to paste into the report."""
    brains = analysis["brains"]
    names = list(brains)
    lines: list[str] = []

    def table(title: str, header: list[str], body: list[list[str]]) -> None:
        lines.append(f"### {title}\n")
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        lines.extend("| " + " | ".join(row) + " |" for row in body)
        lines.append("")

    metrics = [
        ("Éxito en las tareas principales", lambda m: _pct(m["correct"], m["n_core"])),
        ("Éxito fiel (correcto y con las herramientas requeridas)",
         lambda m: _pct(m["faithful"], m["n_core"])),
        ("Llegan a final_answer", lambda m: _pct(m["finished"], m["n_core"])),
        ("Casos de borde acertados", lambda m: _pct(m["edge_correct"], m["n_edge"])),
        ("Pasos sin llamada válida", lambda m: _pct(m["invalid_steps"], m["n_steps"])),
        ("Respuestas vacías", lambda m: _pct(m["empty_answers"], m["n_core"])),
        ("Usa la base de conocimiento (si la necesita)",
         lambda m: _pct(m["kb_used"], m["kb_needed"])),
        ("Pasos medios", lambda m: f"{m['mean_steps']:.1f}"),
        ("Tokens medios", lambda m: f"{m['mean_tokens']:.0f}"),
    ]
    table("Resumen por cerebro", ["Métrica"] + names,
          [[label] + [fn(brains[b]) for b in names] for label, fn in metrics])

    table(
        "Por qué fallan las tareas principales",
        ["Clase de fallo"] + names,
        [
            [text] + [_pct(brains[b]["failures"][key], brains[b]["n_core"]) for b in names]
            for key, text in FAILURE_CLASSES.items()
        ],
    )
    if grid and names:
        table(
            "Resultado por tarea",
            ["Tarea"] + names,
            [[tid] + [cells.get(b, "-") for b in names] for tid, cells in analysis["grid"].items()],
        )
    for brain, error in analysis["skipped"].items():
        lines.append(f"* `{brain}` no se ha ejecutado: {error}")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--report", default="reports/phase4_eval.json")
    parser.add_argument("--markdown", default=None, help="also write the tables to this file")
    parser.add_argument("--no-grid", action="store_true", help="omit the task by brain table")
    args = parser.parse_args()

    results = json.loads(Path(args.report).read_text(encoding="utf-8"))
    text = render(analyse(results), grid=not args.no_grid)
    print(text)
    if args.markdown:
        Path(args.markdown).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
