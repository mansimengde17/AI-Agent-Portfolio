"""Dual engine OCR with character level agreement scoring.

Two simulated engines (standing in for Tesseract and EasyOCR) read the
same scan with different error patterns. Where they agree, confidence is
high. Where they disagree, the segment is marked uncertain and, if the
page level agreement falls below a floor, the page is routed to the
vision model fallback (a stronger but costlier reading).
"""

from __future__ import annotations

from dataclasses import dataclass

from .documents import render_text, simulate_scan

VISION_FALLBACK_FLOOR = 0.90

PREPROCESS_STEPS = ["deskew", "binarize", "denoise", "upscale"]


@dataclass
class OCRResult:
    doc_id: str
    text: str
    engine_agreement: float
    uncertain_segments: list[str]
    used_vision_fallback: bool
    preprocessing: list[str]


def _align_and_vote(a: str, b: str) -> tuple[str, float, list[str]]:
    """Character alignment for equal length reads; for unequal reads we
    align on line boundaries. Agreement is the fraction of positions where
    the engines produced the same character."""
    lines_a, lines_b = a.split("\n"), b.split("\n")
    merged_lines, agreements, uncertain = [], [], []
    for line_a, line_b in zip(lines_a, lines_b):
        if line_a == line_b:
            merged_lines.append(line_a)
            agreements.append(1.0)
            continue
        length = max(len(line_a), len(line_b))
        merged, same = [], 0
        for i in range(length):
            ca = line_a[i] if i < len(line_a) else ""
            cb = line_b[i] if i < len(line_b) else ""
            if ca == cb:
                merged.append(ca)
                same += 1
            else:
                # prefer the character that looks like part of a number
                # or word rather than a confusion glyph
                pick = ca if ca.isalnum() or ca in ".,:- " else cb
                merged.append(pick or cb or ca)
        merged_lines.append("".join(merged))
        agreements.append(same / max(1, length))
        if agreements[-1] < 0.9:
            uncertain.append(line_a[:50])
    agreement = sum(agreements) / max(1, len(agreements))
    return "\n".join(merged_lines), agreement, uncertain


def run_ocr(doc: dict) -> OCRResult:
    preprocessing = list(PREPROCESS_STEPS) if doc["scan_quality"] == "poor" \
        else ["binarize"]
    engine_a = simulate_scan(doc, engine_seed=1)   # tesseract stand in
    engine_b = simulate_scan(doc, engine_seed=2)   # easyocr stand in
    merged, agreement, uncertain = _align_and_vote(engine_a, engine_b)
    used_vision = False
    if agreement < VISION_FALLBACK_FLOOR:
        # Vision model fallback returns a clean structural reading.
        merged = render_text(doc)
        used_vision = True
        agreement = 0.99
    return OCRResult(doc["doc_id"], merged, round(agreement, 4),
                     uncertain, used_vision, preprocessing)
