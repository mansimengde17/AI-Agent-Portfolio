# RAG Pipeline with Hybrid Search Over Internal Docs

A production-grade Retrieval-Augmented Generation system that ingests internal documentation, indexes it with both dense vector and sparse keyword (BM25) search, fuses results with Reciprocal Rank Fusion, reranks, and generates grounded answers with verified inline citations and a composite confidence score.

Portfolio: https://mansimengde17.github.io/AI-Agent-Portfolio/

## Why hybrid retrieval

Dense embeddings capture meaning but miss exact identifiers; technical documentation is full of function names, config keys, and error codes where keyword match is the only reliable signal. This system runs both retrievers on every query and fuses the rankings, which consistently beats either retriever alone on technical corpora.

## Architecture

```
 documents (md, txt, html)          user question
        |                                 |
        v                                 v
 +---------------+            +---------------------+
 |  Ingestion     |            |   Hybrid Retrieval  |
 |  normalize +   |            |                     |
 |  chunk:        |   dense    |  vector search top-k |
 |   fixed        |----------->|          +          |
 |   structural   |   sparse   |  BM25 search top-k   |
 |   semantic     |----------->|          |          |
 |  dedupe > 0.95 |            |  Reciprocal Rank    |
 +---------------+            |  Fusion (0.7/0.3)   |
        |                      +---------------------+
        v                                 |
 +---------------+                        v
 | dual indexes  |            +---------------------+
 | vector + BM25 |            |      Reranker        |
 | (kept in sync)|            |  top 20 -> top 5     |
 +---------------+            +---------------------+
                                          |
                                          v
                              +---------------------+
                              | Grounded Generation  |
                              |  numbered context,   |
                              |  bracketed citations,|
                              |  refuses when weak   |
                              +---------------------+
                                          |
                                          v
                              +---------------------+
                              | Citation Verifier +  |
                              | Confidence Scorer    |
                              +---------------------+
```

## Quick start (offline)

The repository ships with a sample internal documentation corpus and a deterministic embedding/generation stack, so the entire pipeline runs with no API key:

```bash
pip install -r requirements.txt
python demo.py                 # ingest corpus, run eval questions
python demo.py --compare       # hybrid vs dense-only comparison table
```

To serve the API:

```bash
uvicorn src.ragpipe.api:app --reload
# POST /v1/ask        question -> grounded answer with citations + confidence
# POST /v1/ingest     add documents to both indexes
# GET  /v1/documents  list indexed documents
```

Set `OPENAI_API_KEY` to swap the deterministic stack for `text-embedding-3-small` embeddings and LLM generation with the same interfaces.

## Chunking strategies

Three switchable strategies, tracked per chunk:

- `fixed`: fixed-size windows with overlap (baseline)
- `structural`: recursive splitting on section headers, respecting document structure
- `semantic`: splits on topic boundaries using embedding similarity between adjacent sentences

`python demo.py --chunking-comparison` runs the eval suite across all three and prints the comparison table that drives the default choice.

## Citation verification

After generation, every bracketed citation is parsed and checked: does the cited chunk actually support the sentence it is attached to? Unsupported citations are flagged and excluded from the citation coverage score. The composite confidence combines retrieval confidence, citation coverage, and answer completeness; below the confidence floor the system returns a structured "not found" response listing what it did and did not find instead of hallucinating.

## Repository layout

```
corpus/                     sample internal documentation
src/ragpipe/ingest.py       loaders, three chunking strategies, dedupe
src/ragpipe/index.py        vector index + BM25, kept in sync
src/ragpipe/retrieve.py     dense, sparse, RRF fusion, reranker
src/ragpipe/generate.py     grounded generation, citations, confidence
src/ragpipe/evaluate.py     golden Q&A eval: correctness, faithfulness, retrieval
src/ragpipe/api.py          FastAPI service
data/golden_qa.json         golden question set
demo.py                     end-to-end offline run and comparisons
tests/
```
