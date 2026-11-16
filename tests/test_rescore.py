"""Scoring a saved report again with a (changed) benchmark, on small made-up results."""

from agent.rescore import rescore

TASKS = {"t21": {"id": "t21", "check": {"type": "contains", "value": "no está"}}}


def row(id, succeeded=True, answer="No está en la base", correct=False, core=False):
    return {
        "id": id, "category": "x", "core": core, "succeeded": succeeded, "final_answer": answer,
        "correct": correct, "n_steps": 1, "tokens_used": 10, "steps": [],
    }


def test_rescore_changes_correct_and_the_summaries_but_not_the_rest():
    results = {
        "thinking": {
            "config": {"rag_mode": "auto"},
            "rows": [
                row("t21"),  # a correct answer that the old check missed
                row("t21", succeeded=False),  # the text matches, but the run did not finish
                row("t99", core=True, correct=True),  # no longer in the benchmark: kept as is
            ],
        },
        "rlm": {"error": "ValueError: no adapter", "rows": []},
    }
    new = rescore(results, TASKS)
    rows = new["thinking"]["rows"]
    assert [r["correct"] for r in rows] == [True, False, True]
    assert rows[0]["tokens_used"] == 10 and rows[0]["check"] == TASKS["t21"]["check"]
    assert new["thinking"]["edge"]["success_rate"] == 0.5
    assert new["thinking"]["success_rate"] == 1.0
    assert new["thinking"]["config"] == {"rag_mode": "auto"}
    assert new["rlm"] == results["rlm"]  # a skipped brain is left alone
