#!/usr/bin/env python3
"""Offline end-to-end demo: ingest, ask, evaluate, compare retrieval modes."""

from __future__ import annotations

import argparse
import glob
import os
import sys

sys.path.insert(0, "src")

from ragpipe.evaluate import evaluate, load_cases
from ragpipe.generate import generate
from ragpipe.index import HybridIndex, embed
from ragpipe.ingest import (chunk_fixed, chunk_semantic, chunk_structural,
                            dedupe, load_document)
from ragpipe.retrieve import retrieve


def build_index(strategy: str = "structural") -> HybridIndex:
    index = HybridIndex()
    for path in sorted(glob.glob("corpus/*.md")):
        with open(path, encoding="utf-8") as fh:
            text = load_document(path, fh.read())
        name = os.path.basename(path)
        if strategy == "fixed":
            chunks = chunk_fixed(name, text)
        elif strategy == "semantic":
            chunks = chunk_semantic(name, text, embed)
        else:
            chunks = chunk_structural(name, text)
        chunks, _ = dedupe(chunks, embed)
        index.add(chunks)
    return index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare", action="store_true",
                        help="hybrid vs dense-only comparison")
    parser.add_argument("--chunking-comparison", action="store_true")
    args = parser.parse_args()

    cases = load_cases()

    if args.chunking_comparison:
        print(f"{'strategy':<12} {'correctness':>12} {'faithfulness':>13}"
              f" {'refusals ok':>12}")
        for strategy in ("fixed", "structural", "semantic"):
            metrics = evaluate(build_index(strategy), cases)
            print(f"{strategy:<12} {metrics['answer_correctness']:>12.1%}"
                  f" {metrics['faithfulness']:>13.1%}"
                  f" {metrics['correct_refusal_rate']:>12.1%}")
        return

    index = build_index()
    print(f"Indexed {len(index.chunks)} chunks from"
          f" {len(glob.glob('corpus/*.md'))} documents\n")

    if args.compare:
        for hybrid in (True, False):
            metrics = evaluate(index, cases, hybrid=hybrid)
            print(metrics)
        return

    for question in [
            "What error code is returned when the API key is missing?",
            "What is the default value of MAX_CONCURRENCY?",
            "How much traffic does the canary stage receive and for how long?",
            "What is the on-call rotation schedule for the data team?"]:
        retrieved = retrieve(index, question)
        answer = generate(question, retrieved)
        print(f"Q: {question}")
        print(f"A: {answer.text}")
        print(f"   confidence={answer.confidence}"
              f" retrieval={answer.retrieval_confidence}"
              f" citations_verified={answer.citation_coverage}\n")

    metrics = evaluate(index, cases)
    print("Eval:", metrics)


if __name__ == "__main__":
    main()
