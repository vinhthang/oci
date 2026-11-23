# ADR-0061: Upgrade `ai-incident-commander` to `v0.6.0`, Extend Narrow Runtime Remediation RBAC, and Expose `/metrics`

* **Status**: 🟢 Accepted
* **Date**: 2026-11-24
* **Authors**: Thang Hoang & Antigravity

---

## Context

`ai-incident-commander` (`14608a48af`, published as `ghcr.io/vinhthang/ai-incident-commander@sha256:ded51700eaadf9ef6adeb5a909a1c392491cc37ee85344b33f144860a0986b46`) introduces Go-allowlisted runtime remediation (`ROLLOUT_RESTART` on `Deployment`/`StatefulSet` and `DELETE_FAILED_JOB` on finished failed `Job`s), proactive daily audit dispatch (`ENABLE_DAILY_PROACTIVE_FIX`, `DAILY_MAX_PROACTIVE_FIXES`), `VICTORIALOGS_URL` enrichment for `apps` error triage, and Prometheus `/metrics` exposition on port `8085`.

In `vinhthang/oci`, `ClusterRole/ai-incident-commander-reader` was previously strictly read-only (`get`, `list`, `watch`), causing live `ROLLOUT_RESTART` and `DELETE_FAILED_JOB` actions to return `runtime_rbac_denied` (`Forbidden`), and `aiIncidentCommander.image` was still pinned to `0.5.2`.

## Decision

1. **Pin `aiIncidentCommander` to `0.6.0` Multi-Arch Digest**:
   - Update `charts/vinhthang-fleet/values.yaml` to `tag: "0.6.0"` and `digest: sha256:ded51700eaadf9ef6adeb5a909a1c392491cc37ee85344b33f144860a0986b46`.
2. **Extend `ClusterRole/ai-incident-commander-reader` with Least-Privilege Write Verbs**:
   - Grant `["get", "list", "watch", "patch"]` exclusively on `apps` `["deployments", "statefulsets"]` (keeping `["replicasets", "daemonsets"]` strictly read-only).
   - Grant `["get", "list", "watch", "delete"]` on `batch` `["jobs", "cronjobs"]`.
   - Preserve zero write permissions on core `""` resources (`pods`, `pods/exec`, `nodes`, `persistentvolumeclaims`) and zero access to `secrets`.
   - Rely on Go code enforcement (`internal/k8s/remediate.go`) to block protected namespaces (`kube-system`, `kube-public`, `kube-node-lease`, `data`), stateful database workloads (`postgres`, `mongodb`, `redis`, `pulsar`, `etcd`), and self-restart (`system/ai-incident-commander`).
3. **Wire Configurable Runtime, Proactive & Observability Settings**:
   - Expose `VICTORIALOGS_URL`, `ENABLE_RUNTIME_REMEDIATION`, `RUNTIME_PROTECTED_NAMESPACES`, `RUNTIME_VERIFY_TIMEOUT`, `ENABLE_DAILY_PROACTIVE_FIX`, and `DAILY_MAX_PROACTIVE_FIXES` from `values.yaml` into `Deployment/ai-incident-commander`.
   - Annotate `Service/ai-incident-commander` with `prometheus.io/scrape: "true"`, `prometheus.io/port: "8085"`, and `prometheus.io/path: "/metrics"`.

## Consequences

### Positive
* Enables autonomous `ROLLOUT_RESTART` and failed-`Job` cleanup with post-action `kubectl rollout status` verification and `#AutoRemediation` reporting.
* Exposes `commander_*` Prometheus metrics for VictoriaMetrics scraping without adding new ports or Secrets.
* Keeps `secrets`, `nodes`, `pods/exec`, and core data namespaces protected under least-privilege RBAC + Go allowlists.

### Negative / Trade-offs
* `ClusterRole/ai-incident-commander-reader` retains its historical `-reader` resource name to preserve continuity across Helm upgrades while holding narrow `patch`/`delete` verbs on `deployments`/`statefulsets`/`jobs`/`cronjobs`.
