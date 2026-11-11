"""Complexity classifier.

A transparent linear model over hand-designed features, trained with a
one-vs-rest averaged perceptron on the labeled dataset. No external ML
dependency; the whole decision path is inspectable, which matters when a
routing decision needs to be explained after the fact.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

REASONING_VERBS = ("analyze", "compare", "design", "prove", "refute",
                   "derive", "justify", "defend", "reconstruct", "strategy",
                   "tradeoff", "trade-off", "why", "step by step",
                   "recommend", "argue")
MODERATE_VERBS = ("summarize", "classify", "rewrite", "group", "condense",
                  "rephrase", "translate this document", "release notes",
                  "bullet", "theme", "tone")
FORMAT_MARKERS = ("json", "table", "yaml", "csv", "markdown", "sections")

FEATURE_NAMES = ["bias", "log_tokens", "reasoning_verbs", "moderate_verbs",
                 "constraints", "has_context", "format_complexity",
                 "question_words", "multi_part"]


def extract_features(prompt: str) -> list[float]:
    lowered = prompt.lower()
    tokens = len(prompt.split())
    constraints = len(re.findall(
        r"\b(at least|under \d+|no more than|must|considering|including"
        r"|covering|address)\b", lowered))
    multi_part = lowered.count(" and ") + lowered.count(";") + lowered.count(", then")
    return [
        1.0,
        min(len(prompt) / 200.0, 3.0),
        float(sum(lowered.count(v) for v in REASONING_VERBS)),
        float(sum(lowered.count(v) for v in MODERATE_VERBS)),
        float(constraints),
        1.0 if ("context:" in lowered or "given this" in lowered
                or "attached" in lowered or "following" in lowered) else 0.0,
        float(sum(lowered.count(m) for m in FORMAT_MARKERS)),
        float(sum(lowered.startswith(q) for q in
                  ("what", "who", "when", "where", "which", "is ", "convert",
                   "extract", "return", "fix", "strip", "uppercase"))),
        float(min(multi_part, 4)),
    ]


@dataclass
class ComplexityClassifier:
    weights: dict[int, list[float]]  # tier -> weight vector

    @classmethod
    def train(cls, examples: list[dict], epochs: int = 30) -> "ComplexityClassifier":
        dim = len(FEATURE_NAMES)
        weights = {t: [0.0] * dim for t in (1, 2, 3)}
        totals = {t: [0.0] * dim for t in (1, 2, 3)}
        data = [(extract_features(e["prompt"]), e["tier"]) for e in examples]
        for _ in range(epochs):
            for features, tier in data:
                scores = {t: sum(w * f for w, f in zip(weights[t], features))
                          for t in (1, 2, 3)}
                predicted = max(scores, key=scores.get)
                if predicted != tier:
                    for i, f in enumerate(features):
                        weights[tier][i] += f
                        weights[predicted][i] -= f
                for t in (1, 2, 3):
                    for i in range(dim):
                        totals[t][i] += weights[t][i]
        n = epochs * len(data)
        averaged = {t: [v / n for v in totals[t]] for t in (1, 2, 3)}
        return cls(weights=averaged)

    def predict(self, prompt: str) -> tuple[int, dict[int, float]]:
        features = extract_features(prompt)
        scores = {t: sum(w * f for w, f in zip(self.weights[t], features))
                  for t in (1, 2, 3)}
        return max(scores, key=scores.get), scores

    def accuracy(self, examples: list[dict]) -> float:
        hits = sum(self.predict(e["prompt"])[0] == e["tier"] for e in examples)
        return hits / len(examples)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({str(t): w for t, w in self.weights.items()}, fh)

    @classmethod
    def load(cls, path: str) -> "ComplexityClassifier":
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
        return cls(weights={int(t): w for t, w in raw.items()})


def load_dataset(path: str = "data/complexity_dataset.json") -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["examples"]


def train_default(dataset_path: str = "data/complexity_dataset.json",
                  feedback_path: str = "data/feedback.jsonl") -> ComplexityClassifier:
    examples = load_dataset(dataset_path)
    if os.path.exists(feedback_path):
        with open(feedback_path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    examples.append(json.loads(line))
    return ComplexityClassifier.train(examples)


if __name__ == "__main__":
    classifier = train_default()
    examples = load_dataset()
    print(f"Training-set accuracy: {classifier.accuracy(examples):.1%}"
          f" on {len(examples)} examples")
    classifier.save("data/classifier_weights.json")
    print("Saved weights to data/classifier_weights.json")
