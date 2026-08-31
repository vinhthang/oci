# ADR-0012: GitOps Automated Edge Caddyfile Synchronization

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-26
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
Whenever new microservices or subdomains (such as `vault.vinhthang.dev`, `memos.vinhthang.dev`, or `ai.vinhthang.dev`) are introduced to the cluster, their ingress routing, reverse proxy targets, and authentication policies (Google OAuth2 forward_auth vs zero-knowledge client auth) were previously manually configured in `/etc/caddy/Caddyfile` on the Edge Gateway (`amd10`).

This manual step broke the GitOps paradigm, introduced latency, and created potential configuration drift between the Git repository and the live edge gateway.

---

## 2. Decision
We codified the edge gateway configuration and automated its synchronization directly through our GitOps pipeline:

1. **Declarative Master Caddyfile in Git**:
   * Created [`caddy/Caddyfile`](../../caddy/Caddyfile) in the root repository containing all subdomain definitions, TLS policies, SSO forward-auth blocks, and security headers.
2. **Automated Edge Deployment via GitOps**:
   * Updated the deployment synchronization pipeline ([`scripts/gitops-sync.sh`](../../scripts/gitops-sync.sh)) and the in-cluster GitOps webhook controller to automatically copy `caddy/Caddyfile` to `/etc/caddy/Caddyfile` on `amd10` (`152.70.101.162` / `10.0.0.235`) and execute `caddy reload`.
3. **Zero-Downtime Hot Reloading**:
   * Utilized Caddy's dynamic runtime reload API (`/usr/local/bin/caddy reload --config /etc/caddy/Caddyfile`), ensuring active TCP and WebSocket connections are never dropped during configuration updates.

---

## 3. Consequences

### Positive:
* **True Single Source of Truth**: 100% of cluster workloads, Helm values, and edge reverse-proxy routes are versioned and audited in Git.
* **Zero Manual Server Edits**: Provisioning a new subdomain now only requires defining its block in `caddy/Caddyfile` and pushing to `main`.
* **Zero Downtime**: Caddy performs graceful configuration reloads in milliseconds without dropping in-flight requests or certificate renewals.

### Negative / Trade-offs:
* Requires SSH or webhook reachability from the deployment pipeline to `amd10` over the private VCN.
