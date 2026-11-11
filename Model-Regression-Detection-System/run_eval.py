#!/usr/bin/env python3
"""CLI entry point: run the eval pipeline for a prompt version."""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "src")

from regression_detector.alerts import send_slack_alert
from regression_detector.compare import (DEFAULT_CRITICAL_DELTA,
                                         DEFAULT_DRIFT_FLOOR,
                                         DEFAULT_WARN_DELTA, RunStore,
                                         check_drift, compare_runs)
from regression_detector.config import PromptConfig
from regression_detector.llm import get_provider
from regression_detector.report import render_report
from regression_detector.runner import run_eval


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True, help="prompt YAML path")
    parser.add_argument("--dataset", default="data/golden_dataset.json")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"])
    parser.add_argument("--db", default="eval_history.db")
    parser.add_argument("--warn-delta", type=float, default=DEFAULT_WARN_DELTA)
    parser.add_argument("--critical-delta", type=float,
                        default=DEFAULT_CRITICAL_DELTA)
    parser.add_argument("--drift-floor", type=float, default=DEFAULT_DRIFT_FLOOR)
    parser.add_argument("--alert", action="store_true",
                        help="send a Slack alert (needs SLACK_WEBHOOK_URL)")
    args = parser.parse_args()

    config = PromptConfig.from_yaml(args.prompt)
    with open(args.dataset, encoding="utf-8") as fh:
        dataset = json.load(fh)

    provider = get_provider(args.provider)
    print(f"Running {len(dataset['cases'])} golden cases against prompt"
          f" {config.version} ({provider.name})...")
    run = run_eval(config, dataset, provider).to_dict()

    store = RunStore(args.db)
    baseline = store.latest_before(run["timestamp"])
    store.save(run)

    comparison = compare_runs(run, baseline, args.warn_delta,
                              args.critical_delta)
    comparison = check_drift(store, comparison, floor=args.drift_floor)

    report_path = render_report(run, comparison, store.recent_pass_rates(10))

    print(f"Pass rate: {run['pass_rate']:.1%}"
          + (f" (baseline {comparison.baseline_pass_rate:.1%},"
             f" delta {comparison.delta:+.1%})"
             if comparison.delta is not None else ""))
    for message in comparison.messages:
        print(f"- {message}")
    print(f"Report: {report_path}")
    print(f"Status: {comparison.status.upper()}")

    if args.alert:
        sent = send_slack_alert(comparison)
        print("Slack alert sent." if sent
              else "Slack alert skipped (SLACK_WEBHOOK_URL not set).")

    return 1 if comparison.status == "critical" else 0


if __name__ == "__main__":
    raise SystemExit(main())
