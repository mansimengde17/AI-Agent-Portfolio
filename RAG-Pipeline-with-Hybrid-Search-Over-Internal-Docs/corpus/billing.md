# Billing and Quotas

## Plans

Meridian has three plans: Starter, Growth, and Enterprise. Starter includes
100000 API calls per month. Growth includes 2 million calls and adds the
analytics module. Enterprise is custom and adds the audit log export and
SSO.

## Overage

Calls beyond the plan quota are billed at 0.40 dollars per thousand calls on
Starter and 0.25 dollars per thousand on Growth. Overage charges appear on
the next invoice. Enterprise contracts define custom overage terms.

## Rate limits

Independent of billing quotas, every key has a rate limit: 100 requests per
second on Starter, 500 on Growth, and negotiated limits on Enterprise.
Exceeding the rate limit returns HTTP 429 with error E2001 and a Retry-After
header.

## Quota alerts

Quota alerts fire at 80 and 100 percent of monthly usage, delivered by email
and webhook. The webhook payload includes the metric, the threshold crossed,
and current usage. Alert thresholds are configurable per workspace.
