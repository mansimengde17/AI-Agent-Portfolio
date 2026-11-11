"""Unified provider interface.

send_request(prompt, model_key) works identically for OpenAI, Anthropic,
Ollama, and the offline simulation provider. Every call returns a
standardized LLMResult with text, token counts, latency, cost, and model.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from dataclasses import dataclass

from .registry import REGISTRY, cost_of


@dataclass
class LLMResult:
    text: str
    model_key: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    cost_usd: float


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def simulate(prompt: str, model_key: str) -> LLMResult:
    """Deterministic offline simulation of a provider call.

    Response quality scales with the model's quality tier so the verification
    loop has real signal to work with: a low-tier model answering a complex
    prompt produces a visibly thinner answer than the top-tier model.
    """
    config = REGISTRY[model_key]
    seed = int(hashlib.sha256(f"{model_key}:{prompt}".encode()).hexdigest(), 16)
    depth = {"high": 3, "medium": 2, "low": 1}[config.quality_tier]
    complexity_markers = sum(prompt.lower().count(v) for v in
                             ("analyze", "compare", "explain why", "design",
                              "multi-step", "prove", "strategy"))
    sentences = []
    for i in range(depth + min(complexity_markers, 2)):
        sentences.append(
            f"Point {i + 1}: response segment {seed % 97:02d}-{i} addressing"
            f" the request '{' '.join(prompt.split()[:6])}'.")
    if complexity_markers > depth:
        sentences.append("Note: full multi-step reasoning was truncated.")
    text = " ".join(sentences)
    input_tokens = _estimate_tokens(prompt)
    output_tokens = _estimate_tokens(text)
    return LLMResult(
        text=text,
        model_key=model_key,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_s=config.avg_latency_s * (0.8 + (seed % 40) / 100),
        cost_usd=cost_of(model_key, input_tokens, output_tokens),
    )


def _openai_call(prompt: str, model_key: str) -> LLMResult:
    config = REGISTRY[model_key]
    body = json.dumps({"model": config.model_id,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    usage = data.get("usage", {})
    return LLMResult(
        text=data["choices"][0]["message"]["content"], model_key=model_key,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        latency_s=time.perf_counter() - start,
        cost_usd=cost_of(model_key, usage.get("prompt_tokens", 0),
                         usage.get("completion_tokens", 0)))


def _anthropic_call(prompt: str, model_key: str) -> LLMResult:
    config = REGISTRY[model_key]
    body = json.dumps({"model": config.model_id, "max_tokens": 1024,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"Content-Type": "application/json",
                 "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01"})
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    usage = data.get("usage", {})
    return LLMResult(
        text=data["content"][0]["text"], model_key=model_key,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        latency_s=time.perf_counter() - start,
        cost_usd=cost_of(model_key, usage.get("input_tokens", 0),
                         usage.get("output_tokens", 0)))


def _ollama_call(prompt: str, model_key: str) -> LLMResult:
    config = REGISTRY[model_key]
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    body = json.dumps({"model": config.model_id, "prompt": prompt,
                       "stream": False}).encode()
    req = urllib.request.Request(f"{host}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
    return LLMResult(
        text=data.get("response", ""), model_key=model_key,
        input_tokens=data.get("prompt_eval_count", 0),
        output_tokens=data.get("eval_count", 0),
        latency_s=time.perf_counter() - start, cost_usd=0.0)


def send_request(prompt: str, model_key: str, live: bool = False) -> LLMResult:
    """Unified entry point. live=False uses the offline simulation."""
    if not live:
        return simulate(prompt, model_key)
    provider = REGISTRY[model_key].provider
    if provider == "openai":
        return _openai_call(prompt, model_key)
    if provider == "anthropic":
        return _anthropic_call(prompt, model_key)
    return _ollama_call(prompt, model_key)
