"""Doc repair engine: targeted corrections with confidence-based modes."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

from .diff_detector import ChunkChange
from .doc_parser import DocSection
from .staleness import StalenessFinding


@dataclass
class Repair:
    section_id: str
    mode: str              # auto_fix | review_flag
    original: str
    corrected: str
    notes: list[str]

    def diff(self) -> str:
        return "\n".join(difflib.unified_diff(
            self.original.splitlines(), self.corrected.splitlines(),
            fromfile="docs (current)", tofile="docs (repaired)", lineterm=""))


def repair(change: ChunkChange, section: DocSection,
           finding: StalenessFinding,
           confidence_threshold: float = 0.8) -> Repair:
    """Rewrite only the stale fragments, preserving surrounding prose.

    High-confidence mechanical fixes (renames, default changes, signature
    updates) are applied textually. Anything below the confidence threshold
    is returned as a draft with TODO markers for human review.
    """
    corrected = section.content
    notes: list[str] = []

    if change.old is not None and change.new is not None:
        # Renamed parameters: old -> new positionally.
        for old_param, new_param in zip(change.old.params, change.new.params):
            if old_param != new_param:
                corrected = re.sub(rf"`{re.escape(old_param)}`",
                                   f"`{new_param}`", corrected)
                corrected = re.sub(rf"\b{re.escape(old_param)}=",
                                   f"{new_param}=", corrected)
                notes.append(f"renamed '{old_param}' to '{new_param}'")
        # Changed defaults.
        for param, old_default in change.old.defaults.items():
            new_default = change.new.defaults.get(param)
            if new_default is not None and new_default != old_default:
                corrected = corrected.replace(old_default, new_default)
                notes.append(f"updated default of '{param}' from"
                             f" {old_default} to {new_default}")
        # Verbatim old signatures.
        if change.old.signature in corrected:
            corrected = corrected.replace(change.old.signature,
                                          change.new.signature)
            notes.append("updated signature block")

    if finding.confidence >= confidence_threshold and corrected != section.content:
        mode = "auto_fix"
    else:
        mode = "review_flag"
        marker = (f"<!-- TODO(doc-check): verify against"
                  f" {change.chunk_id}: {change.detail} -->")
        if corrected == section.content:
            corrected = f"{marker}\n{corrected}"
            notes.append("no mechanical fix available; flagged for review")
        else:
            corrected = f"{marker}\n{corrected}"
            notes.append("fix drafted but below confidence threshold")

    return Repair(section_id=section.section_id, mode=mode,
                  original=section.content, corrected=corrected, notes=notes)


def summarize(repairs: list[Repair], verified_ok: int) -> str:
    fixed = sum(r.mode == "auto_fix" for r in repairs)
    flagged = sum(r.mode == "review_flag" for r in repairs)
    return (f"Doc Check Results: {verified_ok} section(s) verified accurate,"
            f" {fixed} auto-fixed, {flagged} flagged for review.")
