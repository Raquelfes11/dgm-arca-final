"""The ReAct loop with a scripted "model": no weights are loaded.

``generate`` is replaced by a function that returns prepared outputs, and the tokenizer by one
that counts words. That is enough to test the loop rules (repeated calls, tools that need
confirmation, memory) deterministically.
"""

import json

import pytest

from agent.memory import ConversationMemory
from agent.react_agent import (
    AUTO_SEARCH_TOP_K,
    MAX_REPEATED_CALLS,
    MIN_TOP_K,
    ReActAgent,
    _action_line_fallback,
    _resolve_adapter,
    search_knowledge_base,
)
from tool_use.registry import tool
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


KNOWN = {"dose_calculator": None, "search_knowledge_base": None, "final_answer": None}


def test_action_line_with_only_the_tool_name():
    call = _action_line_fallback("Thought: busco.\nAction: search_knowledge_base", KNOWN)
    assert call.name == "search_knowledge_base" and call.arguments == {}


def test_action_line_with_the_arguments_after_the_name():
    call = _action_line_fallback('Action: dose_calculator {"expression": "10 * 20"}', KNOWN)
    assert call.name == "dose_calculator" and call.arguments == {"expression": "10 * 20"}


def test_action_line_with_a_whole_json_call():
    # the shape Qwen3-1.7B wrote in the phase-4 evaluation (t09, t20)
    raw = (
        "Voy a calcular.\n\n"
        'Action: {"name": "dose_calculator", "arguments": {"expression": "10 * 20", "decimals": 1}}'
    )
    call = _action_line_fallback(raw, KNOWN)
    assert call.name == "dose_calculator"
    assert call.arguments == {"expression": "10 * 20", "decimals": 1}


def test_action_line_json_call_accepts_parameters_instead_of_arguments():
    raw = 'Action: {"name": "dose_calculator", "parameters": {"expression": "2 * 3"}}'
    call = _action_line_fallback(raw, KNOWN)
    assert call.arguments == {"expression": "2 * 3"}


def test_action_line_json_call_without_arguments_has_empty_arguments():
    call = _action_line_fallback('Action: {"name": "search_knowledge_base"}', KNOWN)
    assert call.name == "search_knowledge_base" and call.arguments == {}


def test_action_line_ignores_tools_that_do_not_exist():
    assert _action_line_fallback("Action: borrar_todo", KNOWN) is None
    assert _action_line_fallback('Action: {"name": "borrar_todo", "arguments": {}}', KNOWN) is None
    assert _action_line_fallback('Action: {"name": ["dose_calculator"]}', KNOWN) is None


def test_action_line_ignores_broken_json_and_other_json():
    broken = 'Action: {"name": "dose_calculator", "arguments": {'
    assert _action_line_fallback(broken, KNOWN) is None
    assert _action_line_fallback('Action: ["dose_calculator"]', KNOWN) is None
    assert _action_line_fallback("Action:", KNOWN) is None


def test_action_line_ignores_text_inside_think():
    closed = '<think>Action: {"name": "dose_calculator", "arguments": {}}</think>Hola'
    unclosed = 'Hola <think>Action: {"name": "dose_calculator", "arguments": {}}'
    assert _action_line_fallback(closed, KNOWN) is None
    assert _action_line_fallback(unclosed, KNOWN) is None


def test_action_line_takes_the_last_one_whatever_its_shape():
    raw = (
        "Action: dose_calculator\nmejor no.\n"
        'Action: {"name": "final_answer", "arguments": {"answer": "7"}}'
    )
    assert _action_line_fallback(raw, KNOWN).name == "final_answer"
    raw = 'Action: {"name": "final_answer", "arguments": {"answer": "7"}}\nAction: dose_calculator'
    assert _action_line_fallback(raw, KNOWN).name == "dose_calculator"


def test_loop_runs_a_call_written_as_action_json():
    step = (
        "Thought: calculo.\n"
        'Action: {"name": "dose_calculator", "arguments": {"expression": "1 + 1", "decimals": 2}}'
    )
    agent = scripted_agent([step, tool_call("final_answer", answer="2")])
    response = agent.run("task", max_steps=4, brain="base")
    assert response.succeeded and response.final_answer == "2"
    assert response.steps[0].action.name == "dose_calculator"  # it ran, with no nudge first
    assert "2" in response.steps[0].observation


def test_system_prompt_is_formatted():
    prompt = ReActAgent().system_prompt(7)
    assert "at most 7 steps" in prompt
    for leftover in ("{{", "{max_steps}", "{tools_description}"):
        assert leftover not in prompt
    assert '"name": "final_answer"' in prompt  # the braces of the JSON survived format()
    assert "dose_calculator" in prompt  # the tool descriptions were injected


EMPTY_CALLS = [
    tool_call("final_answer", answer=""),
    tool_call("final_answer", answer="   "),
    tool_call("final_answer"),  # without the answer argument
]


