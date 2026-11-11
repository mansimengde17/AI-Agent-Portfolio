#!/usr/bin/env python3
"""Offline end-to-end demonstration: route a mixed workload, verify a
sample, and print the cost savings report."""

from __future__ import annotations

import argparse
import os
import random
import sys

sys.path.insert(0, "src")

from cost_autopilot.classifier import load_dataset, train_default
from cost_autopilot.router import Router
from cost_autopilot.store import AuditStore
from cost_autopilot.verifier import Verifier


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--db", default="autopilot.db")
    args = parser.parse_args()

    if os.path.exists(args.db):
        os.remove(args.db)

    random.seed(11)
    classifier = train_default()
    examples = load_dataset()
    print(f"Classifier training-set accuracy: "
          f"{classifier.accuracy(examples):.1%}")

    router = Router(classifier)
    verifier = Verifier(top_model=router.baseline_model,
                        threshold=router.verification["agreement_threshold"])
    store = AuditStore(args.db)

    # Simulated workload: mostly simple traffic, like real production mixes.
    weighted = ([e for e in examples if e["tier"] == 1] * 6
                + [e for e in examples if e["tier"] == 2] * 3
                + [e for e in examples if e["tier"] == 3] * 1)
    workload = [random.choice(weighted)["prompt"] for _ in range(args.requests)]

    escalations = 0
    for prompt in workload:
        decision = router.route(prompt)
        verification = None
        if random.random() < router.verification["sample_rate"]:
            verification = verifier.verify(prompt, decision)
            if verification.escalated:
                escalations += 1
        result = (verification.escalated_result
                  if verification and verification.escalated
                  else decision.result)
        store.log(prompt, decision.tier, result.model_key, result.cost_usd,
                  result.input_tokens, result.output_tokens, result.latency_s,
                  router.baseline_model,
                  verification.agreement if verification else None,
                  bool(verification and verification.escalated))

    stats = store.stats()
    print(f"\nRouted {stats['requests']} requests")
    for model, count in sorted(stats["routing_distribution"].items()):
        print(f"  {model:<14} {count} requests")
    print(f"Escalations: {stats['escalations']}"
          f" ({stats['escalations'] / stats['requests']:.1%})")
    print(f"Actual cost:      ${stats['actual_cost_usd']:.4f}")
    print(f"All-{router.baseline_model} cost:  ${stats['baseline_cost_usd']:.4f}")
    print(f"Savings:          {stats['savings_pct']}%")


if __name__ == "__main__":
    main()
