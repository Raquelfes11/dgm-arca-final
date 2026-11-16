"""agent.evaluate end to end with a fake agent: no model is loaded, the report is written."""

import json
import sys

from agent import evaluate
from api.schemas import AgentAction, AgentResponse, AgentStep

TASKS = [
    {
        "id": "a1", "category": "ficha_calculo", "task": "Cuántos mg son 6 x 80 mg",
        "required_tools": ["search_knowledge_base", "dose_calculator"],
        "check": {"type": "number", "value": 480},
    },
    {
        "id": "e1", "category": "fuera_del_corpus", "core": False, "task": "Dosis de algo",
        "required_tools": ["search_knowledge_base"],
        "check": {"type": "regex", "value": "(?i)no se encuentra"},
    },
]


class FakeAgent:
    """Answers 480 mg to everything, with an automatic search step like rag_mode auto."""

    def run(self, task, max_steps, brain):
        search = AgentStep(
            thought="", action=AgentAction(name="search_knowledge_base"), automatic=True)
        answer = AgentStep(
            thought="", action=AgentAction(name="final_answer", arguments={"answer": "480 mg"}))
        return AgentResponse(final_answer="480 mg", steps=[search, answer], n_steps=1)


def test_main_runs_the_benchmark_and_writes_the_report(tmp_path, monkeypatch):
    bench = tmp_path / "bench.jsonl"
    bench.write_text("\n".join(json.dumps(t) for t in TASKS), encoding="utf-8")
    out = tmp_path / "report.json"
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "agent.react_agent.ReActAgent.from_env", classmethod(lambda cls, **kwargs: FakeAgent()))
    argv = ["evaluate", "--bench", str(bench), "--brains", "thinking", "--rag-mode", "auto",
            "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)

    evaluate.main()

    result = json.loads(out.read_text(encoding="utf-8"))["thinking"]
    assert result["success_rate"] == 1.0  # the core task: 480 is the answer
    assert result["edge"]["n_tasks"] == 1 and result["edge"]["success_rate"] == 0.0
    assert result["config"]["rag_mode"] == "auto" and result["config"]["use_tools"] is True
    first = result["rows"][0]
    assert first["tools_used"] == ["final_answer"]  # the automatic search is not the model's
    assert first["auto_tools"] == ["search_knowledge_base"]
    assert first["required_tools_used"] is False  # dose_calculator was never called
