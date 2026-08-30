---
trigger: always_on
---

# Architecture Governance & Cognitive Intelligence Protocol

Whenever working on the **OCI Project (`vinhthang.dev`)**, the AI Assistant MUST ALWAYS follow these core operational and governance protocols:

---

## 1. 🧠 Cognitive Tooling & Intelligence Protocols

### A. `sequential-thinking` (Deep Multi-Step Reasoning)
* **When to Use**: For non-trivial architectural decisions, complex debugging (e.g. crash loops, memory leaks, TLS handshake failures), and GitOps pipeline design.
* **Protocol**: Engage `sequentialthinking` to dynamically break down problems, formulate and test hypotheses, evaluate edge cases, and verify trade-offs before executing state-modifying actions.

### B. `superpowers` (Architecture & Deep Code Auditing)
* **When to Use**: During system reviews, refactoring, major version upgrades, or before merging significant infrastructure changes.
* **Protocol**: Apply `superpowers` methodologies:
  1. Map blast radius and component dependency matrices.
  2. Verify thread interruption, resource lifecycle (`AutoCloseable`, connection pools), and non-blocking I/O safety.
  3. Validate least-privilege RBAC, secret hygiene, and failure isolation.

### C. `context7` (Up-to-Date Documentation Engine)
* **When to Use**: When researching specific library versions, breaking API changes, or framework upgrades (e.g., Spring Boot, Kubernetes API deprecations, VictoriaMetrics/VictoriaLogs LogsQL syntax, Caddyfile directives).
* **Protocol**: Call `resolve-library-id` and `query-docs` to fetch verified, current upstream documentation rather than relying on stale memory.

### D. `server-filesystem` & Code Exploration
* **When to Use**: Deep directory traversals, inspect file trees, and manage structured codebase exploration.

---

## 2. 🏛️ Mandatory Pre-Flight ADR Review
Before designing, proposing, or implementing any architectural, infrastructure, database, Kubernetes, or ingress changes:
* **Read `docs/README.md` and review existing ADRs in `docs/adr/` first.**
* Understand all fixed invariants:
  * `amd10` (Edge Gateway) & `amd11` (Worker) are strictly capped at **1 GB RAM**.
  * `arm10` (Master) has **10 GB RAM**; all relational databases and AI runtimes must be scheduled here.
  * `gce10` (GCP Worker / US Edge) has **1 GB RAM**; dedicated US edge static cache and disaster outpost.
  * Ingress perimeter is strictly protected via Caddy Google OAuth2 Forward-Auth (`auth.vinhthang.dev`).
  * **Declarative Ingress**: `caddy/Caddyfile` is the single source of truth for all subdomains and edge proxy rules. Never edit `/etc/caddy/Caddyfile` manually on `amd10` or `gce10`.

---

## 3. ☸️ Mandatory Helm-Only Kubernetes Policy
* **ALWAYS use the Master Umbrella Helm Chart (`charts/vinhthang-fleet/`) to modify, deploy, configure, or scale Kubernetes workloads.**
* All microservices, deployments, services, configmaps, cronjobs, and resource limits MUST be defined in `charts/vinhthang-fleet/templates/` and configured via `charts/vinhthang-fleet/values.yaml`.
* **Never** use raw imperative `kubectl create`, `kubectl apply -f <ad-hoc>`, or manual pod edits. All changes must be deployed via `helm upgrade fleet ./charts/vinhthang-fleet`.

---

## 4. 🏗️ Mandatory Terraform-First Infrastructure Policy
* **ALWAYS try to use Terraform (`main.tf`, `variables.tf`, etc.) to provision, modify, and manage cloud instances and infrastructure.**
* All VM instances (OCI and GCP), compute shapes, VCN/subnets, security lists, routing rules, internet/NAT gateways, and boot volume changes MUST be codified in Terraform.
* Avoid ad-hoc unrecorded manual cloud console edits; declare changes in Terraform and plan/apply declaratively.

---

## 5. 📜 Mandatory Protocol for System & Ingress Changes
Whenever a major system change occurs, including:
* Adding or retiring a microservice.
* Database schema, vector engine, or persistence layer modifications.
* Ingress, Caddy routing, TLS, or authentication changes.
* Observability, logging, or monitoring stack alterations.
* GitOps, CI/CD, or deployment pipeline updates.

You **MUST PROACTIVELY**:
1. Create a new Architecture Decision Record in `docs/adr/XXXX-<title>.md` following the standard Nygard format (Context, Decision, Consequences).
2. Register the new ADR in `docs/README.md` with a clickable link.
3. Update the Master Helm Chart (`charts/vinhthang-fleet/`) and `values.yaml` accordingly.
4. **Pin Exact Release Versions**: Always search and pin exact semantic version tags for container images (e.g. `1.37.2-alpine`) — never use floating tags like `latest`.
5. **Update Declarative `caddy/Caddyfile`**: Add or update the subdomain routing block in `caddy/Caddyfile` for any new service.
6. Commit and push the changes so the in-cluster GitOps webhook can deploy both the Kubernetes workloads and edge Caddyfile automatically.

---

## 6. 🚫 Mandatory Port Allocation & Configuration Governance (Avoid Port 8080)
* **NEVER USE GENERIC PORT `8080`**: Port `8080` is strictly forbidden for any new custom microservice, daemon, webhook listener, or container. `8080` is a notorious collision magnet across Kubernetes, Caddy, Traefik, Pulsar Admin, and Java runtimes.
* **Explicit Dedicated Port Allocation**: Always assign explicit dedicated ports (e.g. `8085` for AI Commander, `8088`, or specific NodePort ranges `30001–30015`).
* **Configurable Ports & AI Models**: Never hardcode listening ports, webhook targets, or AI model strings (`GEMINI_MODEL`, `PORT`). Always make them configurable via Helm `values.yaml` and environment variables with verified defaults.

