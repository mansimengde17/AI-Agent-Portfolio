"""Model Regression Detection System.

CI/CD-style evaluation pipeline for LLM-powered features. Runs a golden
dataset against a versioned prompt, diffs the results against the previous
run, and raises warnings or critical failures on quality regressions.
"""

__version__ = "1.0.0"
