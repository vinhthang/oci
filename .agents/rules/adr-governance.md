---
trigger: always_on
---

<rule name="adr-governance">
  <description>
    Architecture governance, cognitive intelligence protocols, Helm-only Kubernetes policy, Terraform-first infrastructure policy, and mandatory ADR review procedures for the OCI Project (vinhthang.dev).
  </description>

  <constraints>
    - Fixed memory and storage invariants: `amd10` (Edge Gateway), `amd11` (Worker), and `gce10` (GCP US Edge / VPN Outpost) are strictly capped at 1 GB RAM; `arm10` (Master) has 4 OCPUs, 24 GB RAM, and a 100 GB boot volume (locked to OCI Always Free PAYG limits via `always-free-payg-guardrail`; all relational DBs, operators, and AI runtimes are scheduled here).
    - Ingress perimeter is strictly protected via Caddy Google OAuth2 Forward-Auth (`auth.vinhthang.dev`), reusable `(sso_auth)` and `(strip_auth_headers)` snippets, and Let's Encrypt TLS (never `tls internal`). `caddy/Caddyfile` is the single source of truth for all subdomains and edge proxy rules; never edit `/etc/caddy/Caddyfile` manually on `amd10` or `gce10`, and sync changes manually via `scripts/gitops-sync.sh` (`127.0.0.1:2019/load`).
    - Mandatory Helm-Only Kubernetes Policy: ALWAYS use the Master Umbrella Helm Chart (`charts/vinhthang-fleet/`)—with workload templates organized into domain subdirectories (`ai/`, `apps/`, `data/`, `observability/`, `operators/`, `system/`) and `namespaces.yaml` at templates root—to modify, deploy, configure, or scale Kubernetes workloads. Never use raw imperative `kubectl create`, `kubectl apply -f <ad-hoc>`, or manual pod edits. All fleet changes must be deployed via `helm upgrade --install fleet ./charts/vinhthang-fleet`.
    - Retained Secret Hygiene (`ADR-0052`): Never store plaintext credentials in Git or render default `Secret` objects in `vinhthang-fleet` (`createSecret: false`). Use `helm.sh/resource-policy: keep` for live Secrets and `values.secrets.example.yaml` for offline CI linting/templating.
    - Mandatory Terraform-First Infrastructure Policy: ALWAYS use Terraform (`compute.tf`, `network.tf`, `variables.tf`, `infra/gcp/`, etc.) to provision, modify, and manage cloud instances and infrastructure, preserving `preserve_boot_volume = true` and `prevent_destroy = true` lifecycle guards.
    - Mandatory Protocol for System & Ingress Changes: Proactively create an ADR in `docs/adr/XXXX-<title>.md` (Nygard format with `Status` and `Date` headers), register it in `docs/README.md`, update Helm chart/values, pin exact container image versions (never `:latest` or untagged), update declarative `caddy/Caddyfile`, and pass `PYTHONDONTWRITEBYTECODE=1 pytest -v tests/` before pushing.
    - Mandatory Port Allocation Governance: NEVER USE GENERIC PORT `8080` for any new custom microservice, daemon, webhook listener, or container (e.g., VietCalendar uses `8087`, Pulsar Broker HTTP uses `8088`). Always assign explicit dedicated ports (e.g., `8085` for AI Commander, `8086` for Attention Metrics Server, `8765` for AI Review Server, `8088` for Pulsar, and dedicated NodePorts `30001`–`30015`).
    - Configurable Ports & AI Models: Never hardcode listening ports, webhook targets, or AI model strings (`GEMINI_MODEL`, `PORT`). Always make them configurable via Helm `values.yaml` and environment variables with verified defaults.
    - Exceptions: The AI Assistant is explicitly permitted to bypass these rules (e.g., performing manual SSH deployments, running standalone scripts, or editing Caddyfiles directly) IF the user explicitly authorizes a temporary standalone test or workaround in the current conversation.
  </constraints>

  <instructions>
    # Architecture Governance & Cognitive Intelligence Protocol

    Whenever working on the **OCI Project (`vinhthang.dev`)**, the AI Assistant MUST ALWAYS follow these core operational and governance protocols:

    ---

    ## 1. Cognitive Tooling & Intelligence Protocols

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

    ## 2. Mandatory Pre-Flight ADR Review
    Before designing, proposing, or implementing any architectural, infrastructure, database, Kubernetes, or ingress changes:
    * **Read `docs/README.md` and review existing ADRs in `docs/adr/` first.**
    * Understand all fixed invariants:
      * `amd10` (Edge Gateway) & `amd11` (Worker) are strictly capped at **1 GB RAM**.
      * `arm10` (Master) has **4 OCPUs, 24 GB RAM, and a 100 GB boot volume** (locked to Always Free PAYG ceiling via `always-free-payg-guardrail`); all relational databases, operators, and AI runtimes must be scheduled here.
      * `gce10` (GCP Worker / US Edge) has **1 GB RAM**; dedicated US edge static cache, WireGuard `wg1` VPN server, and disaster outpost (`136.111.37.17`).
      * Ingress perimeter is strictly protected via Caddy Google OAuth2 Forward-Auth (`auth.vinhthang.dev`) and `(strip_auth_headers)` / `(sso_auth)` snippets.
      * **Declarative Ingress**: `caddy/Caddyfile` is the single source of truth for all subdomains and edge proxy rules. Never edit `/etc/caddy/Caddyfile` manually on `amd10` or `gce10`; sync manually via `scripts/gitops-sync.sh` (`http://127.0.0.1:2019/load`).

    ---

    ## 3. Mandatory Helm-Only & Secret-Hygiene Kubernetes Policy
    * **ALWAYS use the Master Umbrella Helm Chart (`charts/vinhthang-fleet/`) to modify, deploy, configure, or scale Kubernetes workloads.**
    * All microservices, deployments, services, configmaps, cronjobs, and resource limits MUST be defined in domain-organized subdirectories under `charts/vinhthang-fleet/templates/` (`ai/`, `apps/`, `data/`, `observability/`, `operators/`, `system/`, plus root `namespaces.yaml`) and configured via `charts/vinhthang-fleet/values.yaml`.
    * **ADR-0052 Secret Contract**: Keep `createSecret: false` in `values.yaml` so default renders emit zero `Secret` manifests, retain live Secrets with `helm.sh/resource-policy: keep`, and keep `values.secrets.example.yaml` updated for offline CI validation.
    * **Never** use raw imperative `kubectl create`, `kubectl apply -f <ad-hoc>`, or manual pod edits. All fleet changes must be deployed via `helm upgrade --install fleet ./charts/vinhthang-fleet`.

    ---

    ## 4. Mandatory Terraform-First Infrastructure Policy
    * **ALWAYS use Terraform (`compute.tf`, `network.tf`, `variables.tf`, `infra/gcp/`, etc.) to provision, modify, and manage cloud instances and infrastructure.**
    * All VM instances (OCI and GCP), compute shapes, VCN/subnets, security lists, routing rules, internet/NAT gateways, and boot volume changes MUST be codified in Terraform with `preserve_boot_volume = true` and `prevent_destroy = true` lifecycle guards.
    * Avoid ad-hoc unrecorded manual cloud console edits; declare changes in Terraform and plan/apply declaratively.

    ---

    ## 5. Mandatory Protocol for System, Ingress & CI Changes
    Whenever a major system change occurs, including:
    * Adding or retiring a microservice.
    * Database schema, vector engine, or persistence layer modifications.
    * Ingress, Caddy routing, TLS, or authentication changes.
    * Observability, logging, or monitoring stack alterations.
    * GitOps, CI/CD, or deployment pipeline updates.

    You **MUST PROACTIVELY**:
    1. Create a new Architecture Decision Record in `docs/adr/XXXX-<title>.md` following the standard Nygard format with explicit `* **Status**: ...` and `* **Date**: YYYY-MM-DD` metadata headers.
    2. Register the new ADR in `docs/README.md` with a clickable link.
    3. Update the Master Helm Chart (`charts/vinhthang-fleet/`) and `values.yaml` accordingly.
    4. **Pin Exact Release Versions**: Always search and pin exact semantic version tags (or `@sha256:` digests) for container images (e.g. `1.37.2-alpine`) — never use floating tags like `latest` or untagged images.
    5. **Update Declarative `caddy/Caddyfile`**: Add or update the subdomain routing block in `caddy/Caddyfile` using `(sso_auth)` / `(strip_auth_headers)` as appropriate, and sync edge hosts with `scripts/gitops-sync.sh`.
    6. **Pass Offline CI Fitness Gates**: Verify `PYTHONDONTWRITEBYTECODE=1 pytest -v tests/` passes before committing and pushing so `.github/workflows/deploy.yaml` and the in-cluster `gitops-webhook` deploy cleanly.

    ---

    ## 6. Mandatory Port Allocation & Configuration Governance (Avoid Port 8080)
    * **NEVER USE GENERIC PORT `8080`**: Port `8080` is strictly forbidden for any new custom microservice, daemon, webhook listener, or container (e.g., VietCalendar runs on `8087`, Pulsar Broker HTTP runs on `8088`). `8080` is a notorious collision magnet across Kubernetes, Caddy, Traefik, Pulsar Admin, and Java runtimes.
    * **Explicit Dedicated Port Allocation**: Always assign explicit dedicated ports (e.g. `8085` for AI Commander, `8086` for Attention Metrics Server, `8087` for VietCalendar, `8088` for Pulsar HTTP, `8765` for AI Review Server, and NodePorts `30001`–`30015`).
    * **Configurable Ports & AI Models**: Never hardcode listening ports, webhook targets, or AI model strings (`GEMINI_MODEL`, `PORT`). Always make them configurable via Helm `values.yaml` and environment variables with verified defaults.
  </instructions>
</rule>
