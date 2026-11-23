"""Generate training traces for the small thinking brain with the big vLLM model.

For every task of the training bank the agent runs once with the teacher (brain vllm). The
teacher is deterministic (temperature 0), so a second run would give the same trace: one run
per task is enough, and the quality filter is the task's own check, not a vote.

A trace is kept only if all of this holds:

1. The run finished, the final answer passes the strict numeric check of the task, and it
   used the tools the task requires (alternatives included).
2. The answer is traceable: its citations exist in the retrieved passages and the passage
   that holds the evidence is cited.
3. The format is clean: every model step is a tag call, there was no nudge, no reminder, no
   repeated call and no memory summary. A student that learns from a trace with a correction
   inside would learn to need the correction.
4. Every model output is short enough for the student (max_new_tokens is 1024 for the local
   brains). A trace that needs more than that cannot be reproduced by the student.

What is saved. Each kept trace has the exact conversation the teacher saw, one record per model
call (prompt and completion), so the SFT step can train on each assistant turn with the loss
only on the completion. Each task is logged, kept or not, with the reason, and the run can be
resumed: tasks already in the log are skipped.

Run (on the DGX, with VLLM_API_KEY in .env)::

    python -m agent.generate_traces --bench agent/bench/tasks_train.jsonl \\
        --out agent/data/agent_traces.jsonl --log agent/data/agent_traces_log.jsonl
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from agent.evaluate import (
    citation_report,
    check_answer,
    required_tools_met,
    automatic_tools,
    tools_used,
)

MAX_RAW_CHARS = 3000  # about 900 tokens of Spanish with <think>, under the 1024 of the student
MARKERS = ("Invalid tool call", "No tool call found", "[Warning", "Loop detected")


def read_jsonl(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: str | Path, row: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def recording(agent):
    """Make agent.generate keep every call: the prompt it got and the raw text it returned.

    Returns (records, restore): the list fills up while the agent runs, and restore() puts
    agent.generate back as it was. Only this object changes, which is enough because the loop
    calls self.generate.
    """
    records: list[dict] = []
    had_own = "generate" in vars(agent)
    original = agent.generate

    def generate(messages, brain, thinking=None):
        raw = original(messages, brain, thinking)
        records.append({"prompt": [dict(m) for m in messages], "completion": raw, "thinking": thinking})
        return raw

    def restore() -> None:
        if had_own:
            agent.generate = original
        else:
            del agent.generate

    agent.generate = generate
    return records, restore


def clean_reason(records: list[dict], response: dict, max_raw_chars: int = MAX_RAW_CHARS) -> str | None:
    """Why the format of this run is not clean, or None if it is."""
    steps = response["steps"]
    model_steps = [s for s in steps if not s.get("automatic")]
    if response.get("warnings"):
        return "warnings"
    if not records:
        return "no_model_call"
    if len(records) != len(model_steps):
        return "extra_model_calls"  # a summary of the memory, or a call that has no step
    if any(r["thinking"] is False for r in records):
        return "summary_call"
    if any(s.get("action") is None for s in model_steps):
        return "format_nudge"
    if any(s.get("call_route") != "tag" for s in model_steps):
        return "fallback_route"
    if model_steps[-1]["action"]["name"] != "final_answer":
        return "no_final_answer"
    for s in model_steps:
        if s["action"]["name"] == "final_answer" and s.get("observation"):
            return "reminder"
        if any(m in (s.get("observation") or "") for m in MARKERS):
            return "tool_warning"
    if any(r["prompt"][0]["content"] != records[0]["prompt"][0]["content"] for r in records):
        return "memory_summary"
    for before, after in zip(records, records[1:]):
        if after["prompt"][: len(before["prompt"])] != before["prompt"]:
            return "prompt_not_cumulative"
    if any(len(r["completion"]) > max_raw_chars for r in records):
        return "too_long"
    return None


def judge(task: dict, response: dict, records: list[dict], max_raw_chars: int = MAX_RAW_CHARS) -> dict:
    """The verdict of one run: the quality flags and the first reason to reject it, if any."""
    steps = response["steps"]
    used, auto = tools_used(steps), automatic_tools(steps)
    correct = bool(response["succeeded"] and check_answer(task, response["final_answer"], "strict"))
    tools_ok = required_tools_met(task, used | auto)
    report = citation_report(task, response["final_answer"], steps)
    traceable = True if report is None else bool(report["citations_valid"] and report["evidence_cited"])
    format_problem = clean_reason(records, response, max_raw_chars)
    reason = None
    if not correct:
        reason = "incorrect"
    elif not tools_ok:
        reason = "required_tools"
    elif not traceable:
        reason = "not_traceable"
    elif format_problem:
        reason = format_problem
    return {
        "correct": correct,
        "required_tools": tools_ok,
        "traceable": traceable,
        "format_problem": format_problem,
        "accepted": reason is None,
        "reason": reason or "ok",
    }


def system_for(agent, style: str, max_steps: int) -> str:
    """The system prompt the student will see: the teacher's, or the plain one without examples."""
    if style == "same":
        return agent.system_prompt(max_steps)
    before = agent.few_shot
    agent.few_shot = False
    try:
        return agent.system_prompt(max_steps)
    finally:
        agent.few_shot = before


