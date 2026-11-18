"""Score an evaluation report again with the current benchmark, without running any model.

    uv run python -m agent.rescore --report reports/fix/04/fix04_auto.json
    uv run python -m agent.rescore --report reports/fix/04/fix04_auto.json --out reports/otro.json

The report keeps the final answer of every task, so when the way of checking an answer changes
(a better regular expression, a stricter number check) the old runs can be scored again instead
of being run again. Only "correct" and "check" change in each row; the steps, the tools used and
the tokens stay as they were. The result is written next to the report (name_rescored.json) and
can be read with agent.analyze_eval.

The summaries add success_rate_lax and lucky_hits (right in lax, wrong in strict), which is
how many hits of the old check were by chance.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.evaluate import check_answer, summarise_brain


def rescore(results: dict, tasks: dict[str, dict], mode: str = "strict") -> dict:
    """The report with every row checked again against tasks (by id). Skipped brains stay."""
    rescored = {}
    for brain, result in results.items():
        if "error" in result or not result.get("rows"):
            rescored[brain] = result
            continue
        rows = []
        for row in result["rows"]:
            original = row.get("correct_original", row.get("correct", False))
            task = tasks.get(row["id"])
            if task is None:  # a task that is no longer in the benchmark: keep it as it was
                rows.append({**row, "correct_original": original,
                             "correct_lax": row.get("correct_lax", row.get("correct", False))})
                continue
            answered = bool(row.get("succeeded"))
            answer = row.get("final_answer") or ""
            rows.append(
                {
                    **row,
                    "check": task["check"],
                    "core": task.get("core", row.get("core", True)),
                    "correct_original": original,
                    "correct_lax": answered and check_answer(task, answer, "lax"),
                    "correct": answered and check_answer(task, answer, mode),
                }
            )
        rescored[brain] = summarise_brain(rows, result.get("config"))
    return rescored


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--report", required=True)
    parser.add_argument("--bench", default="agent/bench/tasks.jsonl")
    parser.add_argument("--check-mode", choices=["strict", "lax"], default="strict")
    parser.add_argument("--out", default=None, help="default: <report>_rescored.json")
    args = parser.parse_args()

    tasks = {}
    for line in Path(args.bench).read_text(encoding="utf-8").splitlines():
        if line.strip():
            task = json.loads(line)
            tasks[task["id"]] = task
    results = json.loads(Path(args.report).read_text(encoding="utf-8"))
    rescored = rescore(results, tasks, args.check_mode)
    out = Path(args.out) if args.out else Path(args.report).with_suffix("")
    if not args.out:
        out = out.with_name(out.name + "_rescored.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rescored, indent=2, ensure_ascii=False, default=list))
    for brain, result in rescored.items():
        before = results[brain]
        if "error" in result:
            continue
        lax = result.get("success_rate_lax", float("nan"))
        print(
            f"{brain}: core {before['success_rate']:.2f} (before) -> {lax:.2f} (lax) -> "
            f"{result['success_rate']:.2f} ({args.check_mode}) · "
            f"lucky hits {result.get('lucky_hits', 0)} · "
            f"edge {before['edge']['success_rate']:.2f} -> {result['edge']['success_rate']:.2f}"
        )
        for row in result["rows"]:
            if row.get("correct_lax") and not row.get("correct"):
                print(f"    lucky: {row['id']}")
            elif row.get("correct") and not row.get("correct_lax"):
                print(f"    only {args.check_mode} accepts it: {row['id']}")
    print(f"written: {out}")


if __name__ == "__main__":
    main()
