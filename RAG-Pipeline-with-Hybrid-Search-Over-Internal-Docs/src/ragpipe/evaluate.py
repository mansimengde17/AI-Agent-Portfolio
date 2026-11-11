"""Golden Q&A evaluation: correctness, faithfulness, retrieval, refusals."""

from __future__ import annotations

import json

from .generate import generate
from .index import HybridIndex, tokenize
from .retrieve import retrieve


def evaluate(index: HybridIndex, cases: list[dict],
             hybrid: bool = True) -> dict:
    correct = faithful = right_refusals = wrong_refusals = 0
    answerable = [c for c in cases if c["answerable"]]
    unanswerable = [c for c in cases if not c["answerable"]]

    for case in answerable:
        retrieved = retrieve(index, case["question"], hybrid=hybrid)
        answer = generate(case["question"], retrieved)
        if not answer.answered:
            wrong_refusals += 1
            continue
        text_terms = set(tokenize(answer.text))
        if all(term in text_terms for term in case["answer_terms"]):
            correct += 1
        if answer.citation_coverage == 1.0:
            faithful += 1

    for case in unanswerable:
        retrieved = retrieve(index, case["question"], hybrid=hybrid)
        answer = generate(case["question"], retrieved)
        if not answer.answered:
            right_refusals += 1

    return {
        "mode": "hybrid" if hybrid else "dense-only",
        "answer_correctness": round(correct / len(answerable), 3),
        "faithfulness": round(faithful / max(1, len(answerable)
                                             - wrong_refusals), 3),
        "correct_refusal_rate": round(right_refusals
                                      / max(1, len(unanswerable)), 3),
        "wrong_refusals": wrong_refusals,
        "cases": len(cases),
    }


def load_cases(path: str = "data/golden_qa.json") -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["cases"]
