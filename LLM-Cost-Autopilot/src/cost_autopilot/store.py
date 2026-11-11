"""SQLite audit trail and savings statistics."""

from __future__ import annotations

import hashlib
import sqlite3
import time

from .registry import cost_of


class AuditStore:
    def __init__(self, path: str = "autopilot.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS requests (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   timestamp REAL, prompt_hash TEXT, tier INTEGER,
                   model_key TEXT, cost_usd REAL, baseline_cost_usd REAL,
                   latency_s REAL, agreement REAL, escalated INTEGER)""")
        self.conn.commit()

    def log(self, prompt: str, tier: int, model_key: str, cost_usd: float,
            input_tokens: int, output_tokens: int, latency_s: float,
            baseline_model: str, agreement: float | None,
            escalated: bool) -> None:
        baseline_cost = cost_of(baseline_model, input_tokens, output_tokens)
        self.conn.execute(
            "INSERT INTO requests (timestamp, prompt_hash, tier, model_key,"
            " cost_usd, baseline_cost_usd, latency_s, agreement, escalated)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (time.time(), hashlib.sha256(prompt.encode()).hexdigest()[:16],
             tier, model_key, cost_usd, baseline_cost, latency_s,
             agreement, int(escalated)))
        self.conn.commit()

    def stats(self) -> dict:
        row = self.conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(cost_usd), 0),"
            " COALESCE(SUM(baseline_cost_usd), 0),"
            " COALESCE(AVG(latency_s), 0), COALESCE(SUM(escalated), 0)"
            " FROM requests").fetchone()
        count, actual, baseline, avg_latency, escalations = row
        distribution = dict(self.conn.execute(
            "SELECT model_key, COUNT(*) FROM requests GROUP BY model_key"))
        savings_pct = ((baseline - actual) / baseline * 100) if baseline else 0.0
        return {
            "requests": count,
            "actual_cost_usd": round(actual, 4),
            "baseline_cost_usd": round(baseline, 4),
            "savings_pct": round(savings_pct, 1),
            "avg_latency_s": round(avg_latency, 3),
            "escalations": escalations,
            "routing_distribution": distribution,
        }
