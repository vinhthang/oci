# ADR-0052: AI Review Server v0.2.0 — GitHub/GitLab PR Integration, Rulebooks & Retained Secret Hygiene

* **Status**: Accepted
* **Date**: 2026-11-18
* **Category**: AI / Security & Review Infrastructure
* **Amends**: [ADR-0051](0051-deploy-review-vinhthang-dev-server.md)

---

## Context

Following the initial deployment of `review.vinhthang.dev` (`v0.1.1`, ADR-0051), upgrading the platform to **`v0.2.0`** introduces on-demand GitHub PR and GitLab MR inspection/review (`POST /api/v1/pr/inspect`, `POST /api/v1/pr/review`, `POST /api/v1/pr/review/stream`), asynchronous GitHub/GitLab webhook automation (`POST /api/v1/webhook/github`, `POST /api/v1/webhook/gitlab`), repository base-branch rule auto-discovery, built-in methodology rule profiles (`SECURITY_OWASP`, `K8S_INFRA`, `CLEAN_ARCH_TDD`), and selectable **DeepSeek-V3 (`deepseek-chat`) / DeepSeek-R1 (`deepseek-reasoner`) / Gemini (`agy`)** quorum engines.

An infrastructure and security audit of the `v0.1.1` deployment identified four gaps that must be resolved declaratively in `oci`:
1. **Plaintext Bearer Fallback & Secret Retention**: `templates/review-server.yaml` previously defaulted `REVIEW_BEARER_TOKEN` to a hardcoded literal `"review-secret-token"`, and `gitops-webhook` runs `helm upgrade --install fleet ...` from Git without `--set` flags. Secrets must live in a `helm.sh/resource-policy: "keep"` Secret (`review-server-secrets`) referenced via `secretKeyRef`.
2. **Webhook Edge Bypass**: GitHub and GitLab webhook deliveries cannot pass Google OAuth2 Forward-Auth (`302` redirect) and require a dedicated Caddy `POST` route with a `10MB` request body cap and raw-body HMAC/token verification inside Fastify.
3. **Identity Header Spoof Prevention**: Both `@webhook` and `@api_auth` Caddy routes must strip incoming `X-Auth-Request-User` and `X-Auth-Request-Email` headers (`header_up -X-Auth-Request-*`) so external callers cannot impersonate SSO users to bypass Bearer verification.
4. **ADR-0051 Documentation Drift**: ADR-0051 referenced a stale Caddy reverse proxy upstream `10.0.0.216:8765` (actual NodePort upstream is `10.0.0.216:30015`) and non-existent model string `deepseek-v4.1-flash` (actual DeepSeek API models are `DeepSeek-V3 (deepseek-chat)` and `DeepSeek-R1 (deepseek-reasoner)`).

---

## Decision

1. **Amendments to ADR-0051**:
   - Correct Caddy reverse proxy upstream from `10.0.0.216:8765` to NodePort **`10.0.0.216:30015`** (pod container port remains **`8765`**).
   - Replace `deepseek-v4.1-flash` with **`DeepSeek-V3 (deepseek-chat)`** and **`DeepSeek-R1 (deepseek-reasoner)`**.
2. **Declarative Helm Secret Retention (`charts/vinhthang-fleet/templates/review-server.yaml` & `values.yaml`)**:
   - Pin `reviewServer.image.tag` to **`v0.2.0`** (pre-loaded into `arm10` K3s containerd `k8s.io`).
   - Add an optional Helm-managed `Secret` (`review-server-secrets` in `apps`) gated by `reviewServer.createSecret` (`false` in `values.yaml`) with `"helm.sh/resource-policy": "keep"`.
   - Remove the plaintext Bearer fallback entirely; inject `REVIEW_BEARER_TOKEN` (required) and optional `DEEPSEEK_API_KEY`, `GITHUB_TOKEN`, `GITLAB_TOKEN`, `GITHUB_WEBHOOK_SECRET`, and `GITLAB_WEBHOOK_SECRET` via `secretKeyRef`, plus `GITLAB_ALLOWED_HOSTS` (`gitlab.com` default).
3. **Hardened Caddy Ingress (`caddy/Caddyfile`)**:
   - Add `@webhook` (`method POST`, `path /api/v1/webhook/github /api/v1/webhook/gitlab`) before `@api_auth` with `request_body { max_size 10MB }`, `flush_interval -1`, and `header_up -X-Auth-Request-User` / `header_up -X-Auth-Request-Email` stripping.
   - Add `header_up -X-Auth-Request-User` and `header_up -X-Auth-Request-Email` stripping to `@api_auth` (`10.0.0.216:30015`).
4. **Application Security & Async Execution Invariants (`review-server` `v0.2.0`)**:
   - Enforce HTTPS-only allowlisted PR/MR URLs with private/loopback/cluster CIDR blocking and DNS rebinding checks; fence base-branch rules in `<repo_rules trust="untrusted_repository_data">` inside `userContent`.
   - Verify raw-body `X-Hub-Signature-256` / constant-time `X-Gitlab-Token` on webhooks, gate public-repo triggers by sender association/project membership, return `202 Accepted` onto a bounded worker queue (`MAX_CONCURRENT_JOBS = 2`), and serialize sanitized `agy` subprocesses (`MAX_CONCURRENT_AGY = 1`).

---

## Consequences

### Positive
* **Zero-Drift Secret Persistence**: `gitops-webhook` upgrades retain `review-server-secrets` across Git pushes without storing tokens in Git or falling back to hardcoded credentials.
* **Defense-in-Depth Perimeter**: External Bearer and webhook traffic can no longer inject forged `X-Auth-Request-*` headers, and webhook deliveries bypass SSO redirects cleanly for Fastify cryptographic verification.
* **Accurate Fleet Documentation**: ADR-0051's upstream NodePort (`30015`) and DeepSeek model identifiers are explicitly reconciled.

### Negative / Trade-offs
* **Initial One-Time Bootstrap**: Deploying to a fresh cluster requires a single bootstrap `helm upgrade` with `--set reviewServer.createSecret=true --set reviewServer.bearerToken=...` before reverting to clean GitOps upgrades (`createSecret: false`).
* **Optional Bot Credentials**: Webhook ingestion returns `503` and private repo inspections require a Web UI `gitToken` override until `GITHUB_WEBHOOK_SECRET`, `GITLAB_WEBHOOK_SECRET`, `GITHUB_TOKEN`, and `GITLAB_TOKEN` are populated in `review-server-secrets`.
