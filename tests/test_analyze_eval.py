"""The failure analysis of the phase-4 evaluation, on small made-up results."""

from agent.analyze_eval import FAILURE_CLASSES, analyse, analyse_brain, classify_failure, render


def row(id="t01", correct=False, succeeded=True, answer="x", tools=("final_answer",),
        required=("search_knowledge_base", "dose_calculator"), steps=None, core=True):
    steps = steps if steps is not None else [{"action": {"name": "final_answer"}}]
    return {
        "id": id, "correct": correct, "succeeded": succeeded, "final_answer": answer,
        "tools_used": sorted(tools), "required_tools": list(required), "core": core,
        "required_tools_used": set(required) <= set(tools), "steps": steps,
        "n_steps": len(steps), "tokens_used": 100,
    }


def test_each_failure_gets_one_class_in_order():
    assert classify_failure(row(correct=True)) is None
    assert classify_failure(row(succeeded=False)) == "no_termina"
    assert classify_failure(row(answer="  ")) == "respuesta_vacia"
    assert classify_failure(row(answer="42")) == "sin_herramientas"
    used = row(answer="42", tools=("search_knowledge_base", "dose_calculator", "final_answer"))
    assert classify_failure(used) == "resultado_incorrecto"
    assert set(FAILURE_CLASSES) == {
        "no_termina", "respuesta_vacia", "sin_herramientas", "resultado_incorrecto"}


def test_unfinished_run_with_empty_text_is_not_an_empty_answer():
    assert classify_failure(row(succeeded=False, answer="")) == "no_termina"


def test_faithful_success_needs_the_required_tools():
    lucky = row("a", correct=True, tools=("final_answer",))
    honest = row("b", correct=True, tools=("search_knowledge_base", "dose_calculator"))
    metrics = analyse_brain([lucky, honest])
    assert metrics["correct"] == 2 and metrics["faithful"] == 1


def test_metrics_count_invalid_steps_empty_answers_and_kb_use():
    bad_steps = [{"action": None}, {"action": None}, {"action": {"name": "final_answer"}}]
    rows = [
        row("a", answer="", steps=bad_steps),
        row("b", tools=("search_knowledge_base", "final_answer")),
        row("c", correct=True, tools=("search_knowledge_base", "dose_calculator")),
        row("e", core=False, correct=True, required=("convert_units",)),
    ]
    m = analyse_brain(rows)
    assert (m["n_core"], m["n_edge"], m["edge_correct"]) == (3, 1, 1)
    assert (m["invalid_steps"], m["n_steps"]) == (2, 5)
    assert m["empty_answers"] == 1
    assert (m["kb_used"], m["kb_needed"]) == (2, 3)
    assert sum(m["failures"].values()) == 2  # the correct task is not a failure


def test_empty_results_do_not_divide_by_zero():
    m = analyse_brain([])
    assert m["n_core"] == 0 and m["mean_steps"] == 0.0
    assert "Resumen" in render(analyse({}))


def test_skipped_brains_are_reported_and_left_out():
    results = {
        "base": {"rows": [row("t01", correct=True, tools=("search_knowledge_base", "dose_calculator"))]},
        "rlm": {"error": "ValueError: needs ARCA_RLM_ADAPTER", "rows": []},
    }
    analysis = analyse(results)
    assert list(analysis["brains"]) == ["base"]
    text = render(analysis)
    assert "`rlm` no se ha ejecutado" in text and "ARCA_RLM_ADAPTER" in text
    assert "| t01 | OK |" in text


def test_render_without_grid_omits_the_task_table():
    results = {"base": {"rows": [row("t01")]}}
    assert "Resultado por tarea" in render(analyse(results))
    assert "Resultado por tarea" not in render(analyse(results), grid=False)
