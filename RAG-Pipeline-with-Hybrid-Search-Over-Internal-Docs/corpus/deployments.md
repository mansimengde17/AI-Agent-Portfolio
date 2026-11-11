# Deployment Runbook

## Standard deploys

Deploys ship through the pipeline in three stages: build, canary, and fleet.
The canary stage routes 5 percent of traffic to the new version for 30
minutes. Promotion to fleet is automatic when the canary error rate stays
below 0.5 percent.

## Rollbacks

Run meridian rollback --to <version> to roll back. Rollbacks skip the canary
stage and apply to the whole fleet immediately. The last 10 versions are kept
warm and roll back in under 60 seconds; older versions require a full build.

## Configuration

Runtime concurrency is controlled by MAX_CONCURRENCY, which defaults to 64
per instance. Setting it above 128 requires a capacity review. The request
timeout is REQUEST_TIMEOUT_MS, defaulting to 30000.

## Feature flags

Flags are evaluated at request time from the flag service. A flag change
propagates to all instances within 15 seconds; there is no deploy needed.
Flags support percentage rollouts and per-tenant targeting.

## Incident response

Severity 1 incidents page the on-call immediately. During a sev1, deploys
are frozen automatically and the freeze lifts when the incident closes.
The incident commander can override the freeze with meridian deploy --force.
