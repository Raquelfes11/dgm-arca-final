"""The .env file: every variable the code reads is documented, and the agent loads it."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".venv", "tests", "hf_cache", "node_modules", "weights", "__pycache__"}


def variables_read_by_the_code() -> set[str]:
    found: set[str] = set()
    for path in ROOT.rglob("*.py"):
        if SKIP & set(path.relative_to(ROOT).parts):
            continue
        found |= set(re.findall(r"ARCA_[A-Z0-9_]+", path.read_text(encoding="utf-8")))
    return found


def test_every_arca_variable_of_the_code_is_in_the_env_example():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    documented = set(re.findall(r"ARCA_[A-Z0-9_]+", example))
    missing = sorted(variables_read_by_the_code() - documented)
    assert not missing, f"add these variables to .env.example: {missing}"


def test_importing_the_agent_and_the_rag_loads_the_env_file():
    # dotenv.load_dotenv is replaced by a counter in a fresh interpreter, so the test does not
    # depend on whether this machine has a .env file
    code = (
        "import dotenv\n"
        "calls = []\n"
        "dotenv.load_dotenv = lambda *args, **kwargs: calls.append(1)\n"
        "import agent.react_agent\n"
        "after_agent = len(calls)\n"
        "import rag.generate\n"
        "print(after_agent, len(calls))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=300
    )
    assert result.returncode == 0, result.stderr[-800:]
    after_agent, after_rag = map(int, result.stdout.split()[-2:])
    assert after_agent >= 1  # the agent loads it
    assert after_rag > after_agent  # and so does rag.generate, which reads it at import time
