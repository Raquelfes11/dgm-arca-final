"""The training tasks: they are valid, they are the output of the generator and they do not use the
drugs of the two benchmarks."""

import json
import re
from pathlib import Path

import pytest

from agent.make_train_tasks import OUT, build_tasks
from agent.validate_bench import BENCH, CORPUS, validate

BENCHES = [BENCH, Path(BENCH).with_name("tasks_ood.jsonl")]
TOOLS = {"search_knowledge_base", "dose_calculator", "convert_units", "search_medication_cima",
         "create_preparation_sheet", "final_answer"}


def read(path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def drug(file_name: str) -> str:
    return re.sub(r"_\d+\.md$", "", file_name)


def bench_drugs() -> set[str]:
    return {drug(e["file"]) for path in BENCHES for t in read(path) for e in t.get("evidence", [])}


def test_the_committed_file_is_what_the_generator_writes():
    assert read(OUT) == build_tasks()  # run python -m agent.make_train_tasks after changing it


def test_there_are_enough_tasks_with_unique_ids():
    tasks = build_tasks()
    assert len(tasks) >= 100
    assert len({t["id"] for t in tasks}) == len(tasks)
    assert {t["split"] for t in tasks} == {"train"}
    assert all(len(set(t["required_tools"])) >= 2 for t in tasks)


def test_no_training_task_uses_a_drug_of_the_benchmarks():
    banned = bench_drugs()
    used = {drug(e["file"]) for t in build_tasks() for e in t["evidence"]}
    assert not used & banned, sorted(used & banned)
    for t in build_tasks():
        words = set(re.findall(r"[a-záéíóúñ]+", t["task"].lower()))
        for name in banned:
            assert name.split("-")[0] not in words, (t["id"], name)


def test_no_training_task_repeats_the_text_of_a_benchmark_task():
    texts = {t["task"] for path in BENCHES for t in read(path)}
    assert not texts & {t["task"] for t in build_tasks()}


@pytest.mark.skipif(not Path(CORPUS).exists() or not any(Path(CORPUS).glob("*.md")),
                    reason="the corpus is not downloaded")
def test_the_tasks_pass_the_benchmark_validation():
    assert validate(build_tasks(), CORPUS, TOOLS) == []


def test_ambiguous_evidence_is_left_out_and_ids_stay_stable():
    tasks = build_tasks()
    assert not [t for t in tasks if "piperacilina_68080.md" in {e["file"] for e in t["evidence"]}
                and any("80 mg de piperacilina/10 mg" in e["text"] for e in t["evidence"])]
    ids = [int(t["id"][1:]) for t in tasks]
    assert ids == sorted(ids) and ids[-1] > len(ids)  # there are gaps: nothing was renumbered
