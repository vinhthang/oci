# ADR-0053: Evolutionary Fleet Redesign — Zero-Trust Edge Ingress, Declarative Secret Hygiene, Domain Chart Partitioning, and Offline Architectural Fitness Gates

* **Status**: 🟢 Accepted
* **Date**: 2026-11-18
* **Category**: Architecture / Security, CI/CD & Governance
* **Amends**: [ADR-0005](0005-master-helm-chart-and-self-healing-probes.md), [ADR-0012](0012-gitops-automated-edge-caddyfile-sync.md), [ADR-0018](0018-cluster-wide-namespace-domain-partitioning.md)

---

## Context

A comprehensive security, infrastructure, and documentation audit of the **Vinh Thang Cloud & AI Fleet (`vinhthang.dev`)** identified structural drift across five areas:

1. **Edge Ingress & Local Proxy Trust Boundaries**:
   - Non-SSO reverse-proxy blocks in `caddy/Caddyfile` did not uniformly strip incoming `X-Auth-Request-User` and `X-Auth-Request-Email` headers, and duplicated SSO forward-auth blocks instead of reusing declarative snippets.
   - `status.vinhthang.dev` exposed Grafana administrative and exploration paths (`/login*`, `/admin*`, `/api/admin*`, `/explore*`), and `adguard.vinhthang.dev` lacked centralized Google OAuth2 Forward-Auth on its web dashboard.
   - `scripts/agy_proxy.py` needed strict `127.0.0.1` localhost default binding and non-blocking async subprocess discipline, while `network.tf` carried legacy rules referencing ports `8080` and `3000`.
2. **Helm Chart Secret Hygiene, Port Governance, and Template Organization**:
   - Plaintext credential fallbacks and default rendered `Secret` objects conflicted with the retained-secret contract introduced in `ADR-0052` (`helm.sh/resource-policy: "keep"`, `createSecret: false`, `values.secrets.example.yaml`).
   - `vietcalendar` still listened on port `8080` instead of a dedicated port (`8087`), `ClusterRole/gitops-deployer` used wildcard permissions, and `charts/vinhthang-fleet/templates/` held 28+ workload files flat at the template root rather than aligned with the cluster's namespace domains (`ai`, `apps`, `data`, `observability`, `operators`, `system`).
3. **Terraform & Edge Sync Script Drift**:
   - Legacy artifacts (`cloud-init.sh.tpl`, `k8s/`, `pulsar/`) remained in the root tree alongside `compute.tf` without `prevent_destroy` / `preserve_boot_volume` lifecycle guards or Terraform tracking for `gce10`.
   - `scripts/gitops-sync.sh` invoked `caddy reload`, which silently no-ops on `amd10` and `gce10` because the global `:2019` metrics block intercepts `localhost` (`::1`) ahead of the Admin API on `127.0.0.1:2019`.
4. **No Offline Automated Verification Gate**:
   - GitHub Actions (`.github/workflows/deploy.yaml`) linted and templated Helm charts, but lacked an automated offline fitness test suite to prevent regressions in Caddy security, Helm policies, Terraform invariants, and ADR/spec governance.
5. **Documentation, ADR, and Spec Drift**:
   - Stale architecture guides remained in `docs/`, ADR headers lacked uniform `Status` and `Date` metadata, `ADR-0049` carried a duplicate `# ADR-0048` heading, `ADR-0022` and `ADR-0026` remained marked Accepted despite supersession, root `README.md` and `.agents/rules/adr-governance.md` referenced obsolete `10 GB` `arm10` RAM, `main.tf`, and retired `Uptime Kuma`, and `docs/specs/` contained unredacted test credentials and missing Gate 1/Gate 2 tables.

---

## Decision

We execute a five-phase evolutionary redesign across ingress, Helm packaging, Terraform/scripts, CI fitness gates, and documentation governance:

1. **Zero-Trust Edge Ingress & Local Proxy Hardening**:
   - Introduce reusable `(strip_auth_headers)` and `(sso_auth)` snippets in `caddy/Caddyfile`, strip `X-Auth-Request-*` on all non-SSO routes, block `/login*`, `/admin*`, `/api/admin*`, and `/explore*` with `403` on `status.vinhthang.dev`, protect the AdGuard web dashboard with `import sso_auth` (keeping `/dns-query*` open for DoH), route `files.vinhthang.dev` to `10.0.0.216:30002` (`NodePort`), and forbid `tls internal`.
   - Enforce `127.0.0.1` default bind host, Bearer auth on `/v1/*`, and non-blocking async execution in `scripts/agy_proxy.py`, and remove legacy `8080`/`3000` security list ingress rules in `network.tf`.
