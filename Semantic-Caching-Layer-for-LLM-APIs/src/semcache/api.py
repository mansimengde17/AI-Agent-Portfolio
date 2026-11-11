"""OpenAI-compatible caching proxy."""

from __future__ import annotations

import hashlib
import os
import time

from fastapi import FastAPI, Response
from pydantic import BaseModel

from .cache import SemanticCache, namespace_key
from .metrics import Metrics
from .policies import threshold_for, ttl_for

app = FastAPI(title="Semantic Caching Layer", version="1.0.0")
cache = SemanticCache()
metrics = Metrics()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[Message]
    temperature: float = 0.0
    max_tokens: int | None = None


def call_provider(request: ChatRequest, prompt: str) -> dict:
    """Forward a miss to the real provider; offline fallback echoes a
    deterministic simulated completion so the proxy is testable anywhere."""
    if os.environ.get("OPENAI_API_KEY"):
        import json
        import urllib.request
        body = json.dumps(request.model_dump()).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions", data=body,
            headers={"Content-Type": "application/json",
                     "Authorization":
                         f"Bearer {os.environ['OPENAI_API_KEY']}"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    time.sleep(0.15)  # simulated provider latency
    seed = hashlib.sha256(prompt.encode()).hexdigest()[:8]
    text = f"Simulated completion {seed} for: {prompt[:60]}"
    tokens = len(prompt.split()) + len(text.split())
    return {"id": f"chatcmpl-{seed}", "model": request.model,
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": len(prompt.split()),
                      "completion_tokens": len(text.split()),
                      "total_tokens": tokens}}


@app.post("/v1/chat/completions")
def chat(request: ChatRequest, response: Response):
    system = " ".join(m.content for m in request.messages
                      if m.role == "system")
    prompt = " ".join(m.content for m in request.messages
                      if m.role == "user")
    namespace = namespace_key(system, request.model, request.temperature,
                              request.max_tokens)

    ttl = ttl_for(prompt)
    if ttl is None:
        metrics.skipped_uncacheable += 1
        response.headers["X-Cache"] = "BYPASS"
        return call_provider(request, prompt)

    start = time.perf_counter()
    result = cache.lookup(prompt, namespace, threshold_for(prompt))
    if result.hit:
        latency = time.perf_counter() - start
        metrics.record_hit(latency,
                           result.entry.response["usage"]["total_tokens"])
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Similarity"] = str(result.similarity)
        return result.entry.response

    upstream = call_provider(request, prompt)
    latency = time.perf_counter() - start
    metrics.record_miss(latency)
    if upstream["choices"][0]["finish_reason"] == "stop":
        cache.store(prompt, upstream, namespace, request.model, ttl)
    response.headers["X-Cache"] = "MISS"
    return upstream


@app.get("/v1/cache/stats")
def stats():
    summary = metrics.summary()
    summary["entries"] = cache.size
    summary["near_misses"] = len(cache.near_misses)
    return summary


class InvalidateRequest(BaseModel):
    namespace: str | None = None
    model: str | None = None


@app.post("/v1/cache/invalidate")
def invalidate(request: InvalidateRequest):
    removed = cache.invalidate(request.namespace, request.model)
    return {"invalidated": removed}


@app.get("/v1/cache/tuner")
def tuner():
    """Hit rates the current traffic would have had at other thresholds."""
    rows = []
    for threshold in (0.85, 0.90, 0.95, 0.98):
        would_hit = sum(1 for m in cache.near_misses
                        if m["similarity"] >= threshold)
        rows.append({"threshold": threshold,
                     "additional_hits_from_near_misses": would_hit})
    return {"near_misses_analyzed": len(cache.near_misses), "rows": rows}
