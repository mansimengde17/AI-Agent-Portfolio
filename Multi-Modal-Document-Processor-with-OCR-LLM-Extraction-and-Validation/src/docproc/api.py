"""FastAPI surface for the document processor."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .documents import DOCUMENTS
from .pipeline import Processor

app = FastAPI(title="Multi Modal Document Processor", version="1.0.0")
processor = Processor()


class CorrectionRequest(BaseModel):
    field: str
    value: str | float
    reviewer: str
    cause: str  # extraction_error | rule_too_strict


class DecisionRequest(BaseModel):
    decision: str  # approve | reject
    reviewer: str


@app.post("/v1/process/{doc_id}")
def process(doc_id: str):
    doc = next((d for d in DOCUMENTS if d["doc_id"] == doc_id), None)
    if doc is None:
        raise HTTPException(404, f"unknown document {doc_id}")
    return processor.process(doc)


@app.post("/v1/process-all")
def process_all():
    return [processor.process(doc) for doc in DOCUMENTS]


@app.get("/v1/documents")
def documents():
    return [{"doc_id": d["doc_id"], "doc_type": d["doc_type"],
             "scan_quality": d["scan_quality"]} for d in DOCUMENTS]


@app.get("/v1/review-queue")
def review_queue(lane: str | None = None):
    return processor.review.queue(lane)


@app.post("/v1/review-queue/{doc_id}/correct")
def correct(doc_id: str, request: CorrectionRequest):
    if doc_id not in processor.review.pending:
        raise HTTPException(404, f"{doc_id} not in the review queue")
    return processor.review.correct(doc_id, request.field, request.value,
                                    request.reviewer, request.cause)


@app.post("/v1/review-queue/{doc_id}/decide")
def decide(doc_id: str, request: DecisionRequest):
    return processor.review.decide(doc_id, request.decision,
                                   request.reviewer)


@app.get("/v1/analytics")
def analytics():
    return processor.analytics()
