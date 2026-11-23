---
title: "AI Incident Commander v0.5: Diagnostic-First Soak, Sandboxed Runtime Isolation, and Human-Gated Autonomous SRE"
author: "Thang Hoang & Antigravity"
date: "2026-11-23T09:30:00+07:00"
draft: false
showToc: true
TocOpen: true
categories: ["Artificial Intelligence", "DevOps", "Observability", "SRE"]
tags: ["AI Incident Commander", "SRE", "Kubernetes", "Helm", "Grafana", "OpenTelemetry", "Antigravity", "Incident Response"]
---

Three months ago, we introduced [**AI Incident Commander (`v0.1`)**](/posts/ai-incident-commander/)—a Go service sitting inside our K3s `system` namespace that catches firing Grafana 11 alerts, inspects cluster state, and opens automated remediation pull requests via the Antigravity CLI (`agy`).

Running an autonomous SRE agent against a live production fleet for three months is the fastest way to learn where naive automation breaks. By `v0.3.0`, real alerts exposed nine subtle reliability, concurrency, and security bugs—and taught us a counterintuitive truth about incident response: **the smartest thing an autonomous SRE can do during the first 60 seconds of an alert is nothing.**

Across **`ADR-0056` (`v0.4.0`)** and **`ADR-0057` (`v0.5.0`–`v0.5.2`)**, we hardened the commander's runtime, isolated its credentials, embedded a pinned `helm` binary for drift-aware pre-diagnostics, added a cancellable `60s` soak gate, replaced blind auto-merging with a human gate (`AUTO_MERGE=false`), and scheduled a daily `07:15 ICT` fleet audit.

---

## 1. Post-Mortem: Nine Failure Modes From Three Months in Production

An operational audit of `ai-incident-commander` (`v0.3.0`) surfaced nine `P0`/`P1` defects in how the agent interacted with Prometheus, Kubernetes, Git, and `agy`:

1. **Prometheus Scraper Label Shadowing**: Alerts emitted from `kube-state-metrics` carried `pod="fleet-kube-state-metrics-..."` and `service="fleet-kube-state-metrics"` scraper labels that shadowed the real `deployment`, `statefulset`, `job_name`, or `persistentvolumeclaim` targets—poisoning PostgreSQL incident deduplication keys.
2. **Dead-End `AppFixer` Routing**: Infrastructure alerts in namespace `apps` (`category: workload|storage|node|endpoint`) fell into a dead-end `AppFixer` branch instead of opening Helm remediation PRs against the fleet repository.
3. **Pod-Restart Incident Amnesia**: Keeping `ActiveIncidents` solely in Go memory meant a commander pod restart silently dropped incoming `resolved` webhooks, leaving stale incidents open in PostgreSQL and GitHub.
4. **Concurrent Git Workspace Races**: Simultaneous webhook goroutines ran `git checkout` and `git pull` on the same local clone without a mutex.
5. **Unverified Auto-Merges & Missing PR CI**: Reviewer-approved PRs merged immediately without waiting for GitHub Actions (`WaitForPRChecks`), while `.github/workflows/deploy.yaml` originally ran only on `push` to `main`—leaving autonomous PRs with zero CI check runs.
6. **`root` Host Auth Pollution & MCP OOMs**: Mounting `/home/opc/.gemini` read-write as `root` polluted host CLI state and booted unrelated host MCP servers inside a `512Mi` memory limit, without `--disable-slash-commands` or a validated `AGY_MODEL`.
7. **Unauthenticated `/webhook` & Missing `/healthz`**: `/webhook` accepted unauthenticated requests, and probes checked TCP sockets instead of PostgreSQL readiness.
8. **Broken OTLP Logging**: Leaving `OTEL_EXPORTER_OTLP_ENDPOINT` unset dumped verbose OpenTelemetry span JSON straight into stdout and VictoriaLogs.
9. **Hair-Trigger PR Churn**: Firing immediately on transient rollout blips—without waiting to see if Kubernetes self-healed or comparing live Pod specs against Git Helm templates—generated noisy PRs for self-resolving events.

