"""
Lightweight local vector store for RAG.

Design choice (documented in RAG_PIPELINE_EXPLANATION.md):
We use TF-IDF + cosine similarity (scikit-learn) as the embedding/retrieval
backend instead of a hosted vector DB (ChromaDB/Pinecone/etc). This is a
deliberate, defensible choice for a demo/portfolio deployment:
  - Zero external services, zero API keys, zero network calls required.
  - Fully deterministic and reproducible — same query always returns the
    same ranked results, which matters for an explainable decision system.
  - The retrieval interface (`add_documents`, `query`) is abstracted behind
    this module, so swapping in ChromaDB + real sentence-transformer
    embeddings later is a drop-in replacement with no changes to the
    agents that call it.

Each ProcurementRequest gets its own isolated collection (in-memory index,
persisted to disk as a pickle per request) so vendor documents from one
procurement don't leak into another's retrieval context.
"""
from __future__ import annotations
import pickle
import re
from dataclasses import dataclass, field
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

STORE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "vector_store"
STORE_DIR.mkdir(parents=True, exist_ok=True)


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _split_into_units(text: str) -> list[str]:
    """
    Split text into atomic semantic units (bullet lines or sentences)
    BEFORE grouping into chunks. This keeps a single fact (e.g. one
    certification statement) from being torn across a chunk boundary or
    diluted by unrelated neighboring content, which is critical for
    precise evidence retrieval in a short-document corpus like vendor
    proposals.
    """
    units: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Bullet / list lines are already atomic
        if line.startswith(("-", "•", "*")) or re.match(r"^\d+[.)]", line):
            units.append(line)
            continue
        # Otherwise split the line into sentences
        sentences = _SENTENCE_SPLIT_RE.split(line)
        units.extend(s.strip() for s in sentences if s.strip())
    return units


def chunk_text(text: str, chunk_size: int = 60, overlap_units: int = 1) -> list[str]:
    """
    Groups semantic units (sentences/bullets) into chunks up to ~chunk_size
    words, never splitting a unit across a chunk boundary. A 1-unit overlap
    carries context across chunk boundaries without diluting any single
    chunk's topical focus.
    """
    units = _split_into_units(text)
    if not units:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for unit in units:
        unit_words = len(unit.split())
        if current and current_words + unit_words > chunk_size:
            chunks.append(" ".join(current))
            current = current[-overlap_units:] if overlap_units else []
            current_words = sum(len(u.split()) for u in current)
        current.append(unit)
        current_words += unit_words

    if current:
        chunks.append(" ".join(current))

    return chunks


@dataclass
class ChunkRecord:
    chunk_id: str
    text: str
    source_document_id: str
    source_filename: str
    page_number: int | None
    metadata: dict = field(default_factory=dict)


_STOPWORD_TERMS = {
    "vendor", "must", "provide", "offer", "offers", "demonstrate", "disclose",
    "with", "under", "business", "days", "capability", "total", "should",
    "will", "have", "that", "this", "from", "than", "support", "compliance",
}


def _salient_terms(text: str) -> set[str]:
    """
    Extract the terms in a requirement that actually carry discriminating
    meaning (acronyms, numbers, domain nouns) — the words a human would
    scan a document for, as opposed to boilerplate requirement phrasing
    ("vendor must provide..."). Used for a lexical overlap boost alongside
    TF-IDF similarity (see `keyword_overlap_boost`).
    """
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9/\-]*", text)
    terms = set()
    for w in words:
        lw = w.lower()
        if lw in _STOPWORD_TERMS:
            continue
        if len(w) <= 3 and not w.isupper():
            continue
        terms.add(lw)
    return terms


def keyword_overlap_boost(query: str, chunk_text: str, max_boost: float = 0.35) -> float:
    """
    Returns a 0..max_boost bonus based on the fraction of the query's
    salient terms (acronyms, numbers, domain nouns) that appear verbatim
    in the chunk. This is a deliberate hybrid-retrieval design choice:
    TF-IDF's IDF weighting discounts terms that appear across MANY vendor
    documents (e.g. "ISO", "certified", "GDPR" showing up in every vendor's
    compliance section) — exactly the terms that matter most for a direct
    factual match. A lexical overlap boost restores precision for these
    cases without abandoning the statistical ranking for everything else.
    """
    terms = _salient_terms(query)
    if not terms:
        return 0.0
    chunk_lower = chunk_text.lower()
    matched = sum(1 for t in terms if t in chunk_lower)
    return round((matched / len(terms)) * max_boost, 4)


class RequestVectorStore:
    """One TF-IDF index per procurement request (acts as the 'collection')."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.records: list[ChunkRecord] = []
        self.vectorizer: TfidfVectorizer | None = None
        self._matrix = None

    @property
    def _path(self) -> Path:
        return STORE_DIR / f"{self.request_id}.pkl"

    def add_document(self, document_id: str, filename: str, parsed_pages: list[tuple[int, str]]):
        next_idx = len(self.records)
        for page_number, page_text in parsed_pages:
            for chunk in chunk_text(page_text):
                self.records.append(
                    ChunkRecord(
                        chunk_id=f"{document_id}-{next_idx}",
                        text=chunk,
                        source_document_id=document_id,
                        source_filename=filename,
                        page_number=page_number,
                    )
                )
                next_idx += 1
        self._rebuild_index()
        self.save()

    def _rebuild_index(self):
        if not self.records:
            self.vectorizer = None
            self._matrix = None
            return
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
        self._matrix = self.vectorizer.fit_transform([r.text for r in self.records])

    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        """
        Hybrid retrieval: TF-IDF cosine similarity (captures broad topical
        relevance) combined with a lexical keyword-overlap boost (captures
        exact factual matches on acronyms/numbers that IDF would otherwise
        discount — see `keyword_overlap_boost`). Final ranking and the
        returned `similarity` are both post-boost, since that combined
        score is what downstream agents actually reason over.
        """
        if not self.records or self.vectorizer is None:
            return []
        q_vec = self.vectorizer.transform([query_text])
        base_sims = cosine_similarity(q_vec, self._matrix).flatten()

        combined = []
        for idx, base_sim in enumerate(base_sims):
            if base_sim <= 0 and not self.records[idx].text:
                continue
            boost = keyword_overlap_boost(query_text, self.records[idx].text)
            combined.append((idx, min(float(base_sim) + boost, 1.0)))

        combined.sort(key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in combined[:top_k]:
            if score <= 0:
                continue
            rec = self.records[idx]
            results.append({
                "chunk_id": rec.chunk_id,
                "text": rec.text,
                "source_document_id": rec.source_document_id,
                "source_filename": rec.source_filename,
                "page_number": rec.page_number,
                "similarity": round(score, 4),
            })
        return results

    def save(self):
        with open(self._path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load_or_create(cls, request_id: str) -> "RequestVectorStore":
        path = STORE_DIR / f"{request_id}.pkl"
        if path.exists():
            with open(path, "rb") as f:
                return pickle.load(f)
        return cls(request_id)


_CACHE: dict[str, RequestVectorStore] = {}


def get_store(request_id: str) -> RequestVectorStore:
    if request_id not in _CACHE:
        _CACHE[request_id] = RequestVectorStore.load_or_create(request_id)
    return _CACHE[request_id]
