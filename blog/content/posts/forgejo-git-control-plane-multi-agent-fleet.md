---
title: "Coordinating Multi-Workstation Coding Agents at $0/Month: Our Rootless Forgejo Control Plane on git.vinhthang.dev"
author: "Thang Hoang & Antigravity"
date: "2026-11-22T19:00:00+07:00"
draft: false
showToc: true
TocOpen: true
categories: ["DevOps", "AI Engineering", "GitOps", "Security"]
tags: ["Forgejo", "Git", "Multi-Agent", "Kubernetes", "Worktrees", "Code Review", "PostgreSQL", "Always Free"]
---

Once you start running multiple AI coding agents—Antigravity, Claude, Codex, Qoder—across separate physical workstations on the same codebase, **Git becomes your distributed consensus bus**.

Relying on external hosted SaaS Git organizations for multi-agent coordination quickly runs into three walls:
1. **Per-seat bot billing**: Creating isolated identities for every agent role (`agy-mac1`, `claude-mac1`, `review-bot`) on commercial team plans multiplies seat fees.
2. **Third-party API rate limits**: Parallel workers polling issues, claiming tasks, updating PR statuses, and inspecting check runs burn through shared REST rate limits.
3. **Terms-of-Service & credential hygiene**: Wrapping consumer AI OAuth subscriptions in 24/7 external polling daemons violates provider Terms of Service, and sharing a single personal GitHub PAT across every autonomous worker destroys auditability—meaning any agent can push straight to `main` or approve its own PR.

In **`ADR-0058`**, we solved all three at `$0/month` by deploying a private, rootless **Forgejo 17** control plane at **`git.vinhthang.dev`** on `arm10`—wired directly over cluster-internal networking to `review-server` (`v0.5`+) so an automated `review-bot` gates every pull request before squash auto-merge.

---

## 1. Rootless Forgejo 17 on `arm10` Inside `512Mi` RAM

Our K3s control plane (`arm10`, 4 OCPUs, 24 GB RAM) runs inside an OCI private subnet (`10.0.1.0/24`) with plenty of headroom for lightweight Go binaries backed by our central PostgreSQL 18 cluster.

In `charts/vinhthang-fleet/templates/apps/forgejo.yaml`, Forgejo is pinned to **`codeberg.org/forgejo/forgejo:17.0.2-rootless`** (`linux/arm64`) with strict runtime and governance invariants:

* **Non-Root Security Context (`UID/GID 1000:1000`)**: An `initContainer` (`init-permissions`) prepares ownership on `/opt/forgejo/data` (`/var/lib/gitea`) and `/opt/forgejo/config` (`/etc/gitea`), while `init-postgres-db` idempotently provisions the `forgejo` database on `postgres-primary.data.svc.cluster.local:5432`.
* **Port Allocation Discipline**: Forgejo listens on HTTP port **`3000`** (NodePort **`30017`**), strictly avoiding forbidden port `8080`. SSH is disabled (`FORGEJO__server__DISABLE_SSH=true`) so every clone, push, and API call traverses HTTPS TLS.
* **Lockdown & Retained Secrets (`ADR-0052`)**: `INSTALL_LOCK=true`, `DISABLE_REGISTRATION=true`, `REQUIRE_SIGNIN_VIEW=true`, and `DEFAULT_MERGE_STYLE=squash` keep the instance private and history linear. Administrative passwords, `SECRET_KEY`, and `INTERNAL_TOKEN` live in retained Secret `forgejo-secrets` (`"helm.sh/resource-policy": "keep"`, `createSecret: false` by default).
* **Rootless `postStart` Bootstrap Gotcha**: In rootless Forgejo images, the active config path is governed by `GITEA_APP_INI` (`/var/lib/gitea/custom/conf/app.ini`). Our `postStart` hook polls `/api/healthz` and checks `CFG="${GITEA_APP_INI:-/var/lib/gitea/custom/conf/app.ini}"` before idempotently creating the initial admin user—avoiding config-path mismatches against `/etc/gitea/app.ini`.
* **Nightly Disaster Recovery**: Both `/opt/forgejo/data` and `/opt/forgejo/config` are mounted read-only into `CronJob/nightly-fleet-backup` alongside the PostgreSQL `forgejo` dump.

---

## 2. Why `git.vinhthang.dev` Omits Browser-Cookie `sso_auth`

Most dashboards on `*.vinhthang.dev` sit behind Caddy's `(sso_auth)` Google OAuth2 Forward-Auth snippet. Putting `git.vinhthang.dev` behind `(sso_auth)`, however, would instantly break every non-browser Git client:

When `git clone`, `git push`, or `forgejo-git-tool` calls `https://git.vinhthang.dev/api/v1/...` with an `Authorization: token ...` header or HTTP Basic credentials, a cookie-based `forward_auth` gate sees no `_oauth2_proxy` cookie and answers with **`HTTP 302` redirecting to `https://auth.vinhthang.dev/oauth2/start`**. Git CLI clients cannot complete an interactive Google OAuth browser login mid-push.

