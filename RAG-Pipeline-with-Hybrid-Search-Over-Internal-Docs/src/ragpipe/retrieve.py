"""Hybrid retrieval: RRF fusion of dense and sparse results plus reranking."""

from __future__ import annotations

from dataclasses import dataclass

from .index import HybridIndex, tokenize
from .ingest import Chunk


@dataclass
class Retrieved:
    chunk: Chunk
    fused_score: float
    dense_rank: int | None
    sparse_rank: int | None
    rerank_score: float = 0.0


def rrf_fuse(dense: list[tuple[int, float]], sparse: list[tuple[int, float]],
             dense_weight: float = 0.7, k: int = 60) -> dict[int, float]:
    """Reciprocal Rank Fusion with configurable dense/sparse weighting."""
    fused: dict[int, float] = {}
    for rank, (idx, _) in enumerate(dense):
        fused[idx] = fused.get(idx, 0.0) + dense_weight / (k + rank + 1)
    for rank, (idx, _) in enumerate(sparse):
        fused[idx] = fused.get(idx, 0.0) + (1 - dense_weight) / (k + rank + 1)
    return fused


def rerank(question: str, candidates: list[Retrieved]) -> list[Retrieved]:
    """Second-pass relevance scoring of fused candidates.

    Offline: weighted term coverage of the question in the chunk, favoring
    rare exact matches (identifiers, error codes). Production swaps in a
    cross-encoder or LLM-as-judge with the same signature.
    """
    query_terms = tokenize(question)
    for candidate in candidates:
        chunk_terms = set(tokenize(candidate.chunk.text))
        if not query_terms:
            candidate.rerank_score = 0.0
            continue
        hits = sum(1.0 + 0.5 * ("_" in t or t.isdigit() or "-" in t)
                   for t in query_terms if t in chunk_terms)
        candidate.rerank_score = hits / len(query_terms)
    return sorted(candidates, key=lambda c: -c.rerank_score)


def retrieve(index: HybridIndex, question: str, k_each: int = 10,
             keep: int = 5, dense_weight: float = 0.7,
             hybrid: bool = True) -> list[Retrieved]:
    dense = index.dense(question, k_each * 2)
    sparse = index.sparse(question, k_each * 2) if hybrid else []
    fused = rrf_fuse(dense[:k_each], sparse[:k_each], dense_weight)
    if not hybrid:
        fused = {idx: score for rank, (idx, score) in enumerate(dense[:k_each])
                 for idx, score in [(idx, 1.0 / (rank + 1))]}
    dense_ranks = {idx: r for r, (idx, _) in enumerate(dense)}
    sparse_ranks = {idx: r for r, (idx, _) in enumerate(sparse)}
    candidates = [Retrieved(chunk=index.chunks[idx], fused_score=score,
                            dense_rank=dense_ranks.get(idx),
                            sparse_rank=sparse_ranks.get(idx))
                  for idx, score in sorted(fused.items(),
                                           key=lambda x: -x[1])[:20]]
    return rerank(question, candidates)[:keep]
