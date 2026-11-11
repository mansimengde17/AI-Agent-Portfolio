"""Comparison engine: diffs eval runs and detects regressions and drift."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field

DEFAULT_WARN_DELTA = 0.03
DEFAULT_CRITICAL_DELTA = 0.08
DEFAULT_DRIFT_WINDOW = 7
DEFAULT_DRIFT_FLOOR = 0.85


@dataclass
class Comparison:
    status: str                      # pass | warn | critical
    baseline_version: str | None
    candidate_version: str
    baseline_pass_rate: float | None
    candidate_pass_rate: float
    delta: float | None
    regressions: list[dict] = field(default_factory=list)
    improvements: list[dict] = field(default_factory=list)
    category_deltas: dict = field(default_factory=dict)
    drift_warning: bool = False
    drift_average: float | None = None
    messages: list[str] = field(default_factory=list)


class RunStore:
    """SQLite-backed history of eval runs (metadata + full JSON payload)."""

    def __init__(self, path: str = "eval_history.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS runs (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   prompt_version TEXT NOT NULL,
                   model TEXT NOT NULL,
                   provider TEXT NOT NULL,
                   timestamp REAL NOT NULL,
                   pass_rate REAL NOT NULL,
                   payload TEXT NOT NULL)"""
        )
        self.conn.commit()

    def save(self, run_dict: dict) -> int:
        cur = self.conn.execute(
            "INSERT INTO runs (prompt_version, model, provider, timestamp,"
            " pass_rate, payload) VALUES (?, ?, ?, ?, ?, ?)",
            (run_dict["prompt_version"], run_dict["model"],
             run_dict["provider"], run_dict["timestamp"],
             run_dict["pass_rate"], json.dumps(run_dict)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def latest_before(self, timestamp: float) -> dict | None:
        row = self.conn.execute(
            "SELECT payload FROM runs WHERE timestamp < ?"
            " ORDER BY timestamp DESC LIMIT 1", (timestamp,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def recent_pass_rates(self, limit: int) -> list[float]:
        rows = self.conn.execute(
            "SELECT pass_rate FROM runs ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [r[0] for r in rows]


def compare_runs(candidate: dict, baseline: dict | None,
                 warn_delta: float = DEFAULT_WARN_DELTA,
                 critical_delta: float = DEFAULT_CRITICAL_DELTA) -> Comparison:
    if baseline is None:
        return Comparison(
            status="pass",
            baseline_version=None,
            candidate_version=candidate["prompt_version"],
            baseline_pass_rate=None,
            candidate_pass_rate=candidate["pass_rate"],
            delta=None,
            messages=["No baseline run found; this run becomes the baseline."],
        )

    base_by_id = {r["case_id"]: r for r in baseline["results"]}
    regressions, improvements = [], []
    for result in candidate["results"]:
        prior = base_by_id.get(result["case_id"])
        if prior is None:
            continue
        if prior["passed"] and not result["passed"]:
            regressions.append({
                "case_id": result["case_id"],
                "difficulty": result["difficulty"],
                "expected": result["expected_category"],
                "old_output": prior["predicted_category"],
                "new_output": result["predicted_category"],
                "old_summary": prior["predicted_summary"],
                "new_summary": result["predicted_summary"],
            })
        elif not prior["passed"] and result["passed"]:
            improvements.append({"case_id": result["case_id"],
                                 "expected": result["expected_category"]})

    delta = candidate["pass_rate"] - baseline["pass_rate"]
    category_deltas = {
        cat: round(candidate["per_category"].get(cat, 0.0)
                   - baseline["per_category"].get(cat, 0.0), 3)
        for cat in sorted(set(candidate["per_category"])
                          | set(baseline["per_category"]))
    }

    status = "pass"
    messages = []
    if delta <= -critical_delta:
        status = "critical"
        messages.append(
            f"Critical regression: pass rate dropped {abs(delta):.1%}"
            f" (threshold {critical_delta:.0%}). Merge should be blocked.")
    elif delta <= -warn_delta or regressions:
        status = "warn"
        if delta <= -warn_delta:
            messages.append(
                f"Warning: pass rate dropped {abs(delta):.1%}"
                f" (threshold {warn_delta:.0%}).")
        if regressions:
            messages.append(f"{len(regressions)} case(s) flipped from pass"
                            " to fail.")
    if improvements:
        messages.append(f"{len(improvements)} case(s) flipped from fail"
                        " to pass.")

    return Comparison(
        status=status,
        baseline_version=baseline["prompt_version"],
        candidate_version=candidate["prompt_version"],
        baseline_pass_rate=baseline["pass_rate"],
        candidate_pass_rate=candidate["pass_rate"],
        delta=round(delta, 4),
        regressions=regressions,
        improvements=improvements,
        category_deltas=category_deltas,
        messages=messages,
    )


def check_drift(store: RunStore, comparison: Comparison,
                window: int = DEFAULT_DRIFT_WINDOW,
                floor: float = DEFAULT_DRIFT_FLOOR) -> Comparison:
    """Slow-drift detection over a moving average of recent pass rates.

    Catches gradual degradation where no individual run trips the per-run
    thresholds but the trend line is sinking.
    """
    rates = store.recent_pass_rates(window)
    if len(rates) >= window:
        average = sum(rates) / len(rates)
        comparison.drift_average = round(average, 4)
        if average < floor:
            comparison.drift_warning = True
            comparison.messages.append(
                f"Slow drift: {window}-run average pass rate {average:.1%}"
                f" is below the {floor:.0%} floor.")
            if comparison.status == "pass":
                comparison.status = "warn"
    return comparison


def utc_stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
