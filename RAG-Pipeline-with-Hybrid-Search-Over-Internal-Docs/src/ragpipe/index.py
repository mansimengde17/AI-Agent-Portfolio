"""Dual indexes: dense vector and sparse BM25, kept in sync.

The offline embedding is a normalized bag-of-words vector; production swaps
in text-embedding-3-small behind the same embed() signature. BM25 is
implemented directly (Okapi BM25, k1=1.5, b=0.75) to keep the ranking
math visible and dependency-free.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .ingest import Chunk

STOPWORDS = {"the", "a", "an", "and", "or", "to", "of", "for", "on", "in",
             "is", "are", "with", "by", "at", "be", "it", "this", "that",
             "from", "as", "can", "per"}


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_.-]+", text.lower())
            if t not in STOPWORDS and len(t) > 1]


def embed(text: str) -> dict[str, float]:
    counts = Counter(tokenize(text))
    norm = math.sqrt(sum(c * c for c in counts.values())) or 1.0
    return {t: c / norm for t, c in counts.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(b) < len(a):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


class HybridIndex:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.chunks: list[Chunk] = []
        self.vectors: list[dict[str, float]] = []
        self.doc_tokens: list[list[str]] = []
        self.doc_freq: Counter = Counter()
        self.k1, self.b = k1, b

    def add(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            tokens = tokenize(chunk.text)
            self.chunks.append(chunk)
            self.vectors.append(embed(chunk.text))
            self.doc_tokens.append(tokens)
            for term in set(tokens):
                self.doc_freq[term] += 1

    @property
    def _avg_len(self) -> float:
        return (sum(len(t) for t in self.doc_tokens)
                / max(1, len(self.doc_tokens)))

    def dense(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        query_vec = embed(query)
        scored = [(i, cosine(query_vec, vec))
                  for i, vec in enumerate(self.vectors)]
        return sorted(scored, key=lambda x: -x[1])[:k]

    def sparse(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        n = len(self.chunks)
        avg_len = self._avg_len
        scores = [0.0] * n
        for term in tokenize(query):
            df = self.doc_freq.get(term, 0)
            if df == 0:
                continue
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for i, tokens in enumerate(self.doc_tokens):
                tf = tokens.count(term)
                if tf == 0:
                    continue
                denom = tf + self.k1 * (1 - self.b
                                        + self.b * len(tokens) / avg_len)
                scores[i] += idf * tf * (self.k1 + 1) / denom
        ranked = sorted(range(n), key=lambda i: -scores[i])[:k]
        return [(i, scores[i]) for i in ranked if scores[i] > 0]
