"""agent.generate_traces with a scripted teacher: no server, no model, no knowledge base."""

import json

from agent.generate_traces import (
    append_jsonl,
    clean_reason,
    judge,
    read_jsonl,
    recording,
    run_task,
    summarise_log,
)
from agent.react_agent import ReActAgent

TASK = {
    "id": "x001",
    "category": "ficha_calculo",
    "task": "Cuántos mg son 6 x 80 mg",
    "required_tools": ["dose_calculator"],
    "check": {"type": "number", "value": 480, "unit": ["mg"]},
}


class WordTokenizer:
    def encode(self, text):
        return text.split()


def call(name, **arguments):
    return f"<tool_call>\n{json.dumps({'name': name, 'arguments': arguments})}\n</tool_call>"


CALC = "<think>\nPrimero calculo.\n</think>\n\n" + call("dose_calculator", expression="6 * 80", decimals=0)
FINAL = "<think>\nYa está.\n</think>\n\n" + call("final_answer", answer="Son 480 mg.")


def agent_saying(outputs):
    agent = ReActAgent(rag_mode="off")
    agent._get_brain = lambda brain: (WordTokenizer(), None)
    script = iter(outputs)
    agent.generate = lambda messages, brain, thinking=None: next(script)
    return agent


def test_a_clean_correct_run_is_accepted_with_its_turns():
    row, trace = run_task(agent_saying([CALC, FINAL]), TASK, "base", max_steps=5)
    assert row["accepted"] and row["reason"] == "ok" and row["model_calls"] == 2
    assert trace["n_model_steps"] == 2
    first, second = trace["turns"]
    assert first["prompt"][0]["role"] == "system" and first["completion"] == CALC
    assert second["prompt"][: len(first["prompt"])] == first["prompt"]  # prompts only grow
    assert second["prompt"][-1]["role"] == "tool"  # the second call saw the result of the first
    assert trace["messages"][-1] == {"role": "assistant", "content": FINAL}
    assert [m["role"] for m in trace["messages"]] == [
        "system", "user", "assistant", "tool", "assistant"]


def test_run_task_leaves_the_agent_generate_as_it_was():
    agent = agent_saying([CALC, FINAL])
    own = agent.generate
    run_task(agent, TASK, "base", max_steps=5)
    assert agent.generate is own
    plain = ReActAgent(rag_mode="off")
    records, restore = recording(plain)
    restore()
    assert "generate" not in vars(plain)  # the class method is used again


def test_a_wrong_answer_is_rejected():
    wrong = call("final_answer", answer="Son 500 mg.")
    row, trace = run_task(agent_saying([CALC, wrong]), TASK, "base", max_steps=5)
    assert trace is None and row["reason"] == "incorrect"


def test_a_run_that_never_used_the_required_tool_is_rejected():
    row, trace = run_task(agent_saying([FINAL]), TASK, "base", max_steps=5)
    assert trace is None and row["reason"] == "required_tools"


def test_a_format_nudge_is_not_a_clean_trace():
    row, trace = run_task(
        agent_saying(["Voy a calcular el total.", CALC, FINAL]), TASK, "base", max_steps=5)
    assert trace is None and row["correct"] and row["reason"] == "format_nudge"


def test_a_reminder_or_a_repeated_call_is_not_a_clean_trace():
    agent = agent_saying([CALC, CALC, FINAL])  # the second identical call gets a warning
    row, trace = run_task(agent, TASK, "base", max_steps=5)
    assert trace is None and row["reason"] == "tool_warning"


def test_a_long_completion_is_rejected():
    long = "<think>\n" + "x" * 5000 + "\n</think>\n\n" + call("dose_calculator", expression="6 * 80")
    row, trace = run_task(agent_saying([long, FINAL]), TASK, "base", max_steps=5)
    assert trace is None and row["reason"] == "too_long"
    row, trace = run_task(agent_saying([long, FINAL]), TASK, "base", max_steps=5, max_raw_chars=6000)
    assert trace is not None


def test_a_summary_call_makes_the_trace_unclean():
    records = [{"prompt": [{"role": "system", "content": "s"}], "completion": "a", "thinking": False}]
    response = {"warnings": [], "steps": [{"action": {"name": "final_answer"}, "call_route": "tag"}]}
    assert clean_reason(records, response) == "summary_call"


def test_plain_student_prompt_replaces_only_the_system_message():
    agent = agent_saying([CALC, FINAL])
    agent.few_shot = True
    row, trace = run_task(agent, TASK, "base", max_steps=5, student_prompt="plain")
    teacher = agent.system_prompt(5)
    assert agent.few_shot is True  # restored
    assert trace["messages"][0]["content"] != teacher
    assert len(trace["messages"][0]["content"]) < len(teacher)
    assert all(t["prompt"][0]["content"] == trace["messages"][0]["content"] for t in trace["turns"])
    assert [m["role"] for m in trace["messages"]] == ["system", "user", "assistant", "tool", "assistant"]


def test_judge_flags_every_reason_in_order():
    response = {"succeeded": True, "final_answer": "Son 480 mg.", "n_steps": 1, "warnings": [],
                "steps": [{"thought": "", "action": {"name": "final_answer", "arguments": {}},
                           "call_route": "tag"}]}
    verdict = judge(TASK, response, [{"prompt": [{"role": "system", "content": "s"}],
                                      "completion": FINAL, "thinking": None}])
    assert verdict["correct"] and not verdict["required_tools"] and verdict["reason"] == "required_tools"


def test_jsonl_helpers_and_summary(tmp_path):
    path = tmp_path / "sub" / "log.jsonl"
    assert read_jsonl(path) == []
    append_jsonl(path, {"id": "a", "reason": "ok"})
    append_jsonl(path, {"id": "b", "reason": "incorrect"})
    assert [r["id"] for r in read_jsonl(path)] == ["a", "b"]
    assert summarise_log(read_jsonl(path)).startswith("1/2 trazas aceptadas")