---

## 2. Runtime Sandboxing & CI-Gated PRs (`v0.4.0`, `ADR-0056`)

In `v0.4.0`, we eliminated the concurrency, security, and isolation gaps before adding higher-level diagnostic intelligence:

* **Read-Only Host Auth + Ephemeral `emptyDir` Isolation**: `Deployment/ai-incident-commander` now mounts `/home/opc/.gemini/antigravity-cli` **strictly read-only** at `/mnt/host-gemini-cli` (`AGY_HOST_AUTH_DIR=/mnt/host-gemini-cli`), while `/root/.gemini` is an ephemeral `emptyDir`. Before each `agy` invocation, the commander copies only `antigravity-oauth-token`, `installation_id`, and `settings.json`, and writes `{"mcpServers":{}}` to `/root/.gemini/config/mcp_config.json`. Combined with `--disable-slash-commands`, `AGY_MODEL=gemini-3.8-flash-medium`, and a raised `1536Mi` memory limit on `arm10`, `agy` starts fast, loads zero extraneous MCP tools, and never mutates host files as `UID 0`.
* **Grafana Bearer Auth & Retained Secrets (`ADR-0052`)**: Grafana 11 now authenticates every webhook POST using `authorization_scheme: Bearer` backed by retained Secret `ai-commander-webhook-secret` (`"helm.sh/resource-policy": "keep"`, `createWebhookSecret: false` by default).
* **Restart-Safe Reconciliation, Mutexes & `/healthz`**: Added workspace mutex locking around git/Fixer loops, idempotent scraper-label cleanup migrations, restart-safe debounced resolve locks, and a DB-aware HTTP `GET /healthz` probe.
* **Pull Request CI Gates & Clean OTLP Export**: Added `pull_request: branches: [ "main" ]` to `.github/workflows/deploy.yaml` so `WaitForPRChecks` blocks merges until `helm lint`, `terraform fmt`, and `pytest` architectural fitness gates turn green, and wired `OTEL_EXPORTER_OTLP_ENDPOINT` to `otel-collector.observability.svc.cluster.local:4317` (passing bare `host:port` via `otlptracegrpc.WithEndpoint(...)` in `v0.5.0` to silence DNS resolver warnings).

---

## 3. Diagnostic-First `60s` Soak & Pinned Helm Pre-Diagnostics (`v0.5.0`–`v0.5.2`)

Hardening `v0.4.0` stopped crashes and security leaks, but the commander still reacted too fast to transient noise and lacked Helm context during triage. **`ADR-0057`** transformed the pipeline into a **diagnostic-first, human-gated SRE state machine**:

```text
  Grafana 11 Firing Webhook (Bearer Auth Verified)
                     │
                     ▼
     ┌───────────────────────────────┐
     │  SOAKING (SOAK_DURATION=60s)  │◄─── Duplicate firing webhooks dropped
     │  WaitForSoak                  │───► `resolved` webhook cancels soak!
     └───────────────┬───────────────┘     (0 agy tokens, 0 GitHub issues)
                     │  60s elapsed & still firing
                     ▼
     ┌───────────────────────────────┐
     │  CheckWorkloadStatus          │───► Active rollout / already recovered?
     │  + Open Issue/PR Dedup (v0.5.1)│    Defer or suppress cleanly!
     └───────────────┬───────────────┘
                     │  Confirmed real incident
                     ▼
     ┌───────────────────────────────┐
     │  FetchDiagnosticBundle        │  Read-only kubectl + pinned helm v3.21.4
     │  (Zero Secret RBAC)           │  Live Pods/Svcs/Endpoints vs Git values.yaml
     └───────────────┬───────────────┘
                     │
                     ▼
     ┌───────────────────────────────┐
     │  agy Triage (AgyQueue, cap 1) │  3-Way Verdict Gate:
     │  gemini-3.8-flash-medium      │   ├─ VERDICT: IGNORE -> close/no-op
     └───────────────┬───────────────┘   ├─ VERDICT: ESCALATE_HUMAN -> issue only
                     │                   └─ VERDICT: FIX_VIA_PR (requires HIGH conf)
                     ▼
     ┌───────────────────────────────┐
     │  Fixer -> PR -> CI + Reviewer │──► AUTO_MERGE=false: assigned to human owner
     └───────────────────────────────┘
```

