# ADR-0056: Harden AI Incident Commander (`v0.4.0`), Isolate AGY Runtime, and Gate PR CI

* **Status**: Accepted
* **Date**: 2026-11-19

## Context

An operational audit of `ai-incident-commander` (`v0.3.0`) and its Helm/Grafana integration revealed 9 P0/P1 reliability, concurrency, and security defects:
1. Kubernetes infrastructure alerts in namespace `apps` (`category: workload|storage|node|endpoint`) entered a dead-end `AppFixer` branch instead of opening remediation PRs.
2. Prometheus scraper labels (`pod="fleet-kube-state-metrics-..."`, `service="fleet-kube-state-metrics"`) shadowed real `deployment`, `statefulset`, `job_name`, and `persistentvolumeclaim` targets and poisoned Postgres deduplication state.
3. Pod restarts cleared in-memory `ActiveIncidents`, silently dropping subsequent `resolved` webhooks instead of auto-closing DB/GitHub incidents.
4. Concurrent webhook goroutines lacked a workspace mutex around `git checkout` / `git pull` / Fixer loops, risking repository corruption.
5. Reviewer-approved PRs merged immediately without waiting for GitHub Actions CI check runs.
6. The container mounted `/home/opc/.gemini` read-write as `root`, booted unrelated host MCP servers under a `512Mi` memory cap, failed to pass `--disable-slash-commands` or a valid `AGY_MODEL`, and referenced stale `arm10` topology for VietCalendar (`amd11`).
7. `/webhook` accepted unauthenticated requests and probes used TCP sockets instead of a DB-aware `/healthz` handler.
8. `.github/workflows/deploy.yaml` ran only on `push` to `main`, leaving PRs without CI check runs.
9. `OTEL_EXPORTER_OTLP_ENDPOINT` was unset, dumping verbose OTel span JSON to stdout/VictoriaLogs.

## Decision

1. Upgrade `ghcr.io/vinhthang/ai-incident-commander` to **`v0.4.0`** pinned by multi-arch digest (`sha256:2e7385d61773d9ebd2c928dbffecb4df21a659eb7cc65901df1951c2c99e2cbb`) with `AGY_MODEL=gemini-3.8-flash-medium`, workspace mutex locking, `WaitForPRChecks` merge gating, idempotent scraper cleanup migrations, restart-safe debounced resolve locks, Bearer auth (`WEBHOOK_AUTH_TOKEN`), and HTTP `GET /healthz` probes.
2. Isolate the `agy` runtime inside `Deployment/ai-incident-commander`:
   - Mount `/home/opc/.gemini/antigravity-cli` **read-only** at `/mnt/host-gemini-cli` (`AGY_HOST_AUTH_DIR=/mnt/host-gemini-cli`) so OAuth tokens remain synchronized without host-filesystem mutation by UID 0.
   - Mount an ephemeral `emptyDir` at `/root/.gemini`; the commander syncs only `antigravity-oauth-token`, `installation_id`, and `settings.json` per invocation and writes `{"mcpServers":{}}` to `/root/.gemini/config/mcp_config.json`.
   - Increase `resources.limits.memory` on `arm10` from `512Mi` to `1536Mi` (`requests.memory: 128Mi`).
3. Enforce shared Bearer token authentication between Grafana and AI Incident Commander using ADR-0052 retained Secrets (`ai-commander-webhook-secret` with `helm.sh/resource-policy: keep` in `system` and `observability`, `createWebhookSecret: false` by default). Grafana provisions `authorization_scheme: Bearer` and `authorization_credentials: "${AI_COMMANDER_WEBHOOK_TOKEN}"`.
4. Wire `OTEL_EXPORTER_OTLP_ENDPOINT: otel-collector.observability.svc.cluster.local:4317` cleanly into `Deployment/ai-incident-commander`.
5. Add `pull_request: branches: [ "main" ]` to `.github/workflows/deploy.yaml` so autonomous PRs receive verifiable CI check runs before merge.

## Consequences

* **Positive**: Zero host `.gemini` pollution, faster MCP-free `agy` triage with `gemini-3.8-flash-medium`, authenticated internal webhooks, clean VictoriaLogs stdout, and CI-gated auto-merges.
* **Operational**: Initial cluster rollout uses a two-stage Helm upgrade (`aiIncidentCommander.createWebhookSecret=true` -> verify `keep` -> `createWebhookSecret=false`) before Git push so `gitops-webhook` preserves live tokens.
