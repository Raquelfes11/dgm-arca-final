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
    new = rescore(results, TASKS, mode="lax")
    rows = new["thinking"]["rows"]
    assert [r["correct"] for r in rows] == [True, False, True]
    assert rows[0]["tokens_used"] == 10 and rows[0]["check"] == TASKS["t21"]["check"]
    assert new["thinking"]["edge"]["success_rate"] == 0.5
    assert new["thinking"]["success_rate"] == 1.0
    assert new["thinking"]["config"] == {"rag_mode": "auto"}
    assert new["rlm"] == results["rlm"]  # a skipped brain is left alone
    assert [r["correct_original"] for r in rows] == [False, False, True]
    assert [r["correct_lax"] for r in rows] == [True, False, True]
    assert new["thinking"]["lucky_hits"] == 0

def test_rescore_strict_counts_lucky_hits():
    tasks = {"t01": {"id": "t01", "core": True,
                     "check": {"type": "number", "value": 4, "unit": "mL"}}}
    results = {"m": {"config": {}, "rows": [
        row("t01", answer="Son 7 comprimidos y 4 mg", core=True),  # 4 by chance, wrong unit
        row("t01", answer="Hay que dar 4 ml", core=True),
    ]}}
    new = rescore(results, tasks)  # strict by default
    s = new["m"]
    assert [r["correct"] for r in s["rows"]] == [False, True]
    assert [r["correct_lax"] for r in s["rows"]] == [True, True]
    assert s["lucky_hits"] == 1
    assert s["success_rate_lax"] == 1.0 and s["success_rate"] == 0.5