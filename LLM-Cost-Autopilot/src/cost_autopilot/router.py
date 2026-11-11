"""Router: tier-based model selection with a hot-swappable routing map."""

from __future__ import annotations

from dataclasses import dataclass

import yaml

from .classifier import ComplexityClassifier
from .providers import LLMResult, send_request


@dataclass
class RoutingDecision:
    tier: int
    model_key: str
    scores: dict
    result: LLMResult


class Router:
    def __init__(self, classifier: ComplexityClassifier,
                 config_path: str = "config/routing.yaml", live: bool = False):
        self.classifier = classifier
        self.live = live
        with open(config_path, encoding="utf-8") as fh:
            config = yaml.safe_load(fh)
        self.routing_map: dict[int, str] = {
            int(k.replace("tier", "")): v for k, v in config["routing"].items()}
        self.baseline_model: str = config["baseline_model"]
        self.verification = config.get("verification", {})

    def update_routing(self, new_map: dict[int, str]) -> None:
        self.routing_map.update(new_map)

    def route(self, prompt: str) -> RoutingDecision:
        tier, scores = self.classifier.predict(prompt)
        model_key = self.routing_map[tier]
        result = send_request(prompt, model_key, live=self.live)
        return RoutingDecision(tier=tier, model_key=model_key,
                               scores=scores, result=result)
