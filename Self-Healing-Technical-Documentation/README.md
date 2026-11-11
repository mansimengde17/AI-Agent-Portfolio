# Self-Healing Technical Documentation

A GitHub Action that monitors a codebase, detects when code changes make documentation inaccurate, identifies the specific stale sections, and either auto-generates corrected docs or flags the discrepancies for human review.

Portfolio: https://mansimengde17.github.io/AI-Agent-Portfolio/

## The problem

Every team's docs are perpetually stale. Code changes ship daily; documentation is updated when someone notices, which is usually after a user hits the discrepancy. This tool closes the loop automatically: every pull request is checked against the documentation that describes the changed code, and stale sections are repaired or flagged before the PR merges.

## Architecture

```
                 pull request (code changes)
                          |
                          v
 +--------------------------------------------------+
 |               Change Detection                    |
 |  parse git diff -> map hunks to code chunks ->    |
 |  filter noise (comments, whitespace, tests)       |
 +--------------------------------------------------+
        |
        v
 +--------------------------------------------------+
 |             Code-to-Docs Link Graph               |
 |  code chunks (functions, classes, CLI, config)    |
 |  <-> doc sections (split by heading)              |
 |  linked by name mentions + embedding similarity   |
 +--------------------------------------------------+
        |
        v  suspect sections
 +--------------------------------------------------+
 |            Staleness Verification                 |
 |  old code + new code + doc section ->             |
 |  is the doc still accurate? what exactly broke?   |
 +--------------------------------------------------+
        |
        v  confirmed stale
 +--------------------------------------------------+
 |               Doc Repair Engine                   |
 |  high confidence: rewrite the stale fragment,     |
 |  preserve style, open an auto-fix PR              |
 |  low confidence: PR comment with TODO markers     |
 +--------------------------------------------------+
```

## Quick start (offline)

The repository includes a miniature target project (`example/`) with source code and docs, so the full detect-verify-repair cycle can be run locally with no API key:

```bash
pip install -r requirements.txt
python demo.py
```

The demo applies a realistic code change to the example project (a renamed parameter and a changed default), rebuilds the link graph, detects the affected doc sections, verifies staleness, and prints the repaired documentation with a unified diff.

## How the link graph is built

1. Code is parsed with Python's `ast` module into semantic chunks: function signatures with docstrings, class definitions, and constants. Each chunk gets a stable identifier (`path::qualified_name`).
2. Markdown docs are split into sections by heading. Each section records its heading path and every backticked code reference it mentions.
3. Links are created when a doc section mentions a chunk's name, then augmented with cosine similarity between deterministic bag-of-words embeddings (swap in `text-embedding-3-small` for production via `EMBEDDINGS=openai`).
4. The graph persists as `docs_link_graph.json`, so incremental runs only re-embed changed chunks.

## Staleness verification and repair modes

For each suspect section the verifier receives the old code, the new code, and the doc text. Offline, the check is deterministic: parameter names, defaults, and return descriptions mentioned in docs are compared against the new signature. With an API key set, an LLM performs the same judgment with an explanation. Repairs come in two modes:

- Auto-fix (high confidence): mechanical changes such as renamed parameters or changed defaults are rewritten in place, preserving the sentence structure around them.
- Review-flag (low confidence): behavioral or feature-level changes produce a draft with TODO markers and a PR comment linking the affected sections.

## Using it as a GitHub Action

```yaml
# .github/workflows/doc-check.yml in the target repository
- uses: mansimengde17/Self-Healing-Technical-Documentation@main
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    confidence_threshold: "0.8"
    docs_path: "docs/"
```

On every PR that modifies code files, the Action posts a summary comment ("3 sections verified accurate, 1 auto-fixed, 2 flagged for review") and, for high-confidence fixes, pushes a companion branch with the corrected docs.

## Repository layout

```
action.yml                     GitHub Action definition
src/selfheal/code_parser.py    ast-based semantic chunking of source code
src/selfheal/doc_parser.py     markdown section splitting and reference mining
src/selfheal/linker.py         code-to-docs link graph
src/selfheal/diff_detector.py  git diff parsing and noise filtering
src/selfheal/staleness.py      staleness verification
src/selfheal/repair.py         targeted doc correction with confidence modes
example/                       miniature target project used by the demo
demo.py                        offline end-to-end run
tests/                         unit tests
```
