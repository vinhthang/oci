# ADR-0058: Private Forgejo Git Control Plane (`git.vinhthang.dev`) & Multi-Agent Fleet

* **Status**: Accepted
* **Date**: 2026-11-19
* **Category**: AI / GitOps & Multi-Agent Coordination Infrastructure
* **Amends**: [ADR-0053](0053-evolutionary-fleet-redesign-zero-trust-ingress-and-fitness-gates.md)

---

## Context

Coordinating multiple AI coding subscriptions and agents across separate physical workstations requires a central Git control plane with free per-agent identities, branch-level write enforcement, cross-agent PR reviews, and zero third-party API rate limits. Relying on external hosted SaaS organizations incurs per-seat costs for isolated bot accounts, while running external OAuth polling wrappers over consumer AI subscriptions violates provider Terms of Service.

---

## Decision

1. **Deploy Forgejo Rootless on `arm10` (`charts/vinhthang-fleet/templates/apps/forgejo.yaml`)**:
   - Pin `codeberg.org/forgejo/forgejo:17.0.2-rootless` (`linux/arm64`, UID/GID `1000:1000`) in namespace `apps` on `arm10`, bounded at `128Mi` request / `512Mi` limit, exposing HTTP container port `3000` (avoiding forbidden port `8080`) on NodePort **`30017`** with SSH disabled (`FORGEJO__server__DISABLE_SSH=true`, HTTPS-only).
   - Back application state with the shared PostgreSQL 18 cluster (`postgres-primary.data.svc.cluster.local:5432`, database `forgejo` initialized via `init-postgres-db`) and persist repositories/config under `/opt/forgejo/data` and `/opt/forgejo/config` (ownership prepared via `init-permissions`).
   - Lock down instance visibility (`DISABLE_REGISTRATION=true`, `REQUIRE_SIGNIN_VIEW=true`, `INSTALL_LOCK=true`) and default pull requests to `squash` merging.
   - Store administrative credentials and signing keys (`FORGEJO_ADMIN_USER`, `FORGEJO_ADMIN_PASSWORD`, `FORGEJO_SECRET_KEY`, `FORGEJO_INTERNAL_TOKEN`) in retained Secret `forgejo-secrets` (`"helm.sh/resource-policy": "keep"`), disabled by default (`forgejo.createSecret: false`) to render zero default Secrets.
2. **Expose `amd10` Edge TLS Ingress (`caddy/Caddyfile` — `git.vinhthang.dev`)**:
   - Reverse-proxy `git.vinhthang.dev` -> `10.0.0.216:30017` from `amd10` with `security_headers`, `strip_auth_headers`, `max_size 500MB`, and `flush_interval -1`. Point the `git.vinhthang.dev` DNS `A` record strictly to `amd10` (`152.70.101.162`, since `10.0.0.216:30017` is reachable only inside the private OCI VCN).
   - Omit cookie `sso_auth` so Git HTTPS and `/api/v1/*` personal token clients never hit HTTP 302 OAuth redirects, relying on Forgejo native authentication and `REQUIRE_SIGNIN_VIEW=true`.
3. **Nightly Backup & Cross-Agent Branch Governance**:
   - Mount `/opt/forgejo` (covering both `data/` repositories and `config/` state) read-only into `CronJob/nightly-fleet-backup` at `/backup-src/forgejo`.
   - Coordinate workstations via `forge-fleet` CLI branch protections (`main` push restricted to admin; `required_approvals >= 1` blocking self-approval; `merge_when_checks_succeed: true` auto-merge upon 2nd-agent approval) and `google-slot` repo partitioning.

---

## Consequences

### Positive
* Zero extra SaaS seat cost (`$0/mo` on `arm10` Always Free PAYG headroom) with free unlimited per-agent accounts and local worktree isolation.
* Hard branch-protection guardrails prevent agents from pushing directly to `main` or approving their own PRs.
* Automatic nightly archival of Forgejo PostgreSQL tables and `/opt/forgejo` (`data/` + `config/`).

### Negative / Trade-offs
* Requires a one-time `helm upgrade --no-hooks ... --set forgejo.createSecret=true` bootstrap (followed by reverting to `createSecret=false`), `amd10`-only DNS setup for `git.vinhthang.dev`, and `./scripts/gitops-sync.sh` (`--no-hooks`) execution by the operator.
