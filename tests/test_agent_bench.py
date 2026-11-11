"""The phase-4 benchmark and its checker, without loading any model.

The corpus (rag/corpus/*.md) is not in git, so the evidence test is skipped when it has
not been downloaded; everything else runs anywhere.
"""

import json
from pathlib import Path

import pytest

from agent.evaluate import check_answer, number_values, summarise
from agent.validate_bench import BENCH, CORPUS, evaluate_expression, load_tasks, validate

TOOLS = {
    "search_knowledge_base",
    "search_medication_cima",
    "convert_units",
    "dose_calculator",
    "create_preparation_sheet",
    "final_answer",
}


def number(value, answer, **extra):
    return check_answer({"check": {"type": "number", "value": value, **extra}}, answer)


def test_spanish_decimal_comma_is_not_a_thousand_separator():
    assert number(7.5, "La dosis es 7,5 mg/kg")
    assert not number(75, "La dosis es 7,5 mg/kg")
    assert number(0.8, "Administrar 0,8 mL")
    assert not number(8, "Administrar 0,8 mL")


def test_thousands_separators_in_both_conventions():
    assert number(2310, "Total: 2.310 mg")
    assert number(2310, "Total: 2,310 mg")
    assert number(8400, "Son 8.400 mg en total")
    assert number(8_400_000, "8.400.000 UI")
    assert number(1050.5, "1.050,5 mg")
    assert number(1050.5, "1,050.5 mg")


def test_ambiguous_number_accepts_both_readings():
    assert sorted(number_values("1.050")) == [1.05, 1050.0]
    assert number(1.05, "1.050") and number(1050, "1.050")


def test_numbers_inside_ranges_and_codes():
    assert number(2, "entre 2-8 mg") and number(8, "entre 2-8 mg")
    assert number_values("vitamina B12") == []
    assert number(-3, "bajó a -3 puntos")


def test_tolerance():
    assert number(10.5, "10,52 mg/h", tolerance=0.05)
    assert not number(10.5, "10,7 mg/h", tolerance=0.05)


def test_all_any_and_negate():
    both = {"type": "all", "checks": [
        {"type": "number", "value": 900}, {"type": "number", "value": 2400}]}
    assert check_answer({"check": both}, "900 mg y 2400 mg")
    assert not check_answer({"check": both}, "solo 900 mg")
    either = {"type": "any", "checks": [
        {"type": "contains", "value": "no puedo"}, {"type": "contains", "value": "no consta"}]}
    assert check_answer({"check": either}, "No consta en la ficha")
    assert not check_answer({"check": either}, "Son 5 mL")
    no_dose = {"type": "regex", "value": r"\d+\s*mg", "negate": True}
    assert check_answer({"check": no_dose}, "No tengo ese dato")
    assert not check_answer({"check": no_dose}, "Dar 20 mg")


def test_contains_ignores_accents_and_case():
    assert check_answer({"check": {"type": "contains", "value": "perfusión"}}, "PERFUSION lenta")


def test_unknown_check_never_passes():
    assert not check_answer({"check": {"type": "nope", "value": 1}}, "1")
    assert not check_answer({}, "1")


def test_summarise_handles_empty_and_mixed_rows():
    assert summarise([])["n_tasks"] == 0
    rows = [
        {"correct": True, "n_steps": 3, "tokens_used": 100},
        {"correct": False, "n_steps": 5, "tokens_used": 300},
    ]
    assert summarise(rows) == {
        "n_tasks": 2, "success_rate": 0.5, "mean_steps": 4.0, "mean_tokens": 200.0}


def test_evaluate_expression_is_plain_arithmetic():
    assert evaluate_expression("6 * 80") == 480
    assert evaluate_expression("-(1 + 2) ** 2 / 3") == -3
    with pytest.raises(ValueError):
        evaluate_expression("__import__('os').getcwd()")


def test_validate_reports_the_usual_mistakes():
    good = {
        "id": "a", "task": "t", "required_tools": ["dose_calculator", "convert_units"],
        "check": {"type": "number", "value": 480}, "answer_exprs": ["6 * 80"],
    }
    assert validate([good], tools=TOOLS) == []
    wrong_number = {**good, "id": "b", "answer_exprs": ["6 * 70"]}
    one_tool = {**good, "id": "c", "required_tools": ["dose_calculator"]}
    bad_tool = {**good, "id": "d", "required_tools": ["dose_calculator", "weather"]}
    bad_regex = {**good, "id": "e", "check": {"type": "regex", "value": "("}}
    missing = {"id": "f", "task": "t"}
    for task, text in [
        (wrong_number, "expects 480"), (one_tool, "at least two"), (bad_tool, "unknown tool"),
        (bad_regex, "does not compile"), (missing, "missing field"),
    ]:
        assert any(text in p for p in validate([task], tools=TOOLS)), text
    assert any("repeated id" in p for p in validate([good, good], tools=TOOLS))
    edge = {**one_tool, "id": "g", "core": False}
    assert validate([edge], tools=TOOLS) == []


# ---- the committed benchmark ----------------------------------------------------------------


@pytest.fixture(scope="module")
def tasks():
    return load_tasks(BENCH)


def test_benchmark_is_well_formed(tasks):
    assert validate(tasks, tools=TOOLS) == []


def test_benchmark_has_at_least_twenty_multi_tool_core_tasks(tasks):
    core = [t for t in tasks if t.get("core", True)]
    assert len(core) >= 20
    assert all(len(set(t["required_tools"])) >= 2 for t in core)


def test_every_line_is_valid_json_with_a_spanish_or_english_task(tasks):
    for line in Path(BENCH).read_text(encoding="utf-8").splitlines():
        if line.strip():
            assert json.loads(line)["task"].strip()


def test_reference_answers_pass_their_own_check(tasks):
    """The solution text written for each task must be accepted by its check."""
    for task in tasks:
        if "solution" in task and not task.get("expected_behaviour"):
            assert check_answer(task, task["solution"]), task["id"]


@pytest.mark.skipif(not any(CORPUS.glob("*.md")), reason="corpus not downloaded")
def test_evidence_is_in_the_corpus(tasks):
    problems = [p for p in validate(tasks, CORPUS, TOOLS) if "evidence" in p]
    assert problems == []
