---
title: "From CLI Plugin to Cloud Control Plane: Architecting review.vinhthang.dev v1.0 with Cordis, Multi-Agent Quorums, and Warm-Standby Supervisors"
author: "Vinh Thang"
date: "2026-11-20T21:00:00+07:00"
draft: false
showToc: true
TocOpen: true
categories: ["AI Engineering", "Code Review", "Architecture", "Security"]
tags: ["AI Review Server", "Cordis", "Multi-Agent", "DeepSeek", "Gemini", "Antigravity", "Zero-Trust", "Caddy", "Kubernetes"]
---

Earlier this autumn, we wrote about building a local [two-stage spec-driven AI code reviewer](/posts/two-stage-spec-driven-development-ai-review/) as an Antigravity CLI plugin. Local scripts got us surprisingly far—until we needed GitHub, GitLab, and Forgejo webhooks to trigger asynchronous multi-model critiques 24/7, share a persistent audit ledger across workstations, and evaluate translated chapters from our book pipeline without burning through personal CLI quotas.

A local plugin running inside a developer's laptop session cannot be a webhook receiver, a multi-round finite state machine, or a team-wide audit trail.

What followed was a rapid, four-ADR evolution (`ADR-0050` through `ADR-0059`) that took **`review.vinhthang.dev`** from an abandoned third-party prototype (`OpenMausBot`), through a clean-room Fastify server (`v0.1`–`v0.5`), into **`v1.0.1`**—a modular **Cordis 4.0.5 IoC monorepo** running on our 24 GB `arm10` K3s node with a warm-standby `stream-json` `agy` supervisor, non-root `UID 1000` runtime isolation, and cryptographic edge-to-pod SSO verification.

---

## 1. Why Clean-Room Won: Retiring `OpenMausBot` for `arm10`

Before building `review-server` from scratch, we briefly evaluated **OpenMausBot** (`ADR-0050`) as a multi-agent hub. In practice, retrofitting an interactive chat/agent broker into an autonomous CI/CD review server created friction everywhere: interactive device-pairing gates stalled automated pipelines, permission brokers blocked programmatic runs, and loopback restrictions fought our cluster networking.

In **`ADR-0051`**, we retired OpenMausBot completely and deployed a clean-room TypeScript/Node.js 22+ service (`review-server`) on `arm10`:
* **Dedicated Port Governance**: Container port **`8765`** exposed internally via ClusterIP and externally at NodePort **`30015`** (strictly avoiding forbidden port `8080`).
* **Bounded Footprint**: `100m`–`1000m` CPU and `256Mi`–`1024Mi` RAM on `arm10`, backed by the cluster's **PostgreSQL 18** database (`review_service` schema).
* **Orthogonal Model Quorum**: Pairing **DeepSeek (`deepseek-chat` for V3 and `deepseek-reasoner` for R1)** with **Google Gemini (`agy` CLI)** so independent architectures cross-check each other rather than echoing a single model's blind spots.

---

## 2. Multi-Stage Workstreams, `finding_ledger`, and the `skeptic-judge` FSM

Single-shot PR reviews (`v0.2.0`, `ADR-0052`) quickly revealed two weaknesses in real engineering workflows:
1. **Context loss across fix rounds**: When a developer pushes a remediation commit or submits a structured rebuttal, a stateless reviewer re-invents new nitpicks while forgetting whether earlier `P0`/`P1` blockers were actually resolved.
2. **Specialist noise**: Throwing every security, Kubernetes, architecture, and style prompt into one giant monolithic review inflates false positives and burns tokens.

In **`v0.3.0` (`ADR-0054`)**, we introduced **Multi-Agent Workstreams** and an explicit **Finite State Machine (FSM)**:

