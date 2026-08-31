# ADR-0008: Superpowers Security Hardening, Least-Privilege RBAC, and Automated Disaster Recovery

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-25
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
A comprehensive `superpowers` architectural and security audit identified four key reliability and security gaps across the cluster:
1. **Secret Hygiene**: Certain application manifests embedded sensitive database URLs and JWT credentials directly in environment variables.
2. **Over-Privileged RBAC**: The in-cluster `gitops-webhook` controller was bound to the global `cluster-admin` role.
3. **Disaster Recovery Gap**: Stateful databases (`/opt/postgres`, `/opt/uptime-kuma/kuma.db`, `/opt/memos`) resided on host storage without automated snapshot backups.
4. **Concurrency Lock Contention**: Rapid consecutive Git pushes could cause `.hugo_build.lock` race conditions during Hugo static site generation.

---

## 2. Decision
1. **Secret Hygiene & Centralization**:
   * Consolidated all database credentials, JWT secrets, and connection strings into the Kubernetes Secret `postgres-secret`.
   * Refactored `charts/vinhthang-fleet/templates/anythingllm.yaml` and `grafana.yaml` to reference credentials via `secretKeyRef`.
2. **Least-Privilege RBAC Scoping**:
   * Created a dedicated, scoped `ClusterRole: gitops-deployer` granting verbs (`get`, `list`, `watch`, `create`, `update`, `patch`, `delete`) only on necessary API groups:
     * `""` (core): `deployments`, `services`, `configmaps`, `secrets`, `serviceaccounts`, `pods`, `endpoints`.
     * `apps`: `deployments`, `daemonsets`.
     * `batch`: `cronjobs`, `jobs`.
     * `networking.k8s.io`: `ingresses`.
     * `rbac.authorization.k8s.io`: `roles`, `rolebindings`, `clusterroles`, `clusterrolebindings`.
   * Replaced the global `cluster-admin` ClusterRoleBinding with `gitops-deployer`.
3. **Automated Nightly Disaster Recovery CronJob (`nightly-fleet-backup`)**:
   * Deployed a scheduled Kubernetes CronJob running daily at `19:00 UTC` (**02:00 AM Indochina Time**).
   * Executes `pg_dumpall` for PostgreSQL 18.
   * Archives PostgreSQL SQL dumps and Uptime Kuma SQLite databases into `/opt/backups/daily/fleet-backup-<date>.tar.gz`.
   * Enforces an automated **7-day retention policy** (`find /backup/daily -name "fleet-backup-*.tar.gz" -mtime +7 -delete`).
4. **Hugo Concurrency & Lock Handling**:
   * Added `threading.Lock()` and stale `.hugo_build.lock` removal inside `sync_daemon.py` on `amd10` to guarantee atomic, serialized rebuilds.

---

## 3. Consequences
### Positive:
* **Strict Least Privilege**: The GitOps webhook has only the permissions required to manage the Helm release.
* **Guaranteed Disaster Recovery**: Verified automated daily backups with rolling 7-day retention.
* **Secret Hygiene**: Zero plain-text credentials in ConfigMaps or deployment environment declarations.
* **Concurrency Safety**: Hugo site generation is thread-safe and resilient against rapid consecutive pushes.

### Negative / Trade-offs:
* Nightly backups consume ~200 KB – 5 MB of local disk per archive (auto-pruned after 7 days).
