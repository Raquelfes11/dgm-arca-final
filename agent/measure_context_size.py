"""Measure how many tokens the things that enter the agent's conversation take.

    uv run python -m agent.measure_context_size      # writes reports/agent_context_size.json

It uses the tokenizer of the base model (``ARCA_RLM_BASE_MODEL``) and measures:

* the system prompt, with the agent's tools and ``max_steps=10``;
* the result of ``search_knowledge_base`` for the first ``N_QUESTIONS`` questions of the gold
  set, with ``top_k`` 3 and 5 (tokens and characters);
* the result of one ``search_medication_cima`` call.

It is what the memory policy (``agent/memory.py``, EXPERIMENTS.md) is based on: how soon the
token budget of the agent is used up.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

GOLD = Path("rag/gold/gold.jsonl")
REPORT = Path("reports/agent_context_size.json")
N_QUESTIONS = 20


def summary(values: list[int]) -> dict:
    return {
        "n": len(values),
        "min": min(values),
        "median": int(statistics.median(values)),
        "max": max(values),
    }


def main() -> None:
    from transformers import AutoTokenizer

    from agent.react_agent import BRAINS, ReActAgent

    tokenizer = AutoTokenizer.from_pretrained(BRAINS["base"]())
    count = lambda text: len(tokenizer.encode(text))  # noqa: E731
    agent = ReActAgent.from_env()
    questions = [
        json.loads(line)["question"] for line in GOLD.read_text().splitlines() if line.strip()
    ]
    questions = questions[:N_QUESTIONS]

    prompt = agent.system_prompt(10)
    results: dict = {"system_prompt_tokens": count(prompt), "system_prompt_chars": len(prompt)}
    for top_k in (3, 5):
        observations = [
            str(agent.registry.call("search_knowledge_base", {"query": q, "top_k": top_k}).result)
            for q in questions
        ]
        results[f"search_knowledge_base top_k={top_k} tokens"] = summary(
            [count(o) for o in observations]
        )
        results[f"search_knowledge_base top_k={top_k} chars"] = summary(
            [len(o) for o in observations]
        )
    cima = agent.registry.call("search_medication_cima", {"active_ingredient": "cefotaxima"})
    results["search_medication_cima cefotaxima tokens"] = count(str(cima.result))
    results["search_medication_cima cefotaxima chars"] = len(str(cima.result))

    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    for name, value in results.items():
        print(f"{name:48s} {value}")


if __name__ == "__main__":
    main()
