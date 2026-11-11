"""Async quality verification loop.

Samples routed requests, re-runs them through the top-tier model, scores
agreement between the cheap answer and the reference answer, escalates on
divergence, and appends routing failures to the classifier feedback file.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .providers import LLMResult, send_request
from .router import RoutingDecision


@dataclass
class Verification:
    agreement: float
    verified_against: str
    escalated: bool
    escalated_result: LLMResult | None
    cost_delta_usd: float


def agreement_score(candidate: str, reference: str) -> float:
    """Content overlap between candidate and reference answers (0-1).

    Offline stand-in for LLM-as-judge agreement scoring; with live providers
    this can be swapped for an embedding similarity or judge call.
    """
    a = set(candidate.lower().split())
    b = set(reference.lower().split())
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class Verifier:
    def __init__(self, top_model: str, threshold: float = 0.55,
                 auto_escalate: bool = True, live: bool = False,
                 feedback_path: str = "data/feedback.jsonl"):
        self.top_model = top_model
        self.threshold = threshold
        self.auto_escalate = auto_escalate
        self.live = live
        self.feedback_path = feedback_path

    def verify(self, prompt: str, decision: RoutingDecision) -> Verification:
        if decision.model_key == self.top_model:
            return Verification(1.0, self.top_model, False, None, 0.0)

        reference = send_request(prompt, self.top_model, live=self.live)
        agreement = agreement_score(decision.result.text, reference.text)
        escalated = False
        escalated_result = None
        cost_delta = 0.0

        if agreement < self.threshold:
            # Routing failure: the cheap model diverged from the reference.
            self._record_failure(prompt, decision)
            if self.auto_escalate:
                escalated = True
                escalated_result = reference
                cost_delta = reference.cost_usd - decision.result.cost_usd

        return Verification(agreement=round(agreement, 3),
                            verified_against=self.top_model,
                            escalated=escalated,
                            escalated_result=escalated_result,
                            cost_delta_usd=round(cost_delta, 6))

    def _record_failure(self, prompt: str, decision: RoutingDecision) -> None:
        """Feed the failure back as a training example one tier up."""
        os.makedirs(os.path.dirname(self.feedback_path), exist_ok=True)
        example = {"prompt": prompt, "tier": min(decision.tier + 1, 3)}
        with open(self.feedback_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(example) + "\n")
