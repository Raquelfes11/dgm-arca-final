"""make bench: runs the three steps with a labelled output and never touches the phase 4 baseline."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BASELINE = "reports/phase4/phase4_eval.json"

pytestmark = pytest.mark.skipif(shutil.which("make") is None, reason="make is not installed")


def dry_run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["make", "-n", "bench", *args], cwd=ROOT, capture_output=True, text=True, timeout=60
    )


def test_bench_needs_a_change_number_and_a_label():
    result = dry_run()
    assert result.returncode != 0
    assert "FIX" in result.stderr and "LABEL" in result.stderr
    assert dry_run("FIX=09").returncode != 0


def test_bench_runs_validate_evaluate_and_analyse_with_a_labelled_output():
    result = dry_run("FIX=99", "LABEL=prueba")
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "agent.validate_bench" in out
    assert "--out reports/fix/99/fix99_prueba.json" in out
    assert "--report reports/fix/99/fix99_prueba.json" in out
    assert "--markdown reports/fix/99/fix99_prueba.md" in out
    assert out.index("agent.validate_bench") < out.index("agent.evaluate")
    assert out.index("agent.evaluate") < out.index("agent.analyze_eval")
    assert BASELINE not in out


def test_bench_passes_the_brains_and_options_through():
    result = dry_run(
        "FIX=99", "LABEL=x", "BRAINS=base rlm", "RAG_MODE=tool", "NO_TOOLS=1", "IDS=t01 t02"
    )
    assert result.returncode == 0, result.stderr
    assert "--brains base rlm --rag-mode tool" in result.stdout
    assert "--ids t01 t02" in result.stdout
    assert "--no-tools" in result.stdout


def test_bench_does_not_overwrite_an_existing_report():
    existing = ROOT / "reports" / "fix" / "99" / "fix99_existente.json"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("{}", encoding="utf-8")
    try:
        refused = dry_run("FIX=99", "LABEL=existente")
        assert refused.returncode != 0
        assert "Ya existe" in refused.stderr
        assert dry_run("FIX=99", "LABEL=existente", "FORCE=1").returncode == 0
    finally:
        existing.unlink()
        existing.parent.rmdir()