2. **Helm Domain Partitioning, Secret Hygiene & Port Governance**:
   - Reorganize `charts/vinhthang-fleet/templates/` into domain subdirectories (`ai/`, `apps/`, `data/`, `observability/`, `operators/`, `system/`) with `namespaces.yaml` (`helm.sh/resource-policy: keep`) at the templates root.
   - Enforce zero default rendered `Secret` objects in `vinhthang-fleet` (`values.secrets.example.yaml` for CI/offline lint & template validation), zero plaintext credential fallbacks, exact pinned image tags (zero `:latest` or untagged images), zero `*` wildcards in `ClusterRole/gitops-deployer`, and dedicated port `8087` for `vietcalendar` / `8088` for Pulsar HTTP (zero custom `8080` workloads).
   - Harden `charts/vedge-api-local` (`"$db"` quoting in `db-init-job.yaml` and `readinessProbe` in `deployment.yaml`).
3. **Terraform & Edge Sync Script Alignment**:
   - Remove legacy `cloud-init.sh.tpl`, `k8s/`, and `pulsar/`.
   - Enforce `preserve_boot_volume = true` and `prevent_destroy = true` on `amd10`, `amd11`, and `arm10` in `compute.tf`, and codify `gce10` (`google_compute_instance` with `prevent_destroy = true`) under `infra/gcp/main.tf`.
   - Standardize `scripts/gitops-sync.sh` on manual edge Caddyfile sync to both `amd10` and `gce10` via Caddy Admin API (`http://127.0.0.1:2019/load`, removing `caddy reload`), and harden `scripts/trigger-gemini-indexer.sh` (`set -euo pipefail`, `-n system`).
4. **Offline Architectural Fitness Gates (`tests/` + CI)**:
   - Establish an offline `pytest` architectural fitness suite (`tests/test_caddy_security.py`, `tests/test_helm_policies.py`, `tests/test_terraform_and_scripts.py`, `tests/test_docs_and_specs_governance.py`) executed automatically in `.github/workflows/deploy.yaml` (`PYTHONDONTWRITEBYTECODE=1 pytest -v tests/`).
5. **Documentation, ADR & Spec Normalization**:
   - Prune duplicate root guides in `docs/`, normalize `Status`/`Date` metadata and supersession notes across `docs/adr/0001`–`0052`, fix `ADR-0049` numbering, mark `ADR-0022` and `ADR-0026` as `🔴 Deprecated`, normalize all 6 packages in `docs/specs/` (Gate 1/Gate 2 tables, secret redactions, `ADR-0049` references), and align `README.md`, `docs/README.md`, and `.agents/rules/adr-governance.md` with the current `4 OCPUs / 24 GB RAM / 100 GB` `arm10` architecture, `compute.tf` + `infra/gcp/`, and `30001`–`30015` NodePorts.

---

## Consequences

### Positive
* **Zero-Trust Perimeter**: Spoofed `X-Auth-Request-*` headers are stripped at the edge, administrative Grafana/AdGuard surfaces are locked down, and `tls internal` self-signed fallbacks are eliminated.
* **Repeatable Offline CI Gates**: Every push to `main` validates Helm rendering, image pinning, port governance, RBAC least privilege, Caddy snippets, Terraform lifecycle guards, and ADR/spec metadata in seconds without live cluster access.
* **Single Source of Truth**: Documentation, governance rules, Helm templates, and Terraform directories align 1:1 with the live multi-cloud fleet.

### Negative / Trade-offs
* **Manual Edge Sync Step**: Updating `caddy/Caddyfile` or Hugo blog content requires running `scripts/gitops-sync.sh` explicitly rather than relying on in-cluster `gitops-webhook` pushes to `amd10`/`gce10`.
* **Strict CI Guardrails**: Introducing new services or ADRs requires updating `values.secrets.example.yaml`, pinned tags, `docs/README.md`, and matching `tests/` invariants before CI passes.
