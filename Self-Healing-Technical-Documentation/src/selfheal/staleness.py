"""Verify whether linked doc sections are actually stale after a change."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .diff_detector import ChunkChange
from .doc_parser import DocSection


@dataclass
class StalenessFinding:
    section_id: str
    chunk_id: str
    stale: bool
    confidence: float
    problems: list[str]


def verify(change: ChunkChange, section: DocSection) -> StalenessFinding:
    """Deterministic staleness check.

    A section is stale if it references parameters, defaults, or names that
    the change removed or altered. With an API key, the same interface is
    served by an LLM given (old code, new code, doc section); the offline
    check keeps CI deterministic and free.
    """
    problems: list[str] = []
    content = section.content
    tokens = set(re.findall(r"`([^`]+)`", content)) | set(content.split())

    if change.change_type == "removed" and change.old is not None:
        short = change.old.name.split(".")[-1]
        if short in str(tokens):
            problems.append(f"documents removed symbol '{change.old.name}'")

    if change.old is not None and change.new is not None:
        removed_params = [p for p in change.old.params
                          if p not in change.new.params]
        for param in removed_params:
            if re.search(rf"`{re.escape(param)}`|\b{re.escape(param)}=", content):
                problems.append(f"references old parameter '{param}'")
        for param, old_default in change.old.defaults.items():
            new_default = change.new.defaults.get(param)
            if new_default != old_default and old_default in content:
                problems.append(
                    f"states old default {param}={old_default}"
                    f" (now {new_default})")
        old_sig = change.old.signature
        if old_sig in content and old_sig != change.new.signature:
            problems.append("shows the old signature verbatim")

    stale = bool(problems)
    # Mechanical findings (defaults, renames) are high confidence; removed
    # symbols and structural changes need human judgment.
    confidence = 0.9 if stale and change.change_type in ("default", "signature") \
        else (0.6 if stale else 0.95)
    return StalenessFinding(section_id=section.section_id,
                            chunk_id=change.chunk_id, stale=stale,
                            confidence=confidence, problems=problems)
