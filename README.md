# AI Agent Portfolio

Production-grade systems that ship, measure, protect, and continuously improve AI in real-world environments.

[Explore the interactive portfolio](https://mansimengde17.github.io/AI-Agent-Portfolio/) · [Browse all source code](https://github.com/mansimengde17/AI-Agent-Portfolio)

This monorepo contains 15 independent AI engineering projects spanning the full production lifecycle: evaluation, model routing, observability, retrieval, caching, safety, experimentation, document intelligence, agent orchestration, and fine-tuning. Each project includes working code, architecture documentation, tests, Docker packaging where applicable, and an offline deterministic path that can be explored without paid API keys.

## What makes this portfolio different

- **Real operational problems:** The projects address silent quality regressions, runaway model costs, opaque pipeline failures, stale evaluation data, unreliable retrieval, unsafe SQL generation, and other problems teams encounter after an AI prototype reaches production.
- **Production engineering foundations:** APIs, databases, CI/CD, Docker, rate limiting, tracing, queues, statistical testing, audit logs, and human-review workflows are treated as core parts of the AI system.
- **A distinct competency in every project:** The collection demonstrates evaluation, cost optimization, observability, gateways, hybrid search, semantic caching, guardrails, feature flags, prompt experimentation, OCR, orchestration, and parameter-efficient fine-tuning.
- **More than model calls:** These systems route, verify, trace, gate, compare, fall back, refuse, roll back, and escalate. They are designed to measure and correct their own behavior.

## The 15 projects

| # | Project | Core capability | What it demonstrates |
|---:|---|---|---|
| 01 | [Model Regression Detection System](./Model-Regression-Detection-System) | Continuous LLM evaluation | Golden-dataset testing, prompt-change CI, drift detection, case-level diffs, and regression alerts. |
| 02 | [LLM Cost Autopilot](./LLM-Cost-Autopilot) | Cost-aware model routing | Complexity classification, cheapest-capable-model routing, asynchronous quality verification, and automatic escalation. |
| 03 | [Failure Forensics Tool for AI Pipelines](./Failure-Forensics-Tool-for-AI-Pipelines) | AI observability and diagnosis | Span-level tracing, backward root-cause analysis, failure taxonomy, evidence chains, and a feedback-to-evaluation loop. |
| 04 | [Self-Healing Technical Documentation](./Self-Healing-Technical-Documentation) | Documentation automation | Code-to-doc link graphs, staleness detection, mechanical repairs, and human review for behavioral changes. |
| 05 | [LLM Output Arbitration System](./LLM-Output-Arbitration-System) | Multi-model output verification | Parallel specialized critics, disagreement detection, evidence-based adjudication, and confidence-scored verdicts. |
| 06 | [RAG Pipeline with Hybrid Search](./RAG-Pipeline-with-Hybrid-Search-Over-Internal-Docs) | Grounded retrieval | Dense retrieval plus BM25, reciprocal-rank fusion, reranking, verified citations, confidence scoring, and honest refusal. |
| 07 | [Semantic Caching Layer for LLM APIs](./Semantic-Caching-Layer-for-LLM-APIs) | Latency and cost reduction | OpenAI-compatible proxying, embedding similarity, namespaced cache keys, TTL policies, threshold tuning, and savings metrics. |
| 08 | [Text-to-SQL with Guardrails](./Text-to-SQL-Interface-with-Guardrails-and-Hallucination-Detection) | Safe natural-language analytics | Schema-aware generation, zero-write enforcement, read-only execution, back-translation checks, and hallucination detection. |
| 09 | [Prompt Versioning and A/B Testing Platform](./Prompt-Versioning-and-A-B-Testing-Platform) | Controlled prompt experimentation | Versioned prompts, deterministic traffic splitting, Welch's t-tests, guardrails, rollback, and audit history. |
| 10 | [LoRA Fine-Tuning Pipeline](./Fine-Tuning-Pipeline-with-LoRA-on-a-Domain-Specific-Dataset) | Domain adaptation | Leakage-safe dataset construction, LoRA/QLoRA training, hyperparameter sweeps, base-versus-tuned evaluation, and forgetting checks. |
| 11 | [LLM Gateway](./LLM-Gateway-with-Rate-Limiting-Fallback-Routing-and-Observability) | Reliable model access | Team authentication, rate limits, budgets, retries, provider fallback, circuit breakers, traces, and Prometheus metrics. |
| 12 | [AI Feature Flag System](./AI-Feature-Flag-System-with-Gradual-Rollout-and-Quality-Monitoring) | Quality-aware rollout | Consistent assignment, staged releases, judge scoring, canary statistical gates, quality monitoring, and automatic rollback. |
| 13 | [Automated Eval Dataset Generator](./Automated-Eval-Dataset-Generator-from-Production-Logs) | Evaluation data flywheel | PII redaction, deduplication, clustering, anomaly sampling, automatic labeling, review queues, and regression-ready datasets. |
| 14 | [Multi-Modal Document Processor](./Multi-Modal-Document-Processor-with-OCR-LLM-Extraction-and-Validation) | Document intelligence | Dual-engine OCR, vision fallback, schema extraction, field-level confidence, validation, anomaly detection, and human review. |
| 15 | [Agent Orchestration System](./Agent-Orchestration-System-with-Tool-Use-Memory-and-Human-in-the-Loop) | Governed multi-agent workflows | Supervisor planning, permissioned tools, specialist agents, reviewer loops, persistent memory, execution traces, and human approval. |

## How the systems fit together

The projects map to six stages in the lifecycle of a production AI feature:

```text
Ship safely
  RAG + Text-to-SQL guardrails
        ↓
Build reliable infrastructure
  LLM Gateway + Semantic Cache
        ↓
Control cost and rollout
  Cost Autopilot + AI Feature Flags
        ↓
Measure quality continuously
  Regression Detection + A/B Testing + Eval Generation + Arbitration
        ↓
Diagnose, repair, and process
  Failure Forensics + Self-Healing Docs + Document Processing
        ↓
Orchestrate and customize
  Agent Orchestration + LoRA Fine-Tuning
```

### 1. Ship safely

The RAG and Text-to-SQL systems demonstrate user-facing AI built defensively: verified citations, structured confidence, destructive-operation blocking, hallucination detection, and refusal when evidence is insufficient.

### 2. Put reliable infrastructure in front of models

The LLM Gateway handles authentication, rate limits, budgets, outages, and provider failover. The Semantic Cache recognizes repeated intent and returns validated cached responses with near-zero latency.

### 3. Control cost and release risk

The Cost Autopilot routes requests to the cheapest capable model and verifies quality asynchronously. The AI Feature Flag system releases model and prompt changes in stages and rolls them back when measured quality falls below baseline.

### 4. Measure everything

Regression Detection evaluates prompt changes against verified cases. Prompt A/B Testing adds statistical rigor. The Eval Dataset Generator converts real production failures into future tests. Output Arbitration independently audits high-value model responses.

### 5. Diagnose and repair failures

Failure Forensics traces multi-step pipelines to the originating error. Self-Healing Documentation repairs code-induced documentation drift. The Multi-Modal Document Processor measures confidence from OCR through structured extraction and routes uncertainty to people.

### 6. Orchestrate and customize

The Agent Orchestration system coordinates specialist agents under tool permissions, reviewer checks, memory, and human approval. When prompting is not sufficient, the LoRA pipeline provides reproducible domain-specific model adaptation and benchmarking.

## Repository structure

```text
AI-Agent-Portfolio/
├── README.md
├── docs/                         # GitHub Pages portfolio
├── Model-Regression-Detection-System/
├── LLM-Cost-Autopilot/
├── Failure-Forensics-Tool-for-AI-Pipelines/
├── ...
└── Agent-Orchestration-System-with-Tool-Use-Memory-and-Human-in-the-Loop/
```

Every project is self-contained. Open its README for architecture, components, setup instructions, API examples, tests, and expected behavior.

## Running a project locally

Most projects expose an offline demonstration with a similar workflow:

```bash
cd "<project-directory>"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python demo.py
```

Some projects use a different entry point or optional Docker services. Follow the README inside the selected project for its exact commands. Secrets and provider credentials belong in an untracked `.env` file—never commit them.

## GitHub Pages

The [interactive portfolio website](https://mansimengde17.github.io/AI-Agent-Portfolio/) is published from [`docs/`](./docs). It provides a visual tour of all 15 systems, explains what makes the collection different, and shows how the projects form one production AI lifecycle.

The previous `Real-Time-Financial-Intelligence-Platform` Pages address has been retired. The `AI-Agent-Portfolio` URL above is the canonical portfolio site.

## Author

Built by [Mansi Mengde](https://github.com/mansimengde17).
