# 🏛️ Architecture Decision Records (ADRs) & Technical Design Index

> **IMPORTANT FOR AI AGENTS & DEVELOPERS**:
> Before making any infrastructural or codebase modifications to this repository, **you MUST review these Architecture Decision Records (ADRs)** to understand the core design principles, memory constraints, and networking boundaries of the **Vinh Thang Cloud & AI Fleet (`vinhthang.dev`)**.

---

## 📚 Master ADR Registry

| ADR Number | Title | Status | Primary Component | Key Rationale |
| :--- | :--- | :---: | :--- | :--- |
| [**ADR-0001**](adr/0001-hybrid-k3s-multi-arch-topology.md) | **3-Node Hybrid Multi-Architecture K3s Cluster** | 🟢 Accepted | K3s / Infrastructure | Unify ARM64 (10GB) + AMD64 (1GB) into 1 cluster with strict nodeSelectors. |
| [**ADR-0002**](adr/0002-caddy-edge-gateway-and-google-oauth2-sso.md) | **Caddy Edge Gateway & Google OAuth2 SSO** | 🟢 Accepted | Security / Ingress | Single public IPv4 entrypoint with cookie-based forward_auth SSO. |
| [**ADR-0003**](adr/0003-victoriametrics-and-victorialogs-observability.md) | **Ultra-Lightweight Observability (VictoriaMetrics + VictoriaLogs)** | 🟢 Accepted | Observability / Telemetry | PromQL + LogsQL full-text streaming in < 80MB total RAM vs heavy Prometheus/Loki. |
| [**ADR-0004**](adr/0004-postgresql-18-pgvector-and-decoupled-state.md) | **PostgreSQL 18.6 `pgvector` & Decoupled State Architecture** | 🟢 Accepted | Databases / Persistence | Persistent AI vector embeddings + relational storage; stateless in-memory VietCalendar. |
| [**ADR-0005**](adr/0005-master-helm-chart-and-self-healing-probes.md) | **Master Umbrella Helm Chart & Self-Healing Probes** | 🟢 Accepted | Packaging / Reliability | Single `values.yaml` control plane with automated liveness/readiness recovery. |
| [**ADR-0006**](adr/0006-in-cluster-gitops-webhook-and-blog-pipeline.md) | **In-Cluster GitOps Webhook & Event-Driven Hugo Rebuild** | 🟢 Accepted | CI/CD / GitOps | Zero-touch deployment on `git push` via in-cluster webhook controller in 1.4s. |
| [**ADR-0007**](adr/0007-autonomous-daily-ai-briefing-cronjob.md) | **Autonomous Daily AI Briefing Pipeline** | 🟢 Accepted | AI / Automation | Daily 07:00 AM VN Time CronJob querying VietCalendar, telemetry, and tech briefs. |
| [**ADR-0008**](adr/0008-superpowers-security-hardening-rbac-and-disaster-recovery.md) | **Superpowers Security Hardening, Scoped RBAC & Disaster Recovery** | 🟢 Accepted | Security / Reliability | Scoped RBAC (`gitops-deployer`), secretKeyRef hygiene, and automated nightly backups. |
| [**ADR-0009**](adr/0009-migrate-promtail-to-vector-rust-log-shipper.md) | **Migration from Promtail (EOL) to Vector (Rust) Log Harvester** | 🟢 Accepted | Logging / Rust | 50% memory reduction (< 15MB RAM), native K8s enrichment, and high-speed VictoriaLogs streaming. |
| [**ADR-0010**](adr/0010-consolidate-uptime-monitoring-into-grafana.md) | **Consolidation of Synthetic Uptime Monitoring into Grafana 11** | 🟢 Accepted | Observability / Telemetry | Retired Uptime Kuma; unified HTTP/SSL probing into OTel Collector + Grafana 11. |
| [**ADR-0011**](adr/0011-deploy-vaultwarden-password-manager.md) | **Deployment of Vaultwarden Self-Hosted Password Manager** | 🟢 Accepted | Security / Passwords | Rust Bitwarden (<30MB RAM) on `amd11` with zero-knowledge encryption & client sync. |
| [**ADR-0012**](adr/0012-gitops-automated-edge-caddyfile-sync.md) | **GitOps Automated Edge Caddyfile Synchronization** | 🟢 Accepted | GitOps / Ingress | Declarative `caddy/Caddyfile` in Git with automated edge sync & hot-reload. |
| [**ADR-0013**](adr/0013-private-subnet-isolation-and-nat-gateway.md) | **Private Subnet Isolation & NAT Gateway Architecture** | 🟢 Accepted | Networking / Security | Isolate `arm10`/`amd11` in private subnet with no public IPs; NAT Gateway egress + ProxyJump. |
| [**ADR-0014**](adr/0014-cross-cloud-gcp-always-free-oracle-linux-10-node.md) | **Cross-Cloud Topology & GCP Always Free Oracle Linux 10 Node (`gce10`)** | 🟢 Accepted | Multi-Cloud / Infrastructure | Expand fleet to GCP Always Free ($0/mo) with Oracle Linux 10 UEK, RAM hardening, and 140MB/s storage. |
| [**ADR-0015**](adr/0015-postgresql-ha-cluster-pgpool-read-write-splitting.md) | **PostgreSQL 18 HA Cluster & Pgpool-II Read/Write Splitting** | 🟢 Accepted | Databases / High Availability | 2-Node streaming replication + transparent read/write query splitting via Pgpool. |
| [**ADR-0016**](adr/0016-active-active-geo-distributed-dual-edge-blog.md) | **Active-Active Geo-Distributed Dual-Edge Ingress for Hugo Blog** | 🟢 Accepted | Multi-Cloud / Ingress | Dual-continent edge (Tokyo `amd10` + Iowa `gce10`) with <15ms global latency and zero-downtime failover. |
| [**ADR-0017**](adr/0017-strict-exit-codes-for-ai-incident-commander.md) | **Strict Exit Codes for AI Incident Commander Telemetry** | 🟢 Accepted | Observability / GitOps | Forbid `|| true` in webhooks and cronjobs to ensure AI Incident Commander can reliably catch failures via Grafana `CrashLoopBackOff` alerts. |
| [**ADR-0018**](adr/0018-cluster-wide-namespace-domain-partitioning.md) | **Cluster-Wide Namespace Domain Partitioning (`data`, `apps`, `observability`, `system`)** | 🟢 Accepted | Architecture / Kubernetes | Partition 22+ microservices into 4 isolated domains with scoped RBAC, PVC binding, and zero downtime. |
| [**ADR-0019**](adr/0019-compact-apache-pulsar-and-in-memory-redis-data-infrastructure.md) | **Compact Apache Pulsar & In-Memory Redis Data Infrastructure** | 🟢 Accepted | Data & Messaging | Deploy compact Pulsar (<400M RAM on `arm10`) and pure in-memory Redis (384M on `amd11`) in `data` namespace. |
| [**ADR-0020**](adr/0020-hybrid-cloud-tailscale-node-expansion.md) | **Hybrid-Cloud External Node Integration for 20+ Java Microservices via Tailscale** | 🔴 Deprecated | Architecture / Networking | Expand cluster capacity with 32GB physical host (`oracle10`) over encrypted Tailscale WireGuard mesh. |
| [**ADR-0021**](adr/0021-weaviate-vector-database-kubernetes-migration.md) | **Migration of Weaviate Vector Database & Native MCP Engine to Kubernetes (`ai` Namespace on `arm10`)** | 🟢 Accepted | AI / Database | Migrate standalone Weaviate vector engine from Docker to 24/7 cloud node `arm10` under dedicated `ai` namespace with Secret hygiene. |
| [**ADR-0022**](adr/0022-private-tailscale-only-perimeter-for-weaviate.md) | **Private Tailscale-Only Perimeter for Weaviate** | 🟢 Accepted | Network / Security | Ensure Weaviate is only accessible via Tailscale without public OAuth overhead. |
| [**ADR-0023**](adr/0023-optional-postgresql-read-replica-with-primary-fallback.md) | **Optional PostgreSQL Read Replica with Primary Fallback** | 🟢 Accepted | Database | Demote read replica to optional, failing back to primary if unhealthy. |
| [**ADR-0024**](adr/0024-deploy-apache-pulsar-helm-chart-on-oracle10-node.md) | **Deploy Apache Pulsar Helm Chart on oracle10 Node** | 🔴 Deprecated | Infrastructure | Use external node oracle10 for Apache Pulsar due to memory constraints. |
| [**ADR-0025**](adr/0025-switch-k3s-flannel-backend-to-wireguard-native.md) | **Switch K3s Flannel Backend to Wireguard-Native** | 🔴 Deprecated | Network | Change K3s Flannel to wireguard-native to fix cross-node Tailscale/VCN overlay routing. |
| [**ADR-0026**](adr/0026-relocate-postgresql-replica-redis-memory-optimization.md) | **Relocate PostgreSQL Replica, Pgpool, and Redis** | 🟢 Accepted | Architecture / Infrastructure | Move heavy workloads off 1GB amd11 to arm10 and oracle10 to prevent kernel OOM crashes. |
| [**ADR-0027**](adr/0027-deploy-kubestatemetrics-vmagent.md) | **Deploy Kube-State-Metrics & vmagent** | 🟢 Accepted | Observability | Deployed vmagent and KSM for native K8s metric collection. |
| [**ADR-0028**](adr/0028-taint-and-isolate-external-node-oracle10.md) | **Taint & Isolate External Node `oracle10`** | 🔴 Deprecated | Architecture / Stability | Isolate 32GB external node behind `NoSchedule` taint to prevent overlay failure cascades. |
| [**ADR-0029**](adr/0029-remove-oracle10-from-k3s-cluster.md) | **Remove External Node `oracle10` from K3s Cluster** | 🟢 Accepted | Architecture / Infrastructure | Decommission the 32GB external node to simplify network topology and migrate workloads to internal nodes. |
| [**ADR-0030**](adr/0030-revert-k3s-flannel-to-vxlan.md) | **Revert K3s Flannel Backend to VXLAN** | 🟢 Accepted | Network | Revert K3s Flannel backend from wireguard-native back to vxlan since oracle10 is removed. |
| [**ADR-0031**](adr/0031-expand-grafana-unified-alerting-suite.md) | **Expansion of Grafana 11 Unified Alerting Suite for Autonomous AI Incident Response** | 🟢 Accepted | Observability / Alerting | Declare comprehensive 7-rule alerting suite for workload health, node pressure, and endpoint SLAs. |