def build_trace(task: dict, response: dict, records: list[dict], system: str | None = None) -> dict:
    """The saved trace: the conversation plus one prompt/completion pair per model call."""
    turns = []
    for r in records:
        prompt = [dict(m) for m in r["prompt"]]
        if system is not None:
            prompt[0] = {**prompt[0], "content": system}
        turns.append({"prompt": prompt, "completion": r["completion"]})
    last = turns[-1]
    return {
        "id": task["id"],
        "category": task.get("category"),
        "task": task["task"],
        "final_answer": response["final_answer"],
        "n_model_steps": len(turns),
        "messages": [*last["prompt"], {"role": "assistant", "content": last["completion"]}],
        "turns": turns,
    }


def run_task(agent, task: dict, brain: str, max_steps: int, max_raw_chars: int = MAX_RAW_CHARS,
             student_prompt: str = "same") -> tuple[dict, dict | None]:
    """Run one task with the teacher. Returns (log row, trace or None)."""
    records, restore = recording(agent)
    start = time.perf_counter()
    try:
        response = agent.run(task["task"], max_steps=max_steps, brain=brain).model_dump()
    finally:
        restore()
    latency = round(time.perf_counter() - start, 2)
    verdict = judge(task, response, records, max_raw_chars)
    row = {
        "id": task["id"],
        **verdict,
        "n_steps": response["n_steps"],
        "model_calls": len(records),
        "max_completion_chars": max((len(r["completion"]) for r in records), default=0),
        "latency_s": latency,
        "final_answer": response["final_answer"],
    }
    if not verdict["accepted"]:
        return row, None
    system = None if student_prompt == "same" else system_for(agent, student_prompt, max_steps)
    return row, build_trace(task, response, records, system)


def summarise_log(rows: list[dict]) -> str:
    reasons: dict[str, int] = {}
    for r in rows:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    detail = ", ".join(f"{k} {v}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]))
    return f"{reasons.get('ok', 0)}/{len(rows)} trazas aceptadas ({detail})"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--bench", default="agent/bench/tasks_train.jsonl")
    parser.add_argument("--out", default="agent/data/agent_traces.jsonl", help="accepted traces")
    parser.add_argument("--log", default="agent/data/agent_traces_log.jsonl", help="every task, kept or not")
    parser.add_argument("--brain", default="vllm")
    parser.add_argument("--ids", nargs="+", default=None, help="run only these task ids")
    parser.add_argument("--limit", type=int, default=None, help="run only the first N pending tasks")
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--max-raw-chars", type=int, default=MAX_RAW_CHARS)
    parser.add_argument("--rag-mode", choices=["auto", "tool", "off"], default="auto")
    parser.add_argument(
        "--teacher-prompt", choices=["fewshot", "plain"], default="fewshot",
        help="system prompt the teacher gets (the evaluation default is fewshot)",
    )
    parser.add_argument(
        "--student-prompt", choices=["same", "plain"], default="same",
        help="system prompt written in the traces: same as the teacher's, or plain (no examples)",
    )
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv()

    import httpx

    from agent.react_agent import ReActAgent

    tasks = read_jsonl(args.bench)
    if args.ids:
        tasks = [t for t in tasks if t["id"] in set(args.ids)]
    done = {r["id"] for r in read_jsonl(args.log)}
    pending = [t for t in tasks if t["id"] not in done]
    if args.limit:
        pending = pending[: args.limit]
    print(f"{len(tasks)} tareas, {len(done)} ya hechas, {len(pending)} por hacer", flush=True)

    agent = ReActAgent.from_env(rag_mode=args.rag_mode, few_shot=args.teacher_prompt == "fewshot")
    try:
        for i, task in enumerate(pending, 1):
            row, trace = run_task(
                agent, task, args.brain, args.max_steps, args.max_raw_chars, args.student_prompt
            )
            if trace is not None:
                append_jsonl(args.out, trace)  # first the trace, then the log: a crash repeats the task
            append_jsonl(args.log, row)
            print(f"{i}/{len(pending)} {task['id']}: {row['reason']} "
                  f"({row['model_calls']} llamadas, {row['latency_s']} s)", flush=True)
    except (ValueError, OSError, RuntimeError, httpx.HTTPError) as error:
        print(f"parado: {type(error).__name__}: {error}. Lo hecho está guardado; "
              "vuelve a lanzar el mismo comando y sigue donde lo dejó.", flush=True)
        raise SystemExit(1) from error
    print(summarise_log(read_jsonl(args.log)), flush=True)


if __name__ == "__main__":
    main()
