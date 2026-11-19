"""Phase 4 evaluation: success rate, steps and tokens on multi-tool tasks, per brain.

Each line of the benchmark (agent/bench/tasks.jsonl, see agent/bench/README.md) has a
task, the tools that must be involved, and a way to check the final answer automatically (a
number, a substring, a regex, or several of them). Twenty tasks that need at least two tools is
the minimum; tasks with "core": false are edge cases (impossible, blocked or broken tools)
that are reported apart. Run every brain::

    uv run python -m agent.evaluate --bench agent/bench/tasks.jsonl --brains base rlm thinking vllm

and put the resulting table in your report next to the JSON-vs-code-agent comparison.
Before the first run, uv run python -m agent.validate_bench checks the benchmark itself.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

# A number as written in Spanish or English: 7, 7.5, 7,5, 1.050, 1,050.5, 1.050,5, 8.400.000.
# It must not be glued to a letter on the left, so "2-8" gives 2 and 8 and "B12" gives nothing.
_NUMBER = re.compile(r"(?<![\w])-?\d+(?:[.,]\d+)*")
_CITATION = re.compile(r"\[([^\]]*)\]")

# "[0f15e47eed-0016] (dobutamina_85914.md)" at the start of each chunk returned by the retriever
_CHUNK_HEADER = re.compile(r"^\[([^\]\s]+)\] \(([^)]+\.md)\)", re.M)

UNIT_ALIASES = {
    "mL": {"ml", "milliliter", "milliliters", "millilitre", "millilitres",
           "mililitro", "mililitros", "cc"},
    "L": {"l", "liter", "liters", "litre", "litres", "litro", "litros"},
    "mg": {"mg", "milligram", "milligrams", "milligramo", "miligramo", "miligramos"},
    "g": {"g", "gram", "grams", "gramo", "gramos"},
    "mcg": {"mcg", "µg", "ug", "microgram", "micrograms", "microgramo", "microgramos"},
    "kg": {"kg", "kilogram", "kilograms", "kilogramo", "kilogramos"},
    "min": {"min", "mins", "minute", "minutes", "minuto", "minutos"},
    "h": {"h", "hr", "hrs", "hour", "hours", "hora", "horas"},
    "gotas": {"drop", "drops", "gota", "gotas", "gtt"},
    "gotas/min": {"gotas/min", "gotas/minuto", "gotas/minutos", "gotas por min",
                  "gotas por minuto", "gtt/min", "gtt/minuto", "drops/min", "drops/minute",
                  "drops per minute"},
    "mL/h": {"ml/h", "ml/hr", "ml/hora", "ml/horas", "ml por hora", "ml/hour", "ml per hour"},
    "mL/min": {"ml/min", "ml/minuto", "ml/minute", "ml por min", "ml por minuto"},
    "mg/mL": {"mg/ml", "mg/milliliter", "mg/millilitre", "mg/mililitro"},
    "mcg/kg/min": {"mcg/kg/min", "µg/kg/min", "ug/kg/min", "mcg/kg/minuto", "µg/kg/minuto",
                   "ug/kg/minuto", "mcg/kg/minute", "µg/kg/minute", "ug/kg/minute"},
    # units used in tasks.jsonl
    "mg/día": {"mg/dia", "mg/d", "mg/day", "mg/24h", "mg/24 h"},
    "mg/dosis": {"mg/dosis", "mg/dose"},
    "mL/dosis": {"ml/dosis", "ml/dose"},
    "mg/h": {"mg/h", "mg/hr", "mg/hora", "mg/horas", "mg por hora"},
    "%": {"%", "por ciento"},
}


def _fold(text: str) -> str:
    """Lower case without accents, for substring checks."""
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _readings(token: str) -> list[float]:
    """Every value an unsigned number token can mean.

    7,5 is 7.5; 1.050 is 1.05 (English) or 1050 (Spanish thousands), and both are
    returned because the text does not say which one was meant; 1.050,5 is 1050.5.
    """
    dots, commas = token.count("."), token.count(",")
    if not dots and not commas:
        return [float(token)]
    if dots and commas:  # the last separator is the decimal one
        decimal = "." if token.rfind(".") > token.rfind(",") else ","
        thousands = "," if decimal == "." else "."
        return [float(token.replace(thousands, "").replace(decimal, "."))]
    separator = "." if dots else ","
    parts = token.split(separator)
    if len(parts) > 2:  # 8.400.000: only thousands make sense
        return [float("".join(parts))]
    readings = [float(f"{parts[0]}.{parts[1]}")]
    if len(parts[1]) == 3 and parts[0] != "0":  # 1.050 / 1,050 may also be a thousand
        readings.append(float(parts[0] + parts[1]))
    return readings

def _unit_key(text: str) -> str:
    """Folded unit text: no accents, lower case, micro/mu -> mc, single spaces, no spaces
    around '/'."""
    text = _fold(text).replace("μ", "mc")  # _fold (NFKD) turns µ U+00B5 into μ U+03BC
    text = re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()
    return re.sub(r"\s*/\s*", "/", text)

def _build_alias_index() -> dict[str, frozenset[str]]:
    index: dict[str, frozenset[str]] = {}
    for canonical, aliases in UNIT_ALIASES.items():
        group = frozenset(_unit_key(a) for a in set(aliases) | {canonical})
        for key in group:
            if key in index and index[key] != group:
                raise ValueError(f"unit alias {key!r} appears in two different groups")
            index[key] = group
    return index

_ALIAS_INDEX = _build_alias_index()

def _unit_aliases(unit: str) -> frozenset[str]:
    key = _unit_key(unit)
    return _ALIAS_INDEX.get(key, frozenset({key}))

def _starts_with_unit(tail: str, alias: str) -> bool:
    """tail starts with alias and the unit does not continue (mg must not match mg/kg or mgs)."""
    if not tail.startswith(alias):
        return False
    rest = tail[len(alias):len(alias) + 1]
    return not rest or not (rest.isalnum() or rest == "/")

def number_values(text: str) -> list[float]:
    """Every value that the numbers written in text can mean (see _readings)."""
    values = []
    for token in _NUMBER.findall(text):
        sign = -1.0 if token.startswith("-") else 1.0
        values.extend(sign * value for value in _readings(token.lstrip("-")))
    return values

def final_part(answer: str) -> str:
    """The text that strict mode scores: the final answer without [file#n] citations.

    final_answer is already the content of the agent's final_answer tool, so all of it counts
    (multi-result answers, as in t19 and t20, may span several paragraphs).
    """
    return _CITATION.sub(" ", answer).strip()

def _token_values(token: str) -> list[float]:
    sign = -1.0 if token.startswith("-") else 1.0
    return [sign * v for v in _readings(token.lstrip("-"))]

def _number_with_unit(text: str, value: float, tolerance: float, units: list[str]) -> bool:
    """Some number within tolerance of value, written right before one of the units."""
    wanted = set().union(*(_unit_aliases(u) for u in units)) if units else set()
    for match in _NUMBER.finditer(text):
        if not any(abs(n - value) <= tolerance + 1e-9 for n in _token_values(match.group())):
            continue
        if not wanted:
            return True
        tail = _unit_key(text[match.end(): match.end() + 30])
        if any(_starts_with_unit(tail, alias) for alias in wanted):
            return True
    return False

def check_answer(task: dict, final_answer: str, mode: str = "strict") -> bool:
    """Automatic check of the final answer, according to the task's check field.

    Kinds: contains, regex, all, any (as before) and number. With mode="lax" (the old
    behaviour) number accepts any matching number anywhere in the answer. With
    mode="strict" the number must be in the final part of the answer (see final_part) and
    followed by the unit in check["unit"] (a string or a list; aliases like mcg/µg and
    mL/h/ml/h are equivalent). A number check with no unit is only valid in strict mode if
    it sets "unitless": true (validate_bench enforces it).
    """
    return _check(task.get("check", {}), final_answer, mode)


def _check(check: dict, answer: str, mode: str = "strict") -> bool:
    kind, value = check.get("type"), check.get("value")
    if kind == "contains":
        result = _fold(str(value)) in _fold(answer)
    elif kind == "regex":
        result = re.search(value, answer) is not None
    elif kind == "number":
        tolerance = check.get("tolerance", 0)
        if mode == "lax":
            result = any(abs(n - float(value)) <= tolerance + 1e-9 for n in number_values(answer))
        else:
            unit = check.get("unit")
            units = [unit] if isinstance(unit, str) else list(unit or [])
            result = _number_with_unit(final_part(answer), float(value), tolerance, units)
    elif kind == "all":
        result = all(_check(c, answer, mode) for c in check.get("checks", []))
    elif kind == "any":
        result = any(_check(c, answer, mode) for c in check.get("checks", []))
    else:
        return False
    return not result if check.get("negate") else result


def tools_used(steps: list[dict]) -> set[str]:
    """Tools the model chose to call. Steps the agent made by itself are not counted."""
    return {s["action"]["name"] for s in steps if s.get("action") and not s.get("automatic")}


def automatic_tools(steps: list[dict]) -> set[str]:
    """Tools the agent ran by itself before the first step of the model (rag_mode auto)."""
    return {s["action"]["name"] for s in steps if s.get("action") and s.get("automatic")}


def retrieved_chunks(steps: list[dict]) -> tuple[dict[str, str], str]:
    """chunk id -> file for every chunk the knowledge base returned in this run, plus the
    text of all those observations (folded, for evidence lookups)."""
    chunks, texts = {}, []
    for s in steps:
        action = s.get("action") or {}
        if action.get("name") == "search_knowledge_base" and s.get("observation"):
            chunks.update(_CHUNK_HEADER.findall(s["observation"]))
            texts.append(s["observation"])
    return chunks, re.sub(r"\s+", " ", _fold(" ".join(texts)))


def citation_report(task: dict, answer: str, steps: list[dict]) -> dict | None:
    """Traceability of the answer. None when the task does not rely on the knowledge base."""
    if "search_knowledge_base" not in task.get("required_tools", []):
        return None
    chunks, observed = retrieved_chunks(steps)
    stems = {f.removesuffix(".md"): f for f in chunks.values()}
    cites = [
        c.strip()
        for m in _CITATION.findall(answer)
        for c in re.split(r"[;,]", m)
        if c.strip()
    ]
    cited_files, invalid = set(), []
    for c in cites:
        if c in chunks:
            cited_files.add(chunks[c])
        elif c.removesuffix(".md") in stems:  # file-level citation: accepted but weaker
            cited_files.add(stems[c.removesuffix(".md")])
        else:
            invalid.append(c)
    evidence = task.get("evidence", [])
    evidence_files = {e["file"] for e in evidence}
    return {
        "cited": bool(cites),
        "invalid_citations": invalid,
        "citations_valid": bool(cites) and not invalid,
        "evidence_retrieved": all(
            re.sub(r"\s+", " ", _fold(e["text"])) in observed for e in evidence
        ),
        "evidence_cited": bool(evidence_files) and evidence_files <= cited_files,
    }


def summarise(rows: list[dict]) -> dict:
    n = max(len(rows), 1)
    out = {
        "n_tasks": len(rows),
        "success_rate": sum(r["correct"] for r in rows) / n,
        "mean_steps": sum(r["n_steps"] for r in rows) / n,
        "mean_tokens": sum(r["tokens_used"] for r in rows) / n,
    }

    if rows and all("correct_lax" in r for r in rows):
        out["success_rate_lax"] = sum(r["correct_lax"] for r in rows) / n
        out["lucky_hits"] = sum(r["correct_lax"] and not r["correct"] for r in rows)

    traced = [r for r in rows if r.get("traceable") is not None]
    if traced:
        out["traceable_rate"] = sum(r["traceable"] for r in traced) / len(traced)
        out["uncited_rate"] = sum(not r["citations"]["cited"] for r in traced) / len(traced)
        out["invalid_citation_rate"] = sum(bool(r["citations"]["invalid_citations"]) for r in traced) / len(traced)
    return out


def summarise_brain(rows: list[dict], config: dict | None = None) -> dict:
    """The entry of one brain in the report: core and edge summaries, per category, the rows."""
    core = [r for r in rows if r.get("core", True)]
    edge = [r for r in rows if not r.get("core", True)]
    categories = sorted({r.get("category", "-") for r in rows})
    return {
        "config": config or {},
        **summarise(core),
        "edge": summarise(edge),
        "by_category": {
            c: summarise([r for r in rows if r.get("category", "-") == c]) for c in categories
        },
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--bench", default="agent/bench/tasks.jsonl")
    parser.add_argument("--brains", nargs="+", default=["rlm"])
    parser.add_argument("--ids", nargs="+", default=None, help="run only these task ids")
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--out", default="reports/phase4/phase4_eval.json")
    parser.add_argument(
        "--rag-mode",
        choices=["auto", "tool", "off"],
        default="auto",
        help="auto: the agent searches with the task text before the first step and the model "
        "can still search (default); "
        "tool: the model searches the knowledge base if it wants; "
        "off: no knowledge base",
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="leave out CIMA, convert_units, dose_calculator and the sheet tool",
    )
    parser.add_argument("--few-shot", type=bool, default=True)
    parser.add_argument("--check-mode", choices=["strict", "lax"], default="strict")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv()  # ARCA_RLM_ADAPTER and the model ids live in each teammate's .env

    import httpx

    from agent.react_agent import ReActAgent

    tasks = [
        json.loads(line)
        for line in Path(args.bench).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.ids:
        tasks = [t for t in tasks if t.get("id") in set(args.ids)]
    agent = ReActAgent.from_env(rag_mode=args.rag_mode, use_tools=not args.no_tools, few_shot=args.few_shot)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    results = {}
    for brain in args.brains:
        rows = []
        try:
            for i, task in enumerate(tasks, 1):
                response = agent.run(task["task"], max_steps=args.max_steps, brain=brain)
                response = response.model_dump()
                ok_ans = response["succeeded"] and check_answer(task, response["final_answer"], args.check_mode)
                lax = response["succeeded"] and check_answer(task, response["final_answer"], "lax")
                used = tools_used(response["steps"])
                by_agent = automatic_tools(response["steps"])
                report = citation_report(task, response["final_answer"], response["steps"])
                rows.append(
                    {
                        **task,
                        **response,
                        "correct": ok_ans, 
                        "correct_lax": lax,
                        "tools_used": sorted(used),
                        "auto_tools": sorted(by_agent),
                        "required_tools_used": set(task.get("required_tools", []))
                        <= used | by_agent,
                        "citations": report,
                        "traceable":  None if report is None else bool(
                            ok_ans and report["citations_valid"] and report["evidence_cited"]
                        )
                    }
                )
                print(
                    f"[{brain}] {i}/{len(tasks)} {task.get('id', '?')}: "
                    f"{'OK' if ok_ans else 'fail'} ({response['n_steps']} steps)",
                    flush=True,
                )
        except (ValueError, OSError, RuntimeError, httpx.HTTPError) as error:  # e.g. no rlm adapter, no vLLM key or server
            print(f"[{brain}] skipped: {error}", flush=True)
            results[brain] = {"error": f"{type(error).__name__}: {error}", "rows": rows}
            out.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=list))
            continue
        config = {
            "rag_mode": args.rag_mode,
            "use_tools": not args.no_tools,
            "max_steps": args.max_steps,
        }
        results[brain] = summarise_brain(rows, config)
        # Saved after every brain, so a failure in a later one never loses what is done. It is
        # written before printing the summary, so a mistake there cannot lose a finished run.
        out.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=list))
        print(
            f"{brain:>9}: success {results[brain]['success_rate']:.2f} "
            f"· steps {results[brain]['mean_steps']:.1f} · edge cases "
            f"{results[brain]['edge']['success_rate']:.2f} ({results[brain]['edge']['n_tasks']})",
            flush=True,
        )


if __name__ == "__main__":
    main()
