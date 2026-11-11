"""Semantic cache: embedding store, similarity lookup, TTL, invalidation."""

from __future__ import annotations

import hashlib
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field


def embed(text: str) -> dict[str, float]:
    """Deterministic bag-of-words embedding with bigrams.

    Production swaps in text-embedding-3-small behind the same signature;
    bigrams give the offline version enough phrase sensitivity to
    distinguish 'convert dollars to euros' from 'convert euros to dollars'.
    """
    tokens = re.findall(r"[a-z0-9']+", text.lower())
    grams = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    counts = Counter(grams)
    norm = math.sqrt(sum(c * c for c in counts.values())) or 1.0
    return {g: c / norm for g, c in counts.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(b) < len(a):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def namespace_key(system_prompt: str, model: str, temperature: float,
                  max_tokens: int | None) -> str:
    raw = f"{system_prompt}|{model}|{round(temperature, 1)}|{max_tokens}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class CacheEntry:
    prompt: str
    vector: dict[str, float]
    response: dict
    namespace: str
    model: str
    created: float
    ttl_s: float
    hits: int = 0

    @property
    def expired(self) -> bool:
        return time.time() > self.created + self.ttl_s


@dataclass
class LookupResult:
    hit: bool
    similarity: float
    entry: CacheEntry | None = None
    near_miss: bool = False


class SemanticCache:
    def __init__(self):
        self.entries: dict[str, list[CacheEntry]] = {}
        self.near_misses: list[dict] = []

    def lookup(self, prompt: str, namespace: str,
               threshold: float) -> LookupResult:
        vector = embed(prompt)
        best, best_score = None, 0.0
        for entry in self.entries.get(namespace, []):
            if entry.expired:
                continue
            score = cosine(vector, entry.vector)
            if score > best_score:
                best, best_score = entry, score
        if best is not None and best_score >= threshold:
            best.hits += 1
            return LookupResult(True, round(best_score, 4), best)
        near = best is not None and best_score >= threshold - 0.08
        if near:
            self.near_misses.append({"prompt": prompt,
                                     "similarity": round(best_score, 4),
                                     "threshold": threshold,
                                     "matched": best.prompt})
        return LookupResult(False, round(best_score, 4), None, near_miss=near)

    def store(self, prompt: str, response: dict, namespace: str, model: str,
              ttl_s: float) -> None:
        self.entries.setdefault(namespace, []).append(CacheEntry(
            prompt=prompt, vector=embed(prompt), response=response,
            namespace=namespace, model=model, created=time.time(),
            ttl_s=ttl_s))

    def invalidate(self, namespace: str | None = None,
                   model: str | None = None) -> int:
        removed = 0
        if namespace is not None:
            removed = len(self.entries.pop(namespace, []))
        elif model is not None:
            for ns, entries in self.entries.items():
                keep = [e for e in entries if e.model != model]
                removed += len(entries) - len(keep)
                self.entries[ns] = keep
        else:
            removed = sum(len(v) for v in self.entries.values())
            self.entries.clear()
        return removed

    def evict_expired(self) -> int:
        removed = 0
        for ns in list(self.entries):
            keep = [e for e in self.entries[ns] if not e.expired]
            removed += len(self.entries[ns]) - len(keep)
            self.entries[ns] = keep
        return removed

    @property
    def size(self) -> int:
        return sum(len(v) for v in self.entries.values())