```text
  PR / Spec / Design / Translation Event
                   │
                   ▼
     ┌───────────────────────────┐
     │  Auto-Triage Classifier   │  (Bounded: maxSpecialistsPerRound = 4)
     └─────────────┬─────────────┘
                   │
                   ▼
     ┌───────────────────────────┐       P0/P1 Open       ┌──────────────────────────┐
     │  Parallel Specialist Run  │ ─────────────────────► │  REMEDIATION_REQUIRED    │
     │  (Blind Sanitized Diff)   │                        │  (Developer Fixes /      │
     └─────────────┬─────────────┘                        │   Structured Rebuttals)  │
                   │                                      └────────────┬─────────────┘
                   ▼                                                   │
     ┌───────────────────────────┐   Round >= maxRounds (3)            │
     │  skeptic-judge Arbiter    │ ──────────────────────────┐         │
     │  (Deduplicates & Filters  │                           ▼         │
     │   False Positives against │               ┌───────────────────────┐
     │   finding_ledger)         │ ◄─────────────│  ESCALATED_TO_HUMAN   │
     └─────────────┬─────────────┘  (/review     └───────────────────────┘
                   │                 retry)
                   ▼ P0=0, P1=0
     ┌───────────────────────────┐
     │ GOVERNANCE_CLEAN/APPROVED │
     └───────────────────────────┘
```

Three design invariants make this FSM reliable on a free-tier ARM64 node:
* **Sequential Workstream Stages**: A feature progresses cleanly through `SPEC_REVIEW` → `DESIGN_REVIEW` → `CODE_REVIEW` (plus isolated `TRANSLATION_REVIEW` workstreams added in `v0.4.0`), preventing implementation details from leaking backward into specification reviews.
* **Additive `finding_ledger`**: Findings live in PostgreSQL keyed by `UNIQUE(workstream_id, stage, finding_key)` alongside `agents`, `workstreams`, and `workstream_rounds`. Each round reconciles open findings against new diffs and developer rebuttals—and rolling back versions never requires destructive schema drops.
* **Hard Concurrency Ceilings**: `maxSpecialistsPerRound = 4`, `MAX_CONCURRENT_JOBS = 2`, and `MAX_CONCURRENT_AGY = 1` guarantee that a burst of PR pushes cannot OOM a 1024 MiB pod.

---

## 3. The `v1.0` Architecture Leap: Cordis 4.0.5 IoC & Warm-Standby `AgySupervisor`

By `v0.5.0`, our monolithic Fastify backend + Tailwind SPA was showing its age. Even worse, our `GeminiDriver` had a brutal operational flaw: it **cold-spawned `agy -p <prompt>` as a fresh subprocess on every single review turn**.

Cold-spawning caused four production headaches documented in **`ADR-0059`**:
1. **10–15 second cold-start latency** on every specialist or judge invocation.
2. **Linux `argv` `E2BIG` truncation risk** and prompt exposure in `ps aux` when passing large diffs on the command line.
3. **Missing sandbox flags** (`--sandbox --mode plan --disable-slash-commands`).
4. **Silent crash masking**: Crashed `agy` runs fell back to a deceptive `"No P0 regression observed"` string instead of failing loudly.

In **`v1.0.0` (`ADR-0059`, now running `v1.0.1`)**, we rebuilt the platform as a **Cordis 4.0.5 `pnpm` monorepo** (`@review-server/{cordis,cosmokit,schemastery}`) with reversible IoC plugin lifecycles, React-free snapshot stores, `--dsw-*` CSS Modules, and full backward compatibility for REST/SSE routes and `review-cli.ts` exit codes (`0/1/2/3`).

At the heart of `v1.0` sits **`AgySupervisorService`** (`AGY_MODE=supervisor`):

```text
  Review Turn Request
          │
          ▼  (AsyncSemaphore(1) — strict single-turn serialization)
  ┌──────────────────────────────────────────────────────────────┐
  │                 AgySupervisorService                         │
  │                                                              │
  │  Active Worker (stream-json NDJSON stdin/stdout)             │
  │    └─ agy --model gemini-3.8-flash-medium                    │
  │           --input-format stream-json                         │
  │           --output-format stream-json                        │
  │           --sandbox --mode plan --disable-slash-commands     │
  │    └─ Sanitized env: PATH, HOME, LANG, NODE_ENV only         │
  │                                                              │
  │  Pre-Warmed Standby Worker (Background Boot)                 │
  │    └─ Rotated in after AGY_MAX_TURNS_PER_WORKER=1            │
  │    └─ Preserves 100% blind isolation across review turns     │
  └──────────────────────────────────────────────────────────────┘
          │
          ▼  (Crash / Timeout -> Throws AgyExecutionError, zero fake passes)
```

