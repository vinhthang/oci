# ADR-0018: Cluster-Wide Namespace Domain Partitioning (`data`, `apps`, `observability`, `system`)

## Status
🟢 **Accepted & Implemented**

## Context
As the **Vinh Thang Cloud & AI Fleet (`vinhthang.dev`)** expanded to host over 22+ microservices, databases, streaming nodes, AI engines, and observability agents, maintaining all resources within the single unpartitioned `default` Kubernetes namespace introduced operational friction:
1. **Security & Blast Radius**: Database secrets (`postgres-secret`, API keys) and stateful PersistentVolumeClaims shared the same scope as stateless web applications.
2. **Observability Isolation**: Telemetry collection daemons (Vector, OTel, VictoriaMetrics) mixed with end-user applications.
3. **Multi-Domain Scalability**: Future planned components (Redis HA cluster, Apache Pulsar streaming broker) require dedicated data boundaries.

## Decision
We partitioned the entire Kubernetes cluster into **4 distinct, isolated domain namespaces**:

1. **`data` (Persistence, Caching & Streaming)**:
   * Hosts `postgres-primary` (`arm10`), `postgres-replica` (`amd11`), and `pgpool` (`amd11`).
   * Houses dedicated StorageClasses, `PersistentVolumes`, and `PersistentVolumeClaims` (`postgres-primary-pvc`, `postgres-replica-pvc`).
   * Restricts `postgres-secret` strictly to database authentication.
   * Internal Service FQDN: `postgres.data.svc.cluster.local:5432` (or `postgres.data:5432`).

2. **`apps` (User-Facing Applications & AI Runtimes)**:
   * Hosts `anythingllm`, `memos`, `umami`, `vietcalendar`, `vaultwarden`, `navidrome`, `filebrowser`.
   * Accesses databases via cross-namespace FQDN `postgres.data:5432`.

3. **`observability` (Metrics, Logs & Telemetry Stack)**:
   * Hosts `victoriametrics`, `victorialogs`, `grafana`, `otel-collector`, and `vector` (cluster-wide log harvest DaemonSet).
   * Ingest endpoint: `http://victorialogs.observability.svc.cluster.local:9428`.

4. **`system` (Platform Ingress, SSO & Automation)**:
   * Hosts `central-oauth2-proxy`, `gitops-webhook`, and scheduled automation CronJobs (`daily-ai-briefing`, `nightly-fleet-backup`, `anythingllm-indexer-cron`).

## Consequences

### Positive
* **Domain Cleanliness**: Clear separation of concerns between stateful data, user applications, platform automation, and monitoring.
* **Least-Privilege Security**: Secrets and RBAC policies are strictly scoped to their respective namespaces.
* **Zero Edge Impact**: Caddy reverse proxy communicates via global cluster NodePorts (`10.0.0.216:3000X`), ensuring seamless edge routing without reconfiguration.
* **Zero Data Loss**: Host-backed PersistentVolumes dynamically re-bound to the `data` namespace with 100% data integrity.

### Operational Notes
* Inter-namespace service discovery must use domain FQDNs (e.g. `postgres.data`, `victoriametrics.observability`, `anythingllm.apps`).
