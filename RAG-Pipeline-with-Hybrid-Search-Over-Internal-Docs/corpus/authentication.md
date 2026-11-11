# Authentication Guide

## API keys

Every request to the Meridian platform requires an API key passed in the
X-Meridian-Key header. Keys are scoped per environment: sandbox keys begin
with mk_test_ and production keys begin with mk_live_. Keys never expire on
their own but can be rotated at any time.

## Rotating keys

Use the rotate_key endpoint to rotate a key without downtime. The old key
remains valid for a 24 hour grace period after rotation, controlled by the
KEY_GRACE_HOURS setting which defaults to 24. Rotation events are written to
the audit log.

## OAuth service accounts

Service accounts authenticate with the OAuth client credentials flow. Tokens
are valid for 3600 seconds and must be refreshed by requesting a new token;
refresh tokens are not issued for service accounts. The token endpoint rate
limit is 10 requests per minute per client.

## Error codes

Error E1001 means the API key is missing. Error E1002 means the key is
revoked or expired. Error E1003 means the key is valid but lacks the scope
required for the endpoint. E1003 is also returned when a sandbox key is used
against production.

## IP allowlists

Production keys can be restricted to an IP allowlist with up to 50 CIDR
blocks. Requests from outside the allowlist fail with error E1004 and are
logged with the source address.
