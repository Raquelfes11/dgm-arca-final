"""Which drugs of the corpus a question talks about, and a retriever that searches inside them.

The corpus has one file per drug (ketamina_47034.md), so the name of the file is the name of
the drug. When a question names one or more of them, DrugAwareRetriever searches only inside
their data sheets, a few passages per drug, instead of in the whole corpus. Without this a
question about tobramicina can bring passages of cloruro de potasio, and a question about four
drugs gets the passages of the one that matches best. If the question names no drug of the
corpus, the retriever behaves as before.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from rag.chunking import Chunk
from rag.retriever import Hit, tokenize

MIN_PER_DRUG = 2  # fewest passages of each drug when the question names several

# What a student writes when it is not the name of the file. The keys are the file names without
# the registration number (heparina-sodica_56029.md -> heparina-sodica).
ALIASES = {
    "heparina-sodica": ["heparina"],
    "magnesio-sulfato": ["sulfato de magnesio", "magnesio"],
    "cloruro-de-potasio": ["potasio", "cloruro potasico"],
    "sodio-bicarbonato": ["bicarbonato sodico", "bicarbonato"],
    "adrenalina": ["epinefrina"],
    "noradrenalina": ["norepinefrina"],
    "paracetamol": ["acetaminofeno"],
    "metamizol": ["dipirona"],
}


def _stem(source: str) -> str:
    return re.sub(r"_\d+$", "", Path(source).stem)


def drug_lexicon(sources) -> dict[str, list[list[str]]]:
    """For each source file, the token sequences that name its drug."""
    lexicon = {}
    for source in sorted(set(sources)):
        stem = _stem(source)
        names = [stem.replace("-", " ")] + ALIASES.get(stem, [])
        lexicon[source] = [tokenize(name) for name in names]
    return lexicon


def detect_drugs(text: str, lexicon: dict[str, list[list[str]]]) -> list[str]:
    """Source files of the drugs named in text, in the order they first appear.

    A name matches only as whole words (dopamina does not match inside dobutamina) and
    accents and case are ignored, like in the retrievers.
    """
    tokens = tokenize(text)
    first: dict[str, int] = {}
    for source, names in lexicon.items():
        for name in names:
            size = len(name)
            for start in range(len(tokens) - size + 1):
                if tokens[start : start + size] == name:
                    first[source] = min(first.get(source, start), start)
                    break
    return sorted(first, key=first.get)


def passages_per_drug(top_k: int, n_drugs: int) -> int:
    """Passages to bring for each drug: top_k when there is one, shared out when there are more."""
    return max(MIN_PER_DRUG, math.ceil(top_k / n_drugs))


class DrugAwareRetriever:
    """Wraps a retriever so that a question that names drugs is answered from their sheets only."""

    def __init__(self, base, chunks: list[Chunk]):
        self.base = base
        self.n_chunks = len(chunks)
        self.lexicon = drug_lexicon(chunk.source for chunk in chunks)
        self.name = f"{base.name}+drugs"

    def search(self, query: str, top_k: int = 5) -> list[Hit]:
        """Hits of each drug named in the query, in the order of the query, or the plain search."""
        drugs = detect_drugs(query, self.lexicon)
        if not drugs:
            return self.base.search(query, top_k)
        per_drug = passages_per_drug(top_k, len(drugs))
        ranked = self.base.search(query, self.n_chunks)  # the whole ranking, to filter it
        hits: list[Hit] = []
        for source in drugs:
            hits.extend([hit for hit in ranked if hit.chunk.source == source][:per_drug])
        return hits or self.base.search(query, top_k)
