"""Detect meaningful code changes between two versions of a codebase."""

from __future__ import annotations

from dataclasses import dataclass

from .code_parser import CodeChunk


@dataclass
class ChunkChange:
    chunk_id: str
    change_type: str       # signature | default | removed | added | behavior
    old: CodeChunk | None
    new: CodeChunk | None
    detail: str


NOISE_KINDS = ()  # extend with test-only chunk kinds if needed


def detect_changes(old_chunks: list[CodeChunk],
                   new_chunks: list[CodeChunk]) -> list[ChunkChange]:
    """Compare parsed chunks and keep only doc-relevant changes.

    Comment-only and whitespace-only edits never surface here because the
    comparison happens on parsed structure, not raw text. Internal refactors
    that keep the signature and docstring produce a low-priority 'behavior'
    change only when the body changed.
    """
    old_by_id = {c.chunk_id: c for c in old_chunks}
    new_by_id = {c.chunk_id: c for c in new_chunks}
    changes: list[ChunkChange] = []

    for chunk_id, old in old_by_id.items():
        new = new_by_id.get(chunk_id)
        if new is None:
            changes.append(ChunkChange(chunk_id, "removed", old, None,
                                       f"{old.name} was removed"))
            continue
        if old.params != new.params:
            renamed = [f"{a} -> {b}" for a, b in zip(old.params, new.params)
                       if a != b]
            added = [p for p in new.params if p not in old.params
                     and not any(r.endswith(f"-> {p}") for r in renamed)]
            removed = [p for p in old.params if p not in new.params
                       and not any(r.startswith(f"{p} ->") for r in renamed)]
            detail = "; ".join(
                filter(None, [f"renamed parameters: {', '.join(renamed)}"
                              if renamed else "",
                              f"added parameters: {', '.join(added)}"
                              if added else "",
                              f"removed parameters: {', '.join(removed)}"
                              if removed else ""]))
            changes.append(ChunkChange(chunk_id, "signature", old, new, detail))
        elif old.defaults != new.defaults:
            diffs = [f"{k}: {old.defaults.get(k)} -> {new.defaults.get(k)}"
                     for k in set(old.defaults) | set(new.defaults)
                     if old.defaults.get(k) != new.defaults.get(k)]
            changes.append(ChunkChange(chunk_id, "default", old, new,
                                       f"changed defaults: {'; '.join(diffs)}"))
        elif old.signature != new.signature:
            changes.append(ChunkChange(chunk_id, "signature", old, new,
                                       f"signature changed to {new.signature}"))
        elif old.source != new.source and old.docstring == new.docstring:
            changes.append(ChunkChange(chunk_id, "behavior", old, new,
                                       "implementation changed"))

    for chunk_id, new in new_by_id.items():
        if chunk_id not in old_by_id:
            changes.append(ChunkChange(chunk_id, "added", None, new,
                                       f"{new.name} is new"))
    return changes


def doc_relevant(changes: list[ChunkChange]) -> list[ChunkChange]:
    """Behavior-only changes rarely invalidate docs; everything else can."""
    return [c for c in changes if c.change_type != "behavior"]
