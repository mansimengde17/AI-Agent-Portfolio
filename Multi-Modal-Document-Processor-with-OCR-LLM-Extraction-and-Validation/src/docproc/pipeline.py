"""End to end pipeline: scan -> OCR -> extract -> validate -> route."""

from __future__ import annotations

from .extract import extract
from .ocr import run_ocr
from .routing import ReviewQueue, route
from .validate import validate


class Processor:
    def __init__(self):
        self.review = ReviewQueue()
        self.processed: list[dict] = []

    def process(self, doc: dict) -> dict:
        ocr = run_ocr(doc)
        extraction = extract(ocr)
        validation = validate(extraction["doc_type"], extraction["fields"])
        routing = route(extraction, validation)
        record = {"doc_id": doc["doc_id"],
                  "ocr": {"engine_agreement": ocr.engine_agreement,
                          "used_vision_fallback": ocr.used_vision_fallback,
                          "uncertain_segments": ocr.uncertain_segments,
                          "preprocessing": ocr.preprocessing},
                  "extraction": extraction,
                  "validation": validation,
                  "route": routing}
        if routing["lane"] != "auto_approve":
            self.review.enqueue(doc["doc_id"], record)
        self.processed.append(record)
        return record

    def analytics(self) -> dict:
        lanes: dict[str, int] = {}
        vision = 0
        confidences = []
        for record in self.processed:
            lanes[record["route"]["lane"]] = \
                lanes.get(record["route"]["lane"], 0) + 1
            vision += record["ocr"]["used_vision_fallback"]
            confidences.append(
                record["extraction"]["overall_confidence"])
        total = max(1, len(self.processed))
        return {"documents_processed": len(self.processed),
                "auto_approval_rate": round(
                    lanes.get("auto_approve", 0) / total, 3),
                "lanes": lanes,
                "vision_fallbacks": vision,
                "mean_confidence": round(
                    sum(confidences) / total, 3),
                "corrections": self.review.feedback_report()}
