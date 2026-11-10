"""Phase 4 evaluation: success rate, steps and tokens on multi-tool tasks, per brain.

Each line of the benchmark (``agent/bench/tasks.jsonl``, see ``agent/bench/README.md``) has a
task, the tools that must be involved, and a way to check the final answer automatically (a
number, a substring, a regex, or several of them). Twenty tasks that need at least two tools is
the minimum; tasks with ``"core": false`` are edge cases (impossible, blocked or broken tools)
that are reported apart. Run every brain::

    uv run python -m agent.evaluate --bench agent/bench/tasks.jsonl --brains base rlm thinking

and put the resulting table in your report next to the JSON-vs-code-agent comparison.
Before the first run, ``uv run python -m agent.validate_bench`` checks the benchmark itself.
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


def _fold(text: str) -> str:
    """Lower case without accents, for substring checks."""
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _readings(token: str) -> list[float]:
    """Every value an unsigned number token can mean.

    ``7,5`` is 7.5; ``1.050`` is 1.05 (English) or 1050 (Spanish thousands), and both are
    returned because the text does not say which one was meant; ``1.050,5`` is 1050.5.
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


def number_values(text: str) -> list[float]:
    """Every value that the numbers written in ``text`` can mean (see ``_readings``)."""
    values = []
    for token in _NUMBER.findall(text):
        sign = -1.0 if token.startswith("-") else 1.0
        values.extend(sign * value for value in _readings(token.lstrip("-")))
    return values


def check_answer(task: dict, final_answer: str) -> bool:
    """Automatic check of the final answer, according to the task's ``check`` field.

    Kinds: ``contains`` (ignores case and accents), ``regex`` (as written: use ``(?i)`` for
    case), ``number`` (any number in the answer within ``tolerance`` of ``value``; reads
    ``7,5`` and ``1.050`` the Spanish way too), ``all`` and ``any`` (lists of checks in
    ``checks``). Any check can set ``"negate": true`` to require the opposite.
    """
    return _check(task.get("check", {}), final_answer)


def _check(check: dict, answer: str) -> bool:
    kind, value = check.get("type"), check.get("value")
    if kind == "contains":
        result = _fold(str(value)) in _fold(answer)
    elif kind == "regex":
        result = re.search(value, answer) is not None
    elif kind == "number":
        tolerance = check.get("tolerance", 0)
        result = any(abs(n - float(value)) <= tolerance + 1e-9 for n in number_values(answer))
    elif kind == "all":
        result = all(_check(c, answer) for c in check.get("checks", []))
    elif kind == "any":
        result = any(_check(c, answer) for c in check.get("checks", []))
    else:
        return False
    return not result if check.get("negate") else result


def tools_used(steps: list[dict]) -> set[str]:
    return {s["action"]["name"] for s in steps if s.get("action")}


def summarise(rows: list[dict]) -> dict:
    n = max(len(rows), 1)
    return {
        "n_tasks": len(rows),
        "success_rate": sum(r["correct"] for r in rows) / n,
        "mean_steps": sum(r["n_steps"] for r in rows) / n,
        "mean_tokens": sum(r["tokens_used"] for r in rows) / n,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--bench", default="agent/bench/tasks.jsonl")
    parser.add_argument("--brains", nargs="+", default=["rlm"])
    parser.add_argument("--ids", nargs="+", default=None, help="run only these task ids")
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--out", default="reports/phase4_eval.json")
    args = parser.parse_args()

    from agent.react_agent import ReActAgent

    tasks = [
        json.loads(line)
        for line in Path(args.bench).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.ids:
        tasks = [t for t in tasks if t.get("id") in set(args.ids)]
    agent = ReActAgent.from_env()
    results = {}
    for brain in args.brains:
        rows = []
        for task in tasks:
            response = agent.run(task["task"], max_steps=args.max_steps, brain=brain).model_dump()
            ok = response["succeeded"] and check_answer(task, response["final_answer"])
            used = tools_used(response["steps"])
            rows.append(
                {
                    **task,
                    **response,
                    "correct": ok,
                    "tools_used": sorted(used),
                    "required_tools_used": set(task.get("required_tools", [])) <= used,
                }
            )
        core = [r for r in rows if r.get("core", True)]
        edge = [r for r in rows if not r.get("core", True)]
        categories = sorted({r.get("category", "-") for r in rows})
        results[brain] = {
            **summarise(core),
            "edge": summarise(edge),
            "by_category": {
                c: summarise([r for r in rows if r.get("category", "-") == c]) for c in categories
            },
            "rows": rows,
        }
        print(
            f"{brain:>9}: success {results[brain]['success_rate']:.2f} "
            f"· steps {results[brain]['mean_steps']:.1f} · edge cases "
            f"{results[brain]['edge']['success_rate']:.2f} ({len(edge)})"
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=list))


if __name__ == "__main__":
    main()
