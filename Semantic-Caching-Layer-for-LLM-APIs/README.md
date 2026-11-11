# Semantic Caching Layer for LLM APIs

A middleware caching service that sits between an application and any LLM provider, detects semantically similar requests that have already been answered, and serves cached responses instantly, cutting latency to near zero and reducing API costs by 30 to 60 percent on typical workloads.

Portfolio: https://mansimengde17.github.io/AI-Agent-Portfolio/

## Why semantic, not exact

"What is Python?" and "Explain Python to me" should hit the same cache entry. Exact string matching gets a near-zero hit rate on natural language traffic; embedding the prompt and matching by cosine similarity against previous prompts turns repeated intent into cache hits even when the wording differs.

## Architecture

```
  application (unchanged, points base_url at the proxy)
        |
        v
 +----------------------------------------------+
 |          OpenAI-compatible proxy               |
 |  POST /v1/chat/completions                     |
 +----------------------------------------------+
        |
        v
 +----------------------------------------------+
 |             Cache key builder                  |
 |  embedding(prompt) + hash(system prompt,       |
 |  model, temperature, max_tokens)               |
 |  -> different configs never cross-contaminate  |
 +----------------------------------------------+
        |
   nearest neighbor >= threshold?
     |  yes                      | no
     v                           v
 serve cached           forward to provider
 (sub-ms, $0)           (OpenAI / Anthropic / Ollama)
                                 |
                                 v
                        store response + embedding,
                        TTL by content class
        |
        v
 +----------------------------------------------+
 |   Metrics: hit rate, cost saved, latency       |
 |   P50/P95, near-miss analyzer, threshold tuner |
 +----------------------------------------------+
```

## Quick start (offline load test)

```bash
pip install -r requirements.txt
python loadtest.py --requests 2000
```

The load test replays a realistic mix of unique and repeated (reworded) queries through the cache and prints the headline numbers: hit rate convergence, cost saved versus no cache, and latency percentiles for hits versus misses.

To run the proxy:

```bash
uvicorn src.semcache.api:app --reload
# POST /v1/chat/completions   OpenAI-format; X-Cache header says HIT or MISS
# GET  /v1/cache/stats        hit rate, savings, latency
# POST /v1/cache/invalidate   by system prompt hash, model, or everything
# GET  /v1/cache/tuner        hit rate and accuracy across thresholds
```

## Cache policy details

- Cache key: the prompt embedding is matched only within the namespace of (system prompt hash, model, temperature bucket, max_tokens). Identical user prompts under different system prompts never share entries.
- TTL tiers: a content classifier assigns long TTLs (24 h) to stable factual queries, short TTLs (1 h) to anything referencing time or current events, and skips caching for prompts classified as creative generation.
- Adaptive thresholds: classification-like requests tolerate 0.90 similarity; creative requests require 0.98 or bypass. Defaults are configurable per request type and learned from feedback.
- Invalidation: by system prompt hash (prompt changed), by model (model upgraded), or full flush. Every invalidation is logged.
- Near-miss analyzer: queries falling just under the threshold are recorded, so the threshold can be tuned with real traffic instead of guesses.

## Streaming

Cache hits return complete responses instantly (no streaming needed). Cache misses stream from the provider while buffering; only complete, successful responses are written to the cache.

## Repository layout

```
src/semcache/cache.py      embedding store, similarity lookup, TTL, invalidation
src/semcache/policies.py   TTL classifier and adaptive thresholds
src/semcache/api.py        OpenAI-compatible FastAPI proxy
src/semcache/metrics.py    hit rate, savings, latency percentiles, near misses
loadtest.py                2000-request realistic load test
tests/
```

The vector store is an in-process index by default; `REDIS_URL` switches the same interface to Redis with RedisVL for multi-instance deployments.
