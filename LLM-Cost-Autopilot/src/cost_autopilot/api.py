"""FastAPI service exposing the router."""

from __future__ import annotations

import os
import random

from fastapi import FastAPI
from pydantic import BaseModel

from .classifier import train_default
from .registry import REGISTRY
from .router import Router
from .store import AuditStore
from .verifier import Verifier

LIVE = bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))

app = FastAPI(title="LLM Cost Autopilot", version="1.0.0")
classifier = train_default()
router = Router(classifier, live=LIVE)
verifier = Verifier(top_model=router.baseline_model,
                    threshold=router.verification.get("agreement_threshold", 0.55),
                    auto_escalate=router.verification.get("auto_escalate", True),
                    live=LIVE)
store = AuditStore()


class CompletionRequest(BaseModel):
    prompt: str


class RoutingConfig(BaseModel):
    tier1: str | None = None
    tier2: str | None = None
    tier3: str | None = None


@app.post("/v1/completions")
def completions(request: CompletionRequest):
    decision = router.route(request.prompt)
    verification = None
    sample_rate = router.verification.get("sample_rate", 0.25)
    if random.random() < sample_rate:
        verification = verifier.verify(request.prompt, decision)
    result = (verification.escalated_result
              if verification and verification.escalated
              else decision.result)
    store.log(request.prompt, decision.tier, result.model_key,
              result.cost_usd, result.input_tokens, result.output_tokens,
              result.latency_s, router.baseline_model,
              verification.agreement if verification else None,
              bool(verification and verification.escalated))
    return {
        "text": result.text,
        "routing": {
            "complexity_tier": decision.tier,
            "selected_model": decision.model_key,
            "served_by": result.model_key,
            "escalated": bool(verification and verification.escalated),
            "reason": f"classified tier {decision.tier};"
                      f" mapped to {decision.model_key}",
        },
        "usage": {"input_tokens": result.input_tokens,
                  "output_tokens": result.output_tokens,
                  "cost_usd": result.cost_usd,
                  "latency_s": round(result.latency_s, 3)},
    }


@app.get("/v1/models")
def models():
    return {key: vars(config) for key, config in REGISTRY.items()}


@app.get("/v1/stats")
def stats():
    return store.stats()


@app.put("/v1/routing-config")
def update_routing(config: RoutingConfig):
    updates = {int(tier.replace("tier", "")): model
               for tier, model in config.model_dump().items()
               if model is not None}
    unknown = [m for m in updates.values() if m not in REGISTRY]
    if unknown:
        return {"error": f"unknown models: {unknown}"}
    router.update_routing(updates)
    return {"routing": router.routing_map}
