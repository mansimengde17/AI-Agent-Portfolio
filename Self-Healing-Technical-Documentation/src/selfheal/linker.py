"""Code-to-docs link graph.

Links are created by name-mention heuristics first, then augmented with
cosine similarity over deterministic bag-of-words embeddings. The embedding
function is pluggable; production deployments swap in
text-embedding-3-small while tests and the demo stay offline.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass

from .code_parser import CodeChunk
from .doc_parser import DocSection


def embed(text: str) -> dict[str, float]:
    words = re.findall(r"[a-z_][a-z0-9_]+", text.lower())
    counts = Counter(words)
    norm = math.sqrt(sum(c * c for c in counts.values())) or 1.0
    return {w: c / norm for w, c in counts.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(b) < len(a):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


@dataclass
class Link:
    chunk_id: str
    section_id: str
    reason: str            # name_mention | embedding
    score: float


class LinkGraph:
    def __init__(self, similarity_threshold: float = 0.35):
        self.links: list[Link] = []
        self.similarity_threshold = similarity_threshold

    def build(self, chunks: list[CodeChunk],
              sections: list[DocSection]) -> "LinkGraph":
        self.links = []
        seen = set()
        for section in sections:
            refs = {r.split(".")[-1] for r in section.code_refs}
            for chunk in chunks:
                short = chunk.name.split(".")[-1]
                if short in refs or chunk.name in section.code_refs:
                    self.links.append(Link(chunk.chunk_id, section.section_id,
                                           "name_mention", 1.0))
                    seen.add((chunk.chunk_id, section.section_id))
        for section in sections:
            section_vec = embed(section.content)
            for chunk in chunks:
                if (chunk.chunk_id, section.section_id) in seen:
                    continue
                score = cosine(embed(chunk.docstring + " " + chunk.signature),
                               section_vec)
                if score >= self.similarity_threshold:
                    self.links.append(Link(chunk.chunk_id, section.section_id,
                                           "embedding", round(score, 3)))
        return self

    def sections_for_chunk(self, chunk_id: str) -> list[Link]:
        return [l for l in self.links if l.chunk_id == chunk_id]

    def save(self, path: str = "docs_link_graph.json") -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([asdict(l) for l in self.links], fh, indent=2)

    @classmethod
    def load(cls, path: str = "docs_link_graph.json") -> "LinkGraph":
        graph = cls()
        with open(path, encoding="utf-8") as fh:
            graph.links = [Link(**raw) for raw in json.load(fh)]
        return graph
