"""Cache metrics: hit rate, savings, latency percentiles, near misses."""

from __future__ import annotations

from dataclasses import dataclass, field

# Reference cost used for the savings estimate (USD per 1M tokens, blended).
COST_PER_M_TOKENS = 5.0


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(pct / 100 * (len(ordered) - 1))))
    return ordered[index]


@dataclass
class Metrics:
    hits: int = 0
    misses: int = 0
    tokens_saved: int = 0
    hit_latencies: list[float] = field(default_factory=list)
    miss_latencies: list[float] = field(default_factory=list)
    skipped_uncacheable: int = 0

    def record_hit(self, latency_s: float, tokens: int) -> None:
        self.hits += 1
        self.hit_latencies.append(latency_s)
        self.tokens_saved += tokens

    def record_miss(self, latency_s: float) -> None:
        self.misses += 1
        self.miss_latencies.append(latency_s)

    def summary(self) -> dict:
        total = self.hits + self.misses
        return {
            "requests": total,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 4) if total else 0.0,
            "uncacheable_skipped": self.skipped_uncacheable,
            "estimated_cost_saved_usd": round(
                self.tokens_saved * COST_PER_M_TOKENS / 1_000_000, 4),
            "latency_ms": {
                "hit_p50": round(percentile(self.hit_latencies, 50) * 1000, 2),
                "hit_p95": round(percentile(self.hit_latencies, 95) * 1000, 2),
                "miss_p50": round(percentile(self.miss_latencies, 50) * 1000, 2),
                "miss_p95": round(percentile(self.miss_latencies, 95) * 1000, 2),
            },
        }
