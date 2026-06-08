"""Hybrid (dense + keyword) retrieval over ingested clause chunks.

Dense: cosine over the deterministic ``Embedder`` vectors.
Keyword: BM25 over the same token stream (good for clause numbers and exact terms like "bedroom").
The two normalised scores are blended. This is an in-memory index; the production target is Qdrant
(plan/phase-07), which the ``VectorStore`` API mirrors (upsert / search per jurisdiction).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .embeddings import Embedder, cosine, tokenize
from .ingest import Chunk

_BM25_K1 = 1.5
_BM25_B = 0.75


@dataclass
class SearchHit:
    chunk: Chunk
    score: float
    dense: float
    keyword: float


class VectorStore:
    """One in-memory index keyed by jurisdiction."""

    def __init__(self, dim: int = 256, *, alpha: float = 0.5) -> None:
        self.embedder = Embedder(dim)
        self.alpha = alpha  # weight on dense vs keyword
        self._chunks: dict[str, list[Chunk]] = {}
        self._vectors: dict[str, list[list[float]]] = {}
        self._tokens: dict[str, list[list[str]]] = {}

    def upsert(self, jurisdiction_id: str, chunks: list[Chunk]) -> None:
        self._chunks[jurisdiction_id] = list(chunks)
        self._vectors[jurisdiction_id] = [self.embedder.embed(c.text) for c in chunks]
        self._tokens[jurisdiction_id] = [tokenize(f"{c.section} {c.text}") for c in chunks]

    def search(self, jurisdiction_id: str, query: str, top_k: int = 5) -> list[SearchHit]:
        chunks = self._chunks.get(jurisdiction_id)
        if not chunks:
            return []
        q_vec = self.embedder.embed(query)
        q_tokens = tokenize(query)
        dense = [cosine(q_vec, v) for v in self._vectors[jurisdiction_id]]
        keyword = self._bm25(jurisdiction_id, q_tokens)

        d_max = max(dense) or 1.0
        k_max = max(keyword) or 1.0
        hits: list[SearchHit] = []
        for i, chunk in enumerate(chunks):
            d = dense[i] / d_max
            k = keyword[i] / k_max
            score = self.alpha * d + (1.0 - self.alpha) * k
            hits.append(SearchHit(chunk=chunk, score=score, dense=dense[i], keyword=keyword[i]))
        hits.sort(key=lambda h: (h.score, h.chunk.section), reverse=True)
        return hits[:top_k]

    def _bm25(self, jurisdiction_id: str, q_tokens: list[str]) -> list[float]:
        docs = self._tokens[jurisdiction_id]
        n = len(docs)
        avgdl = sum(len(d) for d in docs) / n if n else 0.0
        # document frequency per query term
        df: dict[str, int] = {}
        for term in set(q_tokens):
            df[term] = sum(1 for d in docs if term in d)
        scores: list[float] = []
        for d in docs:
            dl = len(d)
            counts: dict[str, int] = {}
            for t in d:
                counts[t] = counts.get(t, 0) + 1
            s = 0.0
            for term in q_tokens:
                f = counts.get(term, 0)
                if f == 0 or df.get(term, 0) == 0:
                    continue
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                denom = f + _BM25_K1 * (1 - _BM25_B + _BM25_B * dl / avgdl) if avgdl else 1.0
                s += idf * (f * (_BM25_K1 + 1)) / denom
            scores.append(s)
        return scores
