"""LLM providers.

Two providers share one interface:

- MockProvider: a deterministic, offline simulation of the email classifier.
  Its behavior is sensitive to the quality of the prompt it is given (a prompt
  that keeps the category definitions and tie-breaking rule performs better on
  ambiguous cases), which lets the whole regression pipeline be demonstrated
  and tested without an API key.
- OpenAIProvider: real chat-completions calls via the OpenAI HTTP API.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass

from .config import PromptConfig

CATEGORY_KEYWORDS = {
    "billing": ["charge", "charged", "refund", "invoice", "payment", "billing",
                "card", "price", "pricing", "discount", "subscription", "vat",
                "factura", "seat count", "annual"],
    "technical": ["error", "bug", "crash", "crashs", "broken", "slow", "500",
                  "429", "api", "webhook", "integration", "outage", "404",
                  "export", "exprot", "sync", "index", "lag", "works"],
    "account": ["log in", "login", "password", "2fa", "account", "profile",
                "permission", "role", "admin", "seat", "ownership", "delete my",
                "gdpr", "reset"],
    "general": ["discount?", "on-prem", "soc 2", "feedback", "fantastic",
                "redesign", "student", "docs", "ticket", "update?", "hi"],
}


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    model: str


class MockProvider:
    """Deterministic offline classifier used for demos and tests."""

    name = "mock"

    def classify(self, config: PromptConfig, email: str) -> LLMResponse:
        start = time.perf_counter()
        rich_prompt = "primary blocker" in config.system_prompt.lower()
        lowered = email.lower()

        scores: dict[str, int] = {}
        first_hit: dict[str, int] = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            hits = [lowered.find(k) for k in keywords if k in lowered]
            scores[category] = len(hits)
            first_hit[category] = min(hits) if hits else 10**9

        if not any(scores.values()):
            category = "general"
        elif rich_prompt:
            # With definitions and the tie-break rule present, resolve ties by
            # the customer's primary blocker: explicit asks outrank mentions.
            category = self._resolve_primary_blocker(lowered, scores)
        else:
            # A stripped-down prompt degrades to "first keyword wins", which
            # misroutes ambiguous emails that mention a secondary topic early.
            category = min(scores, key=lambda c: (first_hit[c], -scores[c]))

        summary = self._summarize(email, category, rich_prompt)
        payload = json.dumps({"category": category, "summary": summary})
        latency = time.perf_counter() - start + 0.002
        return LLMResponse(
            text=payload,
            input_tokens=len(config.system_prompt.split()) + len(email.split()),
            output_tokens=len(payload.split()),
            latency_s=latency,
            model=f"mock-{config.model}",
        )

    @staticmethod
    def _resolve_primary_blocker(lowered: str, scores: dict[str, int]) -> str:
        if any(k in lowered for k in ("refund", "charged twice", "invoice lists",
                                      "re-issue", "declined", "tax id", "vat")):
            return "billing"
        if any(k in lowered for k in ("log in", "login", "2fa", "password",
                                      "ownership", "delete my", "gdpr", "role",
                                      "read-only")):
            return "account"
        if any(k in lowered for k in ("error", "crash", "crashs", "429", "500",
                                      "webhook", "slow", "broken", "duplicate",
                                      "spins", "lag")):
            return "technical"
        return max(scores, key=scores.get)

    @staticmethod
    def _summarize(email: str, category: str, rich_prompt: bool) -> str:
        snippet = " ".join(email.split()[:18]).rstrip(".!?")
        if rich_prompt:
            return f"Customer reports a {category} issue: {snippet}."
        return f"{category} email: {snippet[:60]}."


class OpenAIProvider:
    """Thin OpenAI chat-completions client using the standard library."""

    name = "openai"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

    def classify(self, config: PromptConfig, email: str) -> LLMResponse:
        messages = [{"role": "system", "content": config.system_prompt}]
        for shot in config.few_shot:
            messages.append({"role": "user", "content": shot["input"]})
            messages.append({"role": "assistant", "content": shot["output"]})
        messages.append({"role": "user", "content": email})

        body = json.dumps({
            "model": config.model,
            "temperature": config.temperature,
            "response_format": {"type": "json_object"},
            "messages": messages,
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
        )
        start = time.perf_counter()
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        latency = time.perf_counter() - start
        usage = data.get("usage", {})
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            latency_s=latency,
            model=config.model,
        )


def get_provider(name: str):
    if name == "openai":
        return OpenAIProvider()
    return MockProvider()
