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
    assert "BLOQUEADA" in response.steps[0].observation
    assert response.succeeded and response.final_answer == "no puedo"  # the model could go on
    record = agent._call_tool("create_preparation_sheet", {})
    assert not record.ok and record.requires_confirmation


def test_blocked_observation_says_explicitly_that_nothing_was_generated():
    agent = scripted_agent([])
    record = agent._call_tool("create_preparation_sheet", {})
    assert "NO se ha generado" in record.error
    assert "NO EJECUTADA" in record.error


SHEET_CALL = tool_call(
    "create_preparation_sheet",
    medication="paracetamol",
    concentration="10 mg/ml",
    dose="600 mg",
    administration="60 ml",
    steps="15 x 40 = 600",
)


def test_final_answer_claiming_a_blocked_sheet_is_flagged_and_corrected():
    """t23: the model asked for the sheet, was blocked, and still said it was generated."""
    agent = scripted_agent(
        [SHEET_CALL, tool_call("final_answer", answer="Son 600 mg. He generado la hoja de preparación.")]
    )
    response = agent.run("task", max_steps=5, brain="base")
    assert response.warnings and "create_preparation_sheet" in response.warnings[0]
    assert response.final_answer.startswith("AVISO")
    assert "NO se ha generado" in response.final_answer
    assert "600 mg" in response.final_answer  # the useful part of the answer is kept


def test_final_answer_that_admits_the_sheet_was_blocked_is_not_touched():
    answer = "Son 600 mg. No he podido generar la hoja de preparación: está bloqueada."
    agent = scripted_agent([SHEET_CALL, tool_call("final_answer", answer=answer)])
    response = agent.run("task", max_steps=5, brain="base")
    assert response.final_answer == answer and response.warnings == []


def test_sheet_claimed_without_calling_the_tool_is_flagged():
    agent = scripted_agent([tool_call("final_answer", answer="Aquí tienes el PDF con la hoja.")])
    response = agent.run("task", max_steps=3, brain="base")
    assert response.warnings and response.final_answer.startswith("AVISO")


def test_answer_that_does_not_mention_a_sheet_is_not_touched():
    answer = "Son 600 mg según la ficha técnica."
    agent = scripted_agent([tool_call("final_answer", answer=answer)])
    response = agent.run("task", max_steps=3, brain="base")
    assert response.final_answer == answer and response.warnings == []


def test_check_claimed_actions_trusts_a_tool_that_succeeded():
    from agent.react_agent import check_claimed_actions

    answer = "Hoja de preparación generada."
    assert check_claimed_actions(answer, {"create_preparation_sheet"}) == (answer, [])
    assert check_claimed_actions(answer, set())[1]  # same text, tool did not succeed: flagged


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


def test_a_call_in_the_tag_is_marked_as_read_from_the_tag():
    agent = scripted_agent([CALC, tool_call("final_answer", answer="2")])
    response = agent.run("task", max_steps=4, brain="base")
    assert [s.call_route for s in response.steps] == ["tag", "tag"]


def test_a_call_written_as_action_is_marked_as_the_fallback():
    step = (
        "Thought: calculo.\n"
        'Action: {"name": "dose_calculator", "arguments": {"expression": "1 + 1", "decimals": 2}}'
    )
    agent = scripted_agent([step, tool_call("final_answer", answer="2")])
    response = agent.run("task", max_steps=4, brain="base")
    assert [s.call_route for s in response.steps] == ["fallback", "tag"]


def test_a_step_without_a_valid_call_has_no_route():
    agent = scripted_agent(["no llamo a ninguna herramienta", tool_call("final_answer", answer="2")])
    response = agent.run("task", max_steps=4, brain="base")
    assert response.steps[0].call_route is None  # the step that got the nudge
    assert response.steps[1].call_route == "tag"


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
    assert ReActAgent.from_env().rag_mode == "auto"  # the default of the API and the evaluation
    assert ReActAgent().rag_mode == "tool"  # a bare agent keeps the old behaviour
    full = set(ReActAgent.from_env().registry.tools)
    assert {"final_answer", "search_knowledge_base", "dose_calculator"} <= full
    no_rag = set(ReActAgent.from_env(rag_mode="off").registry.tools)
    assert "search_knowledge_base" not in no_rag and "final_answer" in no_rag
    assert set(ReActAgent.from_env(use_tools=False).registry.tools) == {
        "final_answer", "search_knowledge_base"}
    assert set(ReActAgent.from_env(rag_mode="off", use_tools=False).registry.tools) == {
        "final_answer"}


