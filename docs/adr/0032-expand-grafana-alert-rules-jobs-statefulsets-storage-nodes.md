# ADR-0032: Expansion of Grafana Alert Rules for Batch Jobs, StatefulSets, Storage Binding, and Node Liveness

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-31
* **Authors**: Thang Hoang & Antigravity
* **Scope**: Observability / Unified Alerting / AI Incident Commander

---

## 1. Context & Problem Statement
Following an audit of failure telemetry and observability blind spots across the cluster, several critical failure modes were identified that did not trigger any Grafana alert rules, preventing the AI Incident Commander from taking proactive action:
1. **CronJob & Batch Job Failures** (`JobFailed`): Daily backups (`nightly-fleet-backup`), AI vector embeddings (`anythingllm-indexer`), and daily briefings (`daily-briefing`) run as batch Jobs. When a script fails or crashes, it completes in a `Failed` state without creating a permanently restarting Deployment pod.
2. **StatefulSet Replica Degradation** (`StatefulSetReplicasUnavailable`): Relational databases, message brokers, and caches (`postgres`, `pulsar`, `redis`) run as StatefulSets. Replica unavailabilities were not tracked by the `DeploymentReplicasUnavailable` alert.
3. **Unbound Storage & PVC Failures** (`PersistentVolumeClaimUnbound`): PVCs failing to bind due to storage class mismatches, missing local volumes, or node affinity conflicts hung in `Pending` or `Lost` without generating pod crash alerts.
4. **Node Outages** (`NodeNotReady`): Worker node disconnections (`amd11`, `gce10`) or kubelet crashes were not explicitly alerted.
5. **False Positive Ingress Alerting on HTTP 3xx Redirects**: The synthetic `EndpointDown` probe alerted on non-2xx codes, treating legitimate HTTP 302/307 redirects as outages.

---

## 2. Decision

We expanded the declarative alerting suite in `charts/vinhthang-fleet/templates/grafana-alert-rules.yaml` with the following rules:

### 1. Workload & Batch Alerts
* **`StatefulSetReplicasUnavailable`**: `(kube_statefulset_status_replicas - kube_statefulset_status_replicas_ready) > 0` (for 3m, critical).
* **`JobFailed`**: `kube_job_status_failed > 0` (for 0s, critical). Catches CronJob script failures immediately.

### 2. Storage Alerts
* **`PersistentVolumeClaimUnbound`**: `kube_persistentvolumeclaim_status_phase{phase!="Bound"} == 1` (for 3m, critical). Catches storage provisioning/binding errors before pods attempt to mount.

### 3. Node Health Alerts
* **`NodeNotReady`**: `kube_node_status_condition{condition="Ready",status="true"} == 0` (for 2m, critical). Alerts immediately if a Kubernetes node drops out of the cluster.

### 4. Synthetic Ingress SLA Refinement
* Updated `EndpointDown` expression to: `(httpcheck_status{http_status_class="2xx"} == 0) and (httpcheck_status{http_status_class="3xx"} == 0)` to allow valid HTTP redirects while strictly alerting on 4xx/5xx errors or network drops.

---

## 3. Consequences

### Positive:
* **Zero Blind Spots**: 100% of workload types (Deployments, StatefulSets, Batch Jobs, Storage PVCs, Node Conditions, Ingress Probes) are now actively monitored and alerted to the AI Incident Commander.
* **Proactive Storage & Batch Triage**: The AI Incident Commander can now diagnose CronJob failures and PVC binding conflicts before dependent workloads fail.

### Negative:
* Number of active alerting rules in Grafana increases to 11, evaluated concurrently with VictoriaMetrics TSDB with minimal CPU/RAM overhead (< 2MB).