@pytest.mark.parametrize("empty", EMPTY_CALLS)
def test_empty_final_answer_gets_one_more_try(empty):
    agent = scripted_agent([empty, tool_call("final_answer", answer="0,8 mL")])
    response = agent.run("task", max_steps=5, brain="base")
    assert response.succeeded and response.final_answer == "0,8 mL"
    assert "without an answer" in response.steps[0].observation
    assert response.n_steps == 2


def test_two_empty_final_answers_in_a_row_fail_the_run():
    empty = tool_call("final_answer", answer="")
    agent = scripted_agent([empty, empty])
    response = agent.run("task", max_steps=5, brain="base")
    assert not response.succeeded and response.final_answer == ""
    assert response.n_steps == 2
    assert response.steps[-1].observation == "(no tool call)"


def test_a_valid_call_resets_the_empty_final_answer_counter():
    empty = tool_call("final_answer", answer="")
    agent = scripted_agent([empty, CALC, empty, tool_call("final_answer", answer="ok")])
    response = agent.run("task", max_steps=6, brain="base")
    assert response.succeeded and response.final_answer == "ok"
    assert response.n_steps == 4


def test_null_answer_counts_as_empty():
    agent = scripted_agent([tool_call("final_answer", answer=None),
                            tool_call("final_answer", answer="ok")])
    response = agent.run("task", max_steps=5, brain="base")
    assert response.succeeded and response.final_answer == "ok"


class FakeRetriever:
    def __init__(self):
        self.asked = []

    def search(self, query, top_k):
        self.asked.append(top_k)
        return []


def test_search_never_returns_fewer_passages_than_the_minimum(monkeypatch):
    retriever = FakeRetriever()
    monkeypatch.setattr("agent.react_agent._get_retriever", lambda: retriever)
    for asked in (1, MIN_TOP_K, 8):
        search_knowledge_base(query="q", top_k=asked)
    assert retriever.asked == [MIN_TOP_K, MIN_TOP_K, 8]


def agent_with_fake_search(outputs, rag_mode):
    """A scripted agent with a fake knowledge base tool. Returns it and the calls it received."""
    calls = []

    @tool
    def search_knowledge_base(query: str, top_k: int = 5) -> str:
        """Fake knowledge base search."""
        calls.append((query, top_k))
        return "[doc-0001] (ficha.md)\nla dosis es de 1 mg/kg"

    agent = scripted_agent(outputs)
    agent.rag_mode = rag_mode
    agent.registry.register(search_knowledge_base)
    return agent, calls


def test_auto_search_runs_before_the_first_step_and_the_model_sees_it():
    agent, calls = agent_with_fake_search([tool_call("final_answer", answer="ok")], "auto")
    sent = []
    generate = agent.generate

    def spy(messages, brain, thinking=None):
        sent.append(messages)
        return generate(messages, brain, thinking)

    agent.generate = spy
    response = agent.run("dosis de enoxaparina", max_steps=1, brain="base")
    assert calls == [("dosis de enoxaparina", AUTO_SEARCH_TOP_K)]
    assert response.succeeded and response.final_answer == "ok"
    assert response.n_steps == 1  # the automatic search did not use up the only step
    automatic, own = response.steps
    assert automatic.automatic and automatic.action.name == "search_knowledge_base"
    assert "[doc-0001]" in automatic.observation
    assert not own.automatic
    assert "[doc-0001]" in str(sent[0])  # the passages are in the first thing the model reads


def test_tool_mode_does_not_search_by_itself():
    agent, calls = agent_with_fake_search([tool_call("final_answer", answer="ok")], "tool")
    response = agent.run("dosis de enoxaparina", max_steps=3, brain="base")
    assert calls == []
    assert [step.automatic for step in response.steps] == [False]


def test_auto_search_needs_the_tool_in_the_registry():
    agent = scripted_agent([tool_call("final_answer", answer="ok")])
    agent.rag_mode = "auto"
    with pytest.raises(ValueError, match="search_knowledge_base"):
        agent.run("task", max_steps=3, brain="base")


def test_unknown_rag_mode_is_rejected():
    with pytest.raises(ValueError, match="rag_mode"):
        ReActAgent(rag_mode="siempre")


def test_from_env_switches_choose_the_tools():
    full = set(ReActAgent.from_env().registry.tools)
    assert {"final_answer", "search_knowledge_base", "dose_calculator"} <= full
    no_rag = set(ReActAgent.from_env(rag_mode="off").registry.tools)
    assert "search_knowledge_base" not in no_rag and "final_answer" in no_rag
    assert set(ReActAgent.from_env(use_tools=False).registry.tools) == {
        "final_answer", "search_knowledge_base"}
    assert set(ReActAgent.from_env(rag_mode="off", use_tools=False).registry.tools) == {
        "final_answer"}
