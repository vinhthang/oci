# ADR 0036: Deploy Attention Metrics Server to K3s Fleet

## Context
The Antigravity Attention Guard plugin collects agent telemetry, attention metrics, and lifecycle execution signals. To centralize attention metrics persistence, provide real-time agent analytics dashboards, and enable observability across autonomous agent executions, a dedicated centralized ingestion and dashboard service is required.

## Decision
We deploy the `attention-metrics-server` (written in Go with embedded static assets) into the `observability` namespace on the `arm10` master node.
- Dedicated port `8086` and NodePort `30012`.
- Persistence backed by a dedicated PostgreSQL database `attention_metrics` running on `postgres-primary.data.svc.cluster.local:5432`.
- Helm packaging declared in the master umbrella chart (`charts/vinhthang-fleet/templates/attention-metrics-server.yaml`) and configured via `values.yaml` (`ghcr.io/vinhthang/attention-metrics-server:v0.1.0`).
- Edge ingress managed declaratively in `caddy/Caddyfile` for `attention-metrics-server.vinhthang.dev` and `attention.vinhthang.dev`:
  - Public telemetry ingestion endpoints (`/api/metrics`, `/api/health`, `/metrics`) routed directly.
  - Private web UI dashboard secured behind Google OAuth2 Forward-Auth (`auth.vinhthang.dev`).
- Synthetic uptime health monitoring registered in OTel Collector httpcheck target (`https://attention-metrics-server.vinhthang.dev/api/health`).

## Consequences
- Agent telemetry can be ingested securely over HTTPS without exposing the private database.
- Centralized UI is protected by Google OAuth2 Forward-Auth.
- Adheres to ADR governance: dedicated port allocation (`8086`/`30012`), exact version tagging (`v0.1.0`), and pinned to `arm10`.
- Requires database initialization for `attention_metrics` in `postgres.yaml`.
