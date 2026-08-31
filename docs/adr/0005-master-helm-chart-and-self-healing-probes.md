# ADR-0005: Master Umbrella Helm Chart & Self-Healing Probes

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-24
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
Managing 15+ separate raw Kubernetes YAML files created configuration drift, made global version upgrades tedious, and lacked declarative consistency across memory limits, image tags, and NodePorts.

---

## 2. Decision
1. **Master Umbrella Helm Chart (`charts/vinhthang-fleet/`)**:
   * Bundled all 15 microservices, RBAC bindings, ConfigMaps, and CronJobs into a single cohesive chart (`vinhthang-fleet-1.0.x`).
   * Centralized all resource limits, NodePorts (`30001-30009`), and image repositories in [`values.yaml`](../../charts/vinhthang-fleet/values.yaml).
2. **Self-Healing Kubernetes Health Probes**:
   * Configured `livenessProbe` and `readinessProbe` across 100% of workloads:
     * HTTP health checks for web APIs (`/api/ping`, `/api/health`, `/dashboard`, `/ping`).
     * `pg_isready` exec probes for PostgreSQL 18.
     * TCP socket probes for binary/gRPC services.
   * Kubernetes automatically restarts hung containers with zero manual intervention.
3. **1-Command Deployments**:
   * Upgrading the entire fleet is executed via:
     ```bash
     helm upgrade --install fleet ./charts/vinhthang-fleet --kube-context oci-k3s
     ```

---

## 3. Consequences
### Positive:
* Single source of truth for all fleet configurations in `values.yaml`.
* Built-in self-healing and automatic recovery from memory leaks or deadlocks.
* Seamless version upgrades and rollbacks via `helm history fleet`.

### Negative / Trade-offs:
* Requires Helm 3/4 CLI for deployment operations.
