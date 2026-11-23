# ADR-0060: Automated Webhook Rollout for Custom `ghcr.io/vinhthang/*` Services

* **Status**: 🟢 Accepted
* **Date**: 2026-11-23
* **Authors**: Thang Hoang & Antigravity

---

## Context

The in-cluster `gitops-webhook` controller (`ADR-0006`, hardened in `ADR-0042`) only reacted to GitHub `push` events targeting `refs/heads/main` of `vinhthang/oci`. When new container images were built and published for the fleet's five custom `ghcr.io/vinhthang/*` services (`vietcalendar`, `collab-mcp`, `review-server`, `attention-metrics-server`, `ai-incident-commander`)—whether via GitHub Actions, Forgejo CI (`git.vinhthang.dev`), or local `docker buildx push`—rollouts did not happen automatically unless `vinhthang/oci` was manually edited and reconciled.

In addition, running `helm upgrade --install fleet` without `--reset-values` allowed stale persisted `USER-SUPPLIED VALUES` from earlier `--set` runs to silently shadow `charts/vinhthang-fleet/values.yaml`.

## Decision

1. **Extend `gitops-webhook` (`charts/vinhthang-fleet/files/receiver.py`)**:
   - Serve `GET`/`HEAD` `/healthz` and `/` probes, HMAC-authenticated GitHub webhooks on `POST /` and `POST /webhook` (`push` + `package`/`registry_package` events), and Bearer- or HMAC-authenticated `POST /deploy` requests for Forgejo CI and local build scripts.
   - Enforce a strict 5-service allowlist (`vietcalendar`, `collab-mcp`, `review-server`, `attention-metrics-server`, `ai-incident-commander`), `1 MB` maximum request body, regex validation on `tag` and `sha256` `digest`, and `subprocess.run` argument lists with zero shell interpolation.
2. **Hybrid Mutable-`:latest` + Explicit Tag/Digest Rollout via Helm**:
   - Add optional `rolloutTimestamp` pod annotation (`vinhthang.dev/rollout-at`) and `.image.digest` support across all five custom workload templates.
   - For `:latest` + `imagePullPolicy: Always` workloads (`vietcalendar`), webhook triggers bump `rolloutTimestamp` so Kubelet immediately pulls new layers.
   - For tag/digest-pinned workloads (`collab-mcp`, `review-server`, `attention-metrics-server`, `ai-incident-commander`), webhook triggers apply the supplied `tag` or manifest `sha256` `digest` (including pinning the published digest when `:latest` is emitted by a GitHub `package` event).
3. **Smart GitOps Override Reconciliation (`--reset-values -f overrides.yaml`)**:
   - Persist active webhook overrides alongside each service's `baseline_git_image` at `/var/lib/gitops-webhook/state.json` (mounted from `/opt/gitops-webhook` on `arm10`).
   - Run all Helm upgrades with `--no-hooks --reset-values` (plus `-f <overrides>` when overrides are active). On `vinhthang/oci` `main` pushes, drop any service override whose `values.yaml` baseline changed in Git while preserving overrides for untouched services.
4. **CLI Trigger Helper**:
   - Provide `scripts/trigger-image-rollout.sh <service> [tag] [digest]` for local builds and Forgejo CI pipelines.

## Consequences

### Positive
* Zero-SSH automated image pulls and Helm rollouts across all 5 custom `ghcr.io/vinhthang/*` services via GitHub Packages webhooks or `POST /deploy`.
* Unrelated `vinhthang/oci` Git pushes never downgrade webhook-deployed images, while explicit `values.yaml` image bumps cleanly supersede webhook overrides.
* `USER-SUPPLIED VALUES` remain clean (`null`) because every reconcile uses `--reset-values`.

### Negative / Trade-offs
* Active webhook-only overrides live in `/opt/gitops-webhook/state.json` on `arm10` until the corresponding `values.yaml` baseline is updated in Git.
* Only the 5 explicitly allowlisted `ghcr.io/vinhthang/*` services can be rolled out through the webhook API.
