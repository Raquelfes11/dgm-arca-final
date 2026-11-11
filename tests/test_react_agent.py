"""The ReAct loop with a scripted "model": no weights are loaded.

``generate`` is replaced by a function that returns prepared outputs, and the tokenizer by one
that counts words. That is enough to test the loop rules (repeated calls, tools that need
confirmation, memory) deterministically.
"""

import json

import pytest

from agent.memory import ConversationMemory
from agent.react_agent import MAX_REPEATED_CALLS, ReActAgent, _resolve_adapter
from tool_use.tools import SHEETS_DIR


class WordTokenizer:
    def encode(self, text):
        return text.split()


def tool_call(name, **arguments):
    return f"<tool_call>\n{json.dumps({'name': name, 'arguments': arguments})}\n</tool_call>"


def scripted_agent(outputs, summary="resumen de prueba"):
    """An agent whose model says ``outputs`` one after another. Summary calls are counted."""
    agent = ReActAgent()
    agent._get_brain = lambda brain: (WordTokenizer(), None)
    agent.summary_calls = 0
    script = iter(outputs)

    def generate(messages, brain, thinking=None):
        if thinking is False:  # a call from summarize()
            agent.summary_calls += 1
            return summary
        return next(script)

    agent.generate = generate
    return agent


CALC = tool_call("dose_calculator", expression="1 + 1", decimals=2)


def test_second_identical_call_is_warned_and_third_stops_the_run():
    agent = scripted_agent([CALC] * MAX_REPEATED_CALLS)
    response = agent.run("task", max_steps=10, brain="base")
    assert not response.succeeded
    assert response.n_steps == MAX_REPEATED_CALLS  # it did not use the 10 steps
    assert "Warning" not in response.steps[0].observation
    assert "Warning" in response.steps[1].observation  # the 2nd one still ran, with a warning
    assert response.steps[2].observation.startswith("Loop detected")


def test_different_arguments_are_not_a_loop():
    calls = [tool_call("dose_calculator", expression=f"{i} + 1", decimals=2) for i in range(4)]
    agent = scripted_agent([*calls, tool_call("final_answer", answer="done")])
    response = agent.run("task", max_steps=10, brain="base")
    assert response.succeeded and response.final_answer == "done"
    assert all("Warning" not in (s.observation or "") for s in response.steps)


def test_tool_that_requires_confirmation_is_not_run():
    sheet = tool_call(
        "create_preparation_sheet",
        medication="x",
        concentration="1 mg/ml",
        dose="1 mg",
        administration="1 ml",
        steps="a",
    )
    agent = scripted_agent([sheet, tool_call("final_answer", answer="no puedo")])
    files_before = set(SHEETS_DIR.glob("*")) if SHEETS_DIR.exists() else set()
    response = agent.run("task", max_steps=5, brain="base")
    files_after = set(SHEETS_DIR.glob("*")) if SHEETS_DIR.exists() else set()
    assert files_after == files_before  # the PDF was not written
    assert "requires user confirmation" in response.steps[0].observation
    assert response.succeeded and response.final_answer == "no puedo"  # the model could go on
    record = agent._call_tool("create_preparation_sheet", {})
    assert not record.ok and record.requires_confirmation


def test_run_fills_model_and_tokens_used():
    agent = scripted_agent([tool_call("final_answer", answer="ok")])
    agent._tokens_used = 999  # left over from a previous run: must be reset
    response = agent.run("task", max_steps=3, brain="base")
    assert response.model and response.tokens_used == 0  # scripted model counts no tokens


def test_run_compresses_when_the_budget_is_small():
    calls = [tool_call("dose_calculator", expression=f"{i} + 1", decimals=2) for i in range(6)]
    agent = scripted_agent([*calls, tool_call("final_answer", answer="done")])
    agent.token_budget = 120  # the system prompt alone is bigger: always over budget
    response = agent.run("task", max_steps=10, brain="base")
    assert response.succeeded and response.final_answer == "done"
    assert agent.summary_calls >= 1


