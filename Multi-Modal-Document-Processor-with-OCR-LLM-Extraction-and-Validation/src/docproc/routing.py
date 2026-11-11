"""Confidence based routing and the human review workflow."""

from __future__ import annotations

import time

AUTO_APPROVE_FLOOR = 0.90
FAST_REVIEW_FLOOR = 0.70


def route(extraction: dict, validation: dict) -> dict:
    confidence = extraction["overall_confidence"]
    if validation["error_count"] > 0 or confidence < FAST_REVIEW_FLOOR:
        lane = "detailed_review"
        reason = ("critical validation failures"
                  if validation["error_count"] else "low confidence")
    elif validation["warning_count"] > 0 or confidence < AUTO_APPROVE_FLOOR:
        lane = "fast_review"
        reason = ("validation warnings" if validation["warning_count"]
                  else "medium confidence")
    else:
        lane = "auto_approve"
        reason = "high confidence, all validations passed"
    return {"lane": lane, "reason": reason, "confidence": confidence}


class ReviewQueue:
    """Holds routed documents and records reviewer corrections.

    Every correction is logged with whether the extraction was wrong or
    the rule was too strict; that log is the feedback signal that tunes
    prompts and thresholds over time.
    """

    def __init__(self):
        self.pending: dict[str, dict] = {}
        self.corrections: list[dict] = []
        self.decisions: list[dict] = []

    def enqueue(self, doc_id: str, package: dict) -> None:
        self.pending[doc_id] = package

    def queue(self, lane: str | None = None) -> list[dict]:
        items = [{"doc_id": k, **v} for k, v in self.pending.items()]
        if lane:
            items = [i for i in items if i["route"]["lane"] == lane]
        priority = {"detailed_review": 0, "fast_review": 1}
        return sorted(items,
                      key=lambda i: priority.get(i["route"]["lane"], 2))

    def correct(self, doc_id: str, field: str, corrected_value,
                reviewer: str, cause: str) -> dict:
        package = self.pending[doc_id]
        original = package["extraction"]["fields"].get(field)
        package["extraction"]["fields"][field] = corrected_value
        entry = {"doc_id": doc_id, "field": field, "original": original,
                 "corrected": corrected_value, "reviewer": reviewer,
                 "cause": cause,  # extraction_error | rule_too_strict
                 "at": time.time()}
        self.corrections.append(entry)
        return entry

    def decide(self, doc_id: str, decision: str, reviewer: str) -> dict:
        package = self.pending.pop(doc_id, None)
        entry = {"doc_id": doc_id, "decision": decision,
                 "reviewer": reviewer, "at": time.time()}
        self.decisions.append(entry)
        return entry

    def feedback_report(self) -> dict:
        by_field: dict[str, int] = {}
        by_cause: dict[str, int] = {}
        for c in self.corrections:
            by_field[c["field"]] = by_field.get(c["field"], 0) + 1
            by_cause[c["cause"]] = by_cause.get(c["cause"], 0) + 1
        return {"total_corrections": len(self.corrections),
                "by_field": by_field, "by_cause": by_cause,
                "hint": "fields with repeated extraction errors need"
                        " better few shot examples; rule_too_strict"
                        " corrections mean thresholds should relax"}
