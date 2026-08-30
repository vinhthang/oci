# ADR-0031: Expansion of Grafana 11 Unified Alerting Suite for Autonomous AI Incident Response

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-30
* **Authors**: Thang Hoang & Antigravity
* **Scope**: Observability / Unified Alerting / AI Incident Commander

---

## 1. Context & Problem Statement
Following the deployment of `ai-incident-commander` and `kube-state-metrics` (ADR-0027), our Grafana Unified Alerting engine only contained a single provisioned rule (`PodCrashLoopBackOff`). 

Critical failure modes—such as Out-Of-Memory container kills (`OOMKilled`), stalled rollouts (`DeploymentReplicasUnavailable`), unschedulable pending pods (`PodPendingTooLong`), node-level memory/disk pressure on 1GB edge nodes, and synthetic endpoint HTTP outages—were not codified as declarative alerting rules. Consequently, the AI Incident Commander was blind to non-crashloop outages across the fleet.

---

## 2. Decision
We have expanded `grafana-alert-rules` in `charts/vinhthang-fleet/templates/grafana-alert-rules.yaml` into a comprehensive 7-rule alerting suite partitioned into 3 logical groups:

### 1. Kubernetes Workload Health (Actionable by AI Fixer Minion)
1. **`PodCrashLoopBackOff`**: `rate(kube_pod_container_status_restarts_total[5m]) > 0` (for 1m, critical).
2. **`PodOOMKilled`**: `kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1` (instant, critical). Triggers Fixer to evaluate and adjust memory limits in `values.yaml`.
3. **`DeploymentReplicasUnavailable`**: `kube_deployment_status_replicas_unavailable > 0` (for 5m, warning). Detects stuck rollouts and misconfigurations.
4. **`PodPendingTooLong`**: `kube_pod_status_phase{phase="Pending"} == 1` (for 5m, warning). Catches unschedulable pods due to CPU/RAM exhaustion or missing PVCs.

### 2. Kubernetes Node Health (1GB RAM Edge Node Protection)
5. **`NodeMemoryPressure`**: `kube_node_status_condition{condition="MemoryPressure",status="true"} == 1` (for 2m, critical). Protects `amd10`, `amd11`, and `gce10` from kernel freezing.
6. **`NodeDiskPressure`**: `kube_node_status_condition{condition="DiskPressure",status="true"} == 1` (for 2m, critical). Warns before container rootfs / log volumes exhaust host disks.

### 3. Synthetic Ingress SLA (Zero-Trust Endpoint Probing)
7. **`EndpointDown`**: `httpcheck_status{http_status_class="2xx"} == 0` (for 1m, critical). Evaluates OpenTelemetry `httpcheck` probes across all `*.vinhthang.dev` endpoints to catch Caddy reverse proxy or ingress TLS failures instantly.

---

## 3. Consequences
### Positive:
* **Full-Spectrum Incident Coverage**: AI Incident Commander receives real-time telemetry and alerts for all primary failure modes across infrastructure, workloads, and public SLAs.
* **Declarative Provisioning**: 100% of alert rules and contact points are declared in Helm (`grafana-alert-rules.yaml` & `grafana.yaml`) with zero manual Grafana UI configuration.
* **Safe Autonomous Triaging**: Complements the upgraded SRE Triage Minion prompt with clear severity and category classification.

### Negative / Trade-offs:
* Alert evaluation frequency increases slightly in Grafana (all rules evaluated at 1m intervals against VictoriaMetrics TSDB), but resource impact remains negligible (< 5MB RAM).
