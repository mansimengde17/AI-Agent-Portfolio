import sys
import unittest

sys.path.insert(0, "src")

from cost_autopilot.classifier import ComplexityClassifier, load_dataset
from cost_autopilot.registry import cost_of
from cost_autopilot.verifier import agreement_score


class ClassifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.examples = load_dataset()
        cls.classifier = ComplexityClassifier.train(cls.examples)

    def test_training_accuracy_above_bar(self):
        self.assertGreaterEqual(self.classifier.accuracy(self.examples), 0.8)

    def test_simple_prompt_routes_low(self):
        tier, _ = self.classifier.predict("Convert 10 miles to kilometers")
        self.assertEqual(tier, 1)

    def test_complex_prompt_routes_high(self):
        tier, _ = self.classifier.predict(
            "Analyze the tradeoffs between two database architectures,"
            " design an experiment to compare them, and justify your"
            " recommendation step by step considering cost and latency")
        self.assertEqual(tier, 3)


class CostTests(unittest.TestCase):
    def test_cost_math(self):
        self.assertAlmostEqual(cost_of("gpt-4o", 1_000_000, 0), 2.50)
        self.assertAlmostEqual(cost_of("gpt-4o", 0, 1_000_000), 10.00)

    def test_agreement_bounds(self):
        self.assertEqual(agreement_score("a b c", "a b c"), 1.0)
        self.assertEqual(agreement_score("", "a"), 0.0)


if __name__ == "__main__":
    unittest.main()
