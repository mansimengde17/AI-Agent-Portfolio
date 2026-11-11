"""End to end demo: scanned documents to validated structured data.

Walks all sample documents through the full pipeline and shows:
- dual engine OCR agreement and the vision fallback on poor scans
- structured extraction with per field confidence
- validation catching an unknown vendor, a past effective date, and a
  statistical total anomaly
- confidence routing into auto approve, fast review, detailed review
- a reviewer correcting a field, feeding the improvement loop
"""

from __future__ import annotations

import sys

sys.path.insert(0, "src")

from docproc.documents import DOCUMENTS
from docproc.pipeline import Processor


def section(title: str) -> None:
    print(f"\n{'=' * 62}\n{title}\n{'=' * 62}")


def main() -> None:
    processor = Processor()

    section("Processing all documents")
    for doc in DOCUMENTS:
        record = processor.process(doc)
        ocr = record["ocr"]
        extraction = record["extraction"]
        print(f"\n  {doc['doc_id']} ({doc['doc_type']},"
              f" {doc['scan_quality']} scan)")
        print(f"    OCR agreement {ocr['engine_agreement']},"
              f" vision fallback: {ocr['used_vision_fallback']},"
              f" preprocessing: {', '.join(ocr['preprocessing'])}")
        print(f"    extraction confidence"
              f" {extraction['overall_confidence']}")
        for issue in record["validation"]["issues"]:
            print(f"    [{issue['severity']}/{issue['kind']}]"
                  f" {issue['field']}: {issue['message']}")
        print(f"    -> {record['route']['lane']}"
              f" ({record['route']['reason']})")

    section("Review queue (priority ordered)")
    for item in processor.review.queue():
        print(f"  {item['doc_id']}: {item['route']['lane']}"
              f" because {item['route']['reason']}")

    section("Reviewer corrects the unknown vendor invoice")
    queue_ids = list(processor.review.pending)
    target = "inv-1004" if "inv-1004" in queue_ids else queue_ids[0]
    entry = processor.review.correct(
        target, "vendor_name", "Phantom Trading LLC (approved 2026-07)",
        reviewer="ap-clerk", cause="rule_too_strict")
    print(f"  {entry['doc_id']}: {entry['field']}"
          f" '{entry['original']}' -> '{entry['corrected']}'"
          f" (cause: {entry['cause']})")
    processor.review.decide(target, "approve", "ap-clerk")

    section("Pipeline analytics")
    analytics = processor.analytics()
    print(f"  documents processed: {analytics['documents_processed']}")
    print(f"  auto approval rate: {analytics['auto_approval_rate']}")
    print(f"  lanes: {analytics['lanes']}")
    print(f"  vision fallbacks: {analytics['vision_fallbacks']}")
    print(f"  corrections: {analytics['corrections']['total_corrections']}"
          f" ({analytics['corrections']['by_cause']})")
    print("\nDemo complete. Start the API with:"
          " uvicorn docproc.api:app --app-dir src")


if __name__ == "__main__":
    main()
