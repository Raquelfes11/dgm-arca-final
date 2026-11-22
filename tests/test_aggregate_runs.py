"""Mean and range of several runs of the same configuration, on small made-up results."""

import json

import pytest

from agent.aggregate_runs import aggregate, load_runs, render, summarise_values, task_consistency


def row(id, correct, core=True, tokens=100):
    return {
        "id": id, "correct": correct, "succeeded": True, "final_answer": "x", "core": core,
        "tools_used": [], "required_tools": [], "required_tools_used": True, "steps": [],
        "n_steps": 1, "tokens_used": tokens,
    }


def test_values_are_written_as_mean_and_range():
    assert summarise_values([0.5, 0.7, 0.6], "pct") == "60 % [50 %-70 %]"
    assert summarise_values([0.5], "pct") == "50 %"
    assert summarise_values([None, 120.0, 100.0], "int") == "110 [100-120]"
    assert summarise_values([None, None], "num") == "sin dato"


def test_consistency_separates_noise_from_real_failures():
    runs = [
        [row("t01", True), row("t02", True), row("t03", False), row("t99", True, core=False)],
        [row("t01", True), row("t02", False), row("t03", False), row("t99", False, core=False)],
    ]
    assert task_consistency(runs) == {"always": 1, "sometimes": 1, "never": 1}


def test_aggregate_and_render_two_groups():
    low = [[row("t01", True), row("t02", False)], [row("t01", False), row("t02", False)]]
    high = [[row("t01", True), row("t02", True)]]
    summary = aggregate({"1024": low, "4096": high})
    assert summary["1024"]["n_runs"] == 2 and summary["4096"]["n_runs"] == 1
    assert summary["1024"]["metrics"]["Éxito en las tareas principales"] == "25 % [0 %-50 %]"
    assert summary["4096"]["metrics"]["Éxito en las tareas principales"] == "100 %"
    text = render(summary, "thinking")
    assert "1024 (2 ejecuciones)" in text and "4096 (1 ejecuciones)" in text
    assert "Acertadas solo en algunas" in text


def test_load_runs_reads_the_brain_and_complains_when_it_is_missing(tmp_path):
    report = tmp_path / "r.json"
    report.write_text(json.dumps({"thinking": {"rows": [row("t01", True)]},
                                  "rlm": {"error": "no adapter", "rows": []}}))
    assert len(load_runs([str(report)], "thinking")[0]) == 1
    for brain in ("rlm", "vllm"):
        with pytest.raises(ValueError, match=brain):
            load_runs([str(report)], brain)
