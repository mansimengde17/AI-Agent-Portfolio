#!/usr/bin/env python3
"""Realistic load test against the cache core (no server needed)."""

from __future__ import annotations

import argparse
import random
import sys
import time

sys.path.insert(0, "src")

from semcache.cache import SemanticCache, namespace_key
from semcache.metrics import Metrics
from semcache.policies import threshold_for, ttl_for

BASE_QUERIES = [
    "What is Python and what is it used for",
    "Explain how HTTPS encryption works",
    "Summarize the benefits of unit testing",
    "How do I reset my account password",
    "What is the difference between a list and a tuple in Python",
    "Explain what an API rate limit is",
    "How does garbage collection work in Java",
    "What are database indexes and why do they help",
    "Explain the CAP theorem in distributed systems",
    "What is the purpose of a load balancer",
    "Classify this ticket as bug or feature request: the export button crashes",
    "Extract the deadline from: the report is due on Friday at noon",
]

REWORDINGS = [
    lambda q: q,
    lambda q: q.replace("What is", "Explain what is"),
    lambda q: q.replace("Explain", "Please explain"),
    lambda q: q + " in simple terms",
    lambda q: "Can you tell me " + q.lower(),
]


def simulated_provider(prompt: str) -> dict:
    time.sleep(0.002)  # scaled-down stand-in for ~1.5s provider latency
    tokens = len(prompt.split()) * 12
    return {"usage": {"total_tokens": tokens},
            "choices": [{"finish_reason": "stop",
                         "message": {"content": f"answer for {prompt[:30]}"}}]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=2000)
    args = parser.parse_args()
    random.seed(7)

    cache = SemanticCache()
    metrics = Metrics()
    namespace = namespace_key("You are a helpful assistant.", "gpt-4o-mini",
                              0.0, None)

    checkpoints = {}
    for i in range(args.requests):
        if random.random() < 0.25:
            prompt = (f"Unique question {i}: describe scenario"
                      f" {random.randint(0, 10**9)}")
        else:
            base = random.choice(BASE_QUERIES)
            prompt = random.choice(REWORDINGS)(base)

        ttl = ttl_for(prompt) or 86400.0
        start = time.perf_counter()
        result = cache.lookup(prompt, namespace, threshold_for(prompt, 0.80))
        if result.hit:
            metrics.record_hit(time.perf_counter() - start,
                               result.entry.response["usage"]["total_tokens"])
        else:
            upstream = simulated_provider(prompt)
            metrics.record_miss(time.perf_counter() - start)
            cache.store(prompt, upstream, namespace, "gpt-4o-mini", ttl)

        if (i + 1) in (100, 500, 1000, args.requests):
            checkpoints[i + 1] = metrics.summary()["hit_rate"]

    summary = metrics.summary()
    print(f"Requests:        {summary['requests']}")
    print(f"Hit rate:        {summary['hit_rate']:.1%}")
    print("Hit rate convergence: "
          + ", ".join(f"@{n}: {r:.1%}" for n, r in checkpoints.items()))
    print(f"Cost saved:      ${summary['estimated_cost_saved_usd']}"
          f" (at $5.00 per 1M blended tokens)")
    lat = summary["latency_ms"]
    print(f"Latency P50:     hit {lat['hit_p50']}ms vs miss {lat['miss_p50']}ms")
    print(f"Latency P95:     hit {lat['hit_p95']}ms vs miss {lat['miss_p95']}ms")
    print(f"Cache entries:   {cache.size}")
    print(f"Near misses:     {len(cache.near_misses)}")


if __name__ == "__main__":
    main()