Instead, `caddy/Caddyfile` routes `git.vinhthang.dev` directly to `10.0.0.216:30017` with `max_size 500MB` for large packfiles, `flush_interval -1`, `(security_headers)`, and `(strip_auth_headers)`:

```caddy
# 20. Forgejo Private Git & Multi-Agent Control Plane (Native Token/Passkey Auth, REQUIRE_SIGNIN_VIEW=true)
git.vinhthang.dev {
    import security_headers

    request_body {
        max_size 500MB
    }

    reverse_proxy 10.0.0.216:30017 {
        import strip_auth_headers
        flush_interval -1
    }
}
```

Security rests cleanly on Forgejo's native boundary: `REQUIRE_SIGNIN_VIEW=true` blocks all unauthenticated web and API reads, `DISABLE_REGISTRATION=true` blocks external signups, and every agent authenticates with its own scoped Forgejo Personal Access Token (or passkey for human admin login). Note also that `git.vinhthang.dev`'s DNS `A` record points strictly to `amd10` (`152.70.101.162`), because private NodePort `10.0.0.216:30017` is reachable only inside the OCI VCN.

---

## 3. Disjoint Worktrees & Subscription Affinity (`forgejo-git-tool`)

Having a private Git server is only half the story; without task boundaries, two agents claiming issues in the same repository will collide on shared files or violate subscription boundaries.

Our `forgejo-git-tool` workflow enforces three mechanical guardrails:
1. **Disjoint `Owned Files:` Slicing**: Every issue created via `forgejo-git-tool issue-create` or batch `slice` declares explicit `Owned Files:` paths so parallel workers edit non-overlapping modules.
2. **Account Slot Affinity (`google-slot-*`)**: Repositories carry `google-slot-*` topics. `forgejo-git-tool claim` verifies that a personal Google Ultra account stays pinned strictly to its assigned slot without 24/7 polling daemons—while cross-vendor agents (Claude, Codex, Qoder) can review and contribute freely across any repo.
3. **Ephemeral Local Worktrees**: Claiming an `agent:ready` issue checks out a fresh branch inside an isolated local git worktree (`~/worktrees/<repo>`), keeping the workstation's primary working tree untouched while Red-Green-Refactor TDD runs.

---

## 4. In-Cluster `review-bot` Webhook & Squash Auto-Merge Loop

The killer feature of hosting Forgejo in the **same `apps` namespace** as `review-server` (`review.vinhthang.dev`) is sub-millisecond, zero-egress cluster-internal PR gating.

```text
  Workstation Agent (agy-mac1 / claude-mac1 / codex)
     │  1. Claims agent:ready issue -> isolated git worktree
     │  2. TDD Red-Green-Refactor + `forgejo-git-tool pr-create`
     ▼
  ┌────────────────────────────────────────────────────────────┐
  │  Forgejo 17 (:3000, arm10, main branch protected)          │
  │   - Direct pushes to `main` blocked                        │
  │   - required_approvals >= 1 (self-approval forbidden)      │
  └──────────────────────────┬─────────────────────────────────┘
                             │  3. Webhook POST (cluster-internal)
                             ▼  http://review-server.apps.svc.cluster.local:8765/api/v1/webhook/forgejo
  ┌────────────────────────────────────────────────────────────┐
  │  review-server (v1.0.1, apps namespace)                    │
  │   - Executes multi-agent CODE_REVIEW quorum                │
  │   - Calls back http://forgejo.apps.svc.cluster.local:3000  │
  └──────────┬───────────────────────────────────┬─────────────┘
             │  BLOCK (P0/P1 found)              │  PASS (P0=0, P1=0)
             ▼                                   ▼
   Posts `REQUEST_CHANGES`             `review-bot` posts `APPROVED`
   & labels `agent:changes-requested`  + executes squash `/merge`
                                       (FORGEJO_AUTO_MERGE_ON_PASS=true)
```

Notice the two-way cluster-internal wiring in `values.yaml` and `forgejo.yaml`:
* Forgejo explicitly permits internal webhooks via `FORGEJO__webhook__ALLOWED_HOST_LIST=review-server.apps.svc.cluster.local,external`.
* `review-server` talks back to Forgejo over `FORGEJO_INTERNAL_API_URL=http://forgejo.apps.svc.cluster.local:3000/api/v1` using `FORGEJO_BOT_USERNAME=review-bot` and `FORGEJO_AUTO_MERGE_ON_PASS=true`, while `FORGEJO_ALLOWED_HOSTS=git.vinhthang.dev` validates inbound webhook repository URLs.

No workstation agent has permissions to push to `main` or approve its own pull request. Code only lands on `main` as a clean squash commit after an independent agent—or the cluster-internal `review-bot` quorum—verifies tests and signs off. And because `review-server` itself mirrors its `main` branch to `https://git.vinhthang.dev/thang/review-server.git`, our Git control plane also doubles as an encrypted, nightly-backed-up off-GitHub mirror for core fleet repositories.
