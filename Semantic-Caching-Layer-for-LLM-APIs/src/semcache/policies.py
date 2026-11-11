"""Cache policies: TTL classification and adaptive similarity thresholds."""

from __future__ import annotations

import re

TIME_SENSITIVE = re.compile(
    r"\b(today|yesterday|tomorrow|this (week|month|year)|latest|current|"
    r"now|news|stock price|weather|score)\b", re.I)
CREATIVE = re.compile(
    r"\b(write a (story|poem|song)|creative|brainstorm|imagine|invent|"
    r"unique|original)\b", re.I)
CLASSIFICATION_LIKE = re.compile(
    r"\b(classify|categorize|label|is this|yes or no|which of|sentiment|"
    r"extract|translate|convert)\b", re.I)


def ttl_for(prompt: str) -> float | None:
    """Assign a TTL tier by prompt content. None means do not cache."""
    if CREATIVE.search(prompt):
        return None
    if TIME_SENSITIVE.search(prompt):
        return 3600.0            # 1 hour for time-referencing queries
    return 86400.0               # 24 hours for stable content


def threshold_for(prompt: str, default: float = 0.95) -> float:
    """Adaptive similarity threshold by request type.

    Classification-like tasks have a constrained answer space and tolerate
    looser matches; creative tasks require near-identity (and usually skip
    caching entirely via ttl_for).
    """
    if CLASSIFICATION_LIKE.search(prompt):
        return 0.90
    if CREATIVE.search(prompt):
        return 0.98
    return default
