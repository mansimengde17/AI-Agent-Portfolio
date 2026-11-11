"""FastAPI service for the RAG pipeline."""

from __future__ import annotations

import glob
import os

from fastapi import FastAPI
from pydantic import BaseModel

from .generate import generate
from .index import HybridIndex, embed
from .ingest import chunk_structural, dedupe, load_document
from .retrieve import retrieve

app = FastAPI(title="RAG Pipeline with Hybrid Search", version="1.0.0")
index = HybridIndex()
documents: list[str] = []


def ingest_path(path: str) -> int:
    with open(path, encoding="utf-8") as fh:
        text = load_document(path, fh.read())
    chunks, _ = dedupe(chunk_structural(os.path.basename(path), text), embed)
    index.add(chunks)
    documents.append(path)
    return len(chunks)


@app.on_event("startup")
def seed():
    for path in sorted(glob.glob("corpus/*.md")):
        ingest_path(path)


class AskRequest(BaseModel):
    question: str
    hybrid: bool = True


class IngestRequest(BaseModel):
    name: str
    text: str


@app.post("/v1/ask")
def ask(request: AskRequest):
    retrieved = retrieve(index, request.question, hybrid=request.hybrid)
    answer = generate(request.question, retrieved)
    return {
        "answer": answer.text,
        "answered": answer.answered,
        "confidence": {"composite": answer.confidence,
                       "retrieval": answer.retrieval_confidence,
                       "citation_coverage": answer.citation_coverage,
                       "completeness": answer.completeness},
        "citations": [vars(c) for c in answer.citations],
        "retrieved": [{"chunk_id": r.chunk.chunk_id,
                       "heading": r.chunk.heading,
                       "rerank_score": round(r.rerank_score, 3),
                       "dense_rank": r.dense_rank,
                       "sparse_rank": r.sparse_rank} for r in retrieved],
    }


@app.post("/v1/ingest")
def ingest(request: IngestRequest):
    chunks, dropped = dedupe(
        chunk_structural(request.name, request.text), embed)
    index.add(chunks)
    documents.append(request.name)
    return {"chunks_indexed": len(chunks), "duplicates_dropped": dropped}


@app.get("/v1/documents")
def list_documents():
    return {"documents": documents, "chunks": len(index.chunks)}