Three design choices in `v0.5.x` dramatically improved signal-to-noise:
1. **Cancellable `60s` Stabilization Soak**: Rolling restarts, brief image pulls, or momentary scrape blips frequently self-recover inside a minute. Entering `SOAKING` for `SOAK_DURATION=60s` drops duplicate firing payloads and aborts immediately if Grafana sends a `resolved` webhook—spending zero `agy` tokens and opening zero GitHub issues.
2. **Pinned `helm v3.21.4` + Zero-Secret Read-Only RBAC**: Installing `helm v3.21.4` alongside `kubectl` inside the container lets `FetchDiagnosticBundle` compare live Deployments, StatefulSets, Services, Endpoints, Events, and PVCs directly against Git `charts/vinhthang-fleet/values.yaml` and run real `helm lint` / `helm template` validation before invoking `agy`—while `ClusterRole/ai-incident-commander-reader` strictly excludes `secrets` RBAC.
3. **Strict 3-Way Verdict Gate & `AUTO_MERGE=false`**: Triage must emit an explicit `VERDICT: IGNORE`, `VERDICT: ESCALATE_HUMAN`, or `VERDICT: FIX_VIA_PR`. Any `FIX_VIA_PR` below `Confidence: HIGH`—or any `agy` execution error—downgrades automatically to `ESCALATE_HUMAN` without invoking Fixer. Even when Fixer opens a PR and both GitHub Actions CI and the Reviewer pass it, **`AUTO_MERGE=false`** leaves the final merge click to the human operator.

---

## 4. Scheduled `07:15 ICT` Daily `agy` Fleet Audits

Reactive alerting only tells you what broke—not what is slowly drifting. In `v0.5.0`, we added an authenticated `POST /daily-report` endpoint guarded by single-flight execution and serialized through the same `AgyQueue` (`async` worker channel cap `1`) so scheduled audits never contend with live incident triage.

Every morning at **`07:15 AM ICT`** (`15 0 * * *` UTC), `CronJob/ai-commander-daily-report` triggers the endpoint using `curlimages/curl:8.10.1`:

```sh
curl -sS --fail-with-body --max-time 25 -X POST \
  -H "Authorization: Bearer ${WEBHOOK_AUTH_TOKEN}" \
  "http://ai-incident-commander.system.svc.cluster.local:8085/daily-report"
```

*(A quick operational lesson captured in `v0.5.2`: omit `-f` when passing `--fail-with-body` in BusyBox/curl scripts so HTTP error bodies aren't swallowed silently.)*

The resulting read-only `agy` fleet health audit is published in two places simultaneously:
* **Private Engineering Journal (Memos)**: Written directly into `MEMOS_DB_DSN` (`public.memo`) so morning coffee starts with a concise cluster digest.
* **GitHub Issue Tracker**: Filed as `[Daily Fleet Check] YYYY-MM-DD` (labeled `daily-report`), **auto-closed immediately when `HEALTHY`**, or left open and assigned to the owner when `ATTENTION_NEEDED`.

Between `v0.4.0` runtime sandboxing and `v0.5.x` diagnostic-first soaking, AI Incident Commander has matured from an eager PR generator into a disciplined, evidence-backed junior SRE that respects human sign-off and sleeps quietly through transient noise.
