"""Unit tests for the comparison engine."""

import sys
import unittest

sys.path.insert(0, "src")

from regression_detector.compare import RunStore, check_drift, compare_runs


def make_run(version, results):
    per_category = {}
    for r in results:
        per_category.setdefault(r["expected_category"], []).append(
            r["category_match"])
    return {
        "prompt_version": version,
        "model": "gpt-4o-mini",
        "provider": "mock",
        "timestamp": 0.0,
        "pass_rate": sum(r["passed"] for r in results) / len(results),
        "per_category": {c: sum(v) / len(v) for c, v in per_category.items()},
        "results": results,
    }


def case(case_id, passed, category="billing"):
    return {"case_id": case_id, "difficulty": "standard",
            "expected_category": category, "predicted_category": category,
            "expected_summary": "", "predicted_summary": "",
            "category_match": passed, "summary_score": 1.0, "passed": passed,
            "latency_s": 0.0, "input_tokens": 0, "output_tokens": 0}


class CompareTests(unittest.TestCase):
    def test_no_baseline_passes(self):
        run = make_run("v1", [case("a", True)])
        comparison = compare_runs(run, None)
        self.assertEqual(comparison.status, "pass")
        self.assertIsNone(comparison.delta)

    def test_regression_detected_and_flagged_critical(self):
        baseline = make_run("v1", [case(str(i), True) for i in range(10)])
        candidate = make_run("v2", [case(str(i), i >= 2) for i in range(10)])
        comparison = compare_runs(candidate, baseline)
        self.assertEqual(comparison.status, "critical")
        self.assertEqual(len(comparison.regressions), 2)
        self.assertAlmostEqual(comparison.delta, -0.2)

    def test_small_drop_is_warning(self):
        baseline = make_run("v1", [case(str(i), True) for i in range(20)])
        candidate = make_run("v2", [case(str(i), i != 0) for i in range(20)])
        comparison = compare_runs(candidate, baseline)
        self.assertEqual(comparison.status, "warn")
        self.assertEqual(len(comparison.regressions), 1)

    def test_improvements_reported_separately(self):
        baseline = make_run("v1", [case("a", False), case("b", True)])
        candidate = make_run("v2", [case("a", True), case("b", True)])
        comparison = compare_runs(candidate, baseline)
        self.assertEqual(comparison.status, "pass")
        self.assertEqual(len(comparison.improvements), 1)

    def test_drift_warning_fires_on_low_moving_average(self):
        store = RunStore(":memory:")
        for i in range(7):
            store.save(make_run(f"v{i}", [case("a", i % 2 == 0)]))
        run = make_run("v7", [case("a", True)])
        comparison = compare_runs(run, None)
        comparison = check_drift(store, comparison, window=7, floor=0.85)
        self.assertTrue(comparison.drift_warning)
        self.assertEqual(comparison.status, "warn")


if __name__ == "__main__":
    unittest.main()
