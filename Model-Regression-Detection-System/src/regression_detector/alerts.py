"""Slack alerting via incoming webhooks."""

from __future__ import annotations

import json
import os
import urllib.request

from .compare import Comparison

STATUS_LABELS = {"pass": "PASS", "warn": "WARNING", "critical": "CRITICAL"}


def build_slack_payload(comparison: Comparison, report_url: str = "") -> dict:
    headline = (
        f"Eval {STATUS_LABELS[comparison.status]}: prompt"
        f" {comparison.candidate_version} vs baseline"
        f" {comparison.baseline_version or 'none'}"
    )
    lines = [headline]
    if comparison.delta is not None:
        lines.append(
            f"Pass rate {comparison.baseline_pass_rate:.1%} ->"
            f" {comparison.candidate_pass_rate:.1%}"
            f" ({comparison.delta:+.1%})")
    if comparison.regressions:
        flipped = ", ".join(r["case_id"] for r in comparison.regressions[:10])
        lines.append(f"{len(comparison.regressions)} regressions: {flipped}")
    if comparison.drift_warning:
        lines.append(f"Slow drift: {comparison.drift_average:.1%} moving average")
    if report_url:
        lines.append(f"Full diff report: {report_url}")
    return {"text": "\n".join(lines)}


def send_slack_alert(comparison: Comparison, report_url: str = "",
                     webhook_url: str | None = None) -> bool:
    webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        return False
    payload = json.dumps(build_slack_payload(comparison, report_url)).encode()
    req = urllib.request.Request(
        webhook_url, data=payload,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status == 200
