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
| [**ADR-0018**](adr/0018-cluster-wide-namespace-domain-partitioning.md) | **Cluster-Wide Namespace Domain Partitioning (`data`, `apps`, `observability`, `system`)** | 🟢 Accepted | Architecture / Kubernetes | Partition 22+ microservices into 4 isolated domains with scoped RBAC, PVC binding, and zero downtime. |
| [**ADR-0019**](adr/0019-compact-apache-pulsar-and-in-memory-redis-data-infrastructure.md) | **Compact Apache Pulsar & In-Memory Redis Data Infrastructure** | 🟢 Accepted | Data & Messaging | Deploy compact Pulsar (<400M RAM on `arm10`) and pure in-memory Redis (384M on `amd11`) in `data` namespace. |
| [**ADR-0020**](adr/0020-hybrid-cloud-tailscale-node-expansion.md) | **Hybrid-Cloud External Node Integration for 20+ Java Microservices via Tailscale** | 🟢 Accepted | Architecture / Networking | Expand cluster capacity with 32GB physical host (`oracle10`) over encrypted Tailscale WireGuard mesh. |

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