def test_requested_tool_not_called_is_reminded_once(monkeypatch, tmp_path):
    """The task asks for the sheet and the model tries to finish without calling the tool: it is told
    once, calls the tool and the answer is accepted. If it insists, the warning is added."""
    import tool_use.tools as tools_module
    from agent.react_agent import final_answer

    monkeypatch.setattr(tools_module, "SHEETS_DIR", tmp_path)
    sheet = dict(medication="X", concentration="10 mg/mL", dose="600 mg", administration="60 mL", steps="a")

    def call(name, arguments):
        return f'<tool_call>\n{json.dumps({"name": name, "arguments": arguments})}\n</tool_call>'

    def make(script):
        agent = ReActAgent(rag_mode="off")
        agent.registry.register(final_answer)
        agent._get_brain = lambda brain: (type("T", (), {"encode": lambda self, t: t.split()})(), None)
        outputs = iter(script)
        agent.generate = lambda messages, brain, thinking=None: next(outputs)
        agent.summarize = lambda old, brain: "summary"
        return agent

    done = call("final_answer", {"answer": "Hoja generada en /tmp/x.pdf"})
    agent = make([done, call("create_preparation_sheet", sheet), call("final_answer", {"answer": "Hecho."})])
    response = agent.run("genera la hoja de preparación de X")
    assert "no has" in response.steps[0].observation.lower()  # the reminder
    assert list(tmp_path.glob("*.pdf")) and not response.warnings

    agent = make([done, done])  # it insists: second time the answer is accepted, with the warning
    response = agent.run("genera la hoja de preparación de X")
    assert response.final_answer.startswith("AVISO") and response.warnings


def test_concurrent_runs_do_not_mix_their_steps():
    """POST /agent is served from threads and the agent is one object: two requests at the same
    time must not write into each other's trace (a response showed steps of another run)."""
    import threading
    import time

    from agent.react_agent import final_answer

    agent = ReActAgent(rag_mode="off")
    agent.registry.register(final_answer)
    agent._get_brain = lambda brain: (type("T", (), {"encode": lambda self, t: t.split()})(), None)
    agent.summarize = lambda old, brain: "summary"
    calls: dict[str, int] = {}

    def generate(messages, brain, thinking=None):
        time.sleep(0.02)  # let the other thread run in between
        task = next(m["content"] for m in messages if m["role"] == "user")
        calls[task] = calls.get(task, 0) + 1
        if calls[task] == 1:
            return '<tool_call>\n{"name": "dose_calculator", "arguments": {"expression": "1 + 1"}}\n</tool_call>'
        return '<tool_call>\n{"name": "final_answer", "arguments": {"answer": "answer-%s"}}\n</tool_call>' % task

    agent.generate = generate
    responses = {}

    def run(task):
        responses[task] = agent.run(task, max_steps=5, brain="base")

    threads = [threading.Thread(target=run, args=(t,)) for t in ("A", "B")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for task, response in responses.items():
        answers = [s.action.arguments.get("answer") for s in response.steps if s.action and s.action.name == "final_answer"]
        assert answers == [f"answer-{task}"], (task, [s.action.name for s in response.steps if s.action])
        assert len(response.steps) == 2, (task, len(response.steps))


def test_sheet_rules_only_in_prompt_of_runs_that_ask_for_the_sheet():
    agent = ReActAgent(rag_mode="off")
    assert "like a teacher" not in agent.system_prompt(5)
    assert "like a teacher" in agent.system_prompt(5, sheet=True)
    assert "like a teacher" in ReActAgent(rag_mode="off", few_shot=True).system_prompt(5, sheet=True)


@pytest.mark.parametrize(
    "task, asked",
    [
        ("Calcula 15 mg/kg para 40 kg y genera la hoja de preparación en PDF", True),
        ("Necesito una hoja de preparación de la amikacina", True),
        ("Hazme el PDF de la dilución", True),
        ("Calcula la dosis, sin hoja de preparación", False),
        ("No quiero la hoja de preparación, solo la dosis", False),
        ("Calcula la dosis de paracetamol para 40 kg", False),
        ("¿Qué es una hoja de preparación?", False),
    ],
)
def test_requested_tools_reads_the_task(task, asked):
    from agent.react_agent import requested_tools

    assert ("create_preparation_sheet" in requested_tools(task)) is asked


def test_sheet_runs_only_if_the_task_asked_for_it(monkeypatch, tmp_path):
    """Asked in the task: it runs. Called by the model on its own: blocked, nothing is written."""
    import tool_use.tools as tools_module

    monkeypatch.setattr(tools_module, "SHEETS_DIR", tmp_path)
    args = dict(medication="X", concentration="10 mg/mL", dose="600 mg", administration="60 mL", steps="a")
    agent = ReActAgent(rag_mode="off")
    agent._requested = set()
    blocked = agent._call_tool("create_preparation_sheet", args)
    assert not blocked.ok and blocked.requires_confirmation and not list(tmp_path.iterdir())
    agent._requested = {"create_preparation_sheet"}
    done = agent._call_tool("create_preparation_sheet", args)
    assert done.ok and list(tmp_path.glob("*.pdf"))


def test_preparation_sheet_steps_are_split_into_separate_lines():
    from tool_use.tools import _split_steps

    one_line = (
        "Dosis total = peso del paciente (40 kg) x dosis por kg (15 mg/kg) = 600 mg. "
        "Volumen por administración = 600 mg / 10 mg/mL = 60 mL."
    )
    assert _split_steps(one_line) == [
        "Dosis total = peso del paciente (40 kg) x dosis por kg (15 mg/kg) = 600 mg.",
        "Volumen por administración = 600 mg / 10 mg/mL = 60 mL.",
    ]
    assert _split_steps("a = 1; b = 2") == ["a = 1", "b = 2"]
    assert _split_steps("Dosis: 0.5 mg/kg x 70 kg = 35 mg") == ["Dosis: 0.5 mg/kg x 70 kg = 35 mg"]  # decimal kept
    assert _split_steps("uno\ndos\n\ntres") == ["uno", "dos", "tres"]
