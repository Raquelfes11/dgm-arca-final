"""Does a generator cite? Same retrieval, different generator models.

The generator is chosen with the same variables as ``/rag`` (``ARCA_RLM_BASE_MODEL`` and
``ARCA_RLM_ADAPTER``), so run it once per model::

    ARCA_RLM_BASE_MODEL=Qwen/Qwen3-1.7B uv run python -m rag.compare_generators --tag qwen3-1.7b

Each run writes ``reports/rag/generators/<tag>.json`` with every answer and prints the metrics.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Questions the corpus cannot answer (none of these drugs, or this information, is in it).
UNANSWERABLE = [
    "¿Cuál es la dosis habitual de omeprazol intravenoso?",
    "¿Qué dosis de metformina se recomienda en diabetes tipo 2?",
    "¿Cuáles son las contraindicaciones de la atorvastatina?",
    "¿Cómo se ajusta la warfarina según el INR?",
    "¿Cuál es la dosis pediátrica de diazepam rectal?",
    "¿Cuánto cuesta una ampolla de vancomicina en farmacia?",
    "¿Quién descubrió la penicilina y en qué año?",
    "¿Qué dosis de insulina glargina se usa al iniciar el tratamiento?",
]
NUMBER_RE = r"\[([A-Za-z0-9_-]+)\]"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--gold", default="rag/gold/gold.jsonl")
    parser.add_argument("--retriever", default="hybrid")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    import re

    from rag.evaluate import load_gold, resolve_gold
    from rag.generate import build_pipeline

    pipeline = build_pipeline()
    chunks = pipeline.retrievers["bm25"].chunks
    gold = [it for it in resolve_gold(load_gold(args.gold), chunks) if it["relevant_chunk_ids"]]
    gold = gold[: args.limit]

    rows = []
    for item in gold:
        r = pipeline.answer(item["question"], args.top_k, args.retriever)
        brackets = set(re.findall(NUMBER_RE, r.answer))
        retrieved = {c.id for c in r.chunks}
        rows.append(
            {
                "question": item["question"],
                "answer": r.answer,
                "citations": r.citations,
                "invented": sorted(brackets - retrieved),
                "retrieved_has_gold": bool(retrieved & set(item["relevant_chunk_ids"])),
                "cites_gold": bool(set(r.citations) & set(item["relevant_chunk_ids"])),
            }
        )
    unanswerable = []
    for question in UNANSWERABLE:
        r = pipeline.answer(question, args.top_k, args.retriever)
        unanswerable.append({"question": question, "answer": r.answer, "citations": r.citations})

    n = max(len(rows), 1)
    metrics = {
        "model": pipeline.model_id,
        "n_questions": len(rows),
        "cites_something": sum(bool(x["citations"]) for x in rows) / n,
        "cites_gold_chunk": sum(x["cites_gold"] for x in rows) / n,
        "retrieved_gold_chunk": sum(x["retrieved_has_gold"] for x in rows) / n,
        "answers_with_invented_ids": sum(bool(x["invented"]) for x in rows) / n,
        "unanswerable_that_cite": sum(bool(x["citations"]) for x in unanswerable) / len(unanswerable),
    }
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    out = Path(f"reports/rag/generators/{args.tag}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"metrics": metrics, "answerable": rows, "unanswerable": unanswerable}
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
