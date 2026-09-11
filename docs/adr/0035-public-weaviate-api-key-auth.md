# ADR 0035: Public Weaviate via Caddy using Native API Key Auth

## Context
Previously, Weaviate was isolated to a private Tailscale-only perimeter (ADR-0022). This required the AI Incident Commander or other integrations to run Tailscale locally or on specific nodes to communicate with the vector database.

## Decision
We are transitioning Weaviate to a public ingress (`weaviate.vinhthang.dev`) proxied through Caddy, protected by Weaviate's native API key authentication.

## Consequences
- Removes the Tailscale dependency on `arm10` for Weaviate.
- Allows external secure access to Weaviate for integrations.
- Requires passing `AUTHENTICATION_APIKEY_ENABLED`, `AUTHENTICATION_APIKEY_ALLOWED_KEYS`, and `AUTHENTICATION_APIKEY_USERS` in `values.yaml` and disabling anonymous access.
