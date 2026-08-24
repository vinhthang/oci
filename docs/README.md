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
| [**ADR-0004**](adr/0004-postgresql-18-pgvector-and-decoupled-state.md) | **PostgreSQL 18.6 `pgvector` & Decoupled State Architecture** | 🟢 Accepted | Databases / Persistence | Persistent AI vector embeddings + relational storage; isolated SQLite for Uptime Kuma. |
| [**ADR-0005**](adr/0005-master-helm-chart-and-self-healing-probes.md) | **Master Umbrella Helm Chart & Self-Healing Probes** | 🟢 Accepted | Packaging / Reliability | Single `values.yaml` control plane with automated liveness/readiness recovery. |
| [**ADR-0006**](adr/0006-in-cluster-gitops-webhook-and-blog-pipeline.md) | **In-Cluster GitOps Webhook & Event-Driven Hugo Rebuild** | 🟢 Accepted | CI/CD / GitOps | Zero-touch deployment on `git push` via in-cluster webhook controller in 1.4s. |
| [**ADR-0007**](adr/0007-autonomous-daily-ai-briefing-cronjob.md) | **Autonomous Daily AI Briefing Pipeline** | 🟢 Accepted | AI / Automation | Daily 07:00 AM VN Time CronJob querying VietCalendar, telemetry, and tech briefs. |
| [**ADR-0008**](adr/0008-superpowers-security-hardening-rbac-and-disaster-recovery.md) | **Superpowers Security Hardening, Scoped RBAC & Disaster Recovery** | 🟢 Accepted | Security / Reliability | Scoped RBAC (`gitops-deployer`), secretKeyRef hygiene, and automated nightly backups. |

---

## 🏛️ System Invariants & Golden Rules for Future Agents

1. **Hardware Memory Boundaries**:
   * `amd10` (Edge) & `amd11` (Worker) have **1 GB RAM each**. Never schedule heavy Node.js or Java containers on these nodes.
   * `arm10` (Control Plane) has **10 GB RAM**. All relational databases, AI vector runtimes, and observability TSDBs must be pinned to `arm10` (`nodeSelector: kubernetes.io/hostname: arm10`).
2. **GitOps & Deployment Rule**:
   * Do not run ad-hoc manual `docker run` commands on production nodes. All workloads must be codified in [`charts/vinhthang-fleet/`](../charts/vinhthang-fleet/) or [`k8s/`](../k8s/) and pushed to `main`.
3. **Single Sign-On Requirement**:
   * Any new web dashboard or administrative interface must be placed behind Caddy Google OAuth2 Forward-Auth (`auth.vinhthang.dev`) to prevent credential sprawl and public exposure.
4. **Disaster Recovery**:
   * All stateful host directories are located under `/opt/<service>` on the respective nodes and backed up daily via `nightly-fleet-backup`.
