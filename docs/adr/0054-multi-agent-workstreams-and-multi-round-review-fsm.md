# ADR-0054: AI Review Server v0.3.0 — Multi-Agent Workstreams, Auto-Triage & Multi-Round Review FSM

* **Status**: Accepted
* **Date**: 2026-11-18
* **Category**: AI / Multi-Agent Review & Workflow Governance
* **Amends**: [ADR-0052](0052-ai-review-server-github-gitlab-pr-integration.md)

---

## Context

`review.vinhthang.dev` (`v0.2.0`, ADR-0052) introduced GitHub/GitLab PR/MR inspection, webhook automation, rulebook discovery, and retained secret hygiene (`review-server-secrets`). However, `v0.2.0` executed single-shot reviews without persistent multi-stage workflows, specialist agent routing, cross-round finding reconciliation, or adversarial false-positive filtering.

Upgrading `review-server` to **`v0.3.0`** introduces:
1. **Dynamic Specialist Agent Registry & Auto-Triage**: Seven built-in agents (6 domain specialists plus `skeptic-judge`), CRUD endpoints (`/api/v1/agents`), and deterministic auto-triage (`POST /api/v1/triage`) bounded to `maxSpecialistsPerRound = 4` (`MAX_SPECIALISTS_PER_ROUND = 4`) plus `skeptic-judge` arbitration.
2. **Three-Stage Sequential Workstream & Multi-Round FSM**: Managed workstreams (`/api/v1/workstreams`) progressing across `SPEC_REVIEW` → `DESIGN_REVIEW` → `CODE_REVIEW` with bounded rounds (`maxRounds = 3` default), blind prompt sanitization, structured rebuttals, and explicit human escalation/override gates (`INIT`, `AUDIT`, `REMEDIATION_REQUIRED`, `GOVERNANCE_CLEAN`, `ESCALATED_TO_HUMAN`, `APPROVED`, `ABORTED`).
3. **Additive PostgreSQL Persistence (`review_service` schema)**: New tables `review_service.agents`, `review_service.workstreams`, `review_service.workstream_rounds`, and `review_service.finding_ledger` (with supporting indexes) created idempotently alongside existing `reviews` and `findings` tables.

---

## Decision

1. **Helm Image Upgrade (`charts/vinhthang-fleet/values.yaml`)**:
   - Bump `reviewServer.image.tag` from `v0.2.0` to **`v0.3.0`** (`ghcr.io/vinhthang/review-server:v0.3.0`), and subsequently to **`v0.3.1`** (`ghcr.io/vinhthang/review-server:v0.3.1`), pre-built and imported into `arm10` K3s containerd (`k8s.io`) before rollout (`pullPolicy: IfNotPresent`).
   - Preserve `port: 8765`, `nodePort: 30015`, `nodeSelector: arm10`, and `existingSecret: "review-server-secrets"` (`createSecret: false`).
2. **Additive Database Schema & Finding Ledger (`review_service`)**:
   - Apply idempotent DDL (`CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`) on startup for `review_service.agents`, `review_service.workstreams`, `review_service.workstream_rounds`, and `review_service.finding_ledger` (keyed by `UNIQUE(workstream_id, stage, finding_key)`).
   - Keep `review_service.reviews` and `review_service.findings` untouched so historical single-shot reviews and PR audit trails remain fully readable.
3. **Bounded Multi-Agent Execution & `skeptic-judge` Arbitration**:
   - Enforce `maxSpecialistsPerRound = 4` in both `auto` and `manual` triage modes, preserving `MAX_CONCURRENT_JOBS = 2` and `MAX_CONCURRENT_AGY = 1` resource ceilings on `arm10`.
   - Route specialist candidate findings, open ledger items, and developer rebuttals through `skeptic-judge` to dismiss false positives and maintain cross-round state transitions.
4. **Caddy Ingress & Retained Secret Continuity (`ADR-0052`)**:
   - Extend the `review.vinhthang.dev` configuration in `caddy/Caddyfile` for **`v0.3.1`** with explicit public `handle /llms.txt` and `handle /api/llms.txt` routes (mirroring `/api/health` and `/assets/*`) with `header_up -X-Auth-Request-User`, `header_up -X-Auth-Request-Email` spoof-header stripping and `flush_interval -1`, while retaining `@webhook` (`POST /api/v1/webhook/github`, `/api/v1/webhook/gitlab` with `10MB` cap and `header_up -X-Auth-Request-*`), `@api_auth` (`Bearer *` on `/api/v1/*` with `header_up -X-Auth-Request-*`), and Google OAuth2 Forward-Auth for the web dashboard.
   - Retain live Kubernetes Secret `review-server-secrets` (`"helm.sh/resource-policy": "keep"`) across GitOps Helm upgrades (`createSecret: false`).
5. **Zero-Data-Loss Rollback Plan to `v0.2.0`**:
   - Because all `v0.3.0` schema additions (`agents`, `workstreams`, `workstream_rounds`, `finding_ledger`) are strictly additive and leave `reviews` and `findings` backward-compatible, rolling back requires only reverting `reviewServer.image.tag` to `v0.2.0` in `charts/vinhthang-fleet/values.yaml` and running `helm upgrade --install fleet ./charts/vinhthang-fleet` — no database migrations or table drops are needed, and all `v0.3.0` workstream history remains safely preserved in PostgreSQL.

---

## Consequences

### Positive
* **Structured Multi-Round Governance**: Teams can drive spec, design, and code reviews through deterministic multi-round convergence with full finding-ledger traceability and false-positive filtering.
* **Bounded `arm10` Compute Footprint**: `maxSpecialistsPerRound = 4` and existing `MAX_CONCURRENT_AGY = 1` / `1024Mi` pod limits prevent concurrent LLM or `agy` resource exhaustion.
* **Zero-Friction GitOps & Safe Rollback**: Retained secrets and Caddy edge rules from ADR-0052 remain intact, and rollback to `v0.2.0` is instantaneous with zero data loss.

### Negative / Trade-offs
* **Increased Multi-Round Latency**: Running up to 4 specialists plus `skeptic-judge` across up to 3 rounds per stage increases end-to-end workstream latency and LLM token usage compared to single-shot `v0.2.0` reviews.
* **Local Image Pre-Load Requirement**: Because `ghcr.io/vinhthang/review-server:v0.3.0` uses `IfNotPresent` from `arm10`'s local containerd store, new tags must continue to be built and imported via `k3s ctr -n k8s.io images import` before updating `values.yaml`.
