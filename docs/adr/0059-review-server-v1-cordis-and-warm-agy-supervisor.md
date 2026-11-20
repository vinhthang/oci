# ADR-0059: `review-server` v1.0.0 Cordis Monorepo, Warm-Standby `AgySupervisor`, Non-Root UID 1000 & `X-Proxy-Auth-Secret` Hardening

* **Status**: Accepted
* **Date**: 2026-11-20
* **Category**: AI Review Platform, Ingress Security & Fleet Runtime Architecture
* **Amends**: [ADR-0051](0051-deploy-review-vinhthang-dev-server.md), [ADR-0054](0054-multi-agent-workstreams-and-multi-round-review-fsm.md), [ADR-0058](0058-deploy-forgejo-git-control-plane.md)

---

## Context

Inspection of `review-server` (`v0.5.0`) on `2026-11-20` identified six architectural, reliability, and security defects:

1. Legacy monolithic Fastify (`backend/`) + Tailwind SPA (`frontend/`) lacked Cordis IoC service isolation, reversible effect teardown, React-free snapshot stores, and full `Forgejo` / `TRANSLATION_REVIEW` frontend parity.
2. `GeminiDriver` cold-spawned `agy -p <prompt>` on every turn (`10–15s` startup overhead, Linux `argv` `E2BIG` cap, `ps aux` prompt visibility, missing `--sandbox --mode plan`), and masked process crashes behind a fake `"No P0 regression observed"` pass string.
3. `Deployment/review-server` ran as `root` inside the container against `opc` (`1000:1000`) host `.gemini`/`.config` directories.
4. `X-Auth-Request-Email` was trusted directly on internal HTTP port `30015` without verifying a proxy-to-origin shared secret.
5. `review-server` lacked an off-machine Git backup remote.
6. PR webhooks hitting `ESCALATED_TO_HUMAN` threw internal `409` failures without notifying PR authors or supporting `/review retry`.

---

## Decision

1. **Upgrade `reviewServer` to `ghcr.io/vinhthang/review-server:v1.0.0` (Cordis 4.0.5 `pnpm` Monorepo)**:
   - Migrate Host (`packages/host/*`, `apps/{server,cli}`) and Browser Client (`packages/client/*`, `apps/web` with `--dsw-*` CSS Modules) onto vendored `@review-server/{cordis,cosmokit,schemastery}`.
   - Preserve 100% REST/SSE/PostgreSQL `review_service` compatibility (additive `schema_migrations` ledger) and `cli/review-cli.ts` exit codes (`0/1/2/3`).
2. **Deploy Warm-Standby `stream-json` `AgySupervisorService` (`AGY_MODE=supervisor`, `AGY_MAX_TURNS_PER_WORKER=1`)**:
   - Execute `agy --model <m> --input-format stream-json --output-format stream-json --sandbox --mode plan --disable-slash-commands` under sanitized env (`PATH`, `HOME`, `LANG`, `NODE_ENV`), serialize active turns via `AsyncSemaphore(1)`, pre-warm a background standby worker on single-turn rotation for blind review isolation, and fail loudly via `AgyExecutionError` on crash/timeout.
   - Protect personal `arm10` `agy` quota by rewriting `'gemini'` -> `'deepseek-v3'` on public webhooks and defaulting `POST /api/v1/translate` to `'deepseek-v3'` (`403` for `'gemini'` unless `ALLOW_TRANSLATE_AGY=true`).
3. **Harden Pod Runtime to Non-Root `UID 1000:1000`**:
   - Configure `Deployment/review-server` `pod.securityContext` (`runAsNonRoot: true`, `runAsUser: 1000`, `runAsGroup: 1000`, `fsGroup: 1000`, `HOME=/home/node`) matching host `opc` (`1000:1000`), and relocate `host-gemini` / `host-config` volume mounts from `/root/*` to `/home/node/.gemini` and `/home/node/.config`.
4. **Synchronized `X-Proxy-Auth-Secret` Between Edge Caddy (`amd10` + `gce10`) & `review-server`**:
   - Strip spoofed `X-Proxy-Auth-Secret` globally in `(strip_auth_headers)` (`header_up -X-Proxy-Auth-Secret`).
   - Inject `header_up X-Proxy-Auth-Secret {$PROXY_AUTH_SECRET}` inside `review.vinhthang.dev`'s `sso_auth` `reverse_proxy 10.0.0.216:30015` block (`PROXY_AUTH_SECRET` sourced via Caddy systemd `EnvironmentFile`).
   - Wire `PROXY_AUTH_SECRET` in `Deployment/review-server` from retained Secret `review-proxy-auth-secret` (`"helm.sh/resource-policy": "keep"`, gated by `reviewServer.createProxySecret: false`). In `NODE_ENV=production`, `review-server` rejects `X-Auth-Request-Email` lacking a constant-time matching `X-Proxy-Auth-Secret` with `401`.
5. **Private Forgejo Backup**:
   - Mirror `review-server` `main` to private repository `https://git.vinhthang.dev/thang/review-server.git` (backed up nightly by `CronJob/nightly-fleet-backup`).

---

## Consequences

### Positive
* Eliminates `root` container privileges on host `agy` credentials and closes cluster/WireGuard `X-Auth-Request-Email` spoofing.
* Cuts `agy` turn latency via warm-standby `stream-json` while keeping each blind review strictly single-turn isolated (`AGY_MAX_TURNS_PER_WORKER=1`).
* Surfaces live `agy` worker PID/state/turns and one-click worker recycle in the `--dsw-*` Runtime Dashboard and `/api/v1/runtime/status`.

### Negative / Trade-offs
* `amd10` and `gce10` Caddy systemd services must hold matching `PROXY_AUTH_SECRET` environment entries alongside `Secret/review-proxy-auth-secret` on `arm10`; mismatched secrets reject SSO browser sessions with `401` while `Authorization: Bearer` API/CLI access remains unaffected.
