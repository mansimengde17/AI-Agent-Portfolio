# Model Regression Detection System

A CI/CD-style pipeline that continuously tests an LLM-powered feature against a human-verified golden dataset whenever a prompt or model changes, detects quality regressions, and alerts the team via Slack before bad outputs reach users.

Portfolio: https://mansimengde17.github.io/AI-Agent-Portfolio/

## What this system does

Teams ship prompt changes blind. This system treats prompt changes the way engineering teams treat code changes: every change to a file in `prompts/` triggers a full evaluation run against a golden dataset, the results are diffed against the previous baseline, and regressions block the merge.

The feature under test is a customer support email classifier: it reads an email and returns a category (billing, technical, account, general) plus a one-sentence summary.

## Architecture

```
 prompts/*.yaml            data/golden_dataset.json
      |                             |
      v                             v
 +-----------------------------------------+
 |             Eval Runner                  |
 |  batched LLM calls, multi-dimensional    |
 |  scoring: category match, summary        |
 |  relevance (LLM-as-judge), latency,      |
 |  token usage                             |
 +-----------------------------------------+
      |
      v
 +-----------------------------------------+
 |          Comparison Engine               |
 |  pass-rate delta, per-category delta,    |
 |  flipped cases (regressions and          |
 |  improvements), warn/critical            |
 |  thresholds, 7-run drift detection       |
 +-----------------------------------------+
      |                    |
      v                    v
 HTML diff report     Slack webhook alert
 (reports/)           (pass / warn / fail)
      |
      v
 GitHub Action: blocks merge on critical regression
```

## Quick start

The system runs fully offline with a deterministic mock LLM provider, so you can evaluate the pipeline without an API key:

```bash
pip install -r requirements.txt

# Run an eval against prompt v1 and store it as the baseline
python run_eval.py --prompt prompts/classifier_v1.yaml

# Run against prompt v2; this diffs against the previous run
python run_eval.py --prompt prompts/classifier_v2.yaml

# Open the generated diff report
open reports/latest.html
```

To run against the real OpenAI API instead of the mock provider:

```bash
export OPENAI_API_KEY=sk-...
python run_eval.py --prompt prompts/classifier_v2.yaml --provider openai
```

To enable Slack alerts:

```bash
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
python run_eval.py --prompt prompts/classifier_v2.yaml --alert
```

## Adding test cases to the golden dataset

Edit `data/golden_dataset.json`. Every case needs a stable `id`, the input `email`, the `expected_category`, an `expected_summary`, an `expected_difficulty` tag (`standard`, `ambiguous`, `short`, `noisy`), and a `notes` field explaining why the case matters. Do not generate cases with an LLM; the value of this dataset is that it is human-verified ground truth. Expand it over time from production failure cases.

## Adjusting thresholds

Thresholds live in `src/regression_detector/compare.py` and can be overridden with CLI flags:

- `--warn-delta` (default 0.03): pass-rate drop that triggers a warning
- `--critical-delta` (default 0.08): pass-rate drop that fails the run and blocks merge
- Drift: the 7-run moving average of the pass rate is tracked separately; if it drops below `--drift-floor` (default 0.85) a slow-drift warning fires even when no single run regressed

## CI integration

`.github/workflows/eval.yml` runs the pipeline on every pull request that touches `prompts/`. The job posts a summary to the job log, uploads the HTML report as an artifact, and exits non-zero on critical regressions so the merge is blocked.

## Design decisions

- Regressions and improvements are reported separately. A run that fixes 5 cases and breaks 3 is not a net win; the 3 broken cases are new production bugs.
- Slow drift is tracked independently of per-run diffs because gradual degradation (model updates, data shift) never trips a single-run threshold.
- All eval history is stored in SQLite (`eval_history.db`) plus per-run JSON files, so the trend data is queryable and diffable in git.
- The mock provider is prompt-version-sensitive on purpose: prompt v2 deliberately introduces regressions on ambiguous cases so the detection pipeline can be demonstrated end to end without an API key.

## Repository layout

```
prompts/                 versioned prompt YAML files (the "code" under CI)
data/golden_dataset.json human-verified golden dataset
src/regression_detector/ eval runner, comparison engine, reporting, alerting
run_eval.py              CLI entry point
tests/                   unit tests for the comparison engine
reports/                 generated HTML diff reports (gitignored)
```
