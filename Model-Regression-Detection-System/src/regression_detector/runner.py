"""Eval runner: executes the golden dataset against a prompt config."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field

from .config import PromptConfig
from .llm import MockProvider, OpenAIProvider

STOPWORDS = {"the", "a", "an", "and", "or", "to", "of", "for", "on", "in",
             "their", "they", "is", "are", "that", "customer", "requests",
             "reports", "asks", "issue"}


@dataclass
class CaseResult:
    case_id: str
    difficulty: str
    expected_category: str
    predicted_category: str
    expected_summary: str
    predicted_summary: str
    category_match: bool
    summary_score: float
    passed: bool
    latency_s: float
    input_tokens: int
    output_tokens: int
    raw_output: str = ""


@dataclass
class EvalRun:
    prompt_version: str
    model: str
    provider: str
    timestamp: float
    results: list[CaseResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.passed for r in self.results) / len(self.results)

    def per_category_accuracy(self) -> dict[str, float]:
        buckets: dict[str, list[bool]] = {}
        for r in self.results:
            buckets.setdefault(r.expected_category, []).append(r.category_match)
        return {c: sum(v) / len(v) for c, v in sorted(buckets.items())}

    def to_dict(self) -> dict:
        return {
            "prompt_version": self.prompt_version,
            "model": self.model,
            "provider": self.provider,
            "timestamp": self.timestamp,
            "pass_rate": self.pass_rate,
            "per_category": self.per_category_accuracy(),
            "results": [asdict(r) for r in self.results],
        }


def summary_relevance(expected: str, predicted: str) -> float:
    """Judge summary relevance on a 0-1 scale.

    Offline judge: content-word overlap between the predicted summary and the
    human-written ideal summary. When running with the OpenAI provider, this
    can be swapped for an LLM-as-judge scorer; overlap keeps the offline path
    deterministic and free.
    """
    exp = {w.strip(".,:!?").lower() for w in expected.split()} - STOPWORDS
    pred = {w.strip(".,:!?").lower() for w in predicted.split()} - STOPWORDS
    if not exp:
        return 0.0
    return len(exp & pred) / len(exp)


def run_eval(config: PromptConfig, dataset: dict,
             provider: MockProvider | OpenAIProvider,
             summary_threshold: float = 0.30) -> EvalRun:
    run = EvalRun(prompt_version=config.version, model=config.model,
                  provider=provider.name, timestamp=time.time())
    for case in dataset["cases"]:
        response = provider.classify(config, case["email"])
        try:
            parsed = json.loads(response.text)
            predicted_category = str(parsed.get("category", "")).lower().strip()
            predicted_summary = str(parsed.get("summary", ""))
        except (json.JSONDecodeError, AttributeError):
            predicted_category, predicted_summary = "parse_error", ""

        category_match = predicted_category == case["expected_category"]
        score = summary_relevance(case["expected_summary"], predicted_summary)
        run.results.append(CaseResult(
            case_id=case["id"],
            difficulty=case.get("expected_difficulty", "standard"),
            expected_category=case["expected_category"],
            predicted_category=predicted_category,
            expected_summary=case["expected_summary"],
            predicted_summary=predicted_summary,
            category_match=category_match,
            summary_score=round(score, 3),
            passed=category_match and score >= summary_threshold,
            latency_s=round(response.latency_s, 4),
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            raw_output=response.text,
        ))
    return run