Notice the crucial balance between **speed** and **blind isolation**:
* Keeping `AGY_MAX_TURNS_PER_WORKER=1` guarantees that one PR's code diff never contaminates the context window of the next review turn.
* Simultaneously pre-warming a standby `stream-json` worker in the background absorbs the cold-start cost (`AGY_STARTUP_TIMEOUT_MS=180000` for `arm10` load spikes, `AGY_TURN_TIMEOUT_MS=300000`, `AGY_MAX_TURN_DURATION_MS=420000`) before the next turn arrives.
* On public webhooks and `POST /api/v1/translate`, incoming `'gemini'` requests are rewritten to `'deepseek-v3'` (or return `403` unless `ALLOW_TRANSLATE_AGY=true`), protecting personal `arm10` `agy` quota from external abuse.

---

## 4. Four-Tier Zero-Trust Edge Ingress & Non-Root `UID 1000` Hardening

`review.vinhthang.dev` serves four distinct classes of callers on a single domain—human dashboard users, unauthenticated uptime probes/LLMs, CI/CLI automation, and external Git webhooks. Caddy partitions them cleanly in `caddy/Caddyfile`:

```caddy
review.vinhthang.dev {
    import security_headers

    # 1. Public discovery & health endpoints (spoof headers stripped)
    handle /api/health { ... }
    handle /llms.txt { ... }
    handle /assets/* { ... }

    # 2. Raw-body HMAC / token webhooks (GitHub, GitLab, Forgejo)
    @webhook {
        method POST
        path /api/v1/webhook/github /api/v1/webhook/gitlab /api/v1/webhook/forgejo
    }
    handle @webhook {
        request_body { max_size 10MB }
        reverse_proxy 10.0.0.216:30015 {
            import strip_auth_headers
            flush_interval -1
        }
    }

    # 3. CLI / CI Bearer Token API
    @api_auth {
        header Authorization "Bearer *"
        path /api/v1/*
    }
    handle @api_auth {
        reverse_proxy 10.0.0.216:30015 {
            import strip_auth_headers
            flush_interval -1
        }
    }

    # 4. Private Web UI behind Google OAuth2 SSO + Origin Shared Secret
    handle {
        import sso_auth
        reverse_proxy 10.0.0.216:30015 {
            header_up X-Proxy-Auth-Secret {$PROXY_AUTH_SECRET}
            flush_interval -1
        }
    }
}
```

Two hardening fixes from `ADR-0052` and `ADR-0059` closed subtle privilege-escalation paths:
1. **Closing Internal `X-Auth-Request-Email` Spoofing**: Anyone on the internal cluster or WireGuard mesh hitting NodePort `30015` directly could theoretically inject `X-Auth-Request-Email`. In `v1.0`, Caddy globally strips `X-Proxy-Auth-Secret` on all public routes (`(strip_auth_headers)`) and injects `{$PROXY_AUTH_SECRET}` only inside the `sso_auth` block. In `NODE_ENV=production`, `review-server` rejects any `X-Auth-Request-Email` without a constant-time matching `X-Proxy-Auth-Secret` with HTTP `401`.
2. **Non-Root `UID 1000:1000` Pod Security**: Early deployments ran as `root` against host `opc` (`1000:1000`) `.gemini` and `.config` mounts. The `v1.0` Helm Deployment enforces `runAsNonRoot: true`, `runAsUser: 1000`, `runAsGroup: 1000`, `fsGroup: 1000`, and mounts credentials cleanly into `/home/node/.gemini` and `/home/node/.config`.
3. **Retained Secret Hygiene (`ADR-0052`)**: Because our GitOps webhook runs `helm upgrade --install fleet ./charts/vinhthang-fleet` without `--set` flags, `values.yaml` sets `createSecret: false`, `createProxySecret: false`, and `createForgejoSecret: false`—rendering zero `Secret` manifests in default Helm templates while retaining live cluster secrets via `"helm.sh/resource-policy": "keep"`.

Combined with an off-machine mirror to our private Forgejo instance (`git.vinhthang.dev`), `review.vinhthang.dev` has grown from a local CLI experiment into a resilient, zero-trust, multi-agent code and specification governance engine running inside 1 GiB of RAM.
