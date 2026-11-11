#!/usr/bin/env python3
"""Offline end-to-end demonstration on the miniature example project.

Simulates a PR that renames a parameter and changes a default, then runs
the full detect -> link -> verify -> repair cycle.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "src")

from selfheal.code_parser import parse_source
from selfheal.diff_detector import detect_changes, doc_relevant
from selfheal.doc_parser import parse_doc_file
from selfheal.linker import LinkGraph
from selfheal.repair import repair, summarize
from selfheal.staleness import verify

NEW_CLIENT_SOURCE = '''
"""Miniature target project: a small API client used by the demo."""

DEFAULT_TIMEOUT = 60


def create_client(api_key, base_url="https://api.example.com",
                  timeout=60, max_retries=3):
    """Create a configured API client.

    Returns a dict-based client handle used by fetch_records.
    """
    return {"api_key": api_key, "base_url": base_url,
            "timeout": timeout, "max_retries": max_retries}


def fetch_records(client, dataset, page_size=100):
    """Fetch records from a dataset, paginated by page_size."""
    return {"client": client, "dataset": dataset, "page_size": page_size,
            "records": []}
'''


def main() -> None:
    with open("example/client.py", encoding="utf-8") as fh:
        old_source = fh.read()
    old_chunks = parse_source("example/client.py", old_source)
    new_chunks = parse_source("example/client.py", NEW_CLIENT_SOURCE)
    sections = parse_doc_file("example/docs/usage.md")

    graph = LinkGraph().build(new_chunks, sections)
    graph.save()
    print(f"Link graph: {len(graph.links)} links between"
          f" {len(new_chunks)} code chunks and {len(sections)} doc sections")

    changes = doc_relevant(detect_changes(old_chunks, new_chunks))
    print(f"\nDoc-relevant changes detected: {len(changes)}")
    for change in changes:
        print(f"  [{change.change_type}] {change.chunk_id}: {change.detail}")

    sections_by_id = {s.section_id: s for s in sections}
    repairs, verified_ok = [], 0
    for change in changes:
        for link in graph.sections_for_chunk(change.chunk_id):
            section = sections_by_id[link.section_id]
            finding = verify(change, section)
            if not finding.stale:
                verified_ok += 1
                continue
            print(f"\nStale: {section.heading_path}")
            for problem in finding.problems:
                print(f"  - {problem}")
            fix = repair(change, section, finding)
            repairs.append(fix)
            print(f"  mode: {fix.mode}")
            print("\n".join("  " + line for line in fix.diff().splitlines()))

    print("\n" + summarize(repairs, verified_ok))


if __name__ == "__main__":
    main()
