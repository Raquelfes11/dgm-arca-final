"""Read reports/phase4/phase4_eval.json and explain why each brain fails, not only how often.

    uv run python -m agent.analyze_eval
    uv run python -m agent.analyze_eval --report reports/phase4/phase4_eval.json \\
        --markdown reports/phase4/phase4_analysis.md

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
    "valor_sin_unidad": "El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit)",
    "resultado_incorrecto": "Usa las herramientas necesarias pero el resultado es incorrecto",
}

# Mutually exclusive, first match wins. They cover every core task that relies on the
# knowledge base, so their sum is always n_traced.
TRACE_CLASSES = {
    "trazable": "Correcto y trazable (citas válidas y de la evidencia)",
    "correcto_sin_cita": "Correcto pero sin ninguna cita",
    "correcto_cita_inventada": "Correcto pero con citas inventadas (no devueltas por la búsqueda)",
    "correcto_otra_fuente": "Correcto con citas válidas, pero no de la ficha que contiene la evidencia",
    "incorrecto_no_recuperada": "Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever)",
    "incorrecto_bien_citado": "Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura)",
    "incorrecto_sin_fuente": "Incorrecto, con la evidencia recuperada pero sin cita válida de ella",
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
    if row.get("correct_lax") and not row["correct"]:
        return "valor_sin_unidad"
    return "resultado_incorrecto"

def classify_traceability(row: dict) -> str | None:
    """Class of a task that relies on the knowledge base (see TRACE_CLASSES), else None."""
    cites = row.get("citations")
    if cites is None:  # not traced: no search_knowledge_base required, or an old report
        return None
    if row["correct"]:
        if row.get("traceable"):
            return "trazable"
        if not cites["cited"]:
            return "correcto_sin_cita"
        if cites["invalid_citations"]:
            return "correcto_cita_inventada"
        return "correcto_otra_fuente"
    if not cites["evidence_retrieved"]:
        return "incorrecto_no_recuperada"
    if cites["citations_valid"] and cites["evidence_cited"]:
        return "incorrecto_bien_citado"
    return "incorrecto_sin_fuente"

def _rate(part: int, total: int) -> float:
    return part / total if total else 0.0


def analyse_brain(rows: list[dict]) -> dict:
    """Metrics of one brain from its result rows (core and edge tasks together)."""
    core = [r for r in rows if r.get("core", True)]
    edge = [r for r in rows if not r.get("core", True)]
    steps = [s for r in core for s in r["steps"] if not s.get("automatic")]
    needs_kb = [r for r in core if "search_knowledge_base" in r.get("required_tools", [])]
    failures = {name: 0 for name in FAILURE_CLASSES}
    for row in core:
        kind = classify_failure(row)
        if kind:
            failures[kind] += 1
    has_lax = bool(core) and all("correct_lax" in r for r in core)
    traced = [r for r in core if r.get("traceable") is not None]
    cites = [r["citations"] for r in traced]
    
    trace_classes = {name: 0 for name in TRACE_CLASSES}
    for row in core:
        kind = classify_traceability(row)
        if kind:
            trace_classes[kind] += 1
    return {
        "n_core": len(core),
        "n_edge": len(edge),
        "correct": sum(r["correct"] for r in core),
        "faithful": sum(r["correct"] and r.get("required_tools_used", False) for r in core),
        "finished": sum(r["succeeded"] for r in core),
        "edge_correct": sum(r["correct"] for r in edge),
        "invalid_steps": sum(1 for s in steps if s.get("action") is None),
        "n_steps": len(steps),
        "has_route": any("call_route" in s for s in steps),  # old reports do not have it
        "tag_calls": sum(1 for s in steps if s.get("call_route") == "tag"),
        "fallback_calls": sum(1 for s in steps if s.get("call_route") == "fallback"),
        "empty_answers": sum(
            1 for r in core if r["succeeded"] and not str(r.get("final_answer", "")).strip()
        ),
        "kb_used": sum("search_knowledge_base" in r.get("tools_used", []) for r in needs_kb),
        "auto_search": sum(any(s.get("automatic") for s in r["steps"]) for r in core),
        "kb_needed": len(needs_kb),
        "mean_steps": sum(r["n_steps"] for r in core) / len(core) if core else 0.0,
        "mean_tokens": sum(r["tokens_used"] for r in core) / len(core) if core else 0.0,
        "failures": failures,
        "has_lax": has_lax,
        "correct_lax": sum(bool(r.get("correct_lax")) for r in core) if has_lax else 0,
        "lucky": sum(bool(r.get("correct_lax")) and not r["correct"] for r in core),
        "n_traced": len(traced),
        "traceable": sum(r["traceable"] for r in traced),
        "cited": sum(c["cited"] for c in cites),
        "invalid_cites": sum(bool(c["invalid_citations"]) for c in cites),
        "evidence_retrieved": sum(c["evidence_retrieved"] for c in cites),
        "evidence_cited": sum(c["evidence_cited"] for c in cites),
        "correct_untraceable": sum(r["correct"] and not r["traceable"] for r in traced),
        "trace_classes": trace_classes,
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
    """{task id: {brain: "OK" | "casual" | "fallo"}}."""
    grid: dict[str, dict[str, str]] = {}
    for brain, result in results.items():
        for row in result["rows"]:
            if row["correct"]:
                cell = "OK"
            elif row.get("correct_lax"):
                cell = "casual"
            else:
                cell = "fallo"
            grid.setdefault(row["id"], {})[brain] = cell
    return dict(sorted(grid.items()))


def _pct(part: int, total: int) -> str:
    return f"{part}/{total} ({100 * _rate(part, total):.0f} %)"


def _route_pct(metrics: dict, part: int, total: int) -> str:
    """A percentage of the call route metrics, or no data for reports made before they existed."""
    return _pct(part, total) if metrics["has_route"] else "sin dato"


def _data_pct(available: bool, part: int, total: int) -> str:
    """A percentage, or no data for reports made before the metric existed."""
    return _pct(part, total) if available else "sin dato"


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
        ("Aciertos casuales (lucky hits)",
         lambda m: _data_pct(m["has_lax"], m["lucky"], m["n_core"])),
        ("Éxito fiel (correcto y con las herramientas requeridas)",
         lambda m: _pct(m["faithful"], m["n_core"])),
        ("Llegan a final_answer", lambda m: _pct(m["finished"], m["n_core"])),
        ("Casos de borde acertados", lambda m: _pct(m["edge_correct"], m["n_edge"])),
        ("Pasos sin llamada válida", lambda m: _pct(m["invalid_steps"], m["n_steps"])),
        ("Llamadas leídas de la etiqueta tool_call",
         lambda m: _route_pct(m, m["tag_calls"], m["tag_calls"] + m["fallback_calls"])),
        ("Llamadas leídas del respaldo Action",
         lambda m: _route_pct(m, m["fallback_calls"], m["tag_calls"] + m["fallback_calls"])),
        ("Cumplen el formato (llamada válida con etiqueta)",
         lambda m: _route_pct(m, m["tag_calls"], m["n_steps"])),
        ("Respuestas vacías", lambda m: _pct(m["empty_answers"], m["n_core"])),
        ("Busca él mismo en la base de conocimiento (si la necesita)",
         lambda m: _pct(m["kb_used"], m["kb_needed"])),
        ("Con búsqueda automática previa", lambda m: _pct(m["auto_search"], m["n_core"])),
        ("Pasos medios", lambda m: f"{m['mean_steps']:.1f}"),
        ("Tokens medios", lambda m: f"{m['mean_tokens']:.0f}"),
    ]
    table("Resumen por cerebro", ["Métrica"] + names,
          [[label] + [fn(brains[b]) for b in names] for label, fn in metrics])

    if any(brains[b]["n_traced"] for b in names):
        def trace_cell(b: str, count: int) -> str:
            m = brains[b]
            return _pct(count, m["n_traced"]) if m["n_traced"] else "sin dato"

        assert all(
            sum(brains[b]["trace_classes"].values()) == brains[b]["n_traced"] for b in names
        ), "the traceability classes must add up to the number of traced tasks"
        table(
            "Trazabilidad de las tareas que usan la base de conocimiento",
            ["Clase"] + names,
            [
                [text] + [trace_cell(b, brains[b]["trace_classes"][key]) for b in names]
                for key, text in TRACE_CLASSES.items()
            ]
            + [["**Total**"] + [trace_cell(b, brains[b]["n_traced"]) for b in names]],
        )

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
    parser.add_argument("--report", default="reports/phase4/phase4_eval.json")
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