---

## 🏛️ System Invariants & Golden Rules for Future Agents

1. **Hardware Memory Boundaries**:
   * `amd10` (Edge Gateway), `amd11` (Worker), and `gce10` (GCP Worker/Edge) are strictly capped at **1 GB RAM**. Never schedule heavy Node.js or Java containers on these nodes.
   * `arm10` (Control Plane) has **12 GB RAM**. All relational databases, AI vector runtimes, and observability TSDBs must be pinned to `arm10` (`nodeSelector: kubernetes.io/hostname: arm10`).
2. **Mandatory Helm-Only Kubernetes Policy**:
   * **ALL Kubernetes workload changes, deployments, configs, and updates MUST strictly use the Master Umbrella Helm Chart (`charts/vinhthang-fleet/`) and `values.yaml`**.
   * Never apply ad-hoc raw YAML or run imperative `kubectl create/apply` for workloads. Always run `helm upgrade fleet ./charts/vinhthang-fleet`.
3. **Mandatory Terraform-First Infrastructure Policy**:
   * **ALL cloud instance modifications, shapes, boot volume sizes, subnets, and security lists MUST be managed and modified via Terraform (`main.tf`, `variables.tf`, etc.)**.
   * Declare infrastructure changes declaratively via Terraform instead of manual cloud console edits.
