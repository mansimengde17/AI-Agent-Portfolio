# Multi Modal Document Processor with OCR, LLM Extraction, and Validation

An end to end document pipeline: scanned documents in, validated
structured data out. Dual engine OCR with character level agreement, a
vision model fallback for scans OCR cannot handle, schema enforced LLM
extraction with per field confidence, layered validation, and a human
review lane for anything the system is not sure about.

Portfolio: https://mansimengde17.github.io/AI-Agent-Portfolio/

## Why this exists

Document processing is one of the largest categories of enterprise AI
deployment. The hard part is not calling an extraction model, it is
knowing when to trust the output: noisy scans, unknown vendors, totals
that do not add up, and dates that make no sense. This pipeline measures
its own confidence at every step and only asks a human when the evidence
says it should.

## Pipeline

```
document -> preprocessing (deskew, binarize, denoise, upscale)
         -> engine A read + engine B read -> character level voting
         -> agreement < 0.90? vision model fallback
         -> classify doc type -> schema extraction (per field confidence)
         -> type checks -> business rules -> anomaly detector
         -> route: auto approve | fast review | detailed review
         -> reviewer corrections feed back into prompts and thresholds
```

- `src/docproc/documents.py` sample corpus with ground truth and a scan
  noise simulator (two engines, different error patterns)
- `src/docproc/ocr.py` dual engine voting, agreement scoring, vision
  fallback below the 0.90 agreement floor
- `src/docproc/extract.py` Pydantic schemas for invoices, contracts, and
  receipts; per field confidence blending regex clarity with OCR quality
- `src/docproc/validate.py` type rules (totals reconcile, dates ordered),
  business rules (approved vendor list, plausible terms), and a z score
  anomaly detector against vendor history
- `src/docproc/routing.py` confidence lanes plus the review queue with a
  correction log that distinguishes extraction errors from rules that
  were too strict
- `src/docproc/api.py` FastAPI endpoints for processing, review, analytics

## Quick start

```bash
pip install -r requirements.txt
python demo.py                       # full pipeline over the sample corpus
python -m unittest discover tests
uvicorn docproc.api:app --app-dir src --port 8000
```

The demo shows a clean invoice auto approving, a poor scan taking the
vision fallback, an unknown vendor and a past effective date being
caught, a statistical total anomaly being flagged, and a reviewer
correcting a field with the feedback loop recording why.

## Docker

```bash
docker compose up --build
```

## Notes

The OCR engines and the extraction model are deterministic simulations so
everything runs offline. Swapping in Tesseract, EasyOCR, and a hosted
vision model only touches `ocr.py` and `extract.py`; the validation,
routing, and review layers are engine agnostic.
