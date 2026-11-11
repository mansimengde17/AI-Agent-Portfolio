# LLM Cost Autopilot

An intelligent routing layer that sits in front of multiple LLM providers, analyzes each incoming request's complexity, routes it to the cheapest model capable of handling it at acceptable quality, and continuously validates that routing decisions were correct.

Portfolio: https://mansimengde17.github.io/AI-Agent-Portfolio/

## The problem

Most teams send every request to their most capable (and most expensive) model. On typical workloads the majority of requests are simple extraction, reformatting, or classification that a model one tenth the price handles at equal quality. This system routes each request to the cheapest adequate model and proves, with an async verification loop, that quality did not degrade.

## Architecture

```
            POST /v1/completions
                    |
                    v
      +---------------------------+
      |   Complexity Classifier    |   features: token count, instruction
      |   tier 1 / tier 2 / tier 3 |   verbs, constraints, context, output
      +---------------------------+   format complexity
                    |
                    v
      +---------------------------+     config/routing.yaml
      |          Router            | <-- tier -> model mapping,
      +---------------------------+     hot-swappable
          |         |         |
          v         v         v
       cheap      mid       top        unified provider interface
      (haiku,   (gpt-4o-   (gpt-4o,    (OpenAI, Anthropic, Ollama)
       llama)    mini)      sonnet)
                    |
                    v
      +---------------------------+
      |   Async Quality Verifier   |  re-runs sample through top model,
      |   agreement scoring,       |  escalates on divergence, feeds
      |   auto-escalation          |  failures back to the classifier
      +---------------------------+
                    |
                    v
        SQLite audit log + cost dashboard
        ("you saved $X vs all-GPT-4o")
```

## Quick start (offline, no API keys)

The repository ships with a deterministic simulation provider so the full routing, verification, and savings pipeline runs offline:

```bash
pip install -r requirements.txt
python demo.py --requests 200
```

This routes 200 mixed-complexity requests, runs the verification loop, and prints the savings report:

```
Routed 200 requests
  tier1 -> claude-haiku      118 requests
  tier2 -> gpt-4o-mini        58 requests
  tier3 -> gpt-4o             24 requests
Escalations: 4 (2.0%)
Actual cost:      $0.4310
All-GPT-4o cost:  $1.7350
Savings:          75.2%
```

To serve the routing API:

```bash
uvicorn src.cost_autopilot.api:app --reload
# POST /v1/completions  {"prompt": "..."}   router picks the model
# GET  /v1/models       registry with real per-token pricing
# GET  /v1/stats        savings summary
# PUT  /v1/routing-config  update tier-to-model mapping without redeploy
```

With real keys set (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or a local Ollama at `OLLAMA_HOST`), the same interface calls real providers.

## How routing decisions are made

1. Feature extraction: prompt length, presence of reasoning verbs (analyze, compare, prove), constraint count, whether context is supplied, and requested output format complexity.
2. A lightweight linear classifier (trained on the labeled dataset in `data/complexity_dataset.json`) scores the prompt into tier 1 (simple), tier 2 (moderate), or tier 3 (complex). The classifier is deliberately simple and fully inspectable; anything above 80 percent held-out accuracy is enough for V1 because the verifier catches the mistakes.
3. `config/routing.yaml` maps tiers to models. Swapping models requires no code change.

## The verification flywheel

After a response is returned, an async job re-runs a sample of requests through the top-tier model and scores agreement. Significant divergence is logged as a routing failure, optionally auto-escalated, and appended to `data/feedback.jsonl` as a new training example. Retraining the classifier on accumulated failures is one command:

```bash
python -m src.cost_autopilot.classifier --retrain
```

## Repository layout

```
config/routing.yaml         tier-to-model mapping and verification policy
data/complexity_dataset.json  hand-labeled prompts for the classifier
src/cost_autopilot/         registry, providers, classifier, router, verifier, api
demo.py                     offline end-to-end demonstration and load test
tests/                      unit tests
```

## Design decisions

- The classifier is intentionally cheap (microseconds, no API call). Spending an LLM call to decide which LLM to call defeats the purpose.
- Verification is async and sampled, so it never adds user-facing latency; the audit trail in SQLite records every decision with cost, latency, tier, and verification outcome.
- Escalation returns the better answer when latency permits, and every escalation event stores the cost delta and quality gap that triggered it.