4. **Single Sign-On Requirement**:
   * Any new web dashboard or administrative interface must be placed behind Caddy Google OAuth2 Forward-Auth (`auth.vinhthang.dev`) to prevent credential sprawl and public exposure.
5. **Declarative Ingress Rule**:
   * All edge subdomain routing, TLS termination, and reverse-proxying MUST be maintained directly in [`caddy/Caddyfile`](../caddy/Caddyfile). Never edit `/etc/caddy/Caddyfile` manually on `amd10` or `gce10`.
6. **Exact Semantic Versioning**:
   * Always search and pin exact semantic version tags for container images in `values.yaml` (e.g. `1.37.2-alpine`) — never deploy floating tags like `latest`.
7. **Disaster Recovery**:
   * All stateful host directories are located under `/opt/<service>` on the respective nodes and backed up daily via `nightly-fleet-backup`.
8. **Network Perimeter Isolation**:
   * `amd10` and `gce10` are the **public edge gateways** (`152.70.101.162` and `34.61.16.208`). `arm10` and `amd11` reside in the **Private Subnet (`10.0.1.0/24`)** with zero public IP addresses, routing outbound internet traffic via the OCI NAT Gateway and accepting administrative SSH traffic strictly via `ProxyJump` through `amd10`.
9. **Port Allocation Governance (Avoid Port 8080)**:
   * **NEVER USE GENERIC PORT `8080`**: Port `8080` is strictly forbidden for any new custom microservice, daemon, webhook listener, or container. `8080` is a notorious collision magnet across Kubernetes, Caddy, Traefik, Pulsar Admin, and Java runtimes.
   * **Explicit Dedicated Port Allocation**: Always assign explicit dedicated ports (e.g. `8085` for AI Commander, `8088`, or specific NodePort ranges `30001–30015`).
   * **Configurable Ports & AI Models**: Never hardcode listening ports, webhook targets, or AI model strings (`GEMINI_MODEL`, `PORT`). Always make them configurable via Helm `values.yaml` and environment variables with verified defaults.

