"""Grounded generation with citations, verification, and confidence."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .index import tokenize
from .retrieve import Retrieved

CONFIDENCE_FLOOR = 0.30


@dataclass
class Citation:
    marker: int
    chunk_id: str
    sentence: str
    verified: bool


@dataclass
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    retrieval_confidence: float = 0.0
    citation_coverage: float = 0.0
    completeness: float = 0.0
    confidence: float = 0.0
    answered: bool = True
    sources: list[str] = field(default_factory=list)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text)
            if len(s.strip()) > 15]


def generate(question: str, retrieved: list[Retrieved]) -> Answer:
    """Extractive grounded generation.

    Selects the sentences from the retrieved chunks that best cover the
    question terms and assembles them with bracketed citations. Production
    replaces this with an LLM given the same numbered context blocks and the
    instruction to cite; the citation verification and confidence layers are
    identical in both modes.
    """
    query_terms = set(tokenize(question))
    picked: list[tuple[str, int]] = []
    for number, item in enumerate(retrieved, start=1):
        best, best_score = None, 0.0
        for sentence in _sentences(item.chunk.text):
            terms = set(tokenize(sentence))
            score = len(query_terms & terms) / (len(query_terms) or 1)
            if score > best_score:
                best, best_score = sentence, score
        if best and best_score >= 0.25:
            picked.append((best, number))
        if len(picked) >= 3:
            break

    retrieval_confidence = (retrieved[0].rerank_score if retrieved else 0.0)
    if not picked or retrieval_confidence < CONFIDENCE_FLOOR:
        found = ", ".join(f"{r.chunk.source} ({r.chunk.heading or 'section'})"
                          for r in retrieved[:3])
        return Answer(
            text=("The indexed documentation does not contain enough"
                  " information to answer this question."
                  + (f" Closest sections checked: {found}." if found else "")),
            retrieval_confidence=round(retrieval_confidence, 3),
            confidence=round(retrieval_confidence * 0.5, 3),
            answered=False,
            sources=[r.chunk.chunk_id for r in retrieved[:3]])

    text = " ".join(f"{sentence} [{number}]" for sentence, number in picked)
    citations = [
        Citation(marker=number,
                 chunk_id=retrieved[number - 1].chunk.chunk_id,
                 sentence=sentence,
                 verified=_supports(sentence, retrieved[number - 1].chunk.text))
        for sentence, number in picked]
    coverage = (sum(c.verified for c in citations) / len(citations))
    completeness = min(1.0, sum(
        1 for t in query_terms if t in tokenize(text)) / (len(query_terms) or 1)
        + 0.2)
    confidence = round(0.4 * min(1.0, retrieval_confidence)
                       + 0.4 * coverage + 0.2 * completeness, 3)
    return Answer(text=text, citations=citations,
                  retrieval_confidence=round(retrieval_confidence, 3),
                  citation_coverage=round(coverage, 3),
                  completeness=round(completeness, 3),
                  confidence=confidence,
                  sources=[r.chunk.chunk_id for r in retrieved])


def _supports(sentence: str, chunk_text: str) -> bool:
    """Citation verification: does the cited chunk contain the claim?"""
    sentence_terms = set(tokenize(sentence))
    chunk_terms = set(tokenize(chunk_text))
    if not sentence_terms:
        return False
    return len(sentence_terms & chunk_terms) / len(sentence_terms) >= 0.8