def test_summarize_falls_back_when_the_model_returns_only_an_unclosed_think():
    agent = scripted_agent([])
    agent.generate = lambda messages, brain, thinking=None: "<think>\nhmm, let me see"
    summary = agent.summarize([{"role": "user", "content": "la tarea"}], "thinking")
    assert "la tarea" in summary


def make_memory(**kwargs):
    memory = ConversationMemory("sys", count_tokens=len, token_budget=10, **kwargs)
    memory.add("user", "THE TASK")
    for i in range(4):
        memory.add("assistant", f"call {i}")
        memory.add("tool", "x" * 50, name="t")
    return memory


def test_pin_first_keeps_the_task_verbatim():
    memory = make_memory(keep_last=2, pin_first=True)
    assert memory.compress(lambda old: "summary")
    assert memory.messages[0]["content"] == "THE TASK"
    assert len(memory.messages) == 1 + 2


def test_without_pin_first_the_task_can_be_summarised():
    memory = make_memory(keep_last=2)
    seen = []
    memory.compress(lambda old: seen.extend(old) or "summary")
    assert any(m["content"] == "THE TASK" for m in seen)


def test_kept_messages_never_start_with_an_orphan_tool_result():
    memory = make_memory(keep_last=3, pin_first=True)  # a cut of 3 would start on a tool message
    memory.compress(lambda old: "summary")
    kept = memory.messages[1:]
    assert kept[0]["role"] == "assistant"
    assert len(kept) >= 3


def test_long_tool_results_are_cut_for_the_summarizer_only():
    memory = ConversationMemory("sys", count_tokens=len, token_budget=10, keep_last=2, obs_chars=20)
    memory.add("assistant", "old call")
    memory.add("tool", "y" * 500, name="t")  # old: will be summarised
    memory.add("assistant", "recent call")
    memory.add("tool", "z" * 500, name="t")  # recent: stays as it is
    seen = []
    assert memory.compress(lambda old: seen.extend(old) or "summary")
    assert len(seen[1]["content"]) < 40  # what the summarizer saw was cut
    assert memory.messages[1]["content"] == "z" * 500  # the live message was not touched


def test_adapter_missing_without_repo_fails_with_a_clear_message(monkeypatch, tmp_path):
    monkeypatch.setenv("ARCA_RLM_ADAPTER", str(tmp_path / "missing"))
    monkeypatch.delenv("ARCA_RLM_ADAPTER_REPO", raising=False)
    with pytest.raises(FileNotFoundError, match="ARCA_RLM_ADAPTER_REPO"):
        _resolve_adapter()


def test_adapter_missing_is_downloaded_from_the_repo(monkeypatch, tmp_path):
    target = tmp_path / "adapter"
    downloads = []
    monkeypatch.setenv("ARCA_RLM_ADAPTER", str(target))
    monkeypatch.setenv("ARCA_RLM_ADAPTER_REPO", "someone/some-adapter")
    monkeypatch.setattr(
        "huggingface_hub.snapshot_download",
        lambda repo, local_dir: downloads.append((repo, local_dir)),
    )
    assert _resolve_adapter() == str(target)
    assert downloads == [("someone/some-adapter", str(target))]


def test_adapter_not_set_is_an_error(monkeypatch):
    monkeypatch.delenv("ARCA_RLM_ADAPTER", raising=False)
    with pytest.raises(ValueError, match="ARCA_RLM_ADAPTER"):
        _resolve_adapter()


def test_run_creates_its_memory_with_the_task_pinned(monkeypatch):
    seen = []

    class SpyMemory(ConversationMemory):
        def render(self):
            seen.append(self.pin_first)
            return super().render()

    monkeypatch.setattr("agent.react_agent.ConversationMemory", SpyMemory)
    agent = scripted_agent([tool_call("final_answer", answer="ok")])
    agent.run("task", max_steps=2, brain="base")
    assert seen == [True]  # the default of the class is False: the agent must turn it on
