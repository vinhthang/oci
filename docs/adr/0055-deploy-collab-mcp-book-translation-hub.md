# ADR-0055: Book Collaboration MCP Hub (`collab.vinhthang.dev`) & `review-server` v0.4.0

* **Status**: Accepted
* **Date**: 2026-11-19
* **Category**: AI / Multi-Agent Translation & MCP Infrastructure
* **Amends**: [ADR-0054](0054-multi-agent-workstreams-and-multi-round-review-fsm.md)

---

## Context

Collaborative multi-agent book translation (`en -> vi` and `zh -> vi`) previously coupled engine code, translated book artifacts, and contributor authentication to GitHub Pull Requests inside `vinhthang/collab-book-translate`. Decoupling the corpus into `vinhthang/collab-books` (Option A) and enabling frictionless external AI agent participation—including a public **`ANONYMOUS`** role—requires:

1. **Standalone `collab-mcp` Hub (`https://collab.vinhthang.dev`)**: A Python 3.12 Streamable HTTP MCP (`/mcp`), SSE (`/sse`), REST (`/api/v1/*`), `/llms.txt`, and read-only HTML Bookshelf (`/`) service enforcing 3-tier authentication (`ANONYMOUS` with SHA-256 `revision_token`, self-serve `AGENT_KEY`, and `ADMIN`), sliding-window IP rate limits, deterministic XML/byte-invariance checks, and 4-class pre-LLM prompt-injection quarantine.
2. **`review-server` `v0.4.0` (`https://review.vinhthang.dev`)**: Isolated `TRANSLATION_REVIEW` workstreams (3 built-in Vietnamese translation specialists + `skeptic-judge` arbitration) and `POST /api/v1/translate` for `ch01` seeding and starved-chapter fallback.

---

## Decision

1. **Upgrade `review-server` to `v0.4.0`**:
   - Bump `reviewServer.image.tag` from `v0.3.1` to **`v0.4.0`** (`ghcr.io/vinhthang/review-server:v0.4.0`), pre-loaded into `arm10` K3s containerd (`k8s.io`).
2. **Deploy `collab-mcp` (`charts/vinhthang-fleet/templates/collab-mcp.yaml` & `values.yaml`)**:
   - Deploy `ghcr.io/vinhthang/collab-mcp:v0.1.0` (`IfNotPresent`) in namespace `apps` on `arm10`, container port **`8766`**, NodePort **`30016`**, bounded at `128Mi` request / `512Mi` limit.
   - Persist operational state in PostgreSQL (`collab_service` schema inside `review_service`) and mount `/opt/collab-mcp/data` (`/data`) for the synchronized `vinhthang/collab-books` git checkout.
   - Reuse `review-server-secrets` (`REVIEW_BEARER_TOKEN`, `GITHUB_TOKEN`) for internal `http://review-server.apps.svc.cluster.local:8765` calls and `vinhthang/collab-books` pushes, and store `COLLAB_ADMIN_TOKEN` in a retained `collab-mcp-secrets` Secret (`"helm.sh/resource-policy": "keep"`).
3. **Dual-Edge Caddy Ingress (`caddy/Caddyfile` — `collab.vinhthang.dev`)**:
   - Route `/admin*` through Google OAuth2 Forward-Auth (`10.0.0.216:30004`) copying verified `X-Auth-Request-User` and `X-Auth-Request-Email` to `10.0.0.216:30016`.
   - Route public `/`, `/mcp*`, `/sse*`, `/messages*`, `/llms.txt`, `/api/llms.txt`, `/api/health`, and `/api/v1/*` directly to `10.0.0.216:30016` with `10MB` body cap, `flush_interval -1`, and mandatory `header_up -X-Auth-Request-User` / `header_up -X-Auth-Request-Email` spoof stripping.

---

## Consequences

### Positive
* **Zero-Credential Agent Onboarding**: External MCP clients connect directly to `https://collab.vinhthang.dev/mcp` as `ANONYMOUS` without GitHub accounts, while pre-LLM gates shield `review-server` LLM quotas.
* **Clean Secret & Resource Hygiene**: Zero plaintext tokens in Git, `512Mi` memory ceiling, non-8080 port `8766` / NodePort `30016`, and cluster-internal `review-server` calls.

### Negative / Trade-offs
* **One-Time Secret & Image Bootstrap**: Requires pre-loading `review-server:v0.4.0` and `collab-mcp:v0.1.0` into `arm10` containerd and a one-time `helm upgrade` with `collabMcp.createSecret=true` to initialize `collab-mcp-secrets`.
