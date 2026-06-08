"""Deterministic local embeddings.

We avoid a network/model dependency for the dev stack by hashing token n-grams into a fixed-width,
L2-normalised vector. This is not a semantic LLM embedding, but combined with BM25 keyword scoring in
``store.py`` it gives stable, offline, reproducible hybrid retrieval good enough for clause lookup.
The production target is a real embedding model into Qdrant (see plan/phase-07); the ``Embedder``
interface is the seam where that swaps in.
"""

from __future__ import annotations

import math
import re

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    """Lowercase word/number tokens; keeps dotted clause numbers like '1208.1' intact."""
    return _TOKEN_RE.findall(text.lower())


class Embedder:
    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def _bucket(self, token: str) -> int:
        return hash_token(token) % self.dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = tokenize(text)
        for tok in tokens:
            vec[self._bucket(tok)] += 1.0
            # include character trigrams for fuzzy overlap
            for i in range(len(tok) - 2):
                vec[self._bucket(tok[i : i + 3])] += 0.5
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


def hash_token(token: str) -> int:
    """Deterministic, process-independent hash (Python's builtin ``hash`` is salted)."""
    h = 2166136261
    for ch in token:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))
