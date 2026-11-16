# ADR-0051: Deploy AI Review Server (`review.vinhthang.dev`) with Dual-Layer Ingress and Orthogonal Quorum

* **Status**: Accepted
* **Date**: 2026-11-16
* **Category**: AI / Ingress & Review Infrastructure

---

## Context

To automate rigorous code critiques and specification reviews across development workflows, we needed a dedicated, high-performance, unconstrained AI Review service on **`review.vinhthang.dev`** running on **`arm10`** (dedicated port **`8765`**, NodePort **`30015`**).

Rather than adopting complex third-party platforms with restrictive permission brokers, interactive pairing gates, and loopback blocklists (such as OpenMausBot), we established a clean-room TypeScript/Node.js architecture borrowing OpenMausBot's multi-engine LLM abstractions, Server-Sent Events (SSE) streaming, and responsive React dashboard while maintaining full autonomous execution.

The platform enforces:
1. **Two-Stage Spec-Driven Reviews**: Stage 1 (`spec-review` for WHAT/WHY, EARS syntax, and observable acceptance criteria) and Stage 2 (`design-review` for bidirectional plan-to-spec traceability and ADR invariants).
2. **Adversarial Multi-Model Quorum**: Independent, parallel review execution by **DeepSeek (`deepseek-v4.1-flash`)** and **Google Gemini (`gemini-3.8-flash-high` via host `agy` CLI)**, synthesizing findings under Ray Dalio's *Zero Error Suppression* principle (P0/P1 hard blockers vs P2/P3 advisory).
3. **Audit History Persistence**: Full review records and structured findings saved to the cluster's existing PostgreSQL 18 database on `arm10`.

---

## Decision

1. **Clean-Room Repository & Architecture (`github/review-server`)**:
   - Backend built with Fastify, TypeScript, Node.js 22+, and `@fastify/static`, serving REST/SSE endpoints on port `8765`.
   - Frontend built with React 19, Vite, and responsive dark-mode UI compiled to static assets served by the backend.
   - Dual-engine quorum driver registry (`deepseek` + `gemini`). Multi-account Gemini rotation is explicitly deferred (`GeminiAccountPool` stub).
   - In-memory database fallback to allow fully functional standalone operation even when PostgreSQL is disconnected.
2. **Helm-Only Kubernetes Fleet Deployment (`charts/vinhthang-fleet/`)**:
   - Codify `templates/review-server.yaml` scheduled in namespace `apps` on `arm10` (`nodeSelector: kubernetes.io/hostname: arm10`).
   - Assign dedicated non-conflicting port **`8765`** and NodePort **`30015`** (strictly avoiding port `8080` per governance rules).
   - Allocate resource bounds: `requests: { cpu: 100m, memory: 256Mi }`, `limits: { cpu: 1000m, memory: 1024Mi }`.
   - Connect to cluster PostgreSQL via `postgres-primary.data.svc.cluster.local:5432/review_service`.
3. **Declarative Dual-Layer Ingress (`caddy/Caddyfile`)**:
   - Expose `review.vinhthang.dev` through Caddy reverse proxy to `10.0.0.216:8765` with `flush_interval -1` for unbuffered SSE streaming.
   - Dual-layer security perimeter:
     - `/api/v1/*` with `Authorization: Bearer *` header is proxied directly for Antigravity, CLI, and CI/CD pipelines.
     - Web dashboard requests without API bearer headers are protected via Google OAuth2 Forward-Auth (`auth.vinhthang.dev`).

---

## Consequences

### Positive
* **Autonomous High-Performance Reviews**: Sub-second SSE streaming critiques and automated P0/P1 blocker detection without interactive consent card friction.
* **Orthogonal Cross-Verification**: Combining DeepSeek and Gemini eliminates hallucinations and ensures high-confidence architectural defect discovery.
* **Zero Host OOM Risk**: Capped at 1024 MiB RAM on `arm10` with self-healing liveness and readiness probes.
* **Unified Audit History**: Historical reviews and structured finding catalogs queryable from PostgreSQL 18.

### Negative / Trade-offs
* **DeepSeek Token Cost**: DeepSeek streaming requires a valid `DEEPSEEK_API_KEY` (simulated fallback activates if unconfigured).
* **Single Active Host Session**: Multi-account Gemini rotation is deferred to a future phase; Gemini execution relies on the active `agy` CLI session on the host.
