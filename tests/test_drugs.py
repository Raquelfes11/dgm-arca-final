"""Drug detection and the drug aware retriever, with a fake retriever: no model is loaded."""

from rag.chunking import Chunk
from rag.drugs import DrugAwareRetriever, detect_drugs, drug_lexicon, passages_per_drug
from rag.retriever import Hit, tokenize

SOURCES = [
    "ketamina_47034.md", "tobramicina_65261.md", "cloruro-de-potasio_60353.md",
    "heparina-sodica_56029.md", "magnesio-sulfato_23622.md", "adrenalina_35403.md",
    "dopamina_1241804001.md", "dobutamina_85914.md",
]


def chunks_of(sources, per_source=6):
    return [
        Chunk(id=f"{s[:4]}-{i:04d}", doc_id=s, source=s, text=f"{s[:4]} pasaje {i}", index=i)
        for s in sources
        for i in range(per_source)
    ]


class FakeRetriever:
    """Ranks the chunks by how many words of the query they share. Records the top_k asked."""

    name = "fake"

    def __init__(self, chunks):
        self.chunks = chunks
        self.asked = []

    def search(self, query, top_k=5):
        self.asked.append(top_k)
        words = set(tokenize(query))
        scored = [(len(words & set(tokenize(c.text))), c) for c in self.chunks]
        scored.sort(key=lambda pair: -pair[0])  # stable: ties keep the order of the chunks
        return [Hit(c, float(score)) for score, c in scored[:top_k]]


LEXICON = drug_lexicon(SOURCES)


def test_names_come_from_the_file_names_and_ignore_accents_and_case():
    assert detect_drugs("¿Qué dosis de Ketamina lleva?", LEXICON) == ["ketamina_47034.md"]
    assert detect_drugs("cloruro de potasio al 2 %", LEXICON) == ["cloruro-de-potasio_60353.md"]
    assert detect_drugs("heparina sódica 5000 UI", LEXICON) == ["heparina-sodica_56029.md"]


def test_aliases_cover_what_a_student_writes():
    assert detect_drugs("heparina", LEXICON) == ["heparina-sodica_56029.md"]
    assert detect_drugs("sulfato de magnesio", LEXICON) == ["magnesio-sulfato_23622.md"]
    assert detect_drugs("epinefrina en bolo", LEXICON) == ["adrenalina_35403.md"]


def test_names_match_whole_words_only():
    assert detect_drugs("dopamina", LEXICON) == ["dopamina_1241804001.md"]
    assert detect_drugs("dobutamina y dopamina", LEXICON) == [
        "dobutamina_85914.md", "dopamina_1241804001.md"]  # in order of appearance
    assert detect_drugs("ketaminas y tobramicinas", LEXICON) == []
    assert detect_drugs("omeprazol intravenoso", LEXICON) == []


def test_passages_are_shared_out_between_drugs_with_a_floor():
    assert [passages_per_drug(5, n) for n in (1, 2, 3, 4)] == [5, 3, 2, 2]
    assert passages_per_drug(3, 1) == 3


def test_a_question_about_one_drug_only_brings_its_sheet():
    chunks = chunks_of(SOURCES)
    retriever = DrugAwareRetriever(FakeRetriever(chunks), chunks)
    hits = retriever.search("dosis de tobramicina pasaje", top_k=5)
    assert len(hits) == 5
    assert {h.chunk.source for h in hits} == {"tobramicina_65261.md"}


def test_a_question_about_several_drugs_brings_passages_of_each_in_order():
    chunks = chunks_of(SOURCES)
    retriever = DrugAwareRetriever(FakeRetriever(chunks), chunks)
    hits = retriever.search("ketamina, tobramicina, heparina y adrenalina", top_k=5)
    assert [h.chunk.source for h in hits] == (
        ["ketamina_47034.md"] * 2 + ["tobramicina_65261.md"] * 2
        + ["heparina-sodica_56029.md"] * 2 + ["adrenalina_35403.md"] * 2
    )


def test_without_a_drug_in_the_question_it_is_the_plain_search():
    chunks = chunks_of(SOURCES)
    base = FakeRetriever(chunks)
    retriever = DrugAwareRetriever(base, chunks)
    assert retriever.search("omeprazol pasaje", top_k=4) == FakeRetriever(chunks).search(
        "omeprazol pasaje", top_k=4)
    assert retriever.name == "fake+drugs"
