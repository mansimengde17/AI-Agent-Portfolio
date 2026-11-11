"""Ingestion: multi-format loading, three chunking strategies, dedupe."""

from __future__ import annotations

import html.parser
import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    chunk_id: str
    source: str
    heading: str
    text: str
    strategy: str
    index: int
    meta: dict = field(default_factory=dict)


class _HTMLText(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data):
        self.parts.append(data)


def load_document(path: str, raw: str) -> str:
    """Normalize markdown, text, or HTML into plain text with headings kept."""
    if path.endswith((".html", ".htm")):
        parser = _HTMLText()
        parser.feed(raw)
        return "\n".join(p.strip() for p in parser.parts if p.strip())
    return raw


def chunk_fixed(source: str, text: str, size: int = 400,
                overlap: int = 80) -> list[Chunk]:
    words = text.split()
    chunks = []
    step = max(1, size - overlap)
    for i, start in enumerate(range(0, len(words), step)):
        window = words[start:start + size]
        if not window:
            break
        chunks.append(Chunk(f"{source}:fixed:{i}", source, "", " ".join(window),
                            "fixed", i))
        if start + size >= len(words):
            break
    return chunks


def chunk_structural(source: str, text: str) -> list[Chunk]:
    """Split on markdown headings, keeping the heading path as metadata."""
    sections = re.split(r"(?m)^(#{1,6}\s+.*)$", text)
    chunks = []
    heading = "(intro)"
    buffer = sections[0].strip()
    index = 0
    parts = []
    if buffer:
        parts.append((heading, buffer))
    for i in range(1, len(sections), 2):
        heading = sections[i].lstrip("# ").strip()
        body = sections[i + 1].strip() if i + 1 < len(sections) else ""
        if body:
            parts.append((heading, body))
    for heading, body in parts:
        chunks.append(Chunk(f"{source}:structural:{index}", source, heading,
                            f"{heading}. {body}", "structural", index))
        index += 1
    return chunks


def chunk_semantic(source: str, text: str, embed_fn,
                   boundary: float = 0.25) -> list[Chunk]:
    """Split on topic boundaries: adjacent sentence similarity below the
    boundary threshold starts a new chunk."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text)
                 if len(s.strip()) > 20]
    if not sentences:
        return []
    groups: list[list[str]] = [[sentences[0]]]
    for prev, sent in zip(sentences, sentences[1:]):
        a, b = embed_fn(prev), embed_fn(sent)
        similarity = sum(v * b.get(k, 0.0) for k, v in a.items())
        if similarity < boundary:
            groups.append([sent])
        else:
            groups[-1].append(sent)
    return [Chunk(f"{source}:semantic:{i}", source, "", " ".join(group),
                  "semantic", i) for i, group in enumerate(groups)]


def dedupe(chunks: list[Chunk], embed_fn,
           threshold: float = 0.95) -> tuple[list[Chunk], int]:
    """Drop near-duplicate chunks (cosine similarity above threshold)."""
    kept: list[Chunk] = []
    vectors: list[dict] = []
    dropped = 0
    for chunk in chunks:
        vector = embed_fn(chunk.text)
        duplicate = any(
            sum(v * other.get(k, 0.0) for k, v in vector.items()) > threshold
            for other in vectors)
        if duplicate:
            dropped += 1
            continue
        kept.append(chunk)
        vectors.append(vector)
    return kept, dropped
