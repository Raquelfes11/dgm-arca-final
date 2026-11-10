"""Check the task benchmark itself, before spending GPU time on it.

    uv run python -m agent.validate_bench                   # structure, arithmetic, evidence
    uv run python -m agent.validate_bench --retrieval       # also: does the retriever find it?

The benchmark (agent/bench/tasks.jsonl) is only worth as much as its answers, so this
script checks that:

* every task has the fields agent/evaluate.py needs, a well-formed check, unique ids
  and, for the core tasks, at least two different tools;
* the arithmetic written in answer_exprs gives the value the check expects (the number
  in the check is not typed by hand and forgotten);
* every evidence passage is still in the corpus. CIMA updates its data sheets, so this is
  the check that tells you a task has gone stale after rag.download_corpus is run again;
* with --retrieval: whether the phase-3 retriever (the one behind search_knowledge_base)
  brings that passage in its top k for the task text. It separates tasks the agent cannot
  solve because the passage never reaches it from tasks it solves badly.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import unicodedata
from pathlib import Path

BENCH = Path(__file__).parent / "bench" / "tasks.jsonl"
CORPUS = Path(__file__).resolve().parent.parent / "rag" / "corpus"
CHECK_KINDS = {"contains", "regex", "number", "all", "any"}
REQUIRED_FIELDS = ("id", "task", "required_tools", "check")


def load_tasks(path: Path = BENCH) -> list[dict]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def known_tools() -> set[str]:
    """Names the agent can call: the phase-2 registry plus the two the agent adds."""
    from tool_use.tools import default_registry

    return set(default_registry().tools) | {"search_knowledge_base", "final_answer"}


def evaluate_expression(expression: str) -> float:
    """Evaluate plain arithmetic (numbers, + - * / ** and parentheses) without eval."""

    def walk(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd):
            value = walk(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp):
            left, right = walk(node.left), walk(node.right)
            operations = {
                ast.Add: lambda: left + right,
                ast.Sub: lambda: left - right,
                ast.Mult: lambda: left * right,
                ast.Div: lambda: left / right,
                ast.Pow: lambda: left**right,
            }
            if type(node.op) in operations:
                return operations[type(node.op)]()
        raise ValueError(f"unsupported expression: {expression!r}")

    return walk(ast.parse(expression, mode="eval").body)


def _flatten(check: dict) -> list[dict]:
    """The leaf checks of a check (all/any are expanded), in order."""
    if check.get("type") in ("all", "any"):
        return [leaf for sub in check.get("checks", []) for leaf in _flatten(sub)]
    return [check]


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text)


def check_problems(check: dict) -> list[str]:
    problems = []
    kind = check.get("type")
    if kind not in CHECK_KINDS:
        return [f"unknown check type {kind!r}"]
    if kind in ("all", "any"):
        if not check.get("checks"):
            problems.append(f"'{kind}' check without sub-checks")
        for sub in check.get("checks", []):
            problems += check_problems(sub)
    elif "value" not in check:
        problems.append(f"'{kind}' check without value")
    elif kind == "regex":
        try:
            re.compile(check["value"])
        except re.error as error:
            problems.append(f"regex does not compile: {error}")
    elif kind == "number":
        try:
            float(check["value"])
        except (TypeError, ValueError):
            problems.append(f"number check with a non-numeric value {check['value']!r}")
    return problems


def validate(
    tasks: list[dict], corpus_dir: Path | None = None, tools: set[str] | None = None
) -> list[str]:
    """Problems found in the benchmark, as readable lines (empty list = all good).

    corpus_dir=None skips the evidence check and tools=None the tool names.
    """
    problems: list[str] = []
    ids = [t.get("id") for t in tasks]
    for duplicated in sorted({i for i in ids if ids.count(i) > 1}, key=str):
        problems.append(f"{duplicated}: repeated id")
    corpus_cache: dict[str, str] = {}
    for task in tasks:
        name = task.get("id", "?")
        for field in REQUIRED_FIELDS:
            if field not in task:
                problems.append(f"{name}: missing field '{field}'")
        if "check" not in task:
            continue
        problems += [f"{name}: {p}" for p in check_problems(task["check"])]
        required = task.get("required_tools", [])
        if task.get("core", True) and len(set(required)) < 2:
            problems.append(f"{name}: a core task must need at least two different tools")
        if tools is not None:
            problems += [f"{name}: unknown tool {t!r}" for t in required if t not in tools]

        numbers = [c for c in _flatten(task["check"]) if c.get("type") == "number"]
        expressions = task.get("answer_exprs", [])
        if expressions and len(expressions) != len(numbers):
            problems.append(f"{name}: {len(expressions)} answer_exprs for {len(numbers)} numbers")
        for expression, leaf in zip(expressions, numbers):
            try:
                value = evaluate_expression(expression)
            except (ValueError, SyntaxError, ZeroDivisionError) as error:
                problems.append(f"{name}: cannot evaluate {expression!r}: {error}")
                continue
            if abs(value - float(leaf["value"])) > leaf.get("tolerance", 0) + 1e-9:
                problems.append(f"{name}: {expression} = {value:g} but the check expects {leaf['value']}")

        if corpus_dir is None:
            continue
        for item in task.get("evidence", []):
            path = corpus_dir / item["file"]
            if not path.exists():
                problems.append(f"{name}: evidence file {item['file']} is not in the corpus")
                continue
            if item["file"] not in corpus_cache:
                corpus_cache[item["file"]] = _normalise(path.read_text(encoding="utf-8"))
            if _normalise(item["text"]) not in corpus_cache[item["file"]]:
                problems.append(f"{name}: evidence not found in {item['file']}: {item['text'][:60]!r}")
    return problems


def retrieval_report(tasks: list[dict], k: int) -> list[tuple[str, int, int]]:
    """For each task with evidence: how many passages the retriever brings in its top k."""
    from agent.react_agent import _get_retriever

    retriever = _get_retriever()
    report = []
    for task in tasks:
        evidence = task.get("evidence", [])
        if not evidence:
            continue
        retrieved = " ".join(_normalise(h.chunk.text) for h in retriever.search(task["task"], k))
        found = sum(_normalise(item["text"]) in retrieved for item in evidence)
        report.append((task["id"], found, len(evidence)))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--bench", default=str(BENCH))
    parser.add_argument("--corpus", default=str(CORPUS))
    parser.add_argument("--retrieval", action="store_true", help="needs the embedding model")
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()

    tasks = load_tasks(Path(args.bench))
    corpus = Path(args.corpus)
    if not corpus.exists() or not any(corpus.glob("*.md")):
        print(f"Aviso: no hay corpus en {corpus}; no se comprueba la evidencia.")
        corpus = None
    problems = validate(tasks, corpus, known_tools())
    core = sum(1 for t in tasks if t.get("core", True))
    print(f"{len(tasks)} tareas ({core} principales, {len(tasks) - core} de borde)")
    for problem in problems:
        print("  PROBLEMA:", problem)
    print("El banco es válido." if not problems else f"{len(problems)} problemas.")

    if args.retrieval:
        report = retrieval_report(tasks, args.k)
        print(f"\nPasajes de evidencia en los {args.k} primeros resultados del retriever:")
        for task_id, found, total in report:
            print(f"  {task_id}: {found}/{total}")
        all_found = sum(f == t for _, f, t in report)
        print(f"Tareas con toda su evidencia recuperada: {all_found}/{len(report)}")
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
