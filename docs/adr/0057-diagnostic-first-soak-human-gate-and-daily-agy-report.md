# ADR-0057: Diagnostic-First Soak, Human-Gated PRs, and Scheduled Daily `agy` Fleet Report (`v0.5.0`)

* **Status**: Accepted
* **Date**: 2026-11-20

## Context

Even after the `v0.4.0` reliability and isolation fixes (ADR-0056), [`ai-incident-commander`](https://github.com/vinhthang/ai-incident-commander) acted immediately on every firing alert, lacked an in-container `helm` binary for pre-triage Helm chart/values drift verification, lacked structured Service & Endpoints verification before invoking `agy`, allowed errors or low-confidence triage outputs to fall through toward Fixer, auto-merged approved PRs without human sign-off, and had no scheduled daily SRE audit report.

## Decision

1. **Upgrade to `v0.5.0` (`ghcr.io/vinhthang/ai-incident-commander`) with Pinned `helm v3.21.4`**:
   - Install `helm v3.21.4` inside the commander image alongside `kubectl` so both pre-triage diagnostics and Fixer/Reviewer run real `helm lint`/`helm template` checks cleanly.
   - Maintain **zero Secret RBAC** on `ClusterRole/ai-incident-commander-reader`; live checks inspect Nodes, Pods, Deployments/StatefulSets, Services, Endpoints, Events, PVCs, Jobs, and Git Helm definitions read-only.
2. **Stabilization Soak & Pre-Triage Rollout/Recovery Gate**:
   - Configure `SOAK_DURATION=60s` (`WaitForSoak` in `SOAKING` state). Duplicate firing webhooks are dropped, and any incoming `resolved` webhook cancels the soak channel immediately without invoking `agy` or opening GitHub issues.
   - Run `CheckWorkloadStatus` after soak to defer active Deployment/StatefulSet rollouts and suppress alerts whose target workload or endpoint already recovered.
3. **Structured Service + Helm Pre-Diagnostics & 3-Way Verdict Gate (`AUTO_MERGE=false`)**:
   - Collect `FetchDiagnosticBundle` (Services/Endpoints, Pod logs/describe/previous logs, live Deployment limits/images vs Git `charts/vinhthang-fleet/values.yaml` and templates, `helm lint`, and recent git history) before running `agy`.
   - Enforce an explicit 3-way conclusion (`VERDICT: IGNORE`, `VERDICT: ESCALATE_HUMAN`, `VERDICT: FIX_VIA_PR`). `FIX_VIA_PR` is downgraded to `ESCALATE_HUMAN` unless `Confidence: HIGH`; unrecognized outputs and `agy` errors halt/escalate without invoking Fixer.
   - Set `AUTO_MERGE=false` by default so CI-green, Reviewer-approved PRs are assigned to `GITHUB_OWNER` for final human merge.
4. **Scheduled Daily Fleet Check & Report (`CronJob/ai-commander-daily-report`)**:
   - Expose authenticated `POST /daily-report` (`WEBHOOK_AUTH_TOKEN`, single-flight guarded) queued via `AgyQueue` so daily audits never race live incidents.
   - Schedule `CronJob/ai-commander-daily-report` in namespace `system` at `15 0 * * *` (07:15 AM ICT daily) using `curlimages/curl:8.10.1`.
   - Deliver the `agy` read-only audit report both privately to Memos (`MEMOS_DB_DSN` → `public.memo`) and to GitHub (`[Daily Fleet Check] YYYY-MM-DD`, labeled `daily-report`, auto-closed when `HEALTHY` or left open and assigned when `ATTENTION_NEEDED`).
5. **OTLP Exporter Target Fix**:
   - Pass bare `host:port` endpoints explicitly via `otlptracegrpc.WithEndpoint(...)` so tracing exports cleanly to `otel-collector.observability.svc.cluster.local:4317` without `dns resolver: missing address` warnings.

## Consequences

* **Positive**: Eliminates premature PR churn on transient rollouts/blips, grounds triage decisions in real Service + Helm evidence, enforces human approval before merge (`AUTO_MERGE=false`), and delivers daily automated `agy` fleet health audits into Memos and GitHub.
* **Operational**: Configurable via Helm values (`aiIncidentCommander.soakDuration`, `aiIncidentCommander.autoMerge`, `aiIncidentCommander.dailyReport.*`).
