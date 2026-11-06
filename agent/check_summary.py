"""Look at what the agent's summarizer does with a real search result.

    uv run python -m agent.check_summary [brain ...]      # default: base thinking

For each brain it summarises a short history (one ``search_knowledge_base`` call with its real
result) the way ``ConversationMemory.compress`` does, and prints the summary and the time. Then
it fills a memory with the same result three times and checks that ``compress`` fires, keeps the
task and brings the token count down. Nothing is written to disk.
"""

from __future__ import annotations

import sys
import time

QUESTION = "¿Cómo debe ajustarse la dosis de cefotaxima en pacientes con insuficiencia renal grave?"
CALL = (
    "Thought: busco en la base de conocimiento.\n<tool_call>\n"
    '{"name": "search_knowledge_base", "arguments": '
    '{"query": "cefotaxima insuficiencia renal grave", "top_k": 5}}\n</tool_call>'
)


def main() -> None:
    from agent.memory import ConversationMemory
    from agent.react_agent import ReActAgent

    brains = sys.argv[1:] or ["base", "thinking"]
    agent = ReActAgent.from_env()
    result = agent.registry.call("search_knowledge_base", {"query": QUESTION, "top_k": 5})
    observation = str(result.result)
    history = [
        {"role": "assistant", "content": CALL},
        {"role": "tool", "content": observation, "name": "search_knowledge_base"},
    ]

    for brain in brains:
        agent._get_brain(brain)  # load first, so the time below is only the summary
        start = time.perf_counter()
        summary = agent.summarize(history, brain)
        print(f"\n=== {brain}: {time.perf_counter() - start:.1f} s, {len(summary)} characters")
        print(summary)

    tokenizer, _ = agent._get_brain(brains[0])
    memory = ConversationMemory(
        "sys",
        lambda text: len(tokenizer.encode(text)),
        token_budget=3000,
        keep_last=2,
        pin_first=True,
    )
    memory.add("user", f"TAREA: {QUESTION}")
    for _ in range(3):
        memory.add("assistant", CALL)
        memory.add("tool", observation, name="search_knowledge_base")
    before = (memory.tokens(), len(memory.messages))
    fired = memory.compress(lambda old: agent.summarize(old, brains[0]))
    print(f"\ncompress fired: {fired} | tokens {before[0]} -> {memory.tokens()}")
    print(
        f"messages {before[1]} -> {len(memory.messages)} | task kept: "
        f"{memory.messages[0]['content'].startswith('TAREA:')}"
    )


if __name__ == "__main__":
    main()
